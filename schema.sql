-- 个人投资管理系统数据库结构
-- 运行方式: mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS investment
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE investment;

-- 1. 本金管理表
DROP TABLE IF EXISTS principal;
CREATE TABLE principal (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL COMMENT '归属用户账号',
    broker VARCHAR(100) NOT NULL COMMENT '券商名称，如华宝证券',
    record_date DATE NOT NULL COMMENT '操作日期',
    operation_type ENUM('充值', '取现') NOT NULL COMMENT '本金操作类型',
    amount DECIMAL(15, 2) NOT NULL COMMENT '金额',
    remark VARCHAR(255) DEFAULT NULL COMMENT '备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_user_id (user_id)
) COMMENT='本金充值/取现记录';

-- 2. 证券管理表
DROP TABLE IF EXISTS securities;
CREATE TABLE securities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL COMMENT '归属用户账号',
    broker VARCHAR(100) NOT NULL COMMENT '券商名称，如华宝证券',
    record_date DATE NOT NULL COMMENT '操作日期',
    operation_type ENUM('买入', '卖出', '利息') NOT NULL COMMENT '操作类型',
    stock_code VARCHAR(20) NOT NULL COMMENT '股票/产品代码',
    code_id VARCHAR(20) DEFAULT NULL COMMENT '关联编号',
    stock_name VARCHAR(100) NOT NULL COMMENT '股票/产品名称',
    unit_price DECIMAL(15, 4) DEFAULT NULL COMMENT '单价',
    quantity INT DEFAULT NULL COMMENT '数量',
    total_amount DECIMAL(15, 2) NOT NULL COMMENT '总金额',
    fees DECIMAL(15, 2) DEFAULT 0 COMMENT '费用',
    asset_type ENUM('股票', '债券', '基金', '定存', '港美股') NOT NULL COMMENT '资产类型',
    status ENUM('持有', '结清') DEFAULT '持有' COMMENT '持仓状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_user_id (user_id)
) COMMENT='证券账户操作记录';

-- 3. 场外APP管理表
DROP TABLE IF EXISTS otc_app;
CREATE TABLE otc_app (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL COMMENT '归属用户账号',
    app_name VARCHAR(100) NOT NULL COMMENT 'APP名称，如雪球APP',
    record_date DATE NOT NULL COMMENT '操作日期',
    operation_type ENUM('买入', '卖出', '利息') NOT NULL COMMENT '操作类型',
    product_code VARCHAR(20) NOT NULL COMMENT '产品代码',
    code_id VARCHAR(20) DEFAULT NULL COMMENT '关联编号',
    product_name VARCHAR(100) NOT NULL COMMENT '产品名称',
    unit_price DECIMAL(15, 4) DEFAULT NULL COMMENT '单价/净值',
    quantity DECIMAL(15, 4) DEFAULT NULL COMMENT '数量/份额',
    total_amount DECIMAL(15, 2) NOT NULL COMMENT '总金额',
    fees DECIMAL(15, 2) DEFAULT 0 COMMENT '费用',
    asset_type ENUM('股票', '债券', '基金', '定存', '港美股') NOT NULL COMMENT '资产类型',
    status ENUM('持有', '结清') DEFAULT '持有' COMMENT '持仓状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_user_id (user_id)
) COMMENT='场外基金APP操作记录';

-- 4. 结清记录表
DROP TABLE IF EXISTS settlements;
CREATE TABLE settlements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL COMMENT '归属用户账号',
    settle_date DATE NOT NULL COMMENT '结清日期',
    code VARCHAR(20) NOT NULL COMMENT '产品代码',
    code_id VARCHAR(20) DEFAULT NULL COMMENT '关联编号',
    product_name VARCHAR(100) NOT NULL COMMENT '产品名称',
    asset_type ENUM('股票', '债券', '基金', '定存', '港美股') NOT NULL COMMENT '资产类型',
    invest_amount DECIMAL(15, 2) NOT NULL COMMENT '投资本金（该 code 买入总金额）',
    settle_amount DECIMAL(15, 2) NOT NULL COMMENT '结清金额',
    profit DECIMAL(15, 2) NOT NULL COMMENT '收益',
    fees DECIMAL(15, 2) DEFAULT 0 COMMENT '总费用（买入费用+卖出费用）',
    holding_days INT DEFAULT NULL COMMENT '持有天数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_user_id (user_id)
) COMMENT='结清记录';

-- 2026-08-04
-- securities 表新增 code_id 字段
ALTER TABLE securities ADD COLUMN code_id VARCHAR(20) DEFAULT NULL COMMENT '关联编号' AFTER stock_code;

-- otc_app 表新增 code_id 字段
ALTER TABLE otc_app ADD COLUMN code_id VARCHAR(20) DEFAULT NULL COMMENT '关联编号' AFTER product_code;

-- settlements 表新增 code_id 字段
ALTER TABLE settlements ADD COLUMN code_id VARCHAR(20) DEFAULT NULL COMMENT '关联编号' AFTER code;

-- settlements 表新增 fees、holding_days 字段
ALTER TABLE settlements ADD COLUMN fees DECIMAL(15,2) DEFAULT 0 COMMENT '总费用' AFTER profit;
ALTER TABLE settlements ADD COLUMN holding_days INT DEFAULT NULL COMMENT '持有天数' AFTER fees;

-- settlements 表新增 quantity 字段
ALTER TABLE settlements ADD COLUMN quantity DECIMAL(15,4) DEFAULT NULL COMMENT '数量' AFTER holding_days;

-- 5. 统计分析汇总表（以关联编号为唯一键）
DROP TABLE IF EXISTS statistics_summary;
CREATE TABLE statistics_summary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL COMMENT '归属用户账号',
    code_id VARCHAR(20) NOT NULL UNIQUE COMMENT '关联编号（唯一键）',
    code VARCHAR(50) NOT NULL COMMENT '产品代码',
    name VARCHAR(100) NOT NULL COMMENT '产品名称',
    asset_type VARCHAR(20) DEFAULT NULL COMMENT '资产类型',
    holding_amount DECIMAL(15,2) DEFAULT 0 COMMENT '持有金额',
    status ENUM('持有', '结清') DEFAULT '持有' COMMENT '持仓状态',
    source VARCHAR(20) DEFAULT NULL COMMENT '数据来源（securities/otc_app）',
    remark VARCHAR(500) DEFAULT NULL COMMENT '备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_user_id (user_id)
) COMMENT='统计分析汇总表（关联编号维度）';

-- 2026-08-12
-- 兼容已有库：为 5 张业务表新增 user_id 字段及索引
ALTER TABLE principal ADD COLUMN user_id VARCHAR(50) NOT NULL DEFAULT 'admin' COMMENT '归属用户账号' AFTER id;
ALTER TABLE securities ADD COLUMN user_id VARCHAR(50) NOT NULL DEFAULT 'admin' COMMENT '归属用户账号' AFTER id;
ALTER TABLE otc_app ADD COLUMN user_id VARCHAR(50) NOT NULL DEFAULT 'admin' COMMENT '归属用户账号' AFTER id;
ALTER TABLE settlements ADD COLUMN user_id VARCHAR(50) NOT NULL DEFAULT 'admin' COMMENT '归属用户账号' AFTER id;
ALTER TABLE statistics_summary ADD COLUMN user_id VARCHAR(50) NOT NULL DEFAULT 'admin' COMMENT '归属用户账号' AFTER id;

ALTER TABLE principal ADD INDEX idx_user_id (user_id);
ALTER TABLE securities ADD INDEX idx_user_id (user_id);
ALTER TABLE otc_app ADD INDEX idx_user_id (user_id);
ALTER TABLE settlements ADD INDEX idx_user_id (user_id);
ALTER TABLE statistics_summary ADD INDEX idx_user_id (user_id);

-- ============================================================
-- 6. 用户表
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    user_id VARCHAR(50) NOT NULL UNIQUE COMMENT '用户ID（登录账号）',
    username VARCHAR(100) NOT NULL COMMENT '用户姓名',
    phone VARCHAR(20) DEFAULT '' COMMENT '用户号码',
    password VARCHAR(255) NOT NULL COMMENT '登录密码（哈希）',
    status TINYINT DEFAULT 1 COMMENT '用户状态：1启用 0禁用',
    is_admin TINYINT DEFAULT 0 COMMENT '是否超级管理员：1是 0否',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) COMMENT='用户表';

-- ============================================================
-- 7. 角色表
-- ============================================================
CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    role_name VARCHAR(50) NOT NULL UNIQUE COMMENT '角色名称',
    description VARCHAR(255) DEFAULT '' COMMENT '角色描述',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) COMMENT='角色表';

-- ============================================================
-- 8. 用户-角色关联表（多对多）
-- ============================================================
CREATE TABLE IF NOT EXISTS user_roles (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    user_id INT NOT NULL COMMENT '用户主键ID',
    role_id INT NOT NULL COMMENT '角色主键ID',
    UNIQUE KEY uk_user_role (user_id, role_id)
) COMMENT='用户-角色关联表';

-- ============================================================
-- 9. 角色权限表（页面维度）
-- ============================================================
CREATE TABLE IF NOT EXISTS role_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    role_id INT NOT NULL COMMENT '角色主键ID',
    page VARCHAR(50) NOT NULL COMMENT '页面标识：principal/securities/otc_app/settlement/statistics/users/roles',
    can_view TINYINT DEFAULT 0 COMMENT '查看权限',
    can_add TINYINT DEFAULT 0 COMMENT '新增权限',
    can_edit TINYINT DEFAULT 0 COMMENT '修改权限',
    can_delete TINYINT DEFAULT 0 COMMENT '删除权限',
    UNIQUE KEY uk_role_page (role_id, page)
) COMMENT='角色权限表';

