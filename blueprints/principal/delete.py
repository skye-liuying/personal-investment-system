"""本金管理 — 删除功能（POST /delete）"""

from flask import flash, redirect, request, url_for
from . import principal_bp
from database import get_db
from blueprints.auth.helpers import owner_condition


@principal_bp.route('/delete', methods=['POST'])
def delete():
    record_id = request.form.get('id', '').strip()

    if not record_id:
        flash('缺少记录 ID', 'error')
        return redirect(url_for('principal.query'))

    try:
        record_id = int(record_id)
    except (ValueError, TypeError):
        flash('无效的记录 ID', 'error')
        return redirect(url_for('principal.query'))

    db = get_db()
    cursor = db.cursor()
    # admin 可删除全部；组长可删除自己和组员；普通用户只能删除自己的记录
    owner_sql, owner_params = owner_condition()
    cursor.execute('DELETE FROM principal WHERE id = %s' + owner_sql, (record_id,) + owner_params)
    db.commit()
    cursor.close()
    db.close()

    flash('本金记录删除成功', 'success')
    return redirect(url_for('principal.query'))
