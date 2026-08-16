"""证券管理 — 新增功能（POST /add）"""

from flask import flash, redirect, request, url_for
from . import securities_bp
from database import get_db
from blueprints.auth.helpers import get_current_user_id
from blueprints.statistics.sync import sync_statistics_summary


@securities_bp.route('/add', methods=['POST'])
def add():
    current_user_id = get_current_user_id()
    broker = request.form.get('broker', '').strip()
    record_date = request.form.get('record_date', '').strip()
    operation_type = request.form.get('operation_type', '').strip()
    asset_type = request.form.get('asset_type', '').strip()
    stock_code = request.form.get('stock_code', '').strip()
    code_id = request.form.get('code_id', '').strip()
    stock_name = request.form.get('stock_name', '').strip()
    total_amount = request.form.get('total_amount', '').strip()
    fees = request.form.get('fees', '').strip()

    if not all([broker, record_date, operation_type, asset_type, stock_code, code_id, stock_name, total_amount]):
        flash('请填写所有必填字段（含关联编号）', 'error')
        return redirect(url_for('securities.query'))

    try:
        total_amount = float(total_amount)
    except (ValueError, TypeError):
        flash('总金额格式不正确', 'error')
        return redirect(url_for('securities.query'))

    unit_price = request.form.get('unit_price', '').strip()
    quantity = request.form.get('quantity', '').strip()

    unit_price = float(unit_price) if unit_price else None
    quantity = int(float(quantity)) if quantity else None
    fees = float(fees) if fees else None

    # 买入、卖出、利息：默认状态均为"持有"
    status = '持有'

    db = get_db()
    cursor = db.cursor()

    # 卖出时校验数量不能超过持有数量
    if operation_type == '卖出' and quantity:
        code_id_val = code_id or None
        cursor.execute("""
            SELECT COALESCE(SUM(CASE WHEN operation_type='买入' THEN quantity ELSE -quantity END), 0) AS hold_qty
            FROM securities
            WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND status = '持有' AND user_id = %s
        """, (stock_code, code_id_val, current_user_id))
        row = cursor.fetchone()
        hold_qty = int(row['hold_qty']) if row and row['hold_qty'] else 0
        if quantity > hold_qty:
            cursor.close()
            db.close()
            flash(f'卖出数量（{quantity}）不能超过持有数量（{hold_qty}）', 'error')
            return redirect(url_for('securities.query'))

    cursor.execute(
        'INSERT INTO securities (user_id, broker, record_date, operation_type, asset_type, stock_code, code_id, stock_name, '
        'unit_price, quantity, total_amount, fees, status) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (current_user_id, broker, record_date, operation_type, asset_type, stock_code, code_id or None, stock_name,
         unit_price, quantity, total_amount, fees, status)
    )
    db.commit()

    # 同步统计汇总表
    if code_id:
        sync_statistics_summary(cursor, db, code_id, user_id=current_user_id)
        db.commit()

    # 卖出时自动判断是否结清：相同 code_id + stock_code 的卖出数量 >= 买入数量时，自动结清并写入结算记录
    if operation_type == '卖出':
        auto_settle(cursor, db, stock_code, code_id or None, stock_name, asset_type, record_date, current_user_id)

    cursor.close()
    db.close()

    flash('证券记录添加成功', 'success')
    from urllib.parse import urlencode
    # 新增完成后按本次提交的关联编号（code_id）自动查询，便于直接看到该笔及其同组记录
    params = {}
    if code_id:
        params['code_id'] = code_id
    elif record_date:
        params['date_from'] = record_date
        params['date_to'] = record_date
    return redirect(url_for('securities.query') + '?' + urlencode(params))


def auto_settle(cursor, db, stock_code, code_id_param, stock_name, asset_type, record_date, user_id):
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
          AND user_id = %s
    """, (stock_code, code_id_param, user_id))
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
          AND user_id = %s
    """, (stock_code, code_id_param, user_id))
    sell_row = cursor.fetchone()
    sell_qty = float(sell_row['sell_qty'])
    sell_amount = float(sell_row['sell_amount'])
    sell_fees = float(sell_row['sell_fees'])

    # 利息收入
    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS interest_amount,
               COALESCE(SUM(fees), 0) AS interest_fees
        FROM securities
        WHERE stock_code = %s
          AND IFNULL(code_id, '') = IFNULL(%s, '')
          AND operation_type = '利息'
          AND user_id = %s
    """, (stock_code, code_id_param, user_id))
    interest_row = cursor.fetchone()
    interest_amount = float(interest_row['interest_amount'])
    interest_fees = float(interest_row['interest_fees'])

    if sell_qty >= buy_qty and buy_qty > 0:
        # 标记相同 code_id + stock_code 的所有记录为「结清」
        cursor.execute("""
            UPDATE securities SET status = '结清'
            WHERE stock_code = %s
              AND IFNULL(code_id, '') = IFNULL(%s, '')
              AND user_id = %s
        """, (stock_code, code_id_param, user_id))

        # 总费用 = 买入费用 + 卖出费用 + 利息费用
        total_fees = buy_fees + sell_fees + interest_fees

        # 持有天数
        from datetime import datetime
        holding_days = None
        if first_buy_date and record_date:
            holding_days = (datetime.strptime(str(record_date), '%Y-%m-%d') -
                            datetime.strptime(str(first_buy_date), '%Y-%m-%d')).days

        # 收益 = (卖出金额 + 利息) - 买入金额 - 费用总和
        total_settle = sell_amount + interest_amount
        profit = total_settle - buy_amount - total_fees

        cursor.execute(
            'INSERT INTO settlements (user_id, settle_date, code, code_id, product_name, asset_type, '
            'invest_amount, settle_amount, profit, fees, holding_days) '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
            (user_id, record_date, stock_code, code_id_param, stock_name, asset_type,
             buy_amount, total_settle, profit, total_fees, holding_days)
        )
        db.commit()
        # 同步统计汇总表
        if code_id_param:
            sync_statistics_summary(cursor, db, code_id_param, user_id=user_id)
            db.commit()
        flash('已自动结清，收益：¥{:,.2f}（含利息 ¥{:,.2f}），费用：¥{:,.2f}，持有 {} 天'.format(
            profit, interest_amount, total_fees, holding_days if holding_days else '?'), 'info')
