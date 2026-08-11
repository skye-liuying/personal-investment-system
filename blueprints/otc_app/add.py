"""场外APP管理 — 新增功能（POST /add）"""

from flask import flash, redirect, request, url_for
from . import otc_app_bp
from database import get_db
from blueprints.statistics.sync import sync_statistics_summary


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

    if not all([app_name, record_date, operation_type, asset_type, product_name, total_amount]):
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
    fees = float(fees) if fees else 0.0

    # 状态由操作类型决定：买入/利息 → 持有，卖出 → 持有（卖出后可能触发自动结清）
    status = '持有'

    db = get_db()
    cursor = db.cursor()

    # 卖出时校验数量不能超过持有数量
    if operation_type == '卖出' and quantity:
        code_id_val = code_id or None
        cursor.execute("""
            SELECT COALESCE(SUM(CASE WHEN operation_type='买入' THEN quantity ELSE -quantity END), 0) AS hold_qty
            FROM otc_app
            WHERE product_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND status = '持有'
        """, (product_code, code_id_val))
        row = cursor.fetchone()
        hold_qty = float(row['hold_qty']) if row and row['hold_qty'] else 0
        if quantity > hold_qty:
            cursor.close()
            db.close()
            flash(f'卖出数量（{quantity}）不能超过持有数量（{hold_qty}）', 'error')
            return redirect(url_for('otc_app.query'))

    cursor.execute(
        'INSERT INTO otc_app (app_name, record_date, operation_type, asset_type, product_code, code_id, product_name, '
        'unit_price, quantity, total_amount, fees, status) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (app_name, record_date, operation_type, asset_type, product_code, code_id or None, product_name,
         unit_price, quantity, total_amount, fees, status)
    )
    db.commit()

    # 同步统计汇总表
    if code_id:
        sync_statistics_summary(cursor, db, code_id)
        db.commit()

    # 卖出时自动检查是否可结清
    if operation_type == '卖出' and quantity and code_id:
        _try_settle(cursor, db, code_id, product_code, product_name, asset_type, record_date)
    elif operation_type == '卖出' and quantity:
        # 没有关联编号时，仅按产品代码匹配
        _try_settle(cursor, db, None, product_code, product_name, asset_type, record_date)

    cursor.close()
    db.close()

    flash('场外APP记录添加成功', 'success')
    # 保存后自动查询今日记录
    return redirect(url_for('otc_app.query', date_from=record_date, date_to=record_date))


def _try_settle(cursor, db, code_id, product_code, product_name, asset_type, settle_date):
    """检查卖出后是否需要自动结清此产品，并在结清查询页插入记录"""
    if code_id:
        where_buy = "code_id = %s AND product_code = %s AND operation_type = %s AND status = '持有'"
        where_all = "code_id = %s AND product_code = %s AND status = '持有'"
        params_match = (code_id, product_code)
    else:
        where_buy = "code_id IS NULL AND product_code = %s AND operation_type = %s AND status = '持有'"
        where_all = "code_id IS NULL AND product_code = %s AND status = '持有'"
        params_match = (product_code,)

    # 买入总份额
    cursor.execute(
        f'SELECT COALESCE(SUM(quantity), 0) AS buy_qty FROM otc_app WHERE {where_buy}',
        (*params_match, '买入')
    )
    buy_qty = float(cursor.fetchone()['buy_qty'])

    # 卖出总份额
    cursor.execute(
        f'SELECT COALESCE(SUM(quantity), 0) AS sell_qty FROM otc_app WHERE {where_buy}',
        (*params_match, '卖出')
    )
    sell_qty = float(cursor.fetchone()['sell_qty'])

    # 份额相等且 > 0 → 触发自动结清
    if buy_qty <= 0 or abs(sell_qty - buy_qty) > 0.0001:
        return

    # 先计算结清汇总数据（此时记录仍为持有，故使用 status='持有' 过滤）
    cursor.execute(
        f"""SELECT
               COALESCE(SUM(CASE WHEN operation_type = '买入' THEN total_amount ELSE 0 END), 0) AS invest_total,
               COALESCE(SUM(CASE WHEN operation_type IN ('卖出', '利息') THEN total_amount ELSE 0 END), 0) AS settle_total,
               COALESCE(SUM(COALESCE(fees, 0)), 0) AS total_fees,
               DATEDIFF(MAX(record_date), MIN(record_date)) AS hold_days
           FROM otc_app
           WHERE {where_all}""",
        params_match
    )
    row = cursor.fetchone()

    # 将该产品所有记录标记为结清
    cursor.execute(
        f"UPDATE otc_app SET status = '结清' WHERE {where_all}",
        params_match
    )
    invest_amount = float(row['invest_total'])
    settle_amount = float(row['settle_total'])
    total_fees = float(row['total_fees'])
    holding_days = int(row['hold_days']) if row['hold_days'] is not None else None
    profit = settle_amount - invest_amount - total_fees

    # 插入结清记录
    cursor.execute(
        'INSERT INTO settlements (settle_date, code, code_id, product_name, asset_type, '
        'invest_amount, settle_amount, profit, fees, holding_days, quantity) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (settle_date, product_code, code_id or None, product_name, asset_type,
         invest_amount, settle_amount, profit, total_fees, holding_days, buy_qty)
    )
    db.commit()
    # 同步统计汇总表
    if code_id:
        sync_statistics_summary(cursor, db, code_id)
        db.commit()

    flash(f'卖出份额与买入份额相等，{product_name}（{product_code}）已自动结清，记录已写入结清查询页', 'success')
