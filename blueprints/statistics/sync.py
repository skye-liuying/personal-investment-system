"""同步 statistics_summary 表 — 当 securities / otc_app 数据变动时调用"""


def sync_statistics_summary(cursor, db, code_id, user_id=None):
    """根据 code_id 重新汇总 securities+otc_app 数据，UPSERT 到 statistics_summary

    user_id：当前操作用户的 users.id，用于数据隔离；
    为 None 时表示老数据兼容（不过滤）。
    """
    if not code_id:
        return

    # 数据隔离条件
    user_cond = ''
    user_args = ()
    if user_id is not None:
        user_cond = ' AND user_id = %s'
        user_args = (user_id,)

    # 1. 计算持有状态
    cursor.execute("""
        SELECT COUNT(*) AS cnt FROM securities
        WHERE IFNULL(code_id, '') = %s AND status = '持有'
    """ + user_cond, (code_id,) + user_args)
    sec_holdings = int(cursor.fetchone()['cnt'])

    cursor.execute("""
        SELECT COUNT(*) AS cnt FROM otc_app
        WHERE IFNULL(code_id, '') = %s AND status = '持有'
    """ + user_cond, (code_id,) + user_args)
    otc_holdings = int(cursor.fetchone()['cnt'])

    status = '持有' if (sec_holdings > 0 or otc_holdings > 0) else '结清'

    # 2. 持有金额 = 买入金额 - 卖出金额 - 利息 + 费用
    cursor.execute("""
        SELECT COALESCE(SUM(CASE WHEN operation_type='买入' THEN total_amount
                                 WHEN operation_type='卖出' THEN -total_amount
                                 WHEN operation_type='利息' THEN -total_amount
                                 ELSE 0 END), 0)
             + COALESCE(SUM(COALESCE(fees, 0)), 0) AS holding_amount
        FROM securities
        WHERE IFNULL(code_id, '') = %s AND status = '持有'
    """ + user_cond, (code_id,) + user_args)
    sec_amount = float(cursor.fetchone()['holding_amount'])

    cursor.execute("""
        SELECT COALESCE(SUM(CASE WHEN operation_type='买入' THEN total_amount
                                 WHEN operation_type='卖出' THEN -total_amount
                                 WHEN operation_type='利息' THEN -total_amount
                                 ELSE 0 END), 0)
             + COALESCE(SUM(COALESCE(fees, 0)), 0) AS holding_amount
        FROM otc_app
        WHERE IFNULL(code_id, '') = %s AND status = '持有'
    """ + user_cond, (code_id,) + user_args)
    otc_amount = float(cursor.fetchone()['holding_amount'])

    holding_amount = round(sec_amount + otc_amount, 2)

    # 3. 获取 code / name / asset_type（取最新记录）
    cursor.execute("""
        SELECT stock_code AS code, stock_name AS name, asset_type, id
        FROM securities WHERE IFNULL(code_id, '') = %s
    """ + user_cond + """
        ORDER BY id DESC LIMIT 1
    """, (code_id,) + user_args)
    sec_row = cursor.fetchone()

    cursor.execute("""
        SELECT product_code AS code, product_name AS name, asset_type, id
        FROM otc_app WHERE IFNULL(code_id, '') = %s
    """ + user_cond + """
        ORDER BY id DESC LIMIT 1
    """, (code_id,) + user_args)
    otc_row = cursor.fetchone()

    code = None
    name = None
    asset_type = None
    display_source = None

    if sec_row and otc_row:
        if sec_row['id'] > otc_row['id']:
            code, name, asset_type = sec_row['code'], sec_row['name'], sec_row['asset_type']
        else:
            code, name, asset_type = otc_row['code'], otc_row['name'], otc_row['asset_type']
        display_source = 'securities' if sec_holdings > 0 else ('otc_app' if otc_holdings > 0 else source_from_last_record(sec_row, otc_row))
    elif sec_row:
        code, name, asset_type = sec_row['code'], sec_row['name'], sec_row['asset_type']
        display_source = 'securities'
    elif otc_row:
        code, name, asset_type = otc_row['code'], otc_row['name'], otc_row['asset_type']
        display_source = 'otc_app'


    # 4. 结清 → 删除；持有 → UPSERT
    if status == '结清':
        if user_id is not None:
            cursor.execute(
                "DELETE FROM statistics_summary WHERE code_id = %s AND user_id = %s",
                (code_id, user_id)
            )
        else:
            cursor.execute("DELETE FROM statistics_summary WHERE code_id = %s", (code_id,))
    else:
        if user_id is not None:
            cursor.execute("""
                INSERT INTO statistics_summary (user_id, code_id, code, name, asset_type, holding_amount, status, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    code = VALUES(code),
                    name = VALUES(name),
                    asset_type = VALUES(asset_type),
                    holding_amount = VALUES(holding_amount),
                    status = VALUES(status),
                    source = VALUES(source),
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, code_id, code, name, asset_type, holding_amount, status, display_source))
        else:
            cursor.execute("""
                INSERT INTO statistics_summary (code_id, code, name, asset_type, holding_amount, status, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    code = VALUES(code),
                    name = VALUES(name),
                    asset_type = VALUES(asset_type),
                    holding_amount = VALUES(holding_amount),
                    status = VALUES(status),
                    source = VALUES(source),
                    updated_at = CURRENT_TIMESTAMP
            """, (code_id, code, name, asset_type, holding_amount, status, display_source))
    db.commit()


def source_from_last_record(sec_row, otc_row):
    """当两条记录都存在时，根据最新记录判断来源"""
    if sec_row['id'] > otc_row['id']:
        return 'securities'
    return 'otc_app'
