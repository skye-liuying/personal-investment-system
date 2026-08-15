"""应用入口 — 注册蓝图并启动"""

from flask import Flask, g, redirect, request, session, url_for
from werkzeug.security import generate_password_hash

from config import Config
from database import get_db

app = Flask(__name__)
app.config.from_object(Config)

# 注册蓝图
from blueprints.principal import principal_bp
from blueprints.securities import securities_bp
from blueprints.otc_app import otc_app_bp
from blueprints.statistics import statistics_bp
from blueprints.settlement import settlement_bp
from blueprints.auth import auth_bp
from blueprints.users import users_bp
from blueprints.roles import roles_bp
from blueprints.products import products_bp

app.register_blueprint(principal_bp, url_prefix='/principal')
app.register_blueprint(securities_bp, url_prefix='/securities')
app.register_blueprint(otc_app_bp, url_prefix='/otc_app')
app.register_blueprint(statistics_bp, url_prefix='/statistics')
app.register_blueprint(settlement_bp, url_prefix='/settlement')
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(users_bp, url_prefix='/users')
app.register_blueprint(roles_bp, url_prefix='/roles')
app.register_blueprint(products_bp, url_prefix='/products')


# ---------------- 数据库初始化：建表 + admin 种子数据 ----------------
def init_database():
    """启动时创建用户/角色/权限相关表，并确保 admin 超级管理员存在"""
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL UNIQUE,
            username VARCHAR(100) NOT NULL,
            phone VARCHAR(20) DEFAULT '',
            password VARCHAR(255) NOT NULL,
            status TINYINT DEFAULT 1,
            is_admin TINYINT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) COMMENT='用户表'
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id INT AUTO_INCREMENT PRIMARY KEY,
            role_name VARCHAR(50) NOT NULL UNIQUE,
            description VARCHAR(255) DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) COMMENT='角色表'
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            role_id INT NOT NULL,
            UNIQUE KEY uk_user_role (user_id, role_id)
        ) COMMENT='用户-角色关联表'
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS role_permissions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            role_id INT NOT NULL,
            page VARCHAR(50) NOT NULL,
            can_view TINYINT DEFAULT 0,
            can_add TINYINT DEFAULT 0,
            can_edit TINYINT DEFAULT 0,
            can_delete TINYINT DEFAULT 0,
            UNIQUE KEY uk_role_page (role_id, page)
        ) COMMENT='角色权限表'
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_groups (
            id INT AUTO_INCREMENT PRIMARY KEY,
            leader_id VARCHAR(50) NOT NULL,
            member_id VARCHAR(50) NOT NULL,
            UNIQUE KEY uk_leader_member (leader_id, member_id),
            KEY idx_leader (leader_id),
            KEY idx_member (member_id)
        ) COMMENT='组长-组员关系表'
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(50) NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL,
            asset_type VARCHAR(20) DEFAULT NULL,
            remark VARCHAR(255) DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) COMMENT='产品管理表（全局共享产品字典）'
    """)

    # 兼容旧库：为 5 张业务表补齐 user_id 字段（VARCHAR 存登录账号）与索引
    business_tables = ['principal', 'securities', 'otc_app', 'settlements', 'statistics_summary']
    for table in business_tables:
        try:
            cursor.execute(
                "SELECT COLUMN_NAME, COLUMN_TYPE FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = 'user_id'",
                (table,)
            )
            col = cursor.fetchone()
            if not col:
                cursor.execute(
                    f"ALTER TABLE `{table}` ADD COLUMN user_id VARCHAR(50) NOT NULL "
                    f"DEFAULT 'admin' COMMENT '归属用户账号' AFTER id"
                )
                cursor.execute(f"ALTER TABLE `{table}` ADD INDEX idx_user_id (user_id)")
                db.commit()
                print(f'[init] 已为 {table} 补充 user_id 字段')
            elif not str(col['COLUMN_TYPE']).lower().startswith('varchar'):
                # 旧版 INT 列：按 users 表把数字 id 映射为登录账号，再改列类型
                cursor.execute("SELECT id, user_id FROM users")
                user_map = {str(u['id']): u['user_id'] for u in cursor.fetchall()}
                for uid, login in user_map.items():
                    cursor.execute(
                        f"UPDATE `{table}` SET user_id = %s WHERE user_id = %s",
                        (login, uid)
                    )
                cursor.execute(
                    f"ALTER TABLE `{table}` MODIFY COLUMN user_id VARCHAR(50) NOT NULL "
                    f"DEFAULT 'admin' COMMENT '归属用户账号'"
                )
                db.commit()
                print(f'[init] 已迁移 {table} 的 user_id 为账号字符串')
        except Exception as exc:  # 表不存在等情况跳过
            db.rollback()
            print(f'[init] {table} 迁移跳过: {exc}')

    pages = ['principal', 'securities', 'otc_app', 'statistics', 'settlement', 'users', 'roles', 'products']

    # 确保 admin 角色存在（拥有全部页面全部权限）
    cursor.execute("SELECT id FROM roles WHERE role_name = 'admin'")
    admin_role = cursor.fetchone()
    if not admin_role:
        cursor.execute(
            "INSERT INTO roles (role_name, description) VALUES ('admin', '超级管理员，拥有全部权限')"
        )
        admin_role_id = cursor.lastrowid
        for page in pages:
            cursor.execute(
                "INSERT INTO role_permissions (role_id, page, can_view, can_add, can_edit, can_delete) "
                "VALUES (%s, %s, 1, 1, 1, 1)",
                (admin_role_id, page)
            )
    else:
        admin_role_id = admin_role['id']
        # 补齐 admin 角色缺失的页面权限
        cursor.execute("SELECT page FROM role_permissions WHERE role_id = %s", (admin_role_id,))
        existing_pages = {row['page'] for row in cursor.fetchall()}
        for page in pages:
            if page not in existing_pages:
                cursor.execute(
                    "INSERT INTO role_permissions (role_id, page, can_view, can_add, can_edit, can_delete) "
                    "VALUES (%s, %s, 1, 1, 1, 1)",
                    (admin_role_id, page)
                )

    # 确保组长角色存在（数据范围由用户管理页配置的组员决定）
    cursor.execute("SELECT id FROM roles WHERE role_name = '组长'")
    leader_role = cursor.fetchone()
    if not leader_role:
        cursor.execute(
            "INSERT INTO roles (role_name, description) "
            "VALUES ('组长', '组长：可查看/修改自己和组员创建的数据')"
        )
        leader_role_id = cursor.lastrowid
        # 默认给 5 个业务页面查看/新增/修改权限（删除权限由管理员按需开启）
        for page in ('principal', 'securities', 'otc_app', 'statistics', 'settlement'):
            cursor.execute(
                "INSERT INTO role_permissions (role_id, page, can_view, can_add, can_edit, can_delete) "
                "VALUES (%s, %s, 1, 1, 1, 0)",
                (leader_role_id, page)
            )

    # 确保 admin 超级用户存在（user_id=admin，密码 admin，is_admin=1）
    cursor.execute("SELECT id FROM users WHERE user_id = 'admin'")
    admin_user = cursor.fetchone()
    if not admin_user:
        hashed = generate_password_hash('admin')
        cursor.execute(
            "INSERT INTO users (user_id, username, phone, password, status, is_admin) "
            "VALUES ('admin', '管理员', '', %s, 1, 1)",
            (hashed,)
        )
        admin_uid = cursor.lastrowid
        # 关联 admin 角色
        cursor.execute(
            "INSERT IGNORE INTO user_roles (user_id, role_id) VALUES (%s, %s)",
            (admin_uid, admin_role_id)
        )

    db.commit()
    cursor.close()
    db.close()


# ---------------- 登录检查与权限控制 ----------------
@app.before_request
def check_login_and_permission():
    """所有请求前：未登录跳转登录页；无页面查看权限返回 403"""
    # 静态资源与登录/登出接口放行
    if request.endpoint == 'static' or request.blueprint == 'auth':
        return None

    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    # 加载当前用户权限到 g
    from blueprints.auth.helpers import load_permissions, PAGE_NAMES
    g.permissions = load_permissions(session['user_id'])
    g.current_user = session.get('username', '')

    # 页面级查看权限：业务页面蓝图名与 PAGE_NAMES 一致
    page = request.blueprint
    if page in PAGE_NAMES and not g.permissions.get(page, {}).get('view'):
        return render_403()

    # 操作级权限：POST 请求按 endpoint 推断需要的操作权限
    if request.method == 'POST' and page in PAGE_NAMES:
        action_map = {
            'add': 'add',
            'edit': 'edit',
            'delete': 'delete',
            'correct': 'edit',
            'settle': 'edit',
            'trade': 'add',
            'import_data': 'add',
        }
        endpoint_action = request.endpoint.split('.')[-1] if request.endpoint else ''
        need = action_map.get(endpoint_action)
        if need and not g.permissions.get(page, {}).get(need):
            from flask import flash
            flash('您没有该操作的权限', 'error')
            return redirect(url_for(f'{page}.query'))

    return None


def render_403():
    from flask import render_template
    return render_template('403.html'), 403


@app.context_processor
def inject_globals():
    """模板全局注入：active_page、当前用户与权限判断函数"""
    from blueprints.auth.helpers import has_perm
    active_page = request.blueprint if request.blueprint in (
        'principal', 'securities', 'otc_app', 'statistics', 'settlement', 'users', 'roles', 'products'
    ) else ''
    return {
        'active_page': active_page,
        'current_user': session.get('username', ''),
        'can': has_perm,
    }


@app.route('/')
def index():
    return redirect(url_for('principal.query'))


if __name__ == '__main__':
    init_database()
    app.run(debug=True, host='0.0.0.0', port=5000)
