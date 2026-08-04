"""本金管理 — 删除功能（POST /delete）"""

from flask import flash, redirect, request, url_for
from . import principal_bp
from database import get_db


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
    cursor.execute('DELETE FROM principal WHERE id = %s', (record_id,))
    db.commit()
    cursor.close()
    db.close()

    flash('本金记录删除成功', 'success')
    return redirect(url_for('principal.query'))
