"""统计分析蓝图"""

from flask import Blueprint

statistics_bp = Blueprint('statistics', __name__)

from . import query, settle  # noqa: E402, F401
