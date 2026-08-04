"""本金管理蓝图"""

from flask import Blueprint

principal_bp = Blueprint('principal', __name__)


def get_overview(db, where_clauses=None, params=None):
    """获取本金管理概览统计数据，支持传入查询条件"""
    cursor = db.cursor()

    sql = """
        SELECT
            COALESCE(SUM(CASE WHEN operation_type = '充值' THEN amount ELSE 0 END), 0) AS total_recharge,
            COALESCE(SUM(CASE WHEN operation_type = '取现' THEN amount ELSE 0 END), 0) AS total_withdraw
        FROM principal
    """
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    cursor.execute(sql, tuple(params) if params else ())
    row = cursor.fetchone()
    total_recharge = float(row['total_recharge']) if row else 0
    total_withdraw = float(row['total_withdraw']) if row else 0
    net_principal = total_recharge - total_withdraw

    cursor.close()
    return {
        'total_recharge': total_recharge,
        'total_withdraw': total_withdraw,
        'net_principal': net_principal
    }


# 必须在 __init__.py 末尾导入子模块，以注册路由
from . import query, add, delete, edit  # noqa: E402, F401
