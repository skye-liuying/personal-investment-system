# -*- coding: utf-8 -*-
"""用户管理 — 创建用户（POST /users/add）"""

from flask import flash, redirect, request, url_for
from pymysql.err import IntegrityError
from werkzeug.security import generate_password_hash

from database import get_db

from . import users_bp
from ..auth.helpers import is_admin


@users_bp.route('/add', methods=['POST'])
def add():
    """创建用户：user_id 登录账号、username 姓名、phone 号码、password 登录密码、roles 角色"""
    if not is_admin():
        flash('无权限执行该操作', 'error')
        return redirect(url_for('users.query'))

    user_id = request.form.get('user_id', '').strip()
    username = request.form.get('username', '').strip()
    phone = request.form.get('phone', '').strip()
    password = request.form.get('password', '')
    status = request.form.get('status', '1')
    role_ids = request.form.getlist('roles')

    if not all([user_id, username, password]):
        flash('请填写用户ID、用户姓名和登录密码', 'error')
        return redirect(url_for('users.query'))

    if not password or len(password) < 3:
        flash('密码长度至少 3 位', 'error')
        return redirect(url_for('users.query'))

    db = get_db()
    cursor = db.cursor()

    # 用户ID唯一性校验（代码层预检，防误操作）
    cursor.execute('SELECT id FROM users WHERE user_id = %s', (user_id,))
    if cursor.fetchone():
        cursor.close()
        db.close()
        flash(f'用户ID「{user_id}」已存在', 'error')
        return redirect(url_for('users.query'))

    hashed = generate_password_hash(password)
    try:
        cursor.execute(
            'INSERT INTO users (user_id, username, phone, password, status, is_admin) '
            'VALUES (%s, %s, %s, %s, %s, 0)',
            (user_id, username, phone, hashed, 1 if status == '1' else 0)
        )
    except IntegrityError:
        # 兜底：并发请求绕过预检时，依赖数据库 UNIQUE 约束拦截
        db.rollback()
        cursor.close()
        db.close()
        flash(f'用户ID「{user_id}」已存在，请勿重复创建', 'error')
        return redirect(url_for('users.query'))

    new_uid = cursor.lastrowid

    # 分配角色（用户可关联多种角色）
    for rid in role_ids:
        cursor.execute(
            'INSERT IGNORE INTO user_roles (user_id, role_id) VALUES (%s, %s)',
            (new_uid, rid)
        )

    db.commit()
    cursor.close()
    db.close()

    flash(f'用户「{username}」创建成功', 'success')
    return redirect(url_for('users.query'))
