"""证券管理蓝图"""

from flask import Blueprint

securities_bp = Blueprint('securities', __name__)


def get_overview(db, scope_sql=None, scope_params=None):
    """获取证券管理概览统计数据（仅受数据隔离约束，对齐目标页记录数）

    - holding_count：= 统计分析页（status='持有'）显示的记录数（statistics_summary 按关联编号分组后的行数）
    - settled_count：= 结清查询页显示的记录数（settlements 表总行数）
    - holding_total / interest_profit：全局持有总投入 / 已获利息（securities 明细口径）
    """
    cursor = db.cursor()

    extra_where = (' AND ' + scope_sql) if scope_sql else ''
    extra_args = tuple(scope_params) if scope_params else ()

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

    # 持有中数量 = 统计分析页（status='持有'）记录数：statistics_summary 按关联编号分组后的行数
    cursor.execute(
        "SELECT COUNT(*) AS cnt "
        "FROM statistics_summary "
        "WHERE status = '持有'" + extra_where,
        extra_args
    )
    row = cursor.fetchone()
    holding_count = row['cnt'] if row else 0

    # 已结清数量 = 结清查询页记录数：settlements 表总行数
    cursor.execute(
        "SELECT COUNT(*) AS cnt "
        "FROM settlements" + (' WHERE ' + scope_sql if scope_sql else ''),
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


from . import query, add, delete, edit, lookup_name  # noqa: E402, F401
