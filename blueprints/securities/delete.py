"""证券管理 — 删除功能（POST /delete）"""

from flask import flash, redirect, request, url_for
from . import securities_bp
from database import get_db
from blueprints.statistics.sync import sync_statistics_summary


@securities_bp.route('/delete', methods=['POST'])
def delete():
    record_id = request.form.get('id', '').strip()

    if not record_id:
        flash('缺少记录 ID', 'error')
        return redirect(url_for('securities.query'))

    try:
        record_id = int(record_id)
    except (ValueError, TypeError):
        flash('无效的记录 ID', 'error')
        return redirect(url_for('securities.query'))

    db = get_db()
    cursor = db.cursor()

    # 删除前获取 code_id 用于同步
    cursor.execute('SELECT code_id FROM securities WHERE id = %s', (record_id,))
    row = cursor.fetchone()
    code_id = row['code_id'] if row and row['code_id'] else None

    cursor.execute('DELETE FROM securities WHERE id = %s', (record_id,))
    db.commit()

    # 同步统计汇总表
    if code_id:
        sync_statistics_summary(cursor, db, code_id)
        db.commit()

    cursor.close()
    db.close()

    flash('证券记录删除成功', 'success')
    return redirect(url_for('securities.query'))
