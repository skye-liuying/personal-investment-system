"""数据库连接模块"""

import pymysql
from config import Config

# 显式导入 cryptography，确保 PyMySQL 的 caching_sha2_password 认证可用
import cryptography  # noqa: F401


def get_db():
    """获取数据库连接"""
    return pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        db=Config.MYSQL_DB,
        port=Config.MYSQL_PORT,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
