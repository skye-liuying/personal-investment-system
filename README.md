# 个人投资管理系统

一个基于 **Python + Flask + MySQL** 的 Web 应用，用于管理个人投资记录，包含本金管理、证券管理、场外 APP 管理、统计分析和结清查询五大模块。

> **最后更新：2026-08-03**

## 功能模块

1. **本金管理** — 记录券商账户的充值/取现流水。
2. **证券管理** — 记录证券账户的买入/卖出/利息操作，支持股票、债券、基金、定存。
3. **场外 APP 管理** — 记录场外基金 APP（如雪球、天天基金）的操作记录。
4. **统计分析** — 按资产类型统计投资金额与占比，按 Code 汇总持仓并支持一键结清。
5. **结清查询** — 查询所有结清记录及收益情况。

## 项目结构

```
e:/personal-investment-system/
├── app.py                          # 应用入口：注册蓝图 + 启动
├── config.py                       # 数据库 & Flask 配置
├── database.py                     # 数据库连接工厂
├── paginate.py                     # 分页工具函数
├── schema.sql                      # 数据库建表语句
├── requirements.txt                # Python 依赖
├── blueprints/                     # 蓝图模块（按功能拆分）
│   ├── principal/                  # 本金管理
│   │   ├── __init__.py             # 蓝图创建 + 概览统计
│   │   ├── add.py                  # POST /principal/add     — 新增记录
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
│   └── settlement/                 # 结清查询
│       ├── __init__.py
│       └── query.py                # GET  /settlement/       — 结清记录查询+分页
├── templates/                      # Jinja2 模板
│   ├── base.html                   # 基础布局（导航栏）
│   ├── _pagination.html            # 分页组件（复用）
│   ├── principal.html
│   ├── securities.html
│   ├── otc_app.html
│   ├── statistics.html
│   └── settlement.html
└── static/
    └── style.css                   # 全局样式
```

## 关键设计

### 模块化拆分

原始代码全部集中在约 500 行的 `app.py` 中，不利于维护。重构后按**页面 × 操作**维度拆分为 17 个 `.py` 文件：

| 模块 | 文件 | 职责 | API 端点 |
|------|------|------|----------|
| **本金管理** | `add.py` | 新增充值/取现记录 | `POST /principal/add` |
| | `query.py` | 按券商/日期/类型搜索，分页展示 | `GET /principal/` |
| | `delete.py` | 删除指定记录 | `POST /principal/delete` |
| **证券管理** | `add.py` | 新增买入/卖出/利息记录 | `POST /securities/add` |
| | `query.py` | 按券商/代码/名称/类型/日期搜索，分页展示 | `GET /securities/` |
| | `delete.py` | 删除指定记录 | `POST /securities/delete` |
| **场外APP管理** | `add.py` | 新增买入/卖出/利息记录 | `POST /otc_app/add` |
| | `query.py` | 按APP/代码/名称/类型/日期搜索，分页展示 | `GET /otc_app/` |
| | `delete.py` | 删除指定记录 | `POST /otc_app/delete` |
| **统计分析** | `query.py` | 资产类型占比 + Code汇总（搜索+分页） | `GET /statistics/` |
| | `settle.py` | 一键结清产品（更新状态+写结算表） | `POST /statistics/settle` |
| **结清查询** | `query.py` | 按代码/名称/类型/日期搜索，分页展示 | `GET /settlement/` |

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

- 在对应模块页面填写表单即可添加数据。
- 每行记录后有 **删除** 按钮。
- 在 **统计分析** 页面，点击 Code 行的 **结清** 按钮，输入结清日期和结清金额，系统会：
  - 将该 Code 在「证券管理」和「场外 APP 管理」中的所有记录标记为「结清」。
  - 自动在「结清表」中插入一条结清记录。
- 在 **结清查询** 页面可查看所有历史结清记录及收益汇总。

## 数据库表结构

| 表名 | 说明 |
|------|------|
| `principal` | 本金管理记录 |
| `securities` | 证券管理记录 |
| `otc_app` | 场外 APP 管理记录 |
| `settlement` | 结清记录 |

详见 `schema.sql`。

## 技术栈

- 后端：Flask + PyMySQL（Blueprint 模块化架构）
- 前端：原生 HTML + CSS + JavaScript（Jinja2 模板）
- 数据库：MySQL

## 变更记录

| 日期 | 变更内容 |
|------|----------|
| 2026-08-03 | 项目结构重构：`app.py` 拆分为 17 个文件，引入 Flask Blueprint、共享工具模块、搜索分页 |
| 2026-08-03 | 新增全局搜索 + 服务器端分页（每页 10/20/50/100） |
| 2026-08-03 | 移除页面中的行内编辑功能，简化交互 |
| 2026-08-03 | Python 环境升级到 3.14，虚拟环境重建 |

## 注意事项

- 生产环境请修改 `config.py` 中的 `SECRET_KEY`。
- 默认开启 debug 模式，正式上线请关闭：`app.run(debug=False)`。
