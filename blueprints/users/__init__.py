"""用户管理蓝图"""

from flask import Blueprint

users_bp = Blueprint('users', __name__)

from . import query, add, edit, delete  # noqa: E402, F401
