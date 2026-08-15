# -*- coding: utf-8 -*-
"""用户管理 — 编辑用户（POST /users/edit）"""

from flask import flash, redirect, request, url_for
from werkzeug.security import generate_password_hash

from database import get_db

from . import users_bp
from ..auth.helpers import is_admin


@users_bp.route('/edit', methods=['POST'])
def edit():
    """编辑用户：修改姓名/号码/状态，重置密码，重新分配角色"""
    if not is_admin():
        flash('无权限执行该操作', 'error')
        return redirect(url_for('users.query'))

    uid = request.form.get('id', '').strip()
    username = request.form.get('username', '').strip()
    phone = request.form.get('phone', '').strip()
    password = request.form.get('password', '')
    status = request.form.get('status', '1')
    role_ids = request.form.getlist('roles')
    member_ids = request.form.getlist('group_members')

    if not uid or not username:
        flash('缺少必要参数', 'error')
        return redirect(url_for('users.query'))

    db = get_db()
    cursor = db.cursor()

    # 校验目标用户存在且不是超管自身被禁用
    cursor.execute('SELECT id, is_admin, user_id FROM users WHERE id = %s', (uid,))
    user = cursor.fetchone()
    if not user:
        cursor.close()
        db.close()
        flash('用户不存在', 'error')
        return redirect(url_for('users.query'))

    # 禁止修改超级管理员账号状态（防止误封 admin）
    if user['is_admin'] == 1 and status == '0':
        cursor.close()
        db.close()
        flash('不能禁用超级管理员账号', 'error')
        return redirect(url_for('users.query'))

    if password:
        if len(password) < 3:
            cursor.close()
            db.close()
            flash('密码长度至少 3 位', 'error')
            return redirect(url_for('users.query'))
        hashed = generate_password_hash(password)
        cursor.execute(
            'UPDATE users SET username=%s, phone=%s, status=%s, password=%s WHERE id=%s',
            (username, phone, 1 if status == '1' else 0, hashed, uid)
        )
    else:
        cursor.execute(
            'UPDATE users SET username=%s, phone=%s, status=%s WHERE id=%s',
            (username, phone, 1 if status == '1' else 0, uid)
        )

    # 重新分配角色：先删后插
    cursor.execute('DELETE FROM user_roles WHERE user_id = %s', (uid,))
    for rid in role_ids:
        cursor.execute(
            'INSERT IGNORE INTO user_roles (user_id, role_id) VALUES (%s, %s)',
            (uid, rid)
        )

    # 重新配置组员（组长-组员关系，存登录账号；排除自身避免自环）
    leader_id = user['user_id']
    member_ids = [m for m in member_ids if m and m != leader_id]
    cursor.execute('DELETE FROM user_groups WHERE leader_id = %s', (leader_id,))
    for member_id in member_ids:
        cursor.execute(
            'INSERT IGNORE INTO user_groups (leader_id, member_id) VALUES (%s, %s)',
            (leader_id, member_id)
        )

    db.commit()
    cursor.close()
    db.close()

    flash('用户信息更新成功', 'success')
    return redirect(url_for('users.query'))
