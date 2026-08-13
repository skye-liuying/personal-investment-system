# -*- coding: utf-8 -*-
"""角色管理 — 删除角色（POST /roles/delete）"""

from flask import flash, redirect, request, url_for

from database import get_db

from . import roles_bp
from ..auth.helpers import is_admin


@roles_bp.route('/delete', methods=['POST'])
def delete():
    """删除角色（同时清理权限及用户关联）"""
    if not is_admin():
        flash('无权限执行该操作', 'error')
        return redirect(url_for('roles.query'))

    role_id = request.form.get('id', '').strip()
    if not role_id:
        flash('缺少角色ID', 'error')
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

    if role['role_name'] == 'admin':
        cursor.close()
        db.close()
        flash('不能删除超级管理员角色', 'error')
        return redirect(url_for('roles.query'))

    cursor.execute('DELETE FROM role_permissions WHERE role_id = %s', (role_id,))
    cursor.execute('DELETE FROM user_roles WHERE role_id = %s', (role_id,))
    cursor.execute('DELETE FROM roles WHERE id = %s', (role_id,))

    db.commit()
    cursor.close()
    db.close()

    flash('角色已删除', 'success')
    return redirect(url_for('roles.query'))
