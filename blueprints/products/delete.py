# -*- coding: utf-8 -*-
"""产品管理 — 删除产品（POST /products/delete）"""

from flask import flash, redirect, request, url_for

from database import get_db

from . import products_bp
from ..auth.helpers import is_admin


@products_bp.route('/delete', methods=['POST'])
def delete():
    """删除产品（仅超级管理员）"""
    if not is_admin():
        flash('无权限执行该操作', 'error')
        return redirect(url_for('products.query'))

    pid = request.form.get('id', type=int)
    if not pid:
        flash('缺少产品ID', 'error')
        return redirect(url_for('products.query'))

    db = get_db()
    cursor = db.cursor()

    cursor.execute('SELECT name FROM products WHERE id = %s', (pid,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        db.close()
        flash('产品不存在', 'error')
        return redirect(url_for('products.query'))

    cursor.execute('DELETE FROM products WHERE id = %s', (pid,))
    db.commit()
    cursor.close()
    db.close()

    flash(f'产品「{row["name"]}」删除成功', 'success')
    return redirect(url_for('products.query'))
