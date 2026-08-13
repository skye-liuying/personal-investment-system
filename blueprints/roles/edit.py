# -*- coding: utf-8 -*-
"""角色管理 — 编辑角色及权限（POST /roles/edit）"""

from flask import flash, redirect, request, url_for

from database import get_db

from . import roles_bp
from .add import _parse_permissions
from ..auth.helpers import is_admin


@roles_bp.route('/edit', methods=['POST'])
def edit():
    """修改角色名称/描述，并重新配置各页面权限"""
    if not is_admin():
        flash('无权限执行该操作', 'error')
        return redirect(url_for('roles.query'))

    role_id = request.form.get('id', '').strip()
    role_name = request.form.get('role_name', '').strip()
    description = request.form.get('description', '').strip()

    if not role_id or not role_name:
        flash('缺少必要参数', 'error')
        return redirect(url_for('roles.query'))

    db = get_db()
    cursor = db.cursor()

    cursor.execute('SELECT role_name FROM roles WHERE id = %s', (role_id,))
    role = cursor.fetchone()
    if not role:
        cursor.close()
        db.close()
        flash('角色不存在', 'error')
        return redirect(url_for('roles.query'))

    # 角色名唯一性校验（排除自身）
    cursor.execute(
        'SELECT id FROM roles WHERE role_name = %s AND id != %s',
        (role_name, role_id)
    )
    if cursor.fetchone():
        cursor.close()
        db.close()
        flash(f'角色「{role_name}」已存在', 'error')
        return redirect(url_for('roles.query'))

    is_default = role['role_name'] == 'admin'

    # admin 角色不允许改名或禁用其权限，但可更新描述
    if is_default and role_name != 'admin':
        cursor.close()
        db.close()
        flash('超级管理员角色不允许改名', 'error')
        return redirect(url_for('roles.query'))

    cursor.execute(
        'UPDATE roles SET role_name=%s, description=%s WHERE id=%s',
        (role_name, description, role_id)
    )

    # 非 admin 角色：整体重写权限
    if not is_default:
        cursor.execute('DELETE FROM role_permissions WHERE role_id = %s', (role_id,))
        perms = _parse_permissions(request.form)
        for page, (v, a, e, d) in perms.items():
            cursor.execute(
                'INSERT INTO role_permissions (role_id, page, can_view, can_add, can_edit, can_delete) '
                'VALUES (%s, %s, %s, %s, %s, %s)',
                (role_id, page, v, a, e, d)
            )

    db.commit()
    cursor.close()
    db.close()

    flash(f'角色「{role_name}」更新成功', 'success')
    return redirect(url_for('roles.query'))
