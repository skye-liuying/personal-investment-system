# 个人投资管理系统

一个基于 **Python + Flask + MySQL** 的 Web 应用，用于管理个人投资记录，包含本金管理、证券管理、场外 APP 管理、统计分析和结清查询五大业务模块，并内置用户登录、角色权限体系与数据隔离。

> **版本：2026年Skyeliuying 第二版 | 最后更新：2026-08-13**

## 功能模块

1. **本金管理** — 记录券商账户的充值/取现流水。
2. **证券管理** — 记录证券账户的买入/卖出/利息操作，支持股票、债券、基金、定存。
3. **场外 APP 管理** — 记录场外基金 APP（如雪球、天天基金）的操作记录。
4. **统计分析** — 按资产类型统计投资金额与占比，按 Code 汇总持仓并支持一键结清。
5. **结清查询** — 查询所有结清记录及收益情况。
6. **用户管理** — 管理员创建/禁用用户，登录账号唯一（UNIQUE 约束 + 前后端即时校验）；可配置组长-组员关系。
7. **角色管理** — 管理员按页面 × 操作（查看/新增/修改/删除）配置角色权限；内置 **组长** 角色，数据范围自动扩展到自己和组员。

## 项目结构

```
e:/personal-investment-system/
├── app.py                          # 应用入口：注册蓝图 + 登录/权限全局拦截 + 启动
├── config.py                       # 数据库 & Flask 配置
├── database.py                     # 数据库连接工厂
├── paginate.py                     # 分页工具函数
├── schema.sql                      # 数据库建表语句
├── requirements.txt                # Python 依赖
├── blueprints/                     # 蓝图模块（按功能拆分）
│   ├── auth/                       # 认证与权限
│   │   ├── __init__.py             # 蓝图创建
│   │   ├── login.py                # GET/POST /auth/login  — 登录
│   │   ├── logout.py               # POST /auth/logout     — 退出
│   │   └── helpers.py              # 权限判断/数据隔离等工具函数
│   ├── principal/                  # 本金管理
│   │   ├── __init__.py             # 蓝图创建 + 概览统计
│   │   ├── add.py                  # POST /principal/add     — 新增记录
│   │   ├── edit.py                 # POST /principal/edit    — 编辑记录
│   │   ├── query.py                # GET  /principal/        — 查询+搜索+分页
│   │   └── delete.py               # POST /principal/delete  — 删除记录
│   ├── securities/                 # 证券管理
│   │   ├── __init__.py
│   │   ├── add.py                  # POST /securities/add
│   │   ├── query.py                # GET  /securities/
│   │   └── delete.py               # POST /securities/delete
│   ├── otc_app/                    # 场外APP管理
│   │   ├── __init__.py
│   │   ├── add.py                  # POST /otc_app/add
│   │   ├── query.py                # GET  /otc_app/
│   │   └── delete.py               # POST /otc_app/delete
│   ├── statistics/                 # 统计分析
│   │   ├── __init__.py
│   │   ├── query.py                # GET  /statistics/       — 资产占比+Code汇总
│   │   └── settle.py               # POST /statistics/settle — 产品结清
│   ├── settlement/                 # 结清查询
│   │   ├── __init__.py
│   │   ├── add.py                  # POST /settlement/add    — 新增修正
│   │   ├── edit.py                 # POST /settlement/edit   — 编辑记录
│   │   ├── correct.py              # POST /settlement/correct— 数据矫正
│   │   └── query.py                # GET  /settlement/       — 结清记录查询+分页
│   ├── users/                      # 用户管理
│   │   ├── __init__.py
│   │   ├── query.py                # GET  /users/            — 用户列表
│   │   ├── add.py                  # POST /users/add         — 新增用户
│   │   ├── edit.py                 # POST /users/edit        — 编辑用户
│   │   └── delete.py               # POST /users/delete      — 删除用户
│   └── roles/                      # 角色管理
│       ├── __init__.py
│       ├── query.py                # GET  /roles/            — 角色列表+权限矩阵
│       ├── add.py                  # POST /roles/add         — 新增角色
│       ├── edit.py                 # POST /roles/edit        — 编辑角色
│       └── delete.py               # POST /roles/delete      — 删除角色
├── templates/                      # Jinja2 模板
│   ├── base.html                   # 基础布局（导航栏按权限显隐）
│   ├── _pagination.html            # 分页组件（复用）
│   ├── login.html                  # 登录页
│   ├── 403.html                    # 无权限提示页
│   ├── principal.html
│   ├── securities.html
│   ├── otc_app.html
│   ├── statistics.html
│   ├── settlement.html
│   ├── users.html
│   └── roles.html
└── static/
    └── style.css                   # 全局样式
```

## 关键设计

### 模块化拆分

原始代码全部集中在约 500 行的 `app.py` 中，不利于维护。重构后按**页面 × 操作**维度拆分为 21 个 `.py` 文件：

| 模块 | 文件 | 职责 | API 端点 |
|------|------|------|----------|
| **本金管理** | `add.py` | 新增充值/取现记录（弹窗提交） | `POST /principal/add` |
| | `edit.py` | 编辑指定记录（弹窗提交） | `POST /principal/edit` |
| | `query.py` | 按券商/日期/类型搜索，分页展示 | `GET /principal/` |
| | `delete.py` | 删除指定记录 | `POST /principal/delete` |
| **证券管理** | `add.py` | 新增买入/卖出/利息记录，支持快速交易弹窗 | `POST /securities/add` |
| | `query.py` | 按券商/代码/名称/类型/日期/状态搜索，分页展示 | `GET /securities/` |
| | `delete.py` | 删除指定记录（联动保留查询参数） | `POST /securities/delete` |
| **场外APP管理** | `add.py` | 新增买入/卖出/利息记录，卖出时自动校验数量 | `POST /otc_app/add` |
| | `query.py` | 按APP/代码/名称/类型/日期搜索，分页展示 | `GET /otc_app/` |
| | `delete.py` | 删除指定记录（联动保留查询参数） | `POST /otc_app/delete` |
| **统计分析** | `query.py` | 资产类型占比 + Code汇总（搜索+分页，含 source 标识） | `GET /statistics/` |
| | `settle.py` | 一键结清（支持单价×数量自动计算总金额） | `POST /statistics/settle` |
| **结清查询** | `add.py` | 新增/修正结清记录 | `POST /settlement/add` |
| | `edit.py` | 编辑结清记录 | `POST /settlement/edit` |
| | `correct.py` | 数据矫正：按公式重新计算收益并同步源表状态 | `POST /settlement/correct` |
| | `query.py` | 按代码/名称/类型/日期搜索，分页展示 | `GET /settlement/` |

### Flask Blueprint 机制

- 每个功能模块是一个独立的 **Flask Blueprint**，通过 `url_prefix` 挂载到对应路径。
- 每个 Blueprint 的 `__init__.py` 创建蓝图对象，末尾 `import` 子模块来自动注册路由。
- `__init__.py` 中同时提取了**概览统计**辅助函数（如本金总计、持仓汇总），供 `query.py` 复用。

### 共享工具模块

| 文件 | 说明 |
|------|------|
| `config.py` | 统一管理 MySQL 连接参数和 Flask 密钥 |
| `database.py` | `get_db()` 工厂函数，返回 `pymysql` 连接（DictCursor） |
| `paginate.py` | `paginate()` 从 request 提取 `page`/`per_page`，返回分页元数据字典 |

### 搜索 + 分页

- 所有列表页支持多条件搜索，通过 GET 参数传递。
- `paginate.py` 提取通用分页逻辑：页码、每页条数（10/20/50/100）、偏移量。
- 前端复用 `_pagination.html` 组件，自动保持搜索参数。

### 用户登录与权限体系

系统内置三级权限模型，由 `blueprints/auth/helpers.py` 统一提供：

| 表 | 说明 |
|------|------|
| `users` | 用户表，`user_id`（登录账号）唯一，密码为 Werkzeug 哈希存储 |
| `roles` | 角色表，如 `admin`（超级管理员）、`组长` |
| `user_roles` | 用户-角色多对多关联 |
| `role_permissions` | 角色权限矩阵：页面 × 操作（查看/新增/修改/删除） |
| `user_groups` | 组长-组员关系表（存登录账号，`leader_id` + `member_id` 唯一） |

- **登录校验**：`GET/POST /auth/login` 校验账号、密码哈希、启用状态；登录后 `session` 记录 `login_id`（登录账号）与 `is_admin` 标识。
- **全局拦截**：`app.py` 的 `before_request` 统一处理——未登录跳转登录页；无页面 `view` 权限返回 403；POST 操作按 endpoint 推断所需权限（`add/edit/delete/correct/settle/trade`）并拦截。
- **动态菜单**：`base.html` 中所有导航项用 `{% if can('页面','view') %}` 包裹，无权限页面不显示入口。
- **操作列显隐**：如本金管理页，仅当用户拥有该页 `edit`/`delete` 任一权限时才渲染操作列（`colspan` 自适应）。
- **超级管理员**：`is_admin=1` 用户（如 `admin`）自动拥有所有页面全部权限，不受角色配置限制。

### 数据隔离（多用户）

- 5 张业务表（`principal`/`securities`/`otc_app`/`settlements`/`statistics_summary`）均带 `user_id VARCHAR(50)` 字段，存**登录账号字符串**（如 `liuying`），非 users 表数字主键。
- 查询层通过 `scope_condition()` 注入数据范围条件：
  - `admin` → 查看全部（`(None, None)`）
  - **组长**（在 `user_groups` 表配置了组员）→ `user_id IN (自己, 组员...)`，可查看自己和组员创建的数据
  - 普通用户 → `user_id = %s`，只看自己的数据
- 修改/删除/矫正/结清等操作通过 `owner_condition()` 应用同样的范围条件：组长可修改自己和组员的数据，不能动范围外其他用户的数据。
- 新增记录时自动写入 `get_current_user_id()`（即 `session['login_id']`）。
- 删除证券/场外记录时，统计同步使用**被删记录的归属账号**（而非当前登录者），保证组长删除组员数据后统计正确。
- 统计页结清（`settle`）会先从源头表确定产品的归属用户：仅当该产品在组长范围内归属唯一用户时才允许结清，归属多个用户时提示分别处理，避免脏数据。
- 兼容旧库：`app.py init_database()` 启动时检测业务表 `user_id` 列，若为旧版 INT 列，先按 users 表映射数字 id → 登录账号更新数据，再 `MODIFY COLUMN` 改为 VARCHAR。
- 用户创建三重防重：数据库 `UNIQUE` 约束 + 后端 `IntegrityError` 兜底 + 前端 `checkUserIdExists()` 即时校验。

### 前端性能优化

- 移除 Google Fonts 外部 CDN（国内访问超时且同步阻塞渲染），字体栈改为系统字体，显著提升首屏加载速度。
- 证券管理搜索区改为两行网格布局，一行平铺 5 个查询条件，上下对齐更整齐。

## 环境要求

- Python 3.8+
- MySQL 5.7+ 或 MariaDB 10.3+

## 本地部署步骤

### 1. 克隆/解压项目

```bash
cd personal-investment-system
```

### 2. 创建数据库

登录 MySQL，执行 `schema.sql`：

```bash
mysql -u root -p < schema.sql
```

默认会创建名为 `personal_investment` 的数据库。

### 3. 安装依赖

建议使用虚拟环境：

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 4. 配置数据库连接

编辑 `config.py`，修改数据库连接参数：

```python
# config.py
class Config:
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = ''
    MYSQL_DB = 'personal_investment'
    MYSQL_PORT = 3306
```

### 5. 启动应用

```bash
python app.py
```

或使用 VS Code F5（已配置 `.vscode/launch.json` 使用虚拟环境 Python）。

打开浏览器访问：http://localhost:5000

## 使用说明

### 登录

- 访问 `http://localhost:5000` 自动跳转登录页，默认管理员账号 `admin` / 密码 `admin`（首次启动自动创建，生产环境请修改）。
- 未登录访问任何业务页面会跳转登录页；登录后按当前用户权限动态显示导航菜单。

### 用户管理（仅管理员）

- 管理员在「用户管理」页创建用户：登录账号唯一，重复会在前端即时提示。
- 支持编辑用户信息、重置密码、启用/禁用账号；禁用账号无法登录。

### 角色管理（仅管理员）

- 在「角色管理」页按 **页面 × 操作** 勾选权限矩阵（查看/新增/修改/删除）。
- 给用户分配角色（一个用户可绑定多个角色，权限取并集）。
- 普通用户登录后，无权限的页面不显示菜单入口，直接访问会提示无权限（403）。

### 组长角色（示例：liuying 管理 baba、mama）

1. 系统已内置 **组长** 角色（默认 5 个业务页面拥有查看/新增/修改权限，删除权限按需在角色管理开启），也可自行创建任意角色。
2. 在「用户管理」页编辑用户 **liuying**，在「组员」下拉中多选 **baba、mama**，保存。
3. 将 **组长** 角色（或其他含业务页面权限的角色）分配给 liuying。
4. liuying 登录后，本金/证券/场外/统计/结清页面均可查看、修改自己创建的数据以及 baba、mama 创建的数据；其他用户（如 ccc）的数据不可见、不可操作。

> 说明：组长身份由 `user_groups` 表的配置决定（谁配置了组员谁就是组长），与角色名称无关；数据范围自动扩展为「自己 + 组员」。

### 本金管理
- 点击「充值」或「取现」按钮，弹出弹窗填写券商、日期和金额。
- 弹窗中券商默认填充为最近一笔记录的券商，金额和日期需手动填写。
- 保存后页面自动按保存的券商+日期过滤，显示刚添加的记录。
- 每行记录后有 **编辑** 和 **删除** 按钮。

### 证券管理
- 通过顶部表单新增买入/卖出/利息记录，选中操作类型后自动联动显示对应字段。
- 卖出时系统自动校验数量不超过持有数量。
- 持有记录行左侧有「买入」「卖出」**快速交易按钮**，点击弹窗可快速操作。
- 支持单价 × 数量 = 总金额的自动计算。

### 场外 APP 管理
- 与证券管理类似，支持买入/卖出/利息三种操作类型。
- 卖出时系统自动校验数量不超过持有数量。
- 利息记录不需要填写 product_code。

### 统计分析
- 按资产类型统计投资金额与占比，按 Code 汇总持仓。
- 点击 Code 行的 **结清** 按钮，弹出结清弹窗，支持单价 × 数量自动计算总金额。
- 结清后系统自动将对应 Code 在源表中的所有「持有」记录标记为「结清」。

### 结清查询
- 查询所有已结清记录及收益汇总。
- 每条记录有 **编辑** 和 **删除** 按钮。
- 每条记录有 **数据矫正** 按钮：根据关联编号从源表重新汇总交易数据，按公式重新计算收益：
  > 收益 = (卖出总金额 + 利息) - 买入总金额 - (买入手续费 + 卖出手续费 + 利息手续费)
- 矫正时自动将源表中对应关联编号的「持有」记录状态同步为「结清」。

## 数据库表结构

| 表名 | 说明 |
|------|------|
| `users` | 用户表（登录账号唯一，密码哈希存储，`is_admin` 标记超管） |
| `roles` | 角色表（内置 `admin`、`组长`） |
| `user_roles` | 用户-角色关联表（多对多） |
| `role_permissions` | 角色权限矩阵（页面 × 操作） |
| `user_groups` | 组长-组员关系表（`leader_id`/`member_id` 存登录账号，唯一约束防重复） |
| `principal` | 本金管理记录（`user_id` 归属账号） |
| `securities` | 证券管理记录（`user_id` 归属账号） |
| `otc_app` | 场外 APP 管理记录（`user_id` 归属账号） |
| `settlements` | 结清记录（`user_id` 归属账号） |
| `statistics_summary` | 统计分析汇总表（`user_id` 归属账号，`code_id` 唯一键） |

详见 `schema.sql`。

## 技术栈

- 后端：Flask + PyMySQL（Blueprint 模块化架构）
- 前端：原生 HTML + CSS + JavaScript（Jinja2 模板）
- 数据库：MySQL

## 变更记录

| 日期 | 变更内容 |
|------|----------|
| 2026-08-15 | **组长数据范围**：新增 `user_groups` 组长-组员关系表；内置「组长」角色；查询/编辑/删除/矫正/结清全部支持组长范围（自己+组员）；用户管理页可配置组员；统计同步使用被删记录归属账号；结清前校验产品归属唯一 |
| 2026-08-13 | **用户/角色权限体系**：新增登录认证（`auth` 蓝图）、用户管理（`users` 蓝图）、角色权限管理（`roles` 蓝图）；全局请求拦截（未登录跳转、无权限 403、POST 操作权限校验）；导航菜单与操作列按权限动态显隐 |
| 2026-08-13 | **数据隔离**：5 张业务表 `user_id` 存登录账号字符串（VARCHAR），旧库自动迁移（数字 id → 账号映射）；用户创建三重防重（UNIQUE + IntegrityError 兜底 + 前端即时校验） |
| 2026-08-13 | **前端优化**：移除 Google Fonts CDN 改系统字体栈（修复页面变慢）；证券管理搜索条件一行 5 个平铺布局；本金管理操作列按权限显隐 |
| 2026-08-09 | **2026年Skyeliuying 第二版**：五大模块全面优化升级 |
| 2026-08-09 | **本金管理 UI 重构**：去掉页面表单卡片，改为充值/取现按钮触发弹窗；券商默认填充最近记录；保存后自动定位到新记录 |
| 2026-08-09 | **本金管理**：新增编辑功能（弹窗形式） |
| 2026-08-09 | **证券管理**：新增快速交易按钮（买入/卖出弹窗）；操作类型联动显示字段；单价×数量自动计算；卖出数量校验 |
| 2026-08-09 | **场外APP管理**：操作类型联动显示/隐藏字段；卖出数量校验；product_code 改为非必填（适配利息记录） |
| 2026-08-09 | **统计分析**：结清弹窗增强（新增单价/数量字段，自动计算总金额）；增加 source 标识区分数据来源 |
| 2026-08-09 | **结清查询**：新增数据矫正功能（按公式重算收益，同步源表状态）；新增编辑记录功能 |
| 2026-08-09 | **全局优化**：删除/新增后保留查询参数联动跳转；新增 btn-success/btn-warning/btn-danger 按钮样式；modal 弹窗样式完善 |
| 2026-08-03 | 项目结构重构：`app.py` 拆分为 17 个文件，引入 Flask Blueprint、共享工具模块、搜索分页 |
| 2026-08-03 | 新增全局搜索 + 服务器端分页（每页 10/20/50/100） |
| 2026-08-03 | 移除页面中的行内编辑功能，简化交互 |
| 2026-08-03 | Python 环境升级到 3.14，虚拟环境重建 |

## 注意事项

- 生产环境请修改 `config.py` 中的 `SECRET_KEY`。
- 默认开启 debug 模式，正式上线请关闭：`app.run(debug=False)`。
