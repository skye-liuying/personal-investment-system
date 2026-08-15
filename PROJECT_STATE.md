# PROJECT_STATE.md — 项目状态文档

> **用途**：记录项目结构、设计约定与变更影响，帮助快速定位代码、避免重复全量阅读。
> **维护规则**：每次代码改动完成后，必须更新下方「变更日志」；若模块地图/表结构/约定有变化，同步更新对应章节。
> **协作工作流**：开发新功能前先读本文件 + `git diff`（未提交改动）定位影响面，再精准读取目标文件。

---

## 0. 变更日志（按时间倒序）

> 每条记录：改动内容 + 影响面（哪些模块/函数被牵连），格式见下方模板。最新在最上面。

### 2026-08-15 证券数量输入框步进改为100，仍支持手动填1
- 改动文件：`templates/securities.html`（新增/编辑/买入卖出三处数量 input 由 step=1 改为 step=100，min=0；提交按钮加 formnovalidate 并调用 validateSecForm 保留必填校验）
- 功能：点数量上下箭头默认 +100；仍可手动输入任意整数（如 1），不再被 step 校验拦截
- 逻辑要点：原生表单提交会触发 step 校验，故用 formnovalidate 跳过 step，同时新增 validateSecForm() 手动校验 required，保证必填项不丢失
- 影响面：仅证券页前端交互；后端 quantity 仍按整数处理（int）

### 2026-08-15 证券新增保存后按关联编号自动查询结果
- 改动文件：`blueprints/securities/add.py`（保存成功后重定向：优先带 `code_id` 参数自动查询该关联编号下全部记录；无关联编号时回退为按提交日期查询当天）
- 功能：新增证券记录保存后，列表自动过滤为该笔的关联编号（如 SMFS20260501），便于直接看到本次操作及其同组数据
- 逻辑要点：query 已支持 `code_id` 过滤；重定向参数构造用 `urlencode`
- 影响面：仅新增成功后的重定向行为；不改变存储/校验

### 2026-08-15 证券买入/卖出弹框不再自动填充当天日期
- 改动文件：`templates/securities.html`（quickTrade 函数去掉 `qt_date` = 当天；改为空值；新增弹框 add_date 本就为空）
- 功能：点开买入/卖出（快速交易）或新增弹框时，交易日期留空，需用户手动选择，避免误报为当天
- 逻辑要点：日期 input 仍带 `required`，提交前必须选择，杜绝空日期入库
- 影响面：仅证券页前端交互；不影响后端存储与校验

### 2026-08-15 证券新增名称联动改为下拉建议（避免误填首个匹配）
- 改动文件：`blueprints/securities/lookup_name.py`（改为返回所有匹配项 up to 10，按 精确>左匹配>包含 排序）、`templates/securities.html`（去掉单向 autoFillStockCode 自动覆盖，新增 `showStockSuggestions()` 下拉建议 + 点击其它处收起）、`static/style.css`（新增 `.suggest-box/.suggest-item` 样式）
- 功能：输入股票名称时弹出匹配产品列表（名称+代码），点击某一项才回填代码与名称；不再自动覆盖用户输入，不再只取首个匹配
- 逻辑要点：200ms 防抖；用 mousedown 回填避免输入框失焦导致下拉消失；点击弹框外（非输入框/下拉内）收起下拉，但不关闭弹框本身
- 影响面：仅证券新增弹窗交互；products 全局字典查询不变
- 坑：旧代码曾把匹配名称回写覆盖用户输入，导致「中输入中被强制成中欧」无法改中金；新方案下拉由用户主动点选，输入文本始终保留

### 2026-08-15 弹框交互优化：禁止点击遮罩关闭，仅按钮关闭
- 改动文件：`templates/` 下 9 个含弹框的页面（base/修改密码、users、roles、products、securities、settlement、principal、otc_app、statistics）
- 功能：移除所有 `window.onclick / window.addEventListener('click')` 的「点击弹窗外部关闭」逻辑；弹框现在只能通过右上角 × 或弹框内「取消/关闭」功能按钮关闭，避免误点外部丢失已输入数据
- 影响面：纯前端交互；各弹框的 close 函数（closeAddModal/closeEditModal 等）与按钮 onclick 保持不变，仅去掉遮罩监听
- 坑：statistics 的 tradeModal/settleModal 原用 `style.display='none'` 直关，已一并移除监听；base.html 修改密码弹框同样处理

### 2026-08-15 金额显示优化：悬停展示「万」缩写
- 改动文件：`templates/base.html`（head 加 `.summary-value/.amount-col{cursor:help}`，body 注入 `fmtWan()` + DOMContentLoaded 扫描脚本）
- 功能：本金/证券/场外APP/结清四个页的所有汇总值与金额列，当数值 >=10000 时，鼠标悬停通过原生 title 显示「XXX万YYY.YY」缩写（如 1085835.65 -> 108万5835.65）；<10000 不显示
- 逻辑要点：`fmtWan` 取 floor(值/10000) 为万、余数为后段（去尾 .00），负数保留符号；脚本解析元素文本中的数字（支持千分位逗号），仅给 `.summary-value` 与 `.amount-col` 设 title
- 影响面：纯前端展示增强，无后端逻辑/数据变化；跨页面通用（statistics 的金额列也会被覆盖，无害）
- 坑：收益率百分比列（如结清收益率%）未加 `amount-col`，不会被误标；脚本运行时设置 title，服务端 HTML 不含 title，靠前端执行

### 2026-08-15 结清数据矫正优化：结清日期取自关联编号最后一笔操作日期
- 改动文件：`blueprints/settlement/correct.py`（结清日期改为取 securities+otc_app 中该 code+code_id 的 MAX(record_date) 即最后一笔操作日期；按此重算 holding_days；UPDATE 写入 settle_date；成功提示补结清日期/持有天数）、`templates/settlement.html`（数据矫正确认弹窗文案说明结清日期自动取自最后一笔操作）
- 逻辑要点：优先按 code_id（关联编号）匹配；无关联编号时退化为仅按代码匹配。结清日期=最后一笔操作 record_date，否则保留原值；持有天数=结清日期−首笔买入日；收益率（模板派生=利润/本金）随利润重算自动刷新
- 影响面：仅数据矫正（correct）的结清日期/持有天数计算；不改变权限隔离与统计同步逻辑
- 坑：收益率非存储列，表内展示随 profit/invest_amount 派生，无需单独更新字段

### 2026-08-15 证券管理新增弹窗「名称→代码」联动
- 改动文件：新增 `blueprints/securities/lookup_name.py`；修改 `blueprints/securities/__init__.py`（注册模块）、`templates/securities.html`（新增弹窗股票名称输入框加 `oninput="autoFillStockCode()"`，新增 `autoFillStockCode()` JS 调 `/securities/lookup_name`）
- 功能：新增证券时输入股票名称，自动从 `products` 全局产品字典按名称（精确/左匹配/包含）联动回填股票代码；命中时顺带回填规范名称
- 逻辑要点：products 全局共享（无 user_id），lookup 直接查全表，不做数据隔离；模糊匹配优先精确命中、其次 id 倒序取最近一条
- 影响面：仅证券新增弹窗前端体验；新增一个只读查询接口（无写操作，不影响统计与权限）
- 坑：名称需产品字典中已存在才会带出代码；未命中时不清空已手填的代码（仅当名称为空才清空），避免误删用户手动输入

### 2026-08-15 新增组长/组员数据隔离（user_groups）
- 改动文件：新增 `schema.sql`（user_groups 表）；修改 `blueprints/auth/helpers.py`（PAGES 无新增；新增 `get_group_member_ids`/`group_scope_ids`/`scope_condition` 支持组长范围/`owner_condition`）；`blueprints/users/query.py`+`edit.py`+`templates/users.html`（用户编辑弹窗支持配置组员，列表展示组员）；`blueprints/otc_app/delete.py`、`blueprints/securities/delete.py`、`blueprints/principal/delete.py`、`blueprints/principal/edit.py`、`blueprints/settlement/correct.py`、`blueprints/statistics/settle.py`（删除/编辑/结清改用 `owner_condition` 并按 `record_owner` 同步统计）
- 功能：组长可查看/修改自己和组员（user_groups 表，存登录账号，排除自身防自环）创建的数据；普通用户仅自己；admin 全部。查询用 `scope_condition()`（IN 多账号），修改用 `owner_condition()`（AND user_id IN）
- 逻辑要点：删除/编辑/结清统一以被操作记录的**归属账号 record_owner** 调用 `sync_statistics_summary`，保证统计落在正确账号；结清增加「归属多用户则拒绝统一结清」校验
- 影响面：所有业务增删改查的权限隔离逻辑；users.html 编辑弹窗新增组员多选；schema 存量库启动时自动建 user_groups 表
- 坑：date 无涉及；组长范围与角色名无关，完全由 user_groups 表决定

### 2026-08-15 新增产品管理模块（products，全局共享产品字典，仅超管）
- 改动文件：新增 `blueprints/products/`（`__init__/query/add/edit/delete/import_data.py`）、`templates/products.html`、`templates/icons/package.svg`；修改 `schema.sql`（products 表）、`app.py`（注册蓝图 + init_database 建表 + pages/action_map/active_page）、`blueprints/auth/helpers.py`（PAGES 加 products）、`templates/base.html`（系统管理菜单加产品管理）
- 功能：产品字典独立于业务数据、**不带 user_id（全局共享）**；增删改查 + 搜索分页；导入按钮支持 `M-2026-06`（月）/ `N-2026`（年）/ `D-2026-06-06`（日），读取 securities+otc_app **全部用户**该区间的 code/name/asset_type 去重写入，code 已存在则跳过
- 逻辑要点：products.code 有 UNIQUE 约束，新增/编辑后端双重预检（SELECT + IntegrityError 兜底）；页面与全部路由内部 `is_admin()` 二次校验（仅超管，其他角色不显示菜单）；`import_data` 已加入 action_map（映射 add）
- 影响面：auth/helpers PAGES（角色权限页新增"产品管理"行，admin 角色预置全权限）；app.py 权限拦截；启动时 `init_database()` 自动建 products 表（存量库无需手动迁移）
- 坑：date 无涉及；导入数据范围是**全部账号**（不经过 owner_condition），与业务查询隔离规则不同，属有意设计

### 2026-08-15 证券管理页增加编辑功能（已自测）
- 改动文件：新增 `blueprints/securities/edit.py`；`blueprints/securities/__init__.py`；`templates/securities.html`
- 功能：表格新增「编辑」按钮 → 弹窗（与新增弹窗一致）→ GET 回填 JSON → POST 更新
- 逻辑要点：卖出校验排除自身（`max_allowed = max(original_qty, hold_qty)` 允许历史超卖数据原值保存）；编辑后对旧/新 `code_id` 调 `sync_statistics_summary()`；卖出记录编辑后 `recalc_settle()` 重算结清（UPSERT settlements 防重复）
- 影响面：securities 模块（add/delete 逻辑需保持校验一致）；statistics_summary / settlements 表数据可能被更新
- 坑：GET 返回 JSON 前 date 必须转 `YYYY-MM-DD` 字符串（`record['record_date'].strftime('%Y-%m-%d')`）

### 2026-08-15 修复：编辑结清记录时结清时间未回填
- 改动文件：`blueprints/settlement/query.py`
- 根因：Flask `tojson` 把 `datetime.date` 序列化为 `"Sat, 15 Aug 2026 00:00:00 GMT"`，`<input type="date">` 无法解析
- 修复：查询返回记录后 `r['settle_date'] = str(r['settle_date'])`
- 影响面：settlement 编辑弹窗；同类问题已排查 users.html（其编辑弹窗不读 created_at，无影响）

### 2026-08-15 证券新增后按当日查询全部数据
- 改动文件：`blueprints/securities/add.py`
- 修复：新增成功重定向去掉 broker/stock_name/stock_code 过滤，仅保留 `date_from=date_to=record_date`
- 影响面：securities 列表页跳转行为

---

## 1. 项目概览

- **技术栈**：Flask 2.2.5 + PyMySQL + 原生 HTML/CSS/JS + Jinja2；数据库 MySQL（库名 `investment`）
- **虚拟环境**：`e:/personal-investment-system/.venv`（所有命令用 `.venv/Scripts/python.exe`）
- **启动**：`.venv/Scripts/python.exe app.py`（端口 5000，debug 模式；启动时 `init_database()` 建表/迁移/预置角色）
- **核心文件**：`app.py`（蓝图挂载 + 权限拦截 + 建库逻辑）、`config.py`（连接配置）、`database.py`（`get_db()` 返回 DictCursor）、`paginate.py`（分页）

## 2. 模块地图

所有蓝图 `__init__.py` 末尾 `from . import query, add, ...` 注册路由；业务模块命名统一为 `query/add/edit/delete`（+ 扩展如 `correct/sync/settle/lookup`）。

| 蓝图 | 前缀 | 文件 | 路由（权限点） |
|------|------|------|----------------|
| auth | /auth | login, logout, helpers | login / logout；helpers 提供权限与数据隔离函数 |
| principal 本金 | /principal | query, add, edit, delete | query(view)；add(add)；edit/<id>(edit，GET回填)；delete(delete) |
| securities 证券 | /securities | query, add, delete, **edit** | query(view)；add(add，卖出校验+auto_settle)；delete(delete)；edit/<id>(edit，GET JSON + recalc_settle) |
| otc_app 场外APP | /otc_app | query, add, delete, lookup | query(view)；add(add)；delete(delete)；lookup/<code_id>(回填产品)；**无编辑** |
| statistics 统计 | /statistics | query, settle, trade, sync | query(view)；settle(edit映射)；trade(add映射)；sync 非路由 |
| settlement 结清 | /settlement | query, add, edit, correct | query(view)；add(add)；edit(edit，POST)；correct(edit映射) |
| users 用户 | /users | query, add, edit, delete | 仅超管，内部 `is_admin()` 二次校验；编辑弹窗支持配置组员（user_groups） |
| roles 角色 | /roles | query, add, edit, delete | 仅超管，内部 `is_admin()` 二次校验 |
| products 产品 | /products | query, add, edit, delete, import_data | 仅超管，内部 `is_admin()` 二次校验；import_data 映射 add |

- 概览统计：`__init__.py` 中 `get_overview()`（principal/securities/otc_app 提供）
- 权限映射（app.py action_map）：`correct/settle → edit`，`trade → add`

## 3. 数据模型（要点）

- 业务表均含 `user_id VARCHAR(50)` 存**登录账号字符串**（非 users.id），有 `idx_user_id` 索引；旧库 INT 列启动时自动迁移
- `principal`：broker, record_date, operation_type(充值/取现), amount, remark
- `securities`：operation_type(买入/卖出/利息), stock_code, **code_id**(跨表关联编号), unit_price, quantity(INT), total_amount, fees, asset_type(股票/债券/基金/定存/港美股), status(持有/结清)
- `otc_app`：同 securities 风格，`quantity DECIMAL(15,4)`（可小数），app_name/product_code/product_name
- `settlements`：settle_date, code, code_id, product_name, asset_type, invest_amount, settle_amount, profit, fees, holding_days, quantity
- `statistics_summary`：`code_id` UNIQUE；status='结清' 时删记录，持有则 UPSERT
- 权限相关：`users`(is_admin), `roles`, `user_roles`(多对多), `role_permissions`(role_id, page, can_view/add/edit/delete), `user_groups`(id, leader_id, member_id 存登录账号；UNIQUE(leader_id,member_id)，排除自身防自环)
- `products`（**无 user_id，全局共享**）：code UNIQUE, name, asset_type VARCHAR(20), remark, created_at/updated_at；导入来源 securities.stock_code / otc_app.product_code，按 code 去重

## 4. 权限模型

- `auth/helpers.py`：
  - `get_current_user_id()` → `session['login_id']`（业务归属账号）
  - `is_admin()` / `load_permissions()` / `has_perm(page, action)`（模板 `can()` 底层）
  - `get_group_member_ids()` / `group_scope_ids()`：admin→全部；组长→[自己+组员]；普通→[自己]
  - `scope_condition()`：查询层隔离（返回 `(sql, params)`，admin 返回 `(None,None)`）
  - `owner_condition()`：修改操作归属条件（返回 `' AND user_id=...'` 前缀 SQL）
- `app.py` before_request：登录检查 + view 权限 + POST 按 action_map 校验
- `admin` 角色/用户：全权限、不可改名/删/禁，`is_admin=1` 绕过权限判断
- 「组长」角色预置 5 业务页 view/add/edit；数据范围由 user_groups 表决定（与角色名无关）

## 5. 关键设计约定（重要，改代码前必读）

1. **date 序列化坑**：返回 JSON 给前端前，date 必须手动转 `YYYY-MM-DD` 字符串（`strftime('%Y-%m-%d')`），不能依赖 Flask tojson（会输出 HTTP 日期格式导致 `<input type="date">` 回填失败）。参考 `settlement/query.py`、`principal/edit.py`。
2. **业务表归属用登录账号字符串**：增删改查用 `session['login_id']`，不要用 `users.id`。
3. **组长操作组员数据**：删除/编辑/统计同步用**记录归属账号**（record_owner）而非当前登录者，保证统计正确。
4. **卖出数量校验**：`SUM(CASE WHEN 买入 THEN qty ELSE -qty END)` 算 hold_qty；edit 排除自身 `id != %s` 且 `max_allowed = max(original_qty, hold_qty)`（允许历史超卖原值保存）；securities 数量 INT、otc_app DECIMAL。
5. **结清逻辑**：`auto_settle`（add 路径，INSERT settlements）/ `recalc_settle`（edit 路径，UPSERT 防重复）/ `settle`（统计页一键结清，归属唯一性校验）。
6. **统计同步**：`sync_statistics_summary(cursor, db, code_id, user_id=None)` 按 code_id 重汇总 securities+otc_app，UPSERT statistics_summary；编辑/删除涉及 code_id 变化时新旧都要同步。
7. **users/roles/products 双重校验**：除 before_request 外内部再判 `is_admin()`；products 为全局共享字典（无 user_id），导入读取**全部用户**数据。
8. **组长/组员数据隔离**：查询用 `scope_condition()`（admin→None 全量；组长→`user_id IN (自己,组员)`；普通→`user_id=自己`）；修改(删/编辑/结清)用 `owner_condition()`（AND 同上）。删除/编辑/结清后统一以**被操作记录的归属账号 record_owner** 调 `sync_statistics_summary`，保证统计正确；统计页结清遇「归属多用户」拒绝统一结清。
9. **otc_app 无编辑**：不要假设它有编辑能力。
10. **TestWork/**：一次性验证脚本目录，不参与 git 提交；用户自测脚本可保留供学习。

## 6. 模板与前端约定

- `base.html`：侧边栏按 `can(page,'view')` 显隐；提供 `edit_modal_form` block 与通用 `#editModal`、`openModal()/closeModal()`；flash 在 content-body 顶部
- `_pagination.html`：`goPage()/changePageSize()` 基于 URLSearchParams 保持过滤参数
- 编辑回填两种方式：**fetch JSON**（securities/principal 的 `edit/0`.replace('0',id)）；**`record|tojson|safe` 整对象**（settlement/roles/users）——后者注意 date 字段坑
- 表单交互：单价×数量自动算总额、利息类型隐藏单价数量（securities）；quickTrade/tradeModal/settleModal 等弹窗
