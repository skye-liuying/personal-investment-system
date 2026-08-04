"""数据库连接模块"""

import pymysql
from config import Config


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
