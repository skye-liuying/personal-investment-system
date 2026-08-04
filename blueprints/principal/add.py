"""本金管理 — 新增功能（POST /add）"""

from flask import flash, redirect, request, url_for
from . import principal_bp
from database import get_db


@principal_bp.route('/add', methods=['POST'])
def add():
    broker = request.form.get('broker', '').strip()
    record_date = request.form.get('record_date', '').strip()
    operation_type = request.form.get('operation_type', '').strip()
    amount = request.form.get('amount', '').strip()

    if not all([broker, record_date, operation_type, amount]):
        flash('请填写所有必填字段', 'error')
        return redirect(url_for('principal.query'))

    try:
        amount = float(amount)
    except (ValueError, TypeError):
        flash('金额格式不正确', 'error')
        return redirect(url_for('principal.query'))

    remark = request.form.get('remark', '').strip()

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO principal (broker, record_date, operation_type, amount, remark) '
        'VALUES (%s, %s, %s, %s, %s)',
        (broker, record_date, operation_type, amount, remark)
    )
    db.commit()
    cursor.close()
    db.close()

    flash('本金记录添加成功', 'success')
    return redirect(url_for('principal.query'))
