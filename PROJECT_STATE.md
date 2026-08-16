# PROJECT_STATE.md — 项目状态文档

> **用途**：记录项目结构、设计约定与变更影响，帮助快速定位代码、避免重复全量阅读。
> **维护规则**：每次代码改动完成后，必须更新下方「变更日志」；若模块地图/表结构/约定有变化，同步更新对应章节。
> **协作工作流**：开发新功能前先读本文件 + `git diff`（未提交改动）定位影响面，再精准读取目标文件。

---

## 0. 变更日志（按时间倒序）

> 每条记录：改动内容 + 影响面（哪些模块/函数被牵连），格式见下方模板。最新在最上面。

### 2026-08-16 结清页新增记录：数量用原生输入框，上下箭头 ±100，任意整数可提交（并防缓存）
- 改动文件：`templates/settlement.html`（新增弹框「数量」：`input type=number step="any" min="0" inputmode="numeric" pattern="[0-9]*"`，彻底关闭浏览器 step 倍数校验，避免 1143 被提示"最接近有效值为 1100/1200"；`oninput` 仍调用 `normalizeQtyInput(el)` 强制整数；`onkeydown` 调用 `handleQtyArrow(event)` 接管方向键，按上/下箭头每次 ±100，同时重算买入/卖出总额；去掉上一版的自定义 ±100 按钮及 `relaxQtyStep` 临时校验）、`static/style.css`（删除上一版新增的 `.stepper*` 样式）、`templates/base.html`（新增 `Cache-Control: no-cache, no-store, must-revalidate` / `Pragma: no-cache` / `Expires: 0` meta 标签，防止浏览器缓存旧版 HTML，避免代码已改但界面仍报旧校验错误）
- 背景：`step=100` 会让浏览器强制值必须是 100 的倍数；`step="any"` 虽允许任意值，但原生箭头会 ±1，所以由 JS 接管方向键实现 ±100。用户反馈修改后仍出现旧提示，判断为浏览器缓存了旧版 settlement.html，因此在 base 模板加防缓存 meta
- 功能：新增结清记录时数量只能填整数（可输入任意整数如 1143）；按键盘上/下箭头（或 number 输入框右侧原生箭头）每次增减 100（最小 0）；页面不再被浏览器缓存旧版 HTML
- 影响面：结清页新增弹框数量输入；全站页面缓存策略改为不缓存 HTML（CSS/JS 仍按浏览器默认策略缓存）
- 兼容性：后端 add 逻辑不变

### 2026-08-16 证券页新增记录：资产类型默认显示「请选择」
- 改动文件：`templates/securities.html`（新增弹框「资产类型」`<select>` 新增 `<option value="" selected>请选择</option>` 作为默认项，保留 `required` 强制选择；`openAddModal()` 重置逻辑由 `value='股票'` 改为 `value=''`，使每次打开新增弹框默认落到「请选择」）
- 功能：新增证券记录时，资产类型下拉默认显示「请选择」，用户必须主动选择股票/债券/基金/定存/港美股之一才能提交
- 影响面：证券管理页新增弹框资产类型；编辑弹框未动（编辑时按记录值回填）
- 兼容性：后端 add 逻辑不变（`required` 校验空值会拦截提交）

### 2026-08-16 结清页新增记录：增加收益字段（自动计算）
- 改动文件：`templates/settlement.html`（新增弹框「费用」input 加 `id="add_fees"` 并加 `oninput="calcAddAmount()"`；在买入总额/卖出总额下方新增「收益：<span id="add_profit_hint">」提示；`calcAddAmount()` 增加读取费用并计算 `收益 = 卖出金额 - 买入金额 - 费用`（`settle - invest - fees`），显示在 `#add_profit_hint`，盈利绿色（var(--success)）、亏损红色（var(--danger)），无任何金额输入时显示「-」）
- 公式：`收益 = (卖出单价×数量) - (买入单价×数量) - 费用`，与后端 `add.py` 存储的 `profit = (sp-bp)*qty - fees` 完全一致
- 功能：新增结清记录时，随买入单价/卖出单价/数量/费用输入实时显示收益（非录入字段，自动算）
- 影响面：结清页新增弹框；仅新增弹框（编辑弹框未动，仍无收益实时提示）；后端 add 逻辑不变（本就计算并存储 profit）
- 兼容性：CSS 复用已有 `--success`/`--danger` 变量

### 2026-08-16 修复：结清页数量仍报旧校验（浏览器缓存导致，改服务端禁缓存）
- 改动文件：`app.py`（新增 `@app.after_request def disable_cache(response)`：对所有响应统一加 `Cache-Control: no-cache, no-store, must-revalidate` / `Pragma: no-cache` / `Expires: 0`，比 base.html 的 meta 标签更可靠，确保浏览器不再缓存 HTML）、`templates/base.html`（移除上一版临时加的缓存 meta 标签，避免重复）
- 背景：用户强刷后仍提示 1100/1200 旧校验，确认 settlement.html 第 187 行已是 `step="any"`，问题为浏览器缓存旧版 HTML；meta 标签在部分浏览器/Flask 调试模式下不生效，故改为服务端响应头禁缓存
- 功能：服务端层面禁止缓存，模板/JS 改动即时生效，无需手动强刷
- 影响面：全站所有响应（HTML/JSON/静态资源）；开发期生效（生产如需缓存可移除该函数）
- 兼容性：不影响业务逻辑

### 2026-08-16 结清页新增记录增加产品名称→产品代码联动
- 改动文件：`blueprints/settlement/lookup_name.py`（新增 `lookup_name` 路由 `GET /settlement/lookup_name`，复用 securities 同名接口逻辑；查 `products` 全局字典表（无 user_id 隔离）按名称精确/左匹配/包含模糊匹配，返回最多 10 条 `{code, name}`，按精确优先+id 倒序）、`blueprints/settlement/__init__.py`（注册 import `lookup_name`）、`templates/settlement.html`（新增弹框「产品名称」input 加 `id=add_product_name` 与 `oninput/onfocus=showSettleNameSuggestions('add')`，旁加 `id=addNameSuggest` 下拉框；「产品代码」input 加 `id=add_code`；新增 JS `showSettleNameSuggestions(prefix)` 拉取 `/settlement/lookup_name` 渲染 `.suggest-item`，点选回填名称与代码；`closeAddModal` 关闭时清空下拉框）
- 功能：新增结清记录时，输入产品名称自动下拉匹配 products 字典，点选后自动回填对应产品代码，与证券管理页新增弹框联动行为一致
- 影响面：结清页「新增记录」弹框交互；CSS 复用 style.css 已有 `.suggest-box`/`.suggest-item`/`.suggest-name`/`.suggest-code`（证券页同款，无需新增）；已自测（空查询返回 []、模糊查询返回匹配项、无语法错误）
- 兼容性：仅新增弹框支持联动（编辑弹框未改动，保持原样）；products 为共享字典表，所有用户看到相同候选

### 2026-08-16 用户管理修复：增加独立的「移除组员」入口
- 改动文件：`blueprints/users/remove_member.py`（新增 `remove_member` 路由 `POST /users/remove_member`，仅 admin 可调用；接收 `leader_id`/`member_id`，`DELETE FROM user_groups WHERE leader_id=%s AND member_id=%s`；禁止 leader==member）、`blueprints/users/__init__.py`（注册 import）、`templates/users.html`（「组员」列每个组员渲染为 `.member-chip`，后接独立的移除按钮 `<form>` 提交到 `users.remove_member`，带确认弹窗；仅解除关系不删账号）、`static/style.css`（新增 `.member-chip`/`.member-x` 样式）
- 背景：原"移除组员"只能靠编辑组长、在 multiple-select 里手动取消勾选（UX 陷阱，易表现为"删除不了组员"）；且用户管理页仅 admin 可访问
- 功能：管理员在用户列表「组员」列直接点每个组员的 × 即可从该组长处移除该组员关系；不影响用户账号本身
- 影响面：用户管理页交互；已自测（admin 移除成功、移除自身被拒、非 admin 被拒、页面渲染移除按钮）
- 兼容性：原有"编辑组长取消勾选"与"删除用户清关系"逻辑保持不变

### 2026-08-16 修复 get_overview 的 settlements 统计 SQL 语法错误
- 改动文件：`blueprints/securities/__init__.py`（`get_overview` 中 `settled_count` 查询原为 `FROM settlements" + extra_where`，extra_where 以 ` AND ` 开头，当非 admin（带 scope）时生成 `FROM settlements AND user_id='baba'` 缺 `WHERE` 导致 1064 语法错误；改为 `FROM settlements" + (' WHERE ' + scope_sql if scope_sql else '')`）
- 触发条件：统计页/证券页概览由非 admin 用户（存在数据隔离 scope）访问时必现；admin 因 scope 为空不触发
- 影响面：证券页概览「已结清」卡片统计；已自测（非 admin 用户 userA 访问证券页不再 500，admin 仍正常）

### 2026-08-16 证券管理页概览数量对齐目标页记录数
- 改动文件：`blueprints/securities/__init__.py`（重构 `get_overview`：签名改为 `(db, scope_sql, scope_params)`；`holding_count` 改为 `SELECT COUNT(*) FROM statistics_summary WHERE status='持有' [AND scope]`，即统计分析页 status=持有 的记录数；`settled_count` 改为 `SELECT COUNT(*) FROM settlements [AND scope]`，即结清查询页记录数；`holding_total`/`interest_profit` 维持 securities 明细全局口径）、`blueprints/securities/query.py`（移除 overview_clauses 构造，概览调用改传 `scope_sql, scope_params`）
- 功能：证券页概览「持有中」数量 = 统计分析页（status=持有）显示的记录数；「已结清」数量 = 结清查询页显示的记录数（均仅受数据隔离约束，与目标页默认记录数完全一致）
- 逻辑要点：statistics_summary 以 code_id 唯一键（一行=一个关联编号产品），settlements 一行=一笔结清；两表均带 user_id 支持 scope 隔离。概览不再跟随 securities 表搜索条件（点击卡片跳转的目标页也是全局/默认），语义一致
- 影响面：证券页概览数量统计；已自测（证券页持有中35=统计页35=库35；已结清30=结清页30=库30）

### 2026-08-16 证券管理页概览卡片点击跳转（按关联编号分类查询）
- 改动文件：`templates/securities.html`（概览卡片「持有中」「已结清」由 `<div>` 改为 `<a>` 链接）
- 功能：
  - 点击「持有中」→ 跳转统计分析页 `url_for('statistics.query', status='持有')`，按关联编号分类展示持有的产品
  - 点击「已结清」→ 跳转结清查询页 `url_for('settlement.query')`，展示已结清的产品（按关联编号呈现）
- 逻辑要点：统计分析页 `query` 已支持 `status`/`code_id` 过滤（statistics_summary 含 code_id 列）；结清查询页 `query` 已支持 `code_id` 过滤且默认即已结清记录。卡片带 `cursor:pointer` 与悬停提示文案
- 影响面：仅证券页概览卡片交互；已自测（持有中链接=/statistics/?status=持有；已结清链接=/settlement/）

### 2026-08-16 统计分析页修复：无操作权限时不显示操作列
- 改动文件：`templates/statistics.html`（产品汇总表：表头「操作」列与每行的操作单元格都改为仅在 `can('statistics','add') or can('statistics','edit')` 时渲染；空数据行的 colspan 由权限动态取 6/7）
- 功能：当用户对统计分析页既无「新增」也无「修改」权限时，整列（含表头）隐藏，避免出现空白操作单元格；任一权限存在则正常显示对应按钮
- 逻辑要点：权限判断沿用 `has_perm`（admin 恒为真；普通用户按角色并集），与 before_request 的 POST 操作级拦截一致
- 影响面：仅统计页产品汇总表展示；已自测（无 add/edit 权限用户访问：表头无「操作」列、表格 6 列、无买入/卖出/结清按钮）

### 2026-08-16 证券管理页概览统计默认显示全量结清、搜索时按条件显示
- 改动文件：`blueprints/securities/query.py`（条件构建拆分为「列表查询条件 where_clauses」与「概览统计条件 overview_clauses」两组：公共搜索条件共用；默认 status 为空时列表排除结清但概览不加状态过滤；仅当显式搜索 status=结清/持有 时概览才按状态过滤；`get_overview` 改传 `overview_clauses/overview_params`）
- 功能：默认打开页面（未搜索）时，「已结清」统计框显示全部已结清记录数（此前受列表默认排除结清影响显示 0）；点击搜索（带状态等条件）后按搜索结果展示
- 逻辑要点：概览统计与列表查询解耦；默认无状态过滤时各统计卡按其内置 status 条件独立统计（已结清=全量结清）；搜索 status=持有 时已结清框为 0（符合"搜索结果"语义）
- 影响面：证券查询页概览统计；已自测（默认页已结清 65 条=全量结清；搜索结清+code 过滤显示 1 条；搜索持有显示 0 条；列表仍默认排除结清）

### 2026-08-16 证券管理页默认按买入时间倒序、去掉分组查询
- 改动文件：`blueprints/securities/query.py`（排序统一改为 `record_date DESC, id DESC`，删除原先「持有按 stock_code 分组、结清按 code_id 分组」的 ORDER BY）、`templates/securities.html`（删除记录表格中 group-separator 分组分隔行；概览卡片「X 组」改为「X 条」）、`blueprints/securities/__init__.py`（get_overview 中 holding_count/settled_count 由 `COUNT(DISTINCT stock_code/code_id)` 改为 `COUNT(*)`，与「条数」语义一致）、`static/style.css`（删除不再使用的 .group-separator/.group-tag/.group-code 样式）
- 功能：证券列表（持有/结清）统一按操作日期倒序展示，不再按股票代码或关联编号分组；顶部统计卡片显示记录条数
- 逻辑要点：排序仅影响展示顺序，不影响过滤/统计口径；概览统计仍跟随查询过滤条件（默认页只统计持有，结清页统计结清）
- 影响面：证券查询展示与概览统计；已自测（AAA 两条记录日期 08-15 在 08-10 前；默认页持有 40 条、结清页 65 条与 COUNT(*) 一致）

### 2026-08-15 修复金额悬停万缩写提示（改为立即执行 + MutationObserver）
- 改动文件：`templates/base.html`（金额提示脚本：去掉 DOMContentLoaded 依赖，改为脚本末尾直接执行 applyWanTooltips()，并用 MutationObserver 监听 body 子节点变化，动态重绘表格后持续生效；已处理元素加 data-wan 去重）
- 功能：金额 >=10000 时鼠标悬停仍展示「万」缩写（如 108万5835.65）；修复此前依赖 DOMContentLoaded 在部分场景不触发、及 fetch 重绘表格后 title 被清空导致不显示的问题
- 逻辑要点：fmtWan 算法不变（已验证 1085835.65->108万5835.65、负数、<10000 不提示）；脚本置于 body 末尾 DOM 已就绪，直接执行更可靠
- 影响面：纯前端展示；跨页面通用

### 2026-08-15 证券新增/买入/卖出弹框关联编号必填
- 改动文件：`templates/securities.html`（新增弹窗关联编号 input 加 required；买入/卖出快速交易弹框 code_id 为 readonly 且由行数据预填，本就非空）、`blueprints/securities/add.py`（必填字段校验列表加入 code_id，空则 flash 错误并跳回查询）
- 功能：提交证券记录时关联编号不能为空；前端 validateSecForm 拦截必填，后端 add 路由二次校验
- 逻辑要点：买入/卖出走同一 add 路由且 code_id 预填，天然满足；新增弹窗需手动填写
- 影响面：仅证券新增/快速交易的提交校验；不改变存储结构

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
