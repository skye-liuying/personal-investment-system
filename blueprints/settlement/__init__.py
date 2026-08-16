"""结清查询蓝图"""

from flask import Blueprint

settlement_bp = Blueprint('settlement', __name__)

from . import query, add, edit, correct, lookup_name  # noqa: E402, F401
