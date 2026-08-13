"""统计分析 — 结清功能（POST /settle）"""

from datetime import datetime

from flask import flash, redirect, request, url_for
from . import statistics_bp
from database import get_db
from .sync import sync_statistics_summary
from blueprints.auth.helpers import get_current_user_id


@statistics_bp.route('/settle', methods=['POST'])
def settle():
    current_user_id = get_current_user_id()

    code = request.form.get('code', '').strip()
    code_id = request.form.get('code_id', '').strip()
    source = request.form.get('source', '').strip()
    settle_date = request.form.get('settle_date', '').strip()
    unit_price = request.form.get('unit_price', '').strip()
    quantity = request.form.get('quantity', '').strip()
    total_amount = request.form.get('total_amount', '').strip()
    fees = request.form.get('fees', '').strip()
    product_name = request.form.get('product_name', '').strip()
    asset_type = request.form.get('asset_type', '').strip()

    if not all([code, settle_date, total_amount]):
        flash('请填写所有必填字段', 'error')
        return redirect(url_for('statistics.query'))

    try:
        total_amount = float(total_amount)
    except (ValueError, TypeError):
        flash('总金额格式不正确', 'error')
        return redirect(url_for('statistics.query'))

    unit_price = float(unit_price) if unit_price else None
    quantity = float(quantity) if quantity else None
    fees = float(fees) if fees else 0.0
    code_id_val = code_id or None

    db = get_db()
    cursor = db.cursor()

    # 根据来源表插入卖出记录
    if source == 'securities':
        cursor.execute(
            'SELECT broker FROM securities WHERE stock_code = %s'
            ' AND IFNULL(code_id, \'\') = IFNULL(%s, \'\') AND user_id = %s LIMIT 1',
            (code, code_id_val, current_user_id)
        )
        row = cursor.fetchone()
        broker = row['broker'] if row else ''

        cursor.execute(
            'INSERT INTO securities (user_id, broker, record_date, operation_type, stock_code, code_id,'
            ' stock_name, unit_price, quantity, total_amount, fees, asset_type, status) '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
            (current_user_id, broker, settle_date, '卖出', code, code_id_val, product_name,
             unit_price, quantity, total_amount, fees, asset_type, '持有')
        )
    elif source == 'otc_app':
        cursor.execute(
            'SELECT app_name FROM otc_app WHERE product_code = %s'
            ' AND IFNULL(code_id, \'\') = IFNULL(%s, \'\') AND user_id = %s LIMIT 1',
            (code, code_id_val, current_user_id)
        )
        row = cursor.fetchone()
        app_name = row['app_name'] if row else ''

        cursor.execute(
            'INSERT INTO otc_app (user_id, app_name, record_date, operation_type, product_code, code_id,'
            ' product_name, unit_price, quantity, total_amount, fees, asset_type, status) '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
            (current_user_id, app_name, settle_date, '卖出', code, code_id_val, product_name,
             unit_price, quantity, total_amount, fees, asset_type, '持有')
        )
    else:
        flash('无法识别产品来源', 'error')
        cursor.close()
        db.close()
        return redirect(url_for('statistics.query'))

    db.commit()

    # 更新证券表状态为'结清'（仅当前用户的数据）
    cursor.execute("""
        UPDATE securities SET status = '结清'
        WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND status = '持有' AND user_id = %s
    """, (code, code_id_val, current_user_id))

    # 更新场外APP表状态为'结清'（仅当前用户的数据）
    cursor.execute("""
        UPDATE otc_app SET status = '结清'
        WHERE product_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND status = '持有' AND user_id = %s
    """, (code, code_id_val, current_user_id))

    # 汇总投资金额与费用（仅当前用户的数据）
    invest_amount = 0
    total_fees = 0
    interest_amount = 0
    first_buy_date = None
    buy_qty = 0

    cursor.execute("""
        SELECT MAX(stock_name) AS product_name, MAX(asset_type) AS asset_type,
               COALESCE(SUM(total_amount), 0) AS invest_amount,
               COALESCE(SUM(fees), 0) AS buy_fees,
               COALESCE(SUM(quantity), 0) AS buy_qty,
               MIN(record_date) AS min_date
        FROM securities
        WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND operation_type = '买入' AND user_id = %s
    """, (code, code_id_val, current_user_id))
    row = cursor.fetchone()
    if row and row['invest_amount']:
        invest_amount += float(row['invest_amount'])
        total_fees += float(row['buy_fees'])
        buy_qty += float(row['buy_qty'])
        if not product_name:
            product_name = row['product_name']
        if not asset_type:
            asset_type = row['asset_type']
        if row['min_date']:
            first_buy_date = row['min_date']

    cursor.execute("""
        SELECT MAX(product_name) AS product_name, MAX(asset_type) AS asset_type,
               COALESCE(SUM(total_amount), 0) AS invest_amount,
               COALESCE(SUM(fees), 0) AS buy_fees,
               COALESCE(SUM(quantity), 0) AS buy_qty,
               MIN(record_date) AS min_date
        FROM otc_app
        WHERE product_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND operation_type = '买入' AND user_id = %s
    """, (code, code_id_val, current_user_id))
    row = cursor.fetchone()
    if row and row['invest_amount']:
        invest_amount += float(row['invest_amount'])
        total_fees += float(row['buy_fees'])
        buy_qty += float(row['buy_qty'])
        if not product_name:
            product_name = row['product_name']
        if not asset_type:
            asset_type = row['asset_type']
        if row['min_date'] and (first_buy_date is None or row['min_date'] < first_buy_date):
            first_buy_date = row['min_date']

    # 加上卖出的费用（含本次插入的卖出记录）
    cursor.execute("""
        SELECT COALESCE(SUM(fees), 0) AS sell_fees
        FROM securities
        WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND operation_type = '卖出' AND user_id = %s
    """, (code, code_id_val, current_user_id))
    row = cursor.fetchone()
    if row:
        total_fees += float(row['sell_fees'])

    cursor.execute("""
        SELECT COALESCE(SUM(fees), 0) AS sell_fees
        FROM otc_app
        WHERE product_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND operation_type = '卖出' AND user_id = %s
    """, (code, code_id_val, current_user_id))
    row = cursor.fetchone()
    if row:
        total_fees += float(row['sell_fees'])

    # 利息费用
    cursor.execute("""
        SELECT COALESCE(SUM(fees), 0) AS interest_fees
        FROM securities
        WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND operation_type = '利息' AND user_id = %s
    """, (code, code_id_val, current_user_id))
    row = cursor.fetchone()
    if row:
        total_fees += float(row['interest_fees'])

    cursor.execute("""
        SELECT COALESCE(SUM(fees), 0) AS interest_fees
        FROM otc_app
        WHERE product_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND operation_type = '利息' AND user_id = %s
    """, (code, code_id_val, current_user_id))
    row = cursor.fetchone()
    if row:
        total_fees += float(row['interest_fees'])

    # 持有天数
    holding_days = None
    if first_buy_date and settle_date:
        holding_days = (datetime.strptime(str(settle_date), '%Y-%m-%d') -
                        datetime.strptime(str(first_buy_date), '%Y-%m-%d')).days

    # 收益 = (卖出总金额 + 利息) - 买入总金额 - 费用总和
    settle_total = 0
    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS settle_total
        FROM securities
        WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND operation_type = '卖出' AND user_id = %s
    """, (code, code_id_val, current_user_id))
    row = cursor.fetchone()
    if row:
        settle_total += float(row['settle_total'])

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS settle_total
        FROM otc_app
        WHERE product_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND operation_type = '卖出' AND user_id = %s
    """, (code, code_id_val, current_user_id))
    row = cursor.fetchone()
    if row:
        settle_total += float(row['settle_total'])

    # 加上利息收入
    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS interest_amount
        FROM securities
        WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND operation_type = '利息' AND user_id = %s
    """, (code, code_id_val, current_user_id))
    row = cursor.fetchone()
    if row:
        interest_amount += float(row['interest_amount'])

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS interest_amount
        FROM otc_app
        WHERE product_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND operation_type = '利息' AND user_id = %s
    """, (code, code_id_val, current_user_id))
    row = cursor.fetchone()
    if row:
        interest_amount += float(row['interest_amount'])

    settle_total += interest_amount

    profit = settle_total - invest_amount - total_fees

    # 写入结算记录（带 user_id）
    cursor.execute(
        'INSERT INTO settlements (user_id, settle_date, code, code_id, product_name, asset_type,'
        ' invest_amount, settle_amount, profit, fees, holding_days, quantity) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (current_user_id, settle_date, code, code_id_val, product_name, asset_type,
         invest_amount, settle_total, profit, total_fees, holding_days, buy_qty)
    )
    db.commit()

    # 同步统计汇总表
    if code_id_val:
        sync_statistics_summary(cursor, db, code_id_val, user_id=current_user_id)
        db.commit()

    cursor.close()
    db.close()

    if interest_amount > 0:
        flash('产品结清成功，收益：¥{:,.2f}（含利息 ¥{:,.2f}）'.format(profit, interest_amount), 'success')
    else:
        flash('产品结清成功，收益：¥{:,.2f}'.format(profit), 'success')
    return redirect(url_for('statistics.query'))
