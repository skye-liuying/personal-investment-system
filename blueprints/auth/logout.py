# -*- coding: utf-8 -*-
"""退出登录（POST /auth/logout）"""

from flask import flash, redirect, session, url_for

from . import auth_bp


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('已退出登录', 'success')
    return redirect(url_for('auth.login'))
