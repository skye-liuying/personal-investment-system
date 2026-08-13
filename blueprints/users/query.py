# -*- coding: utf-8 -*-
"""用户管理 — 用户列表（GET /users）"""

from flask import render_template

from database import get_db

from . import users_bp
from ..auth.helpers import is_admin


def get_all_roles():
    """获取所有角色列表"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT id, role_name, description FROM roles ORDER BY id')
    roles = cursor.fetchall()
    cursor.close()
    db.close()
    return roles


def get_user_roles_map(user_id):
    """获取指定用户的角色ID列表"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT role_id FROM user_roles WHERE user_id = %s', (user_id,))
    role_ids = [r['role_id'] for r in cursor.fetchall()]
    cursor.close()
    db.close()
    return role_ids


def fetch_users():
    """查询全部用户（含各自角色名），仅超级管理员可调用"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT u.*, GROUP_CONCAT(r.role_name SEPARATOR '、') AS role_names
        FROM users u
        LEFT JOIN user_roles ur ON ur.user_id = u.id
        LEFT JOIN roles r ON r.id = ur.role_id
        GROUP BY u.id
        ORDER BY u.id
    """)
    users = cursor.fetchall()
    cursor.close()
    db.close()
    return users


def fetch_user_roles():
    """查询每个用户拥有的角色ID，格式 {user_id: [role_id, ...]}"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT user_id, role_id FROM user_roles')
    user_roles = {}
    for row in cursor.fetchall():
        user_roles.setdefault(row['user_id'], []).append(row['role_id'])
    cursor.close()
    db.close()
    return user_roles


@users_bp.route('/')
def query():
    """用户列表页（需超级管理员权限）"""
    if not is_admin():
        return render_template('403.html'), 403
    users = fetch_users()
    roles = get_all_roles()
    user_roles = fetch_user_roles()
    return render_template('users.html', users=users, roles=roles, user_roles=user_roles)
