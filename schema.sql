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
    broker VARCHAR(100) NOT NULL COMMENT '券商名称，如华宝证券',
    record_date DATE NOT NULL COMMENT '操作日期',
    operation_type ENUM('充值', '取现') NOT NULL COMMENT '本金操作类型',
    amount DECIMAL(15, 2) NOT NULL COMMENT '金额',
    remark VARCHAR(255) DEFAULT NULL COMMENT '备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COMMENT='本金充值/取现记录';

-- 2. 证券管理表
DROP TABLE IF EXISTS securities;
CREATE TABLE securities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    broker VARCHAR(100) NOT NULL COMMENT '券商名称，如华宝证券',
    record_date DATE NOT NULL COMMENT '操作日期',
    operation_type ENUM('买入', '卖出', '利息') NOT NULL COMMENT '操作类型',
    stock_code VARCHAR(20) NOT NULL COMMENT '股票/产品代码',
    code_id VARCHAR(20) DEFAULT NULL COMMENT '关联编号',
    stock_name VARCHAR(100) NOT NULL COMMENT '股票/产品名称',
    unit_price DECIMAL(15, 4) DEFAULT NULL COMMENT '单价',
    quantity DECIMAL(15, 4) DEFAULT NULL COMMENT '数量',
    total_amount DECIMAL(15, 2) NOT NULL COMMENT '总金额',
    fees DECIMAL(15, 2) DEFAULT 0 COMMENT '费用',
    asset_type ENUM('股票', '债券', '基金', '定存') NOT NULL COMMENT '资产类型',
    status ENUM('持有', '结清') DEFAULT '持有' COMMENT '持仓状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COMMENT='证券账户操作记录';

-- 3. 场外APP管理表
DROP TABLE IF EXISTS otc_app;
CREATE TABLE otc_app (
    id INT AUTO_INCREMENT PRIMARY KEY,
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
    asset_type ENUM('股票', '债券', '基金', '定存') NOT NULL COMMENT '资产类型',
    status ENUM('持有', '结清') DEFAULT '持有' COMMENT '持仓状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COMMENT='场外基金APP操作记录';

-- 4. 结清记录表
DROP TABLE IF EXISTS settlements;
CREATE TABLE settlements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    settle_date DATE NOT NULL COMMENT '结清日期',
    code VARCHAR(20) NOT NULL COMMENT '产品代码',
    code_id VARCHAR(20) DEFAULT NULL COMMENT '关联编号',
    product_name VARCHAR(100) NOT NULL COMMENT '产品名称',
    asset_type ENUM('股票', '债券', '基金', '定存') NOT NULL COMMENT '资产类型',
    invest_amount DECIMAL(15, 2) NOT NULL COMMENT '投资本金（该 code 买入总金额）',
    settle_amount DECIMAL(15, 2) NOT NULL COMMENT '结清金额',
    profit DECIMAL(15, 2) NOT NULL COMMENT '收益',
    fees DECIMAL(15, 2) DEFAULT 0 COMMENT '总费用（买入费用+卖出费用）',
    holding_days INT DEFAULT NULL COMMENT '持有天数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

