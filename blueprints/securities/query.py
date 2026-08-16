"""证券管理 — 查询功能（GET /）"""

from flask import render_template, request
from . import securities_bp
from . import get_overview
from database import get_db
from paginate import paginate
from blueprints.auth.helpers import scope_condition


@securities_bp.route('/')
def query():
    db = get_db()
    cursor = db.cursor()

    # 公共搜索条件（列表查询与概览统计共用；不含状态默认过滤）
    search_clauses = []
    search_params = []

    # 数据隔离：普通用户只看自己的数据，admin 看全部
    scope_sql, scope_params = scope_condition()
    if scope_sql:
        search_clauses.append(scope_sql)
        search_params.extend(scope_params)

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
        search_clauses.append('broker LIKE %s')
        search_params.append(f'%{broker}%')
    if stock_code:
        search_clauses.append('stock_code LIKE %s')
        search_params.append(f'%{stock_code}%')
    if code_id:
        search_clauses.append('code_id LIKE %s')
        search_params.append(f'%{code_id}%')
    if stock_name:
        search_clauses.append('stock_name LIKE %s')
        search_params.append(f'%{stock_name}%')
    if operation_type:
        search_clauses.append('operation_type = %s')
        search_params.append(operation_type)
    if asset_type:
        search_clauses.append('asset_type = %s')
        search_params.append(asset_type)
    if date_from:
        search_clauses.append('record_date >= %s')
        search_params.append(date_from)
    if date_to:
        search_clauses.append('record_date <= %s')
        search_params.append(date_to)

    # 列表查询条件：默认排除结清记录
    where_clauses = list(search_clauses)
    params = list(search_params)
    if status == '结清':
        where_clauses.append('status = %s')
        params.append(status)
    else:
        # 默认（含空/持有/其它搜索条件）排除结清记录
        where_clauses.append("status != '结清'")

    where_sql = (' WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''

    # 排序：统一按买入时间（操作日期）倒序，不做分组
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

    # 查询最新一笔记录的券商，供新增弹窗默认填充（组长范围为自己+组员）
    if scope_sql:
        cursor.execute(
            'SELECT broker FROM securities WHERE ' + scope_sql + ' ORDER BY id DESC LIMIT 1',
            scope_params
        )
    else:
        cursor.execute('SELECT broker FROM securities ORDER BY id DESC LIMIT 1')
    last_row = cursor.fetchone()
    last_broker = last_row['broker'] if last_row else ''

    cursor.close()

    overview = get_overview(db, scope_sql, scope_params)
    db.close()

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
                           date_to=date_to,
                           last_broker=last_broker)
