"""证券管理蓝图"""

from flask import Blueprint

securities_bp = Blueprint('securities', __name__)


def get_overview(db):
    """获取证券管理概览统计数据"""
    cursor = db.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS total
        FROM securities
        WHERE status = '持有' AND operation_type = '买入'
    """)
    row = cursor.fetchone()
    holding_total = float(row['total']) if row else 0

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS total
        FROM securities
        WHERE operation_type = '利息'
    """)
    row = cursor.fetchone()
    interest_profit = float(row['total']) if row else 0

    cursor.execute("SELECT COUNT(DISTINCT stock_code) AS cnt FROM securities WHERE status = '持有'")
    row = cursor.fetchone()
    holding_count = row['cnt'] if row else 0

    cursor.execute("SELECT COUNT(DISTINCT code_id) AS cnt FROM securities WHERE status = '结清' AND code_id IS NOT NULL")
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
