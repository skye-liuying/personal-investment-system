"""结清查询 — 查询功能（GET /）"""

from flask import render_template, request
from . import settlement_bp
from database import get_db
from paginate import paginate


@settlement_bp.route('/')
def query():
    db = get_db()
    cursor = db.cursor()

    where_clauses = []
    params = []

    code = request.args.get('code', '').strip()
    code_id = request.args.get('code_id', '').strip()
    product_name = request.args.get('product_name', '').strip()
    asset_type = request.args.get('asset_type', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    if code:
        where_clauses.append('code LIKE %s')
        params.append(f'%{code}%')
    if code_id:
        where_clauses.append('IFNULL(code_id, \'\') LIKE %s')
        params.append(f'%{code_id}%')
    if product_name:
        where_clauses.append('product_name LIKE %s')
        params.append(f'%{product_name}%')
    if asset_type:
        where_clauses.append('asset_type = %s')
        params.append(asset_type)
    if date_from:
        where_clauses.append('settle_date >= %s')
        params.append(date_from)
    if date_to:
        where_clauses.append('settle_date <= %s')
        params.append(date_to)

    where_sql = (' WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''

    # 概览统计
    overview_sql = f'SELECT COUNT(*) AS cnt, COALESCE(SUM(invest_amount), 0) AS invest_total, COALESCE(SUM(profit), 0) AS total_profit, COALESCE(SUM(fees), 0) AS total_fees FROM settlements{where_sql}'
    cursor.execute(overview_sql, params)
    overview = cursor.fetchone()
    settle_count = overview['cnt'] if overview else 0
    settle_total = float(overview['invest_total']) if overview else 0
    total_profit = float(overview['total_profit']) if overview else 0
    total_fees = float(overview['total_fees']) if overview else 0
    avg_return = (total_profit / settle_total * 100) if settle_total > 0 else 0

    # 分页
    p = paginate()
    count_sql = f'SELECT COUNT(*) AS cnt FROM settlements{where_sql}'
    p['total'] = cursor.execute(count_sql, params)
    if p['total'] > 0:
        p['total'] = cursor.fetchone()['cnt']

    p['total_pages'] = (p['total'] + p['per_page'] - 1) // p['per_page'] if p['total'] > 0 and p['per_page'] > 0 else (1 if p['total'] > 0 else 0)
    p['has_prev'] = p['page'] > 1
    p['has_next'] = p['page'] < p['total_pages']

    cursor.execute(
        f'SELECT * FROM settlements{where_sql} ORDER BY settle_date DESC, id DESC '
        f'LIMIT {p["per_page"]} OFFSET {p["offset"]}',
        params
    )
    records = cursor.fetchall()
    cursor.close()
    db.close()

    return render_template('settlement.html',
                           records=records,
                           pagination=p,
                           settle_count=settle_count,
                           settle_total=settle_total,
                           total_profit=total_profit,
                           total_fees=total_fees,
                           avg_return=avg_return,
                           code_id=code_id,
                           code=code,
                           product_name=product_name,
                           asset_type=asset_type,
                           date_from=date_from,
                           date_to=date_to)
