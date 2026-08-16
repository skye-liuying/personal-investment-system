# -*- coding: utf-8 -*-
"""产品名称联动查询：输入产品名称时下拉展示匹配的 products 产品字典项，点击后回填代码

products 为全局共享产品字典（无 user_id 隔离），故直接查询全表。
功能同证券管理页新增弹框里的名称联动。
"""

from flask import jsonify, request
from database import get_db
from blueprints.settlement import settlement_bp


@settlement_bp.route('/lookup_name')
def lookup_name():
    """根据产品名称模糊匹配 products 表，返回所有匹配项（最多 10 条）供前端下拉选择

    匹配优先级：精确名称 > 名称左匹配(以输入开头) > 名称包含输入；同优先级按 id 倒序。
    """
    name = (request.args.get('name') or '').strip()
    if not name:
        return jsonify({'matches': []})

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT code, name FROM products "
        "WHERE name = %s OR name LIKE %s OR name LIKE %s "
        "ORDER BY (name = %s) DESC, (name LIKE %s) DESC, id DESC LIMIT 10",
        (name, name + '%', '%' + name + '%', name, name + '%')
    )
    rows = cursor.fetchall()
    db.close()

    matches = [{'code': r['code'] or '', 'name': r['name'] or ''} for r in rows]
    return jsonify({'matches': matches})
