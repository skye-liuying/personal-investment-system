"""场外APP管理蓝图"""

from flask import Blueprint

otc_app_bp = Blueprint('otc_app', __name__)


def get_overview(db):
    """获取场外APP管理概览统计数据"""
    cursor = db.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS total
        FROM otc_app
        WHERE status = '持有' AND operation_type = '买入'
    """)
    row = cursor.fetchone()
    invest_total = float(row['total']) if row else 0

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS total
        FROM otc_app
        WHERE operation_type = '利息'
    """)
    row = cursor.fetchone()
    interest_profit = float(row['total']) if row else 0

    cursor.execute("SELECT COUNT(*) AS cnt FROM otc_app WHERE status = '持有'")
    row = cursor.fetchone()
    holding_count = row['cnt'] if row else 0

    cursor.execute("SELECT COUNT(*) AS cnt FROM otc_app WHERE status = '结清'")
    row = cursor.fetchone()
    settled_count = row['cnt'] if row else 0

    cursor.close()
    return {
        'invest_total': invest_total,
        'interest_profit': interest_profit,
        'holding_count': holding_count,
        'settled_count': settled_count
    }


from . import query, add, delete  # noqa: E402, F401
