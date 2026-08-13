"""结清查询 — 编辑结清记录（POST /settlement/edit）"""

from flask import flash, redirect, request, url_for
from . import settlement_bp
from database import get_db
from blueprints.auth.helpers import get_current_user_id, is_admin


@settlement_bp.route('/edit', methods=['POST'])
def edit():
    record_id = request.form.get('id', '').strip()
    code = request.form.get('code', '').strip()
    code_id = request.form.get('code_id', '').strip()
    product_name = request.form.get('product_name', '').strip()
    asset_type = request.form.get('asset_type', '').strip()
    settle_date = request.form.get('settle_date', '').strip()
    buy_price = request.form.get('buy_price', '').strip()
    sell_price = request.form.get('sell_price', '').strip()
    quantity = request.form.get('quantity', '').strip()
    fees = request.form.get('fees', '').strip()
    holding_days = request.form.get('holding_days', '').strip()

    if not record_id:
        flash('缺少记录ID', 'error')
        return redirect(url_for('settlement.query'))

    if not all([code, product_name, asset_type, settle_date, buy_price, sell_price, quantity]):
        flash('请填写所有必填字段', 'error')
        return redirect(url_for('settlement.query'))

    try:
        buy_price = float(buy_price)
        sell_price = float(sell_price)
        quantity = float(quantity)
    except (ValueError, TypeError):
        flash('金额/数量格式不正确', 'error')
        return redirect(url_for('settlement.query'))

    invest_amount = buy_price * quantity
    settle_amount = sell_price * quantity
    fees = float(fees) if fees else 0.0
    holding_days = int(holding_days) if holding_days else None
    profit = settle_amount - invest_amount - fees

    db = get_db()
    cursor = db.cursor()
    if is_admin():
        cursor.execute(
            'UPDATE settlements SET code=%s, code_id=%s, product_name=%s, asset_type=%s, '
            'settle_date=%s, invest_amount=%s, settle_amount=%s, profit=%s, fees=%s, '
            'holding_days=%s, quantity=%s '
            'WHERE id=%s',
            (code, code_id or None, product_name, asset_type, settle_date,
             invest_amount, settle_amount, profit, fees, holding_days, quantity, record_id)
        )
    else:
        cursor.execute(
            'UPDATE settlements SET code=%s, code_id=%s, product_name=%s, asset_type=%s, '
            'settle_date=%s, invest_amount=%s, settle_amount=%s, profit=%s, fees=%s, '
            'holding_days=%s, quantity=%s '
            'WHERE id=%s AND user_id=%s',
            (code, code_id or None, product_name, asset_type, settle_date,
             invest_amount, settle_amount, profit, fees, holding_days, quantity,
             record_id, get_current_user_id())
        )
    db.commit()
    cursor.close()
    db.close()

    flash('结清记录更新成功', 'success')
    return redirect(url_for('settlement.query'))
