"""结清查询 — 手动新增结清记录（POST /settlement/add）"""

from flask import flash, redirect, request, url_for
from . import settlement_bp
from database import get_db
from blueprints.auth.helpers import get_current_user_id


@settlement_bp.route('/add', methods=['POST'])
def add():
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

    # 收益 = 卖出金额 - 买入金额 - 费用总和
    profit = settle_amount - invest_amount - fees

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO settlements (user_id, settle_date, code, code_id, product_name, asset_type, '
        'invest_amount, settle_amount, profit, fees, holding_days, quantity) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (get_current_user_id(), settle_date, code, code_id or None, product_name, asset_type,
         invest_amount, settle_amount, profit, fees, holding_days, quantity)
    )
    db.commit()
    cursor.close()
    db.close()

    flash('结清记录添加成功', 'success')
    return redirect(url_for('settlement.query'))
