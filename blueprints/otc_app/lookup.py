# -*- coding: utf-8 -*-
"""关联编号查询：输入 code_id 时自动回填产品信息"""

from flask import jsonify
from database import get_db
from blueprints.otc_app import otc_app_bp
from blueprints.auth.helpers import scope_condition


@otc_app_bp.route('/lookup/<code_id>')
def lookup_code_id(code_id):
    """根据关联编号查找最近一条记录，返回产品信息供前端自动填充"""
    db = get_db()
    cursor = db.cursor()

    scope_sql, scope_params = scope_condition()
    if scope_sql:
        cursor.execute("""
            SELECT app_name, product_code, product_name, asset_type
            FROM otc_app
            WHERE code_id = %s AND status = '持有' AND """ + scope_sql + """
            ORDER BY id DESC
            LIMIT 1
        """, (code_id,) + scope_params)
    else:
        cursor.execute("""
            SELECT app_name, product_code, product_name, asset_type
            FROM otc_app
            WHERE code_id = %s AND status = '持有'
            ORDER BY id DESC
            LIMIT 1
        """, (code_id,))

    row = cursor.fetchone()
    db.close()

    if row:
        return jsonify({
            'found': True,
            'app_name': row['app_name'] or '',
            'product_code': row['product_code'] or '',
            'product_name': row['product_name'] or '',
            'asset_type': row['asset_type'] or '基金',
        })
    return jsonify({'found': False})
