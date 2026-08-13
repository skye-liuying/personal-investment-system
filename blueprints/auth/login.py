# -*- coding: utf-8 -*-
"""登录功能（GET/POST /auth/login）"""

from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database import get_db

from . import auth_bp


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form.get('user_id', '').strip()
        password = request.form.get('password', '')

        if not user_id or not password:
            flash('请输入用户名和密码', 'error')
            return render_template('login.html')

        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()
        cursor.close()
        db.close()

        if not user or not check_password_hash(user['password'], password):
            flash('用户名或密码错误', 'error')
            return render_template('login.html')

        if user['status'] != 1:
            flash('该账号已被禁用，请联系管理员', 'error')
            return render_template('login.html')

        # 写入登录会话
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['is_admin'] = user['is_admin']
        session['login_id'] = user['user_id']

        flash(f'欢迎回来，{user["username"]}', 'success')
        return redirect(url_for('principal.query'))

    return render_template('login.html')
