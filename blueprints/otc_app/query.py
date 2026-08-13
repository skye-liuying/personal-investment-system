"""场外APP管理 — 查询功能（GET /）"""

from flask import render_template, request
from . import otc_app_bp
from . import get_overview
from database import get_db
from paginate import paginate
from blueprints.auth.helpers import scope_condition, get_current_user_id


@otc_app_bp.route('/')
def query():
    db = get_db()
    cursor = db.cursor()

    where_clauses = []
    params = []

    # 数据隔离：普通用户只看自己的数据，admin 看全部
    scope_sql, scope_params = scope_condition()
    if scope_sql:
        where_clauses.append(scope_sql)
        params.extend(scope_params)

    app_name = request.args.get('app_name', '').strip()
    product_code = request.args.get('product_code', '').strip()
    code_id = request.args.get('code_id', '').strip()
    product_name = request.args.get('product_name', '').strip()
    operation_type = request.args.get('operation_type', '').strip()
    asset_type = request.args.get('asset_type', '').strip()
    status = request.args.get('status', '持有').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    if app_name:
        where_clauses.append('app_name LIKE %s')
        params.append(f'%{app_name}%')
    if product_code:
        where_clauses.append('product_code LIKE %s')
        params.append(f'%{product_code}%')
    if code_id:
        where_clauses.append('code_id LIKE %s')
        params.append(f'%{code_id}%')
    if product_name:
        where_clauses.append('product_name LIKE %s')
        params.append(f'%{product_name}%')
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

    where_sql = (' WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''

    p = paginate()
    p['total'] = cursor.execute(
        f'SELECT COUNT(*) AS cnt FROM otc_app{where_sql}', params
    )
    if p['total'] > 0:
        p['total'] = cursor.fetchone()['cnt']

    p['total_pages'] = (p['total'] + p['per_page'] - 1) // p['per_page'] if p['total'] > 0 and p['per_page'] > 0 else (1 if p['total'] > 0 else 0)
    p['has_prev'] = p['page'] > 1
    p['has_next'] = p['page'] < p['total_pages']

    cursor.execute(
        f'SELECT * FROM otc_app{where_sql} ORDER BY record_date DESC, id DESC '
        f'LIMIT {p["per_page"]} OFFSET {p["offset"]}',
        params
    )
    records = cursor.fetchall()

    # 最近一条 APP 名称（供新增弹窗默认值）
    if scope_sql:
        cursor.execute(
            "SELECT app_name FROM otc_app WHERE user_id = %s ORDER BY record_date DESC, id DESC LIMIT 1",
            scope_params
        )
    else:
        cursor.execute("SELECT app_name FROM otc_app ORDER BY record_date DESC, id DESC LIMIT 1")
    row = cursor.fetchone()
    last_app_name = row['app_name'] if row and row['app_name'] else ''
    cursor.close()

    overview = get_overview(db, where_clauses, params)
    db.close()

    return render_template('otc_app.html',
                           records=records,
                           pagination=p,
                           invest_total=overview['invest_total'],
                           interest_profit=overview['interest_profit'],
                           holding_count=overview['holding_count'],
                           settled_count=overview['settled_count'],
                           app_name=app_name,
                           product_code=product_code,
                           code_id=code_id,
                           product_name=product_name,
                           operation_type=operation_type,
                           asset_type=asset_type,
                           status=status,
                           date_from=date_from,
                           date_to=date_to,
                           last_app_name=last_app_name)
