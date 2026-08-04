"""分页工具模块"""

from flask import request


def paginate(default_per_page=10):
    """
    从 request 中获取分页参数，返回 page, per_page, offset 字典。
    
    Returns:
        dict: { page, per_page, offset, total, total_pages, has_prev, has_next, page_sizes }
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', default_per_page, type=int)
    if per_page not in [10, 20, 50, 100]:
        per_page = default_per_page
    offset = (page - 1) * per_page
    return {
        'page': page,
        'per_page': per_page,
        'offset': offset,
        'total': 0,
        'total_pages': 0,
        'has_prev': False,
        'has_next': False,
        'page_sizes': [10, 20, 50, 100]
    }
