# -*- coding: utf-8 -*-
"""角色管理 — 创建角色（POST /roles/add）"""

from flask import flash, redirect, request, url_for

from database import get_db

from . import roles_bp
from ..auth.helpers import PAGE_NAMES, is_admin


def _parse_permissions(form):
    """从表单读取每个页面的权限勾选，返回 {page: (view, add, edit, delete)}"""
    result = {}
    for page in PAGE_NAMES:
        result[page] = (
            1 if form.get(f'{page}_view') == 'on' else 0,
            1 if form.get(f'{page}_add') == 'on' else 0,
            1 if form.get(f'{page}_edit') == 'on' else 0,
            1 if form.get(f'{page}_delete') == 'on' else 0,
        )
    return result


@roles_bp.route('/add', methods=['POST'])
def add():
    """创建角色并配置各页面权限"""
    if not is_admin():
        flash('无权限执行该操作', 'error')
        return redirect(url_for('roles.query'))

    role_name = request.form.get('role_name', '').strip()
    description = request.form.get('description', '').strip()

    if not role_name:
        flash('请填写角色名称', 'error')
        return redirect(url_for('roles.query'))

    perms = _parse_permissions(request.form)

    db = get_db()
    cursor = db.cursor()

    cursor.execute('SELECT id FROM roles WHERE role_name = %s', (role_name,))
    if cursor.fetchone():
        cursor.close()
        db.close()
        flash(f'角色「{role_name}」已存在', 'error')
        return redirect(url_for('roles.query'))

    cursor.execute(
        'INSERT INTO roles (role_name, description) VALUES (%s, %s)',
        (role_name, description)
    )
    role_id = cursor.lastrowid

    for page, (v, a, e, d) in perms.items():
        cursor.execute(
            'INSERT INTO role_permissions (role_id, page, can_view, can_add, can_edit, can_delete) '
            'VALUES (%s, %s, %s, %s, %s, %s)',
            (role_id, page, v, a, e, d)
        )

    db.commit()
    cursor.close()
    db.close()

    flash(f'角色「{role_name}」创建成功', 'success')
    return redirect(url_for('roles.query'))
