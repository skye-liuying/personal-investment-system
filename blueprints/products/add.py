# -*- coding: utf-8 -*-
"""产品管理 — 新增产品（POST /products/add）"""

from flask import flash, redirect, request, url_for
from pymysql.err import IntegrityError

from database import get_db

from . import products_bp
from ..auth.helpers import is_admin


@products_bp.route('/add', methods=['POST'])
def add():
    """新增产品：code 全局唯一，重复则拒绝"""
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

    # 唯一性预检（双保险，数据库 UNIQUE 约束兜底）
    cursor.execute('SELECT id FROM products WHERE code = %s', (code,))
    if cursor.fetchone():
        cursor.close()
        db.close()
        flash(f'产品代码「{code}」已存在，请勿重复添加', 'error')
        return redirect(url_for('products.query'))

    try:
        cursor.execute(
            'INSERT INTO products (code, name, asset_type, remark) VALUES (%s, %s, %s, %s)',
            (code, name, asset_type or None, remark or None)
        )
    except IntegrityError:
        db.rollback()
        cursor.close()
        db.close()
        flash(f'产品代码「{code}」已存在，请勿重复添加', 'error')
        return redirect(url_for('products.query'))

    db.commit()
    cursor.close()
    db.close()

    flash(f'产品「{name}」添加成功', 'success')
    return redirect(url_for('products.query'))
