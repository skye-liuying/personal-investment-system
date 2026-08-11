"""本金管理 — 查询功能（GET /）"""

from flask import render_template, request
from . import principal_bp
from . import get_overview
from database import get_db
from paginate import paginate


@principal_bp.route('/')
def query():
    db = get_db()
    cursor = db.cursor()

    # 构建查询条件
    where_clauses = []
    params = []

    broker = request.args.get('broker', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    operation_type = request.args.get('operation_type', '').strip()

    if broker:
        where_clauses.append('broker LIKE %s')
        params.append(f'%{broker}%')
    if date_from:
        where_clauses.append('record_date >= %s')
        params.append(date_from)
    if date_to:
        where_clauses.append('record_date <= %s')
        params.append(date_to)
    if operation_type:
        where_clauses.append('operation_type = %s')
        params.append(operation_type)

    where_sql = (' WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''

    # 分页
    p = paginate()
    p['total'] = cursor.execute(
        f'SELECT COUNT(*) AS cnt FROM principal{where_sql}', params
    )
    if p['total'] > 0:
        p['total'] = cursor.fetchone()['cnt']

    if p['total'] > 0 and p['per_page'] > 0:
        p['total_pages'] = (p['total'] + p['per_page'] - 1) // p['per_page']
    else:
        p['total_pages'] = 1 if p['total'] > 0 else 0

    p['has_prev'] = p['page'] > 1
    p['has_next'] = p['page'] < p['total_pages']

    cursor.execute(
        f'SELECT * FROM principal{where_sql} ORDER BY record_date DESC, id DESC '
        f'LIMIT {p["per_page"]} OFFSET {p["offset"]}',
        params
    )
    records = cursor.fetchall()

    # 查询最新一笔记录的券商，供新增弹窗默认填充
    cursor.execute('SELECT broker FROM principal ORDER BY id DESC LIMIT 1')
    last_row = cursor.fetchone()
    last_broker = last_row['broker'] if last_row else ''

    cursor.close()

    overview = get_overview(db, where_clauses, params)
    db.close()

    return render_template('principal.html',
                           records=records,
                           pagination=p,
                           total_recharge=overview['total_recharge'],
                           total_withdraw=overview['total_withdraw'],
                           net_principal=overview['net_principal'],
                           broker=broker,
                           date_from=date_from,
                           date_to=date_to,
                           operation_type=operation_type,
                           operation_types=['充值', '取现'],
                           last_broker=last_broker)
