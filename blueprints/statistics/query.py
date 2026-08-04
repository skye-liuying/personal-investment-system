"""统计分析 — 查询功能（GET /）"""

from datetime import date

from flask import render_template, request
from . import statistics_bp
from database import get_db
from paginate import paginate


@statistics_bp.route('/')
def query():
    db = get_db()
    cursor = db.cursor()

    code = request.args.get('code', '').strip()
    name = request.args.get('name', '').strip()
    code_id_search = request.args.get('code_id', '').strip()
    asset_type_search = request.args.get('asset_type', '').strip()
    status = request.args.get('status', '').strip()

    # —— 资产类型占比计算 ——
    cursor.execute("""
        SELECT
            asset_type,
            COALESCE(SUM(total_amount), 0) AS amount
        FROM (
            SELECT asset_type, total_amount FROM securities
            WHERE status = '持有' AND operation_type = '买入'
            UNION ALL
            SELECT asset_type, total_amount FROM otc_app
            WHERE status = '持有' AND operation_type = '买入'
        ) AS combined
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

    # —— 按 Code 汇总（证券+场外 合并），含搜索/分页 ——
    where_clauses = []
    params = []

    if code:
        where_clauses.append('(stock_code LIKE %s)')
        params.append(f'%{code}%')
    if name:
        where_clauses.append('(stock_name LIKE %s)')
        params.append(f'%{name}%')
    if code_id_search:
        where_clauses.append('(IFNULL(code_id, \'\') LIKE %s)')
        params.append(f'%{code_id_search}%')
    if asset_type_search:
        where_clauses.append('(asset_type = %s)')
        params.append(asset_type_search)
    if status:
        where_clauses.append('(status = %s)')
        params.append(status)

    inner_where = (' AND ' + ' AND '.join(where_clauses)) if where_clauses else ''

    # 对 otc_app 分支，列名不同，所以用单独的 where
    otc_where_clauses = []
    otc_params = []

    if code:
        otc_where_clauses.append('(product_code LIKE %s)')
        otc_params.append(f'%{code}%')
    if name:
        otc_where_clauses.append('(product_name LIKE %s)')
        otc_params.append(f'%{name}%')
    if code_id_search:
        otc_where_clauses.append('(IFNULL(code_id, \'\') LIKE %s)')
        otc_params.append(f'%{code_id_search}%')
    if asset_type_search:
        otc_where_clauses.append('(asset_type = %s)')
        otc_params.append(asset_type_search)
    if status:
        otc_where_clauses.append('(status = %s)')
        otc_params.append(status)

    otc_inner_where = (' AND ' + ' AND '.join(otc_where_clauses)) if otc_where_clauses else ''

    # 合并子查询
    combined_sql = f"""
        SELECT stock_code AS code, IFNULL(code_id, '') AS code_id, stock_name AS name, asset_type, '持有' AS status,
               COALESCE(SUM(total_amount), 0) AS amount
        FROM securities
        WHERE status = '持有' AND operation_type = '买入'
        {f'AND {inner_where}' if inner_where else ''}
        GROUP BY stock_code, stock_name, asset_type, IFNULL(code_id, '')
        UNION ALL
        SELECT product_code AS code, IFNULL(code_id, '') AS code_id, product_name AS name, asset_type, '持有' AS status,
               COALESCE(SUM(total_amount), 0) AS amount
        FROM otc_app
        WHERE status = '持有' AND operation_type = '买入'
        {f'AND {otc_inner_where}' if otc_inner_where else ''}
        GROUP BY product_code, product_name, asset_type, IFNULL(code_id, '')
    """

    all_params = params + otc_params

    # 分页
    p = paginate()
    count_sql = f'SELECT COUNT(*) AS cnt FROM ({combined_sql}) AS combined'
    p['total'] = cursor.execute(count_sql, all_params)
    if p['total'] > 0:
        p['total'] = cursor.fetchone()['cnt']

    p['total_pages'] = (p['total'] + p['per_page'] - 1) // p['per_page'] if p['total'] > 0 and p['per_page'] > 0 else (1 if p['total'] > 0 else 0)
    p['has_prev'] = p['page'] > 1
    p['has_next'] = p['page'] < p['total_pages']

    query_sql = f"""
        SELECT * FROM ({combined_sql}) AS combined
        ORDER BY code
        LIMIT {p["per_page"]} OFFSET {p["offset"]}
    """
    cursor.execute(query_sql, all_params)
    code_stats = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('statistics.html',
                           type_stats=type_stats,
                           total=total,
                           code_stats=code_stats,
                           pagination=p,
                           today=date.today().isoformat())
