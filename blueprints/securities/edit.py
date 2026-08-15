"""证券管理 — 编辑功能（GET/POST /edit/<int:id>）

GET 返回记录 JSON 供前端编辑弹窗回填；POST 更新记录。
数据隔离：admin 可编辑全部；组长可编辑自己和组员；普通用户只能编辑自己的。
"""

from datetime import datetime

from flask import flash, jsonify, redirect, request, url_for
from . import securities_bp
from database import get_db
from blueprints.auth.helpers import owner_condition
from blueprints.statistics.sync import sync_statistics_summary


@securities_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    db = get_db()
    cursor = db.cursor()

    # ——— 数据隔离：admin 可编辑全部；组长可编辑自己和组员；普通用户只能编辑自己的 ———
    owner_sql, owner_params = owner_condition()

    cursor.execute('SELECT * FROM securities WHERE id = %s' + owner_sql, (id,) + owner_params)
    record = cursor.fetchone()
    if not record:
        cursor.close()
        db.close()
        if request.method == 'GET':
            return jsonify({'error': '记录不存在或无权操作'}), 404
        flash('记录不存在或无权操作', 'error')
        return redirect(url_for('securities.query'))

    # ——— GET：返回 JSON 供编辑弹窗回填 ———
    if request.method == 'GET':
        data = {
            'id': record['id'],
            'broker': record['broker'],
            'record_date': str(record['record_date']),
            'operation_type': record['operation_type'],
            'asset_type': record['asset_type'],
            'stock_code': record['stock_code'],
            'code_id': record['code_id'] or '',
            'stock_name': record['stock_name'],
            'unit_price': float(record['unit_price']) if record['unit_price'] is not None else '',
            'quantity': record['quantity'] if record['quantity'] is not None else '',
            'total_amount': float(record['total_amount']),
            'fees': float(record['fees']) if record['fees'] is not None else 0,
        }
        cursor.close()
        db.close()
        return jsonify(data)

    # ——— POST：更新记录 ———
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
    quantity = int(float(quantity)) if quantity else None
    fees = float(fees) if fees else None

    # 记录归属账号（组长编辑组员数据时保持归属不变）
    record_owner = record['user_id']

    # 卖出时校验数量不能超过持有数量（编辑时排除自身记录）
    if operation_type == '卖出' and quantity:
        code_id_val = code_id or None
        cursor.execute("""
            SELECT COALESCE(SUM(CASE WHEN operation_type='买入' THEN quantity ELSE -quantity END), 0) AS hold_qty
            FROM securities
            WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND status = '持有'
              AND user_id = %s AND id != %s
        """, (stock_code, code_id_val, record_owner, id))
        row = cursor.fetchone()
        hold_qty = int(row['hold_qty']) if row and row['hold_qty'] else 0
        # 自身原数量（编辑时保持原值应被允许，避免历史超卖数据无法保存）
        original_qty = int(record['quantity']) if record['quantity'] else 0
        max_allowed = max(original_qty, hold_qty)
        if quantity > max_allowed:
            cursor.close()
            db.close()
            flash(f'卖出数量（{quantity}）不能超过持有数量（{max_allowed}）', 'error')
            return redirect(url_for('securities.query'))

    old_code_id = record['code_id'] or None

    cursor.execute(
        'UPDATE securities SET broker=%s, record_date=%s, operation_type=%s, asset_type=%s, stock_code=%s, '
        'code_id=%s, stock_name=%s, unit_price=%s, quantity=%s, total_amount=%s, fees=%s '
        'WHERE id=%s' + owner_sql,
        (broker, record_date, operation_type, asset_type, stock_code, code_id or None, stock_name,
         unit_price, quantity, total_amount, fees, id) + owner_params
    )
    db.commit()

    # ——— 同步统计汇总表：新旧 code_id 都要处理 ———
    new_code_id = code_id or None
    for cid in {old_code_id, new_code_id}:
        if cid:
            sync_statistics_summary(cursor, db, cid, user_id=record_owner)
            db.commit()

    # ——— 编辑后若为卖出记录，重新评估结清状态（UPSERT settlements，避免重复插入）———
    if operation_type == '卖出':
        recalc_settle(cursor, db, stock_code, new_code_id, stock_name, asset_type, record_date, record_owner)

    cursor.close()
    db.close()

    flash('证券记录修改成功', 'success')
    return redirect(url_for('securities.query'))


def recalc_settle(cursor, db, stock_code, code_id_param, stock_name, asset_type, record_date, user_id):
    """编辑卖出记录后重算结清状态：

    若同一 code_id + stock_code 的卖出数量 >= 买入数量，则标记结清，
    并更新（或新增）settlements 记录，避免重复插入。
    """
    if not stock_code:
        return

    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS buy_qty,
               COALESCE(SUM(total_amount), 0) AS buy_amount,
               COALESCE(SUM(fees), 0) AS buy_fees,
               MIN(record_date) AS first_buy_date
        FROM securities
        WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '')
          AND operation_type = '买入' AND user_id = %s
    """, (stock_code, code_id_param, user_id))
    buy_row = cursor.fetchone()
    buy_qty = float(buy_row['buy_qty'] or 0)
    buy_amount = float(buy_row['buy_amount'] or 0)
    buy_fees = float(buy_row['buy_fees'] or 0)
    first_buy_date = buy_row['first_buy_date']

    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS sell_qty,
               COALESCE(SUM(total_amount), 0) AS sell_amount,
               COALESCE(SUM(fees), 0) AS sell_fees
        FROM securities
        WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '')
          AND operation_type = '卖出' AND user_id = %s
    """, (stock_code, code_id_param, user_id))
    sell_row = cursor.fetchone()
    sell_qty = float(sell_row['sell_qty'] or 0)
    sell_amount = float(sell_row['sell_amount'] or 0)
    sell_fees = float(sell_row['sell_fees'] or 0)

    # 利息收入
    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS interest_amount,
               COALESCE(SUM(fees), 0) AS interest_fees
        FROM securities
        WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '')
          AND operation_type = '利息' AND user_id = %s
    """, (stock_code, code_id_param, user_id))
    interest_row = cursor.fetchone()
    interest_amount = float(interest_row['interest_amount'] or 0)
    interest_fees = float(interest_row['interest_fees'] or 0)

    if not (sell_qty >= buy_qty and buy_qty > 0):
        return

    # 标记该 code 组所有记录为「结清」
    cursor.execute("""
        UPDATE securities SET status = '结清'
        WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND user_id = %s
    """, (stock_code, code_id_param, user_id))

    # 总费用 = 买入费用 + 卖出费用 + 利息费用
    total_fees = buy_fees + sell_fees + interest_fees

    # 持有天数
    holding_days = None
    if first_buy_date and record_date:
        holding_days = (datetime.strptime(str(record_date), '%Y-%m-%d') -
                        datetime.strptime(str(first_buy_date), '%Y-%m-%d')).days

    # 收益 = (卖出金额 + 利息) - 买入金额 - 费用总和
    total_settle = sell_amount + interest_amount
    profit = total_settle - buy_amount - total_fees

    # UPSERT settlements：存在则更新，不存在则插入
    cursor.execute("""
        SELECT id FROM settlements
        WHERE code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND user_id = %s
        ORDER BY id DESC LIMIT 1
    """, (stock_code, code_id_param, user_id))
    existing = cursor.fetchone()
    if existing:
        cursor.execute(
            'UPDATE settlements SET settle_date=%s, product_name=%s, asset_type=%s, invest_amount=%s, '
            'settle_amount=%s, profit=%s, fees=%s, holding_days=%s WHERE id=%s',
            (record_date, stock_name, asset_type, buy_amount, total_settle, profit, total_fees,
             holding_days, existing['id'])
        )
    else:
        cursor.execute(
            'INSERT INTO settlements (user_id, settle_date, code, code_id, product_name, asset_type, '
            'invest_amount, settle_amount, profit, fees, holding_days) '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
            (user_id, record_date, stock_code, code_id_param, stock_name, asset_type,
             buy_amount, total_settle, profit, total_fees, holding_days)
        )
    db.commit()

    if code_id_param:
        sync_statistics_summary(cursor, db, code_id_param, user_id=user_id)
        db.commit()
