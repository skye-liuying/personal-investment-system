"""证券管理 — 删除功能（POST /delete）"""

from flask import flash, redirect, request, url_for
from . import securities_bp
from database import get_db
from blueprints.auth.helpers import owner_condition
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

    # admin 可删除全部；组长可删除自己和组员；普通用户只能删除自己的记录。
    # 同步统计时使用被删记录的归属账号，保证统计正确。
    owner_sql, owner_params = owner_condition()
    cursor.execute(
        'SELECT code_id, user_id FROM securities WHERE id = %s' + owner_sql,
        (record_id,) + owner_params
    )
    row = cursor.fetchone()
    if not row:
        cursor.close()
        db.close()
        flash('记录不存在或无权操作', 'error')
        return redirect(url_for('securities.query'))

    code_id = row['code_id'] if row['code_id'] else None
    record_owner = row['user_id']
    cursor.execute(
        'DELETE FROM securities WHERE id = %s' + owner_sql,
        (record_id,) + owner_params
    )
    db.commit()

    # 同步统计汇总表
    if code_id:
        sync_statistics_summary(cursor, db, code_id, user_id=record_owner)
        db.commit()

    cursor.close()
    db.close()

    flash('证券记录删除成功', 'success')
    return redirect(url_for('securities.query'))
