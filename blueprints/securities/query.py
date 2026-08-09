"""证券管理 — 查询功能（GET /）"""

from flask import render_template, request
from . import securities_bp
from . import get_overview
from database import get_db
from paginate import paginate


@securities_bp.route('/')
def query():
    db = get_db()
    cursor = db.cursor()

    where_clauses = []
    params = []

    broker = request.args.get('broker', '').strip()
    stock_code = request.args.get('stock_code', '').strip()
    code_id = request.args.get('code_id', '').strip()
    stock_name = request.args.get('stock_name', '').strip()
    operation_type = request.args.get('operation_type', '').strip()
    asset_type = request.args.get('asset_type', '').strip()
    status = request.args.get('status', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    if broker:
        where_clauses.append('broker LIKE %s')
        params.append(f'%{broker}%')
    if stock_code:
        where_clauses.append('stock_code LIKE %s')
        params.append(f'%{stock_code}%')
    if code_id:
        where_clauses.append('code_id LIKE %s')
        params.append(f'%{code_id}%')
    if stock_name:
        where_clauses.append('stock_name LIKE %s')
        params.append(f'%{stock_name}%')
    if operation_type:
        where_clauses.append('operation_type = %s')
        params.append(operation_type)
    if asset_type:
        where_clauses.append('asset_type = %s')
        params.append(asset_type)
    if status:
        where_clauses.append('status = %s')
        params.append(status)
    if date_from:
        where_clauses.append('record_date >= %s')
        params.append(date_from)
    if date_to:
        where_clauses.append('record_date <= %s')
        params.append(date_to)

    # 默认只查持有状态；有搜索条件时查全部
    if not where_clauses:
        where_clauses.append("status = '持有'")

    where_sql = (' WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''

    # 排序：持有模式按股票代码分组，结清模式按关联编号分组，搜索模式按日期
    if len(where_clauses) == 1 and "status = '持有'" in where_clauses:
        order_by = 'stock_code, record_date DESC, id DESC'
    elif len(where_clauses) == 1 and "status = '结清'" in where_clauses:
        order_by = 'code_id, stock_code, record_date DESC, id DESC'
    elif status == '持有':
        order_by = 'stock_code, record_date DESC, id DESC'
    elif status == '结清':
        order_by = 'code_id, stock_code, record_date DESC, id DESC'
    else:
        order_by = 'record_date DESC, id DESC'

    p = paginate()
    cursor.execute(f'SELECT COUNT(*) AS cnt FROM securities{where_sql}', params)
    p['total'] = cursor.fetchone()['cnt']

    p['total_pages'] = (p['total'] + p['per_page'] - 1) // p['per_page'] if p['total'] > 0 and p['per_page'] > 0 else (1 if p['total'] > 0 else 0)
    p['has_prev'] = p['page'] > 1
    p['has_next'] = p['page'] < p['total_pages']

    cursor.execute(
        f'SELECT * FROM securities{where_sql} ORDER BY {order_by} '
        f'LIMIT {p["per_page"]} OFFSET {p["offset"]}',
        params
    )
    records = cursor.fetchall()
    cursor.close()
    db.close()

    overview = get_overview(get_db())

    return render_template('securities.html',
                           records=records,
                           pagination=p,
                           holding_total=overview['holding_total'],
                           interest_profit=overview['interest_profit'],
                           holding_count=overview['holding_count'],
                           settled_count=overview['settled_count'],
                           broker=broker,
                           stock_code=stock_code,
                           code_id=code_id,
                           stock_name=stock_name,
                           operation_type=operation_type,
                           asset_type=asset_type,
                           status=status,
                           date_from=date_from,
                           date_to=date_to)
