"""角色与权限管理蓝图"""

from flask import Blueprint

roles_bp = Blueprint('roles', __name__)

from . import query, add, edit, delete  # noqa: E402, F401
