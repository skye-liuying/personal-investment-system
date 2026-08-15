# -*- coding: utf-8 -*-
"""产品管理 — 产品列表（GET /products）"""

from flask import render_template, request

from database import get_db
from paginate import paginate

from . import products_bp
from ..auth.helpers import is_admin


@products_bp.route('/')
def query():
    """产品列表页：分页 + 按代码/名称/资产类型搜索（仅超级管理员）"""
    if not is_admin():
        return render_template('403.html'), 403

    code = request.args.get('code', '').strip()
    name = request.args.get('name', '').strip()
    asset_type = request.args.get('asset_type', '').strip()

    where_clauses = []
    params = []
    if code:
        where_clauses.append('code LIKE %s')
        params.append(f'%{code}%')
    if name:
        where_clauses.append('name LIKE %s')
        params.append(f'%{name}%')
    if asset_type:
        where_clauses.append('asset_type = %s')
        params.append(asset_type)

    where_sql = (' WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''

    p = paginate()
    db = get_db()
    cursor = db.cursor()

    cursor.execute(f'SELECT COUNT(*) AS cnt FROM products{where_sql}', params)
    p['total'] = cursor.fetchone()['cnt']
    p['total_pages'] = (p['total'] + p['per_page'] - 1) // p['per_page'] if p['total'] > 0 else 0
    p['has_prev'] = p['page'] > 1
    p['has_next'] = p['page'] < p['total_pages']

    cursor.execute(
        f'SELECT * FROM products{where_sql} ORDER BY id DESC '
        f'LIMIT {p["per_page"]} OFFSET {p["offset"]}',
        params
    )
    records = cursor.fetchall()
    cursor.close()
    db.close()

    return render_template(
        'products.html',
        records=records,
        pagination=p,
        code=code,
        name=name,
        asset_type=asset_type,
    )
