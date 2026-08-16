# -*- coding: utf-8 -*-
"""用户管理 — 从组长处移除单个组员（POST /users/remove_member）"""

from flask import flash, redirect, request, url_for

from database import get_db

from . import users_bp
from ..auth.helpers import is_admin


@users_bp.route('/remove_member', methods=['POST'])
def remove_member():
    """移除组长下的某个组员（仅清理 user_groups 关系，不影响用户账号本身）"""
    if not is_admin():
        flash('无权限执行该操作', 'error')
        return redirect(url_for('users.query'))

    leader_id = request.form.get('leader_id', '').strip()
    member_id = request.form.get('member_id', '').strip()
    if not leader_id or not member_id:
        flash('缺少必要参数', 'error')
        return redirect(url_for('users.query'))

    if leader_id == member_id:
        flash('不能移除自身', 'error')
        return redirect(url_for('users.query'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'DELETE FROM user_groups WHERE leader_id = %s AND member_id = %s',
        (leader_id, member_id)
    )
    db.commit()
    cursor.close()
    db.close()

    flash(f'已从「{leader_id}」的组员中移除「{member_id}」', 'success')
    return redirect(url_for('users.query'))
