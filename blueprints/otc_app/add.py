"""场外APP管理 — 新增功能（POST /add）"""

from flask import flash, redirect, request, url_for
from . import otc_app_bp
from database import get_db


@otc_app_bp.route('/add', methods=['POST'])
def add():
    app_name = request.form.get('app_name', '').strip()
    record_date = request.form.get('record_date', '').strip()
    operation_type = request.form.get('operation_type', '').strip()
    asset_type = request.form.get('asset_type', '').strip()
    product_code = request.form.get('product_code', '').strip()
    code_id = request.form.get('code_id', '').strip()
    product_name = request.form.get('product_name', '').strip()
    total_amount = request.form.get('total_amount', '').strip()
    fees = request.form.get('fees', '').strip()
    status = request.form.get('status', '').strip()

    if not all([app_name, record_date, operation_type, asset_type, product_code, product_name, total_amount]):
        flash('请填写所有必填字段', 'error')
        return redirect(url_for('otc_app.query'))

    try:
        total_amount = float(total_amount)
    except (ValueError, TypeError):
        flash('总金额格式不正确', 'error')
        return redirect(url_for('otc_app.query'))

    unit_price = request.form.get('unit_price', '').strip()
    quantity = request.form.get('quantity', '').strip()

    unit_price = float(unit_price) if unit_price else None
    quantity = float(quantity) if quantity else None
    fees = float(fees) if fees else None
    status = status or '持有'

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO otc_app (app_name, record_date, operation_type, asset_type, product_code, code_id, product_name, '
        'unit_price, quantity, total_amount, fees, status) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (app_name, record_date, operation_type, asset_type, product_code, code_id or None, product_name,
         unit_price, quantity, total_amount, fees, status)
    )
    db.commit()
    cursor.close()
    db.close()

    flash('场外APP记录添加成功', 'success')
    return redirect(url_for('otc_app.query'))
