"""证券管理 — 新增功能（POST /add）"""

from flask import flash, redirect, request, url_for
from . import securities_bp
from database import get_db


@securities_bp.route('/add', methods=['POST'])
def add():
    broker = request.form.get('broker', '').strip()
    record_date = request.form.get('record_date', '').strip()
    operation_type = request.form.get('operation_type', '').strip()
    asset_type = request.form.get('asset_type', '').strip()
    stock_code = request.form.get('stock_code', '').strip()
    code_id = request.form.get('code_id', '').strip()
    stock_name = request.form.get('stock_name', '').strip()
    total_amount = request.form.get('total_amount', '').strip()
    fees = request.form.get('fees', '').strip()

    if not all([broker, record_date, operation_type, asset_type, stock_code, stock_name, total_amount]):
        flash('请填写所有必填字段', 'error')
        return redirect(url_for('securities.query'))

    try:
        total_amount = float(total_amount)
    except (ValueError, TypeError):
        flash('总金额格式不正确', 'error')
        return redirect(url_for('securities.query'))

    unit_price = request.form.get('unit_price', '').strip()
    quantity = request.form.get('quantity', '').strip()

    unit_price = float(unit_price) if unit_price else None
    quantity = float(quantity) if quantity else None
    fees = float(fees) if fees else None

    # 买入、卖出、利息：默认状态均为"持有"
    status = '持有'

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO securities (broker, record_date, operation_type, asset_type, stock_code, code_id, stock_name, '
        'unit_price, quantity, total_amount, fees, status) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (broker, record_date, operation_type, asset_type, stock_code, code_id or None, stock_name,
         unit_price, quantity, total_amount, fees, status)
    )
    db.commit()

    # 卖出时自动判断是否结清：相同 code_id + stock_code 的卖出数量 >= 买入数量时，自动结清并写入结算记录
    if operation_type == '卖出':
        auto_settle(cursor, db, stock_code, code_id or None, stock_name, asset_type, record_date)

    cursor.close()
    db.close()

    flash('证券记录添加成功', 'success')
    return redirect(url_for('securities.query'))


def auto_settle(cursor, db, stock_code, code_id_param, stock_name, asset_type, record_date):
    """同一个 code_id + stock_code 的卖出数量 >= 买入数量时，自动标记结清并生成结算记录"""
    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS buy_qty,
               COALESCE(SUM(total_amount), 0) AS buy_amount,
               COALESCE(SUM(fees), 0) AS buy_fees,
               MIN(record_date) AS first_buy_date
        FROM securities
        WHERE stock_code = %s
          AND IFNULL(code_id, '') = IFNULL(%s, '')
          AND operation_type = '买入'
    """, (stock_code, code_id_param))
    buy_row = cursor.fetchone()
    buy_qty = float(buy_row['buy_qty'])
    buy_amount = float(buy_row['buy_amount'])
    buy_fees = float(buy_row['buy_fees'])
    first_buy_date = buy_row['first_buy_date']

    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS sell_qty,
               COALESCE(SUM(total_amount), 0) AS sell_amount,
               COALESCE(SUM(fees), 0) AS sell_fees
        FROM securities
        WHERE stock_code = %s
          AND IFNULL(code_id, '') = IFNULL(%s, '')
          AND operation_type = '卖出'
    """, (stock_code, code_id_param))
    sell_row = cursor.fetchone()
    sell_qty = float(sell_row['sell_qty'])
    sell_amount = float(sell_row['sell_amount'])
    sell_fees = float(sell_row['sell_fees'])

    if sell_qty >= buy_qty and buy_qty > 0:
        # 标记相同 code_id + stock_code 的所有记录为「结清」
        cursor.execute("""
            UPDATE securities SET status = '结清'
            WHERE stock_code = %s
              AND IFNULL(code_id, '') = IFNULL(%s, '')
        """, (stock_code, code_id_param))

        # 总费用 = 买入费用 + 卖出费用
        total_fees = buy_fees + sell_fees

        # 持有天数
        from datetime import datetime
        holding_days = None
        if first_buy_date and record_date:
            holding_days = (datetime.strptime(str(record_date), '%Y-%m-%d') -
                            datetime.strptime(str(first_buy_date), '%Y-%m-%d')).days

        # 收益 = 卖出金额 - 买入金额 - 费用总和
        profit = sell_amount - buy_amount - total_fees

        cursor.execute(
            'INSERT INTO settlements (settle_date, code, code_id, product_name, asset_type, '
            'invest_amount, settle_amount, profit, fees, holding_days) '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
            (record_date, stock_code, code_id_param, stock_name, asset_type,
             buy_amount, sell_amount, profit, total_fees, holding_days)
        )
        db.commit()
        flash('已自动结清，收益：¥{:,.2f}，费用：¥{:,.2f}，持有 {} 天'.format(
            profit, total_fees, holding_days if holding_days else '?'), 'info')
