"""结清查询 — 数据矫正功能（POST /correct）

根据公式重新计算结清记录：
  收益 = (卖出总金额 + 利息) - 买入总金额 - (买入手续费 + 卖出手续费 + 利息手续费)
"""

from datetime import datetime

from flask import flash, redirect, request, url_for
from . import settlement_bp
from database import get_db


@settlement_bp.route('/correct', methods=['POST'])
def correct():
    record_id = request.form.get('id', '').strip()

    if not record_id:
        flash('缺少记录 ID', 'error')
        return redirect(url_for('settlement.query'))

    db = get_db()
    cursor = db.cursor()

    # ——— 查找结清记录 ———
    cursor.execute('SELECT * FROM settlements WHERE id = %s', (record_id,))
    settle = cursor.fetchone()
    if not settle:
        cursor.close()
        db.close()
        flash('未找到对应的结清记录', 'error')
        return redirect(url_for('settlement.query'))

    code = settle['code']
    code_id = settle['code_id'] or None

    invest_amount = 0.0
    total_fees = 0.0
    sell_total = 0.0
    interest_amount = 0.0
    buy_qty = 0.0
    first_buy_date = None

    # ——— 从 securities 汇总 ———
    cursor.execute("""
        SELECT MAX(stock_name) AS product_name, MAX(asset_type) AS asset_type,
               COALESCE(SUM(total_amount), 0) AS invest_amount,
               COALESCE(SUM(fees), 0) AS buy_fees,
               COALESCE(SUM(quantity), 0) AS buy_qty,
               MIN(record_date) AS min_date
        FROM securities
        WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND operation_type = '买入'
    """, (code, code_id))
    row = cursor.fetchone()
    if row and row['invest_amount']:
        invest_amount += float(row['invest_amount'])
        total_fees += float(row['buy_fees'])
        buy_qty += float(row['buy_qty'])
        if row['min_date']:
            first_buy_date = row['min_date']

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS settle_total,
               COALESCE(SUM(fees), 0) AS sell_fees
        FROM securities
        WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND operation_type = '卖出'
    """, (code, code_id))
    row = cursor.fetchone()
    if row:
        sell_total += float(row['settle_total'])
        total_fees += float(row['sell_fees'])

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS interest_amount,
               COALESCE(SUM(fees), 0) AS interest_fees
        FROM securities
        WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND operation_type = '利息'
    """, (code, code_id))
    row = cursor.fetchone()
    if row:
        interest_amount += float(row['interest_amount'])
        total_fees += float(row['interest_fees'])

    # ——— 从 otc_app 汇总 ———
    cursor.execute("""
        SELECT MAX(product_name) AS product_name, MAX(asset_type) AS asset_type,
               COALESCE(SUM(total_amount), 0) AS invest_amount,
               COALESCE(SUM(fees), 0) AS buy_fees,
               COALESCE(SUM(quantity), 0) AS buy_qty,
               MIN(record_date) AS min_date
        FROM otc_app
        WHERE product_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND operation_type = '买入'
    """, (code, code_id))
    row = cursor.fetchone()
    if row and row['invest_amount']:
        invest_amount += float(row['invest_amount'])
        total_fees += float(row['buy_fees'])
        buy_qty += float(row['buy_qty'])
        if row['min_date'] and (first_buy_date is None or row['min_date'] < first_buy_date):
            first_buy_date = row['min_date']

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS settle_total,
               COALESCE(SUM(fees), 0) AS sell_fees
        FROM otc_app
        WHERE product_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND operation_type = '卖出'
    """, (code, code_id))
    row = cursor.fetchone()
    if row:
        sell_total += float(row['settle_total'])
        total_fees += float(row['sell_fees'])

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS interest_amount,
               COALESCE(SUM(fees), 0) AS interest_fees
        FROM otc_app
        WHERE product_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND operation_type = '利息'
    """, (code, code_id))
    row = cursor.fetchone()
    if row:
        interest_amount += float(row['interest_amount'])
        total_fees += float(row['interest_fees'])

    # ——— 数据验证：如果查不到任何买入记录，code 可能不匹配 ———
    if invest_amount == 0:
        cursor.close()
        db.close()
        # 给出详细的错误信息帮助定位问题
        code_id_str = f"'{code_id}'" if code_id else '空'
        flash(
            f'数据矫正失败：在产品代码「{code}」关联编号「{code_id_str}」下未找到任何买入记录。'
            f'请检查结算记录中的产品代码是否与证券管理/场外APP管理中的代码一致。',
            'error'
        )
        return redirect(request.referrer or url_for('settlement.query'))

    # ——— 套用公式 ———
    settle_amount = sell_total + interest_amount
    profit = settle_amount - invest_amount - total_fees

    # 持有天数
    holding_days = None
    settle_date = settle['settle_date']
    if first_buy_date and settle_date:
        holding_days = (datetime.strptime(str(settle_date), '%Y-%m-%d') -
                        datetime.strptime(str(first_buy_date), '%Y-%m-%d')).days

    # ——— 将关联编号下所有持有状态的记录改为结清 ———
    updated_sec = cursor.execute(
        "UPDATE securities SET status = '结清'"
        " WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND status = '持有'",
        (code, code_id)
    )
    updated_otc = cursor.execute(
        "UPDATE otc_app SET status = '结清'"
        " WHERE product_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND status = '持有'",
        (code, code_id)
    )
    synced = updated_sec + updated_otc

    # ——— 更新结清记录 ———
    cursor.execute(
        'UPDATE settlements SET invest_amount = %s, settle_amount = %s, profit = %s,'
        ' fees = %s, holding_days = %s, quantity = %s'
        ' WHERE id = %s',
        (invest_amount, settle_amount, profit, total_fees, holding_days, buy_qty if buy_qty > 0 else None,
         record_id)
    )
    db.commit()
    cursor.close()
    db.close()

    flash(
        '数据矫正成功！投入：¥{:,.2f} 结清金额：¥{:,.2f} 费用：¥{:,.2f} 收益：¥{:,.2f}（{}利息 ¥{:,.2f}）{}'.format(
            invest_amount, settle_amount, total_fees, profit,
            '含' if interest_amount > 0 else '无', interest_amount,
            f'，同步更新 {synced} 条记录状态为结清' if synced > 0 else ''
        ),
        'success'
    )

    # 保留查询参数跳回
    return redirect(request.referrer or url_for('settlement.query'))
