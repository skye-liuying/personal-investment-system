"""产品管理蓝图（全局共享产品字典，仅超级管理员可维护）"""

from flask import Blueprint

products_bp = Blueprint('products', __name__)


from . import query, add, edit, delete, import_data  # noqa: E402, F401
