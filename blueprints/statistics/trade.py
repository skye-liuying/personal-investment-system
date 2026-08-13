"""统计分析 — 买入/卖出操作（POST /trade），根据来源保存到对应表"""

from datetime import datetime

from flask import flash, redirect, request, url_for
from . import statistics_bp
from database import get_db
from .sync import sync_statistics_summary
from blueprints.auth.helpers import get_current_user_id


@statistics_bp.route('/trade', methods=['POST'])
def trade():
    current_user_id = get_current_user_id()

    source = request.form.get('source', '').strip()
    broker = request.form.get('broker', '').strip()
    record_date = request.form.get('record_date', '').strip()
    operation_type = request.form.get('operation_type', '').strip()  # '买入' or '卖出'
    asset_type = request.form.get('asset_type', '').strip()
    code = request.form.get('code', '').strip()
    code_id = request.form.get('code_id', '').strip()
    name = request.form.get('name', '').strip()
    total_amount = request.form.get('total_amount', '').strip()
    fees = request.form.get('fees', '').strip()

    if not all([source, broker, record_date, operation_type, asset_type, code, code_id, name, total_amount]):
        flash('请填写所有必填字段', 'error')
        return redirect(url_for('statistics.query'))

    try:
        total_amount = float(total_amount)
    except (ValueError, TypeError):
        flash('总金额格式不正确', 'error')
        return redirect(url_for('statistics.query'))

    unit_price = request.form.get('unit_price', '').strip()
    quantity = request.form.get('quantity', '').strip()
    unit_price = float(unit_price) if unit_price else None
    quantity = int(float(quantity)) if quantity and source == 'securities' else (float(quantity) if quantity else None)
    fees = float(fees) if fees else 0.0
    code_id_val = code_id or None

    db = get_db()
    cursor = db.cursor()

    if source == 'securities':
        # 卖出时校验数量
        if operation_type == '卖出' and quantity:
            cursor.execute("""
                SELECT COALESCE(SUM(CASE WHEN operation_type='买入' THEN quantity ELSE -quantity END), 0) AS hold_qty
                FROM securities
                WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND status = '持有' AND user_id = %s
            """, (code, code_id_val, current_user_id))
            row = cursor.fetchone()
            hold_qty = int(row['hold_qty']) if row and row['hold_qty'] else 0
            if quantity > hold_qty:
                cursor.close()
                db.close()
                flash(f'卖出数量（{quantity}）不能超过持有数量（{hold_qty}）', 'error')
                return redirect(url_for('statistics.query'))

        cursor.execute(
            'INSERT INTO securities (user_id, broker, record_date, operation_type, asset_type, stock_code, '
            'code_id, stock_name, unit_price, quantity, total_amount, fees, status) '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
            (current_user_id, broker, record_date, operation_type, asset_type, code, code_id_val,
             name, unit_price, quantity, total_amount, fees, '持有')
        )
    elif source == 'otc_app':
        # 卖出时校验数量
        if operation_type == '卖出' and quantity:
            cursor.execute("""
                SELECT COALESCE(SUM(CASE WHEN operation_type='买入' THEN quantity ELSE -quantity END), 0) AS hold_qty
                FROM otc_app
                WHERE product_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND status = '持有' AND user_id = %s
            """, (code, code_id_val, current_user_id))
            row = cursor.fetchone()
            hold_qty = float(row['hold_qty']) if row and row['hold_qty'] else 0
            if quantity > hold_qty:
                cursor.close()
                db.close()
                flash(f'卖出数量（{quantity}）不能超过持有数量（{hold_qty}）', 'error')
                return redirect(url_for('statistics.query'))

        cursor.execute(
            'INSERT INTO otc_app (user_id, app_name, record_date, operation_type, asset_type, product_code, '
            'code_id, product_name, unit_price, quantity, total_amount, fees, status) '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
            (current_user_id, broker, record_date, operation_type, asset_type, code, code_id_val,
             name, unit_price, quantity, total_amount, fees, '持有')
        )
    else:
        cursor.close()
        db.close()
        flash('请选择有效来源（securities / otc_app）', 'error')
        return redirect(url_for('statistics.query'))

    db.commit()

    # 同步统计汇总表
    sync_statistics_summary(cursor, db, code_id_val, user_id=current_user_id)
    db.commit()

    # 卖出时自动检查是否可结清
    if operation_type == '卖出' and code_id_val:
        if source == 'securities':
            _auto_settle_securities(cursor, db, code, code_id_val, name, asset_type, record_date, current_user_id)
        else:
            _auto_settle_otc(cursor, db, code, code_id_val, name, asset_type, record_date, current_user_id)

    cursor.close()
    db.close()

    flash(f'{operation_type}记录添加成功（来源：{source}）', 'success')
    return redirect(url_for('statistics.query'))


def _auto_settle_securities(cursor, db, stock_code, code_id, stock_name, asset_type, record_date, user_id):
    """证券：卖出后剩余份额为0时，自动结清（仅统计当前用户的数据）"""
    # 买入总份额
    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS buy_qty
        FROM securities
        WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '')
          AND operation_type = '买入' AND status = '持有' AND user_id = %s
    """, (stock_code, code_id, user_id))
    buy_qty = float(cursor.fetchone()['buy_qty'])

    # 卖出总份额
    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS sell_qty
        FROM securities
        WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '')
          AND operation_type = '卖出' AND status = '持有' AND user_id = %s
    """, (stock_code, code_id, user_id))
    sell_qty = float(cursor.fetchone()['sell_qty'])

    if buy_qty <= 0 or sell_qty < buy_qty + 0.0001 - 0.0001:
        return

    # 计算结清汇总
    cursor.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN operation_type='买入' THEN total_amount ELSE 0 END), 0) AS buy_amount,
            COALESCE(SUM(CASE WHEN operation_type='买入' THEN COALESCE(fees, 0) ELSE 0 END), 0) AS buy_fees,
            COALESCE(SUM(CASE WHEN operation_type='卖出' THEN total_amount ELSE 0 END), 0) AS sell_amount,
            COALESCE(SUM(CASE WHEN operation_type='卖出' THEN COALESCE(fees, 0) ELSE 0 END), 0) AS sell_fees,
            COALESCE(SUM(CASE WHEN operation_type='利息' THEN total_amount ELSE 0 END), 0) AS interest_amount,
            COALESCE(SUM(CASE WHEN operation_type='利息' THEN COALESCE(fees, 0) ELSE 0 END), 0) AS interest_fees,
            MIN(record_date) AS first_date,
            MAX(record_date) AS last_date
        FROM securities
        WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND status = '持有' AND user_id = %s
    """, (stock_code, code_id, user_id))
    row = cursor.fetchone()
    buy_amount = float(row['buy_amount'])
    buy_fees = float(row['buy_fees'])
    sell_amount = float(row['sell_amount'])
    sell_fees = float(row['sell_fees'])
    interest_amount = float(row['interest_amount'])
    interest_fees = float(row['interest_fees'])
    first_date = row['first_date']
    last_date = row['last_date']

    # 标记所有记录为结清（仅当前用户）
    cursor.execute("""
        UPDATE securities SET status = '结清'
        WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND user_id = %s
    """, (stock_code, code_id, user_id))

    total_fees = buy_fees + sell_fees + interest_fees
    total_settle = sell_amount + interest_amount
    profit = total_settle - buy_amount - total_fees

    holding_days = None
    if first_date and (record_date or last_date):
        end_date = record_date if record_date else str(last_date)
        holding_days = (datetime.strptime(end_date, '%Y-%m-%d') -
                        datetime.strptime(str(first_date), '%Y-%m-%d')).days

    cursor.execute(
        'INSERT INTO settlements (user_id, settle_date, code, code_id, product_name, asset_type, '
        'invest_amount, settle_amount, profit, fees, holding_days) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (user_id, record_date, stock_code, code_id, stock_name, asset_type,
         buy_amount, total_settle, profit, total_fees, holding_days)
    )
    db.commit()
    # 结清后同步统计汇总表（sync 会删除该记录）
    sync_statistics_summary(cursor, db, code_id, user_id=user_id)
    db.commit()

    flash(f'已自动结清，收益：¥{profit:,.2f}（含利息 ¥{interest_amount:,.2f}），费用：¥{total_fees:,.2f}，持有 {holding_days if holding_days else "?"} 天', 'info')


def _auto_settle_otc(cursor, db, product_code, code_id, product_name, asset_type, settle_date, user_id):
    """场外APP：卖出后剩余份额为0时，自动结清（仅统计当前用户的数据）"""
    # 买入总份额
    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS buy_qty
        FROM otc_app
        WHERE code_id = %s AND product_code = %s AND operation_type = '买入' AND status = '持有' AND user_id = %s
    """, (code_id, product_code, user_id))
    buy_qty = float(cursor.fetchone()['buy_qty'])

    # 卖出总份额
    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS sell_qty
        FROM otc_app
        WHERE code_id = %s AND product_code = %s AND operation_type = '卖出' AND status = '持有' AND user_id = %s
    """, (code_id, product_code, user_id))
    sell_qty = float(cursor.fetchone()['sell_qty'])

    if buy_qty <= 0 or abs(sell_qty - buy_qty) > 0.0001:
        return

    # 计算结清汇总
    cursor.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN operation_type='买入' THEN total_amount ELSE 0 END), 0) AS invest_total,
            COALESCE(SUM(CASE WHEN operation_type IN ('卖出', '利息') THEN total_amount ELSE 0 END), 0) AS settle_total,
            COALESCE(SUM(COALESCE(fees, 0)), 0) AS total_fees,
            DATEDIFF(MAX(record_date), MIN(record_date)) AS hold_days
        FROM otc_app
        WHERE code_id = %s AND product_code = %s AND status = '持有' AND user_id = %s
    """, (code_id, product_code, user_id))
    row = cursor.fetchone()

    # 标记所有记录为结清（仅当前用户）
    cursor.execute("""
        UPDATE otc_app SET status = '结清'
        WHERE code_id = %s AND product_code = %s AND status = '持有' AND user_id = %s
    """, (code_id, product_code, user_id))

    invest_amount = float(row['invest_total'])
    settle_amount = float(row['settle_total'])
    total_fees = float(row['total_fees'])
    holding_days = int(row['hold_days']) if row['hold_days'] is not None else None
    profit = settle_amount - invest_amount - total_fees

    cursor.execute(
        'INSERT INTO settlements (user_id, settle_date, code, code_id, product_name, asset_type, '
        'invest_amount, settle_amount, profit, fees, holding_days, quantity) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (user_id, settle_date, product_code, code_id, product_name, asset_type,
         invest_amount, settle_amount, profit, total_fees, holding_days, buy_qty)
    )
    db.commit()
    # 结清后同步统计汇总表（sync 会删除该记录）
    sync_statistics_summary(cursor, db, code_id, user_id=user_id)
    db.commit()

    flash(f'卖出份额与买入份额相等，{product_name}（{product_code}）已自动结清，记录已写入结清查询页', 'success')
