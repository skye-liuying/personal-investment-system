"""统计分析 — 结清功能（POST /settle）"""

from datetime import date

from flask import flash, redirect, request, url_for
from . import statistics_bp
from database import get_db


@statistics_bp.route('/settle', methods=['POST'])
def settle():
    code = request.form.get('code', '').strip()
    code_id = request.form.get('code_id', '').strip()
    settle_date = request.form.get('settle_date', '').strip()
    settle_amount = request.form.get('settle_amount', '').strip()

    if not all([code, settle_date, settle_amount]):
        flash('请填写所有必填字段', 'error')
        return redirect(url_for('statistics.query'))

    try:
        settle_amount = float(settle_amount)
    except (ValueError, TypeError):
        flash('结清金额格式不正确', 'error')
        return redirect(url_for('statistics.query'))

    code_id_val = code_id or None

    db = get_db()
    cursor = db.cursor()

    # 更新证券表（匹配 code + code_id）
    cursor.execute("""
        UPDATE securities SET status = '结清'
        WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND status = '持有'
    """, (code, code_id_val))

    # 更新场外APP表（匹配 code + code_id）
    cursor.execute("""
        UPDATE otc_app SET status = '结清'
        WHERE product_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND status = '持有'
    """, (code, code_id_val))

    # 汇总投资金额与费用
    invest_amount = 0
    product_name = ''
    asset_type = ''
    total_fees = 0
    first_buy_date = None

    cursor.execute("""
        SELECT stock_name AS product_name, asset_type,
               COALESCE(SUM(total_amount), 0) AS invest_amount,
               COALESCE(SUM(fees), 0) AS buy_fees,
               MIN(record_date) AS min_date
        FROM securities
        WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND operation_type = '买入'
    """, (code, code_id_val))
    row = cursor.fetchone()
    if row and row['invest_amount']:
        invest_amount += float(row['invest_amount'])
        total_fees += float(row['buy_fees'])
        product_name = row['product_name']
        asset_type = row['asset_type']
        if row['min_date']:
            first_buy_date = row['min_date']

    cursor.execute("""
        SELECT product_name, asset_type,
               COALESCE(SUM(total_amount), 0) AS invest_amount,
               COALESCE(SUM(fees), 0) AS buy_fees,
               MIN(record_date) AS min_date
        FROM otc_app
        WHERE product_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND operation_type = '买入'
    """, (code, code_id_val))
    row = cursor.fetchone()
    if row and row['invest_amount']:
        invest_amount += float(row['invest_amount'])
        total_fees += float(row['buy_fees'])
        if not product_name:
            product_name = row['product_name']
        if not asset_type:
            asset_type = row['asset_type']
        if row['min_date'] and (first_buy_date is None or row['min_date'] < first_buy_date):
            first_buy_date = row['min_date']

    # 加上卖出的费用
    cursor.execute("""
        SELECT COALESCE(SUM(fees), 0) AS sell_fees
        FROM securities
        WHERE stock_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND operation_type = '卖出'
    """, (code, code_id_val))
    row = cursor.fetchone()
    if row:
        total_fees += float(row['sell_fees'])

    cursor.execute("""
        SELECT COALESCE(SUM(fees), 0) AS sell_fees
        FROM otc_app
        WHERE product_code = %s AND IFNULL(code_id, '') = IFNULL(%s, '') AND operation_type = '卖出'
    """, (code, code_id_val))
    row = cursor.fetchone()
    if row:
        total_fees += float(row['sell_fees'])

    # 持有天数
    from datetime import datetime
    holding_days = None
    if first_buy_date and settle_date:
        holding_days = (datetime.strptime(str(settle_date), '%Y-%m-%d') -
                        datetime.strptime(str(first_buy_date), '%Y-%m-%d')).days

    # 收益 = 卖出金额 - 买入金额 - 费用总和
    profit = settle_amount - invest_amount - total_fees

    # 写入结算记录
    cursor.execute(
        'INSERT INTO settlements (settle_date, code, code_id, product_name, asset_type, invest_amount, settle_amount, '
        'profit, fees, holding_days) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (settle_date, code, code_id_val, product_name, asset_type, invest_amount, settle_amount,
         profit, total_fees, holding_days)
    )
    db.commit()
    cursor.close()
    db.close()

    flash('产品结清成功，收益：¥{:,.2f}'.format(profit), 'success')
    return redirect(url_for('statistics.query'))
