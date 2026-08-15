# -*- coding: utf-8 -*-
"""产品管理 — 编辑产品（POST /products/edit/<id>）"""

from flask import flash, redirect, request, url_for

from database import get_db

from . import products_bp
from ..auth.helpers import is_admin


@products_bp.route('/edit/<int:pid>', methods=['POST'])
def edit(pid):
    """编辑产品：code 修改时仍须保持全局唯一（排除自身）"""
    if not is_admin():
        flash('无权限执行该操作', 'error')
        return redirect(url_for('products.query'))

    code = request.form.get('code', '').strip()
    name = request.form.get('name', '').strip()
    asset_type = request.form.get('asset_type', '').strip()
    remark = request.form.get('remark', '').strip()

    if not code or not name:
        flash('请填写产品代码和产品名称', 'error')
        return redirect(url_for('products.query'))

    db = get_db()
    cursor = db.cursor()

    # 目标产品必须存在
    cursor.execute('SELECT id FROM products WHERE id = %s', (pid,))
    if not cursor.fetchone():
        cursor.close()
        db.close()
        flash('产品不存在', 'error')
        return redirect(url_for('products.query'))

    # code 唯一性预检（排除自身）
    cursor.execute('SELECT id FROM products WHERE code = %s AND id != %s', (code, pid))
    if cursor.fetchone():
        cursor.close()
        db.close()
        flash(f'产品代码「{code}」已存在', 'error')
        return redirect(url_for('products.query'))

    cursor.execute(
        'UPDATE products SET code = %s, name = %s, asset_type = %s, remark = %s WHERE id = %s',
        (code, name, asset_type or None, remark or None, pid)
    )
    db.commit()
    cursor.close()
    db.close()

    flash('产品信息更新成功', 'success')
    return redirect(url_for('products.query'))
