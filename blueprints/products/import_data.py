# -*- coding: utf-8 -*-
"""产品管理 — 从证券/场外记录导入产品字典（POST /products/import）

导入区间标识：
    M-2026-06        按月（2026年6月）
    N-2026           按年（2026年）
    D-2026-06-06     按日（2026-06-06）
读取 securities + otc_app 在该区间内【全部用户】的记录，
取 code/name/asset_type 写入 products 表，code 已存在的跳过。
"""

import re
from datetime import datetime, timedelta

from flask import flash, redirect, request, url_for

from database import get_db

from . import products_bp
from ..auth.helpers import is_admin


def parse_period(token):
    """解析区间标识 → (start_date, end_date, label)；格式非法返回 None"""
    token = (token or '').strip().upper()

    # 按月：M-2026-06
    m = re.fullmatch(r'M-(\d{4})-(\d{2})', token)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        if not 1 <= month <= 12:
            return None
        if month == 12:
            end = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = datetime(year, month + 1, 1) - timedelta(days=1)
        return f'{year:04d}-{month:02d}-01', end.strftime('%Y-%m-%d'), f'{year}年{month}月'

    # 按年：N-2026
    m = re.fullmatch(r'N-(\d{4})', token)
    if m:
        year = int(m.group(1))
        return f'{year:04d}-01-01', f'{year:04d}-12-31', f'{year}年'

    # 按日：D-2026-06-06
    m = re.fullmatch(r'D-(\d{4})-(\d{2})-(\d{2})', token)
    if m:
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            dt = datetime(year, month, day)
        except ValueError:
            return None
        return dt.strftime('%Y-%m-%d'), dt.strftime('%Y-%m-%d'), f'{dt.strftime("%Y-%m-%d")}'

    return None


def fetch_products_map(db, start, end):
    """读取 securities + otc_app 指定日期区间的产品，按 code 去重（首条优先）"""
    cursor = db.cursor()
    products_map = {}

    cursor.execute("""
        SELECT stock_code AS code, stock_name AS name, asset_type
        FROM securities
        WHERE record_date >= %s AND record_date <= %s
        ORDER BY id
    """, (start, end))
    for row in cursor.fetchall():
        code = row['code']
        if code and code not in products_map:
            products_map[code] = {'name': row['name'], 'asset_type': row['asset_type']}

    cursor.execute("""
        SELECT product_code AS code, product_name AS name, asset_type
        FROM otc_app
        WHERE record_date >= %s AND record_date <= %s
        ORDER BY id
    """, (start, end))
    for row in cursor.fetchall():
        code = row['code']
        if code and code not in products_map:
            products_map[code] = {'name': row['name'], 'asset_type': row['asset_type']}

    cursor.close()
    return products_map


@products_bp.route('/import', methods=['POST'])
def import_data():
    """导入产品字典（仅超级管理员）"""
    if not is_admin():
        flash('无权限执行该操作', 'error')
        return redirect(url_for('products.query'))

    token = request.form.get('period', '').strip()
    parsed = parse_period(token)
    if not parsed:
        flash('导入区间格式不正确，请输入 M-2026-06（月）/ N-2026（年）/ D-2026-06-06（日）', 'error')
        return redirect(url_for('products.query'))

    start, end, label = parsed
    db = get_db()
    products_map = fetch_products_map(db, start, end)
    total = len(products_map)

    if total == 0:
        db.close()
        flash(f'未在 {label} 的证券/场外记录中找到任何产品', 'info')
        return redirect(url_for('products.query'))

    # 查询已存在的 code，只插入不存在的
    cursor = db.cursor()
    codes = list(products_map.keys())
    placeholders = ', '.join(['%s'] * len(codes))
    cursor.execute(f'SELECT code FROM products WHERE code IN ({placeholders})', codes)
    existing = {row['code'] for row in cursor.fetchall()}

    inserted = 0
    for code in codes:
        if code in existing:
            continue
        info = products_map[code]
        cursor.execute(
            'INSERT INTO products (code, name, asset_type) VALUES (%s, %s, %s)',
            (code, info['name'], info['asset_type'])
        )
        inserted += 1

    db.commit()
    cursor.close()
    db.close()

    skipped = total - inserted
    flash(
        f'导入完成：{label} 共读取 {total} 个产品，新增 {inserted} 个，跳过 {skipped} 个（已存在）',
        'success' if inserted else 'info'
    )
    return redirect(url_for('products.query'))
