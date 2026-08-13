"""证券管理蓝图"""

from flask import Blueprint

securities_bp = Blueprint('securities', __name__)


def get_overview(db, where_clauses=None, params=None):
    """获取证券管理概览统计数据，支持传入查询条件（数据隔离）"""
    cursor = db.cursor()

    # 附加条件（如 user_id = %s），用于数据隔离；admin 不传则为空
    extra_where = ''
    extra_args = ()
    if where_clauses:
        extra_where = ' AND ' + ' AND '.join(where_clauses)
        extra_args = tuple(params) if params else ()

    cursor.execute(
        "SELECT COALESCE(SUM(total_amount), 0) AS total "
        "FROM securities "
        "WHERE status = '持有' AND operation_type = '买入'" + extra_where,
        extra_args
    )
    row = cursor.fetchone()
    holding_total = float(row['total']) if row else 0

    cursor.execute(
        "SELECT COALESCE(SUM(total_amount), 0) AS total "
        "FROM securities "
        "WHERE operation_type = '利息' AND status = '持有'" + extra_where,
        extra_args
    )
    row = cursor.fetchone()
    interest_profit = float(row['total']) if row else 0

    cursor.execute(
        "SELECT COUNT(DISTINCT stock_code) AS cnt "
        "FROM securities "
        "WHERE status = '持有'" + extra_where,
        extra_args
    )
    row = cursor.fetchone()
    holding_count = row['cnt'] if row else 0

    cursor.execute(
        "SELECT COUNT(DISTINCT code_id) AS cnt "
        "FROM securities "
        "WHERE status = '结清' AND code_id IS NOT NULL" + extra_where,
        extra_args
    )
    row = cursor.fetchone()
    settled_count = row['cnt'] if row else 0

    cursor.close()
    return {
        'holding_total': holding_total,
        'interest_profit': interest_profit,
        'holding_count': holding_count,
        'settled_count': settled_count
    }


from . import query, add, delete  # noqa: E402, F401
