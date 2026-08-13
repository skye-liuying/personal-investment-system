# -*- coding: utf-8 -*-
"""本金管理 — 编辑功能（GET/POST /edit/<int:id>）"""

from flask import request, redirect, url_for, flash, jsonify
from . import principal_bp
from database import get_db
from blueprints.auth.helpers import get_current_user_id, is_admin


@principal_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    db = get_db()
    cursor = db.cursor()

    # 非 admin 只能编辑自己的记录
    owner_sql = '' if is_admin() else ' AND user_id = %s'
    owner_params = () if is_admin() else (get_current_user_id(),)

    if request.method == 'POST':
        broker = request.form.get('broker', '').strip()
        record_date = request.form.get('record_date', '').strip()
        operation_type = request.form.get('operation_type', '').strip()
        amount = request.form.get('amount', '').strip()
        remark = request.form.get('remark', '').strip()

        if not broker or not record_date or not operation_type or not amount:
            flash('请填写完整的本金记录信息', 'danger')
            return redirect(url_for('principal.query'))

        try:
            amount = float(amount)
        except ValueError:
            flash('金额必须是数字', 'danger')
            return redirect(url_for('principal.query'))

        cursor.execute(
            """
            UPDATE principal
            SET broker = %s, record_date = %s, operation_type = %s, amount = %s, remark = %s
            WHERE id = %s
            """ + owner_sql,
            (broker, record_date, operation_type, amount, remark, id) + owner_params
        )
        db.commit()
        cursor.close()
        db.close()
        flash('本金记录更新成功', 'success')
        return redirect(url_for('principal.query'))

    # GET：查询记录并返回 JSON，供前端编辑弹窗回填
    cursor.execute('SELECT * FROM principal WHERE id = %s' + owner_sql, (id,) + owner_params)
    record = cursor.fetchone()
    cursor.close()
    db.close()

    if not record:
        return jsonify({'error': '记录不存在'}), 404

    return jsonify({
        'id': record['id'],
        'broker': record['broker'],
        'record_date': record['record_date'].strftime('%Y-%m-%d') if record['record_date'] else '',
        'operation_type': record['operation_type'],
        'amount': float(record['amount']),
        'remark': record['remark'] or ''
    })
