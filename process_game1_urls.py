import os
import urllib
import requests
import mysql.connector
from tqdm import tqdm
import time
import json
import re
from mysql.connector import Error

# 读取 GitHub Secrets（环境变量）
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_DATABASE')
}

BATCH_SIZE = 100  # 每批次处理的数量

def get_db_connection():
    """获取数据库连接"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        print("数据库连接成功")
        return connection
    except Error as e:
        print(f"数据库连接错误: {e}")
        return None

def get_openid_from_qq(access_token):
    """根据 access_token 请求获取 openid"""
    url = f"https://graph.qq.com/oauth2.0/me?access_token={access_token}"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            match = re.search(r'callback\((.*)\)', response.text)
            if match:
                json_data = json.loads(match.group(1))
                if "error" in json_data:
                    print(f"发生错误: {json_data}")
                    return None, None
                return json_data.get("openid"), json_data.get("client_id")
        print(f"请求失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"获取 openid 发生错误: {e}")

    return None, None

def process_batch(records):
    """批量处理记录"""
    connection = get_db_connection()
    if not connection:
        return

    cursor = connection.cursor()
    to_delete = []

    for record in records:
        access_token = record[0]
        print(f"处理记录: {access_token}")
        openid, _ = get_openid_from_qq(access_token)
        if openid is None:
            print(f"无效的 access_token，删除记录: {access_token}")
            to_delete.append((access_token,))
            continue

    # 批量删除
    if to_delete:
        delete_query = "DELETE FROM game1_urls WHERE access_token = %s"
        cursor.executemany(delete_query, to_delete)
        connection.commit()

    cursor.close()
    connection.close()

def main():
    """主程序"""
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute("SELECT access_token FROM game1_urls ORDER BY level DESC;")
        records = cursor.fetchall()

        with tqdm(total=len(records), desc="处理记录") as pbar:
            for i in range(0, len(records), BATCH_SIZE):
                batch = records[i:i + BATCH_SIZE]
                process_batch(batch)
                pbar.update(len(batch))

        cursor.close()
        connection.close()
    else:
        print("数据库连接失败，无法进行查询")

if __name__ == "__main__":
    main()