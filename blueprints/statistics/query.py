"""统计分析 — 查询功能（GET /），从 statistics_summary 表读取"""

from datetime import date

from flask import render_template, request
from . import statistics_bp
from database import get_db
from paginate import paginate
from blueprints.auth.helpers import scope_condition


@statistics_bp.route('/')
def query():
    db = get_db()
    cursor = db.cursor()

    # 数据隔离：普通用户只看自己的数据，admin 看全部
    scope_sql, scope_params = scope_condition()

    code = request.args.get('code', '').strip()
    name = request.args.get('name', '').strip()
    code_id_search = request.args.get('code_id', '').strip()
    asset_type_search = request.args.get('asset_type', '').strip()
    status = request.args.get('status', '').strip()

    # —— 资产类型占比计算（从 statistics_summary 查询） ——
    if scope_sql:
        cursor.execute("""
            SELECT
                asset_type,
                COALESCE(SUM(holding_amount), 0) AS amount
            FROM statistics_summary
            WHERE status = '持有' AND """ + scope_sql + """
            GROUP BY asset_type
        """, scope_params)
    else:
        cursor.execute("""
            SELECT
                asset_type,
                COALESCE(SUM(holding_amount), 0) AS amount
            FROM statistics_summary
            WHERE status = '持有'
            GROUP BY asset_type
        """)
    raw_type_stats = cursor.fetchall()
    total = sum(float(row['amount']) for row in raw_type_stats)
    type_stats = []
    for row in raw_type_stats:
        amt = float(row['amount'])
        ratio = round(amt / total * 100, 1) if total > 0 else 0
        type_stats.append({
            'asset_type': row['asset_type'],
            'amount': amt,
            'ratio': ratio
        })

    # —— 按 Code 汇总查询 + 搜索/分页 ——
    where_clauses = []
    params = []

    if scope_sql:
        where_clauses.append(scope_sql)
        params.extend(scope_params)
    if code:
        where_clauses.append('(code LIKE %s)')
        params.append(f'%{code}%')
    if name:
        where_clauses.append('(name LIKE %s)')
        params.append(f'%{name}%')
    if code_id_search:
        where_clauses.append('(code_id LIKE %s)')
        params.append(f'%{code_id_search}%')
    if asset_type_search:
        where_clauses.append('(asset_type = %s)')
        params.append(asset_type_search)
    if status:
        where_clauses.append('(status = %s)')
        params.append(status)

    where_sql = ' AND '.join(where_clauses) if where_clauses else ''

    # 分页
    p = paginate()

    if where_sql:
        count_sql = f'SELECT COUNT(*) AS cnt FROM statistics_summary WHERE {where_sql}'
        p['total'] = cursor.execute(count_sql, params)
    else:
        p['total'] = cursor.execute('SELECT COUNT(*) AS cnt FROM statistics_summary')

    if p['total'] > 0:
        p['total'] = cursor.fetchone()['cnt']

    p['total_pages'] = (p['total'] + p['per_page'] - 1) // p['per_page'] if p['total'] > 0 and p['per_page'] > 0 else (1 if p['total'] > 0 else 0)
    p['has_prev'] = p['page'] > 1
    p['has_next'] = p['page'] < p['total_pages']

    query_sql = f"""
        SELECT code, code_id, name, asset_type, holding_amount AS amount, status, source
        FROM statistics_summary
        {f'WHERE {where_sql}' if where_sql else ''}
        ORDER BY code
        LIMIT {p["per_page"]} OFFSET {p["offset"]}
    """
    cursor.execute(query_sql, params)
    code_stats = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('statistics.html',
                           type_stats=type_stats,
                           total=total,
                           code_stats=code_stats,
                           pagination=p,
                           today=date.today().isoformat())
