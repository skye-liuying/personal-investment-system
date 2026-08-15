# -*- coding: utf-8 -*-
"""用户管理 — 删除用户（POST /users/delete）"""

from flask import flash, redirect, request, url_for

from database import get_db

from . import users_bp
from ..auth.helpers import is_admin


@users_bp.route('/delete', methods=['POST'])
def delete():
    """删除用户（同时清理其角色关联）"""
    if not is_admin():
        flash('无权限执行该操作', 'error')
        return redirect(url_for('users.query'))

    uid = request.form.get('id', '').strip()
    if not uid:
        flash('缺少用户ID', 'error')
        return redirect(url_for('users.query'))

    db = get_db()
    cursor = db.cursor()

    cursor.execute('SELECT id, is_admin, user_id FROM users WHERE id = %s', (uid,))
    user = cursor.fetchone()
    if not user:
        cursor.close()
        db.close()
        flash('用户不存在', 'error')
        return redirect(url_for('users.query'))

    if user['is_admin'] == 1:
        cursor.close()
        db.close()
        flash('不能删除超级管理员账号', 'error')
        return redirect(url_for('users.query'))

    # 清理该用户作为组长或组员的组关系
    login_id = user['user_id']
    cursor.execute(
        'DELETE FROM user_groups WHERE leader_id = %s OR member_id = %s',
        (login_id, login_id)
    )
    cursor.execute('DELETE FROM user_roles WHERE user_id = %s', (uid,))
    cursor.execute('DELETE FROM users WHERE id = %s', (uid,))

    db.commit()
    cursor.close()
    db.close()

    flash('用户已删除', 'success')
    return redirect(url_for('users.query'))
