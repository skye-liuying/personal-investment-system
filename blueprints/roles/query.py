# -*- coding: utf-8 -*-
"""角色管理 — 角色列表（GET /roles）"""

from flask import render_template

from database import get_db

from . import roles_bp
from ..auth.helpers import ACTIONS, PAGE_LABELS, PAGE_NAMES, is_admin


def fetch_roles_with_permissions():
    """查询所有角色及其权限明细"""
    db = get_db()
    cursor = db.cursor()

    cursor.execute('SELECT * FROM roles ORDER BY id')
    roles = cursor.fetchall()

    cursor.execute('SELECT * FROM role_permissions')
    perm_rows = cursor.fetchall()

    cursor.close()
    db.close()

    # 权限按 role_id -> {page: {'view':.., 'add':.., ...}} 组织
    perms_map = {}
    for row in perm_rows:
        page = row['page']
        if page not in PAGE_NAMES:
            continue
        perms_map.setdefault(row['role_id'], {})[page] = {
            'view': bool(row['can_view']),
            'add': bool(row['can_add']),
            'edit': bool(row['can_edit']),
            'delete': bool(row['can_delete']),
        }

    # 组装：每个角色带完整权限矩阵（缺失的页面默认全 False）
    for role in roles:
        role['perm_matrix'] = {}
        role_perms = perms_map.get(role['id'], {})
        for page in PAGE_NAMES:
            role['perm_matrix'][page] = role_perms.get(page, {
                'view': False, 'add': False, 'edit': False, 'delete': False,
            })

    return roles


@roles_bp.route('/')
def query():
    """角色列表与权限配置页（需超级管理员权限）"""
    if not is_admin():
        return render_template('403.html'), 403
    roles = fetch_roles_with_permissions()
    return render_template(
        'roles.html',
        roles=roles,
        page_names=PAGE_NAMES,
        page_labels=PAGE_LABELS,
        actions=ACTIONS,
    )
