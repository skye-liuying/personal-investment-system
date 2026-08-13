# -*- coding: utf-8 -*-
"""登录状态与权限工具函数"""

from flask import g, session

from database import get_db

# 系统所有页面（含用户/角色管理页）
PAGES = [
    ('principal', '本金管理'),
    ('securities', '证券管理'),
    ('otc_app', '场外APP管理'),
    ('settlement', '结清查询'),
    ('statistics', '统计分析'),
    ('users', '用户管理'),
    ('roles', '角色管理'),
]
PAGE_NAMES = [p for p, _ in PAGES]
PAGE_LABELS = dict(PAGES)

ACTIONS = [
    ('view', '查看'),
    ('add', '新增'),
    ('edit', '修改'),
    ('delete', '删除'),
]


def get_current_user_id():
    """当前登录用户的登录账号（如 liuying），即业务表 user_id 字段的归属值；未登录返回 None"""
    return session.get('login_id')


def is_admin():
    """当前用户是否为超级管理员"""
    return session.get('is_admin', 0) == 1


def load_permissions(user_id):
    """加载用户权限 {page: {'view': bool, 'add': bool, 'edit': bool, 'delete': bool}}

    超级管理员拥有所有页面全部权限；普通用户按关联角色的权限取并集。
    """
    if session.get('is_admin', 0) == 1:
        return {p: {a: True for a, _ in ACTIONS} for p in PAGE_NAMES}

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT rp.page,
               MAX(rp.can_view) AS can_view,
               MAX(rp.can_add) AS can_add,
               MAX(rp.can_edit) AS can_edit,
               MAX(rp.can_delete) AS can_delete
        FROM user_roles ur
        JOIN role_permissions rp ON rp.role_id = ur.role_id
        WHERE ur.user_id = %s
        GROUP BY rp.page
    """, (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    db.close()

    perms = {p: {a: False for a, _ in ACTIONS} for p in PAGE_NAMES}
    for row in rows:
        page = row['page']
        if page in perms:
            perms[page] = {
                'view': bool(row['can_view']),
                'add': bool(row['can_add']),
                'edit': bool(row['can_edit']),
                'delete': bool(row['can_delete']),
            }
    return perms


def has_perm(page, action='view'):
    """当前登录用户是否拥有页面操作权限"""
    if is_admin():
        return True
    perms = getattr(g, 'permissions', {})
    return perms.get(page, {}).get(action, False)


def scope_condition():
    """数据隔离条件。admin 返回 (None, None) 表示查看全部数据；
    普通用户返回 ('user_id = %s', (uid,)) 表示只看自己的数据。"""
    if is_admin():
        return None, None
    return 'user_id = %s', (get_current_user_id(),)
