"""场外APP管理蓝图"""

from flask import Blueprint

otc_app_bp = Blueprint('otc_app', __name__)


def get_overview(db, where_clauses=None, params=None):
    """获取场外APP管理概览统计数据，支持传入查询条件（数据隔离）"""
    cursor = db.cursor()

    # 附加条件（如 user_id = %s），用于数据隔离；admin 不传则为空
    extra_where = ''
    extra_args = ()
    if where_clauses:
        extra_where = ' AND ' + ' AND '.join(where_clauses)
        extra_args = tuple(params) if params else ()

    cursor.execute(
        "SELECT COALESCE(SUM(total_amount), 0) AS total "
        "FROM otc_app "
        "WHERE status = '持有' AND operation_type = '买入'" + extra_where,
        extra_args
    )
    row = cursor.fetchone()
    invest_total = float(row['total']) if row else 0

    cursor.execute(
        "SELECT COALESCE(SUM(total_amount), 0) AS total "
        "FROM otc_app "
        "WHERE operation_type = '利息' AND status = '持有'" + extra_where,
        extra_args
    )
    row = cursor.fetchone()
    interest_profit = float(row['total']) if row else 0

    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM otc_app WHERE status = '持有'" + extra_where,
        extra_args
    )
    row = cursor.fetchone()
    holding_count = row['cnt'] if row else 0

    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM otc_app WHERE status = '结清'" + extra_where,
        extra_args
    )
    row = cursor.fetchone()
    settled_count = row['cnt'] if row else 0

    cursor.close()
    return {
        'invest_total': invest_total,
        'interest_profit': interest_profit,
        'holding_count': holding_count,
        'settled_count': settled_count
    }


from . import query, add, delete, lookup  # noqa: E402, F401
