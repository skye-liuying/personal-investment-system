"""认证蓝图"""

from flask import Blueprint

auth_bp = Blueprint('auth', __name__)

from . import login, logout  # noqa: E402, F401
