-- ============================================================================
-- 汉江（HanJiang） - 数据库建表脚本
-- 数据库: MySQL 8.0+  |  数据库名: hanjiang_dev  |  字符集: utf8mb4
-- 生成时间: 2026-09-23
-- ============================================================================

CREATE DATABASE IF NOT EXISTS `hanjiang_dev` DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_general_ci;
USE `hanjiang_dev`;
SET FOREIGN_KEY_CHECKS = 0;



-- 用户表
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
    `id`  BIGINT  NOT NULL AUTO_INCREMENT  COMMENT '主键ID',
    `username`  VARCHAR(50)  NOT NULL  COMMENT '用户名',
    `email`  VARCHAR(100)  NOT NULL  COMMENT '邮箱',
    `name`  VARCHAR(100)  COMMENT '姓名',
    `age`  INT  COMMENT '年龄',
    `password_hash`  VARCHAR(255)  COMMENT '密码哈希',
    `phone`  VARCHAR(20)  COMMENT '手机号',
    `avatar_url`  VARCHAR(500)  COMMENT '头像URL',
    `role_id`  BIGINT  NULL  COMMENT '主角色ID',
    `status`  ENUM('active','inactive','locked')  NOT NULL  DEFAULT 'active'  COMMENT '状态',
    `last_login_at`  DATETIME  NULL  COMMENT '最后登录时间',
    `last_login_ip`  VARCHAR(45)  COMMENT '最后登录IP',
    `created_at`  DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP  COMMENT '创建时间',
    `updated_at`  DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP  COMMENT '更新时间',
    `deleted_at`  DATETIME  NULL  COMMENT '软删除时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_email` (`email`),
    KEY `idx_role_id` (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 角色表
DROP TABLE IF EXISTS `roles`;
CREATE TABLE `roles` (
    `id`  BIGINT  NOT NULL AUTO_INCREMENT  COMMENT '主键ID',
    `role_name`  VARCHAR(50)  NOT NULL  COMMENT '角色名称',
    `role_code`  VARCHAR(50)  NOT NULL  COMMENT '角色编码',
    `description`  VARCHAR(255)  COMMENT '角色描述',
    `role_type`  ENUM('system','custom')  NOT NULL  DEFAULT 'custom'  COMMENT '类型',
    `status`  ENUM('enabled','disabled')  NOT NULL  DEFAULT 'enabled'  COMMENT '状态',
    `created_at`  DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP  COMMENT '创建时间',
    `updated_at`  DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP  COMMENT '更新时间',
    `deleted_at`  DATETIME  NULL  COMMENT '软删除时间',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色表';

-- 权限表
DROP TABLE IF EXISTS `permissions`;
CREATE TABLE `permissions` (
    `id`  BIGINT  NOT NULL AUTO_INCREMENT  COMMENT '主键ID',
    `perm_code`  VARCHAR(100)  NOT NULL  COMMENT '权限编码',
    `perm_name`  VARCHAR(100)  NOT NULL  COMMENT '权限名称',
    `module`  VARCHAR(50)  NOT NULL  COMMENT '所属模块',
    `operation`  ENUM('view','create','edit','delete','export','import')  NOT NULL  COMMENT '操作类型',
    `description`  VARCHAR(255)  COMMENT '权限说明',
    `sort_order`  INT  NOT NULL  DEFAULT 0  COMMENT '排序序号',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_perm_code` (`perm_code`),
    KEY `idx_module` (`module`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='权限表';

-- 角色权限关联表
DROP TABLE IF EXISTS `role_permissions`;
CREATE TABLE `role_permissions` (
    `id`  BIGINT  NOT NULL AUTO_INCREMENT  COMMENT '主键ID',
    `role_id`  BIGINT  NOT NULL  COMMENT '角色ID',
    `permission_id`  BIGINT  NOT NULL  COMMENT '权限ID',
    PRIMARY KEY (`id`),
    KEY `idx_role_id` (`role_id`),
    KEY `idx_permission_id` (`permission_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色权限关联表';


-- 登录日志表
DROP TABLE IF EXISTS `login_logs`;
CREATE TABLE `login_logs` (
    `id`  BIGINT  NOT NULL AUTO_INCREMENT  COMMENT '主键ID',
    `user_id`  BIGINT  NULL  COMMENT '用户ID',
    `login_type`  ENUM('password','sso')  NOT NULL  DEFAULT 'password'  COMMENT '登录方式',
    `ip_address`  VARCHAR(45)  COMMENT 'IP地址',
    `status`  ENUM('success','failed')  NOT NULL  COMMENT '登录结果',
    `created_at`  DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP  COMMENT '创建时间',
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='登录日志表';

-- 业务审计日志表
DROP TABLE IF EXISTS `audit_logs`;
CREATE TABLE `audit_logs` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '审计日志ID',
    `entity_type` VARCHAR(100) NOT NULL COMMENT '实体类型',
    `entity_id` VARCHAR(100) NULL COMMENT '实体ID',
    `action` VARCHAR(50) NOT NULL COMMENT '操作类型',
    `operator_id` BIGINT NULL COMMENT '操作者ID',
    `operator_name` VARCHAR(100) NULL COMMENT '操作者用户名',
    `before_data` JSON NULL COMMENT '变更前数据',
    `after_data` JSON NULL COMMENT '变更后数据',
    `ip_address` VARCHAR(45) NULL COMMENT '操作IP',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `remarks` TEXT NULL COMMENT '备注',
    PRIMARY KEY (`id`),
    KEY `idx_audit_entity` (`entity_type`, `entity_id`),
    KEY `idx_audit_operator` (`operator_id`),
    KEY `idx_audit_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='业务审计日志表';

-- 通知发送记录表
DROP TABLE IF EXISTS `notification_records`;
CREATE TABLE `notification_records` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `event_type` VARCHAR(64) NOT NULL COMMENT '事件类型',
    `channel` VARCHAR(32) NOT NULL COMMENT '发送渠道',
    `recipient` VARCHAR(256) NOT NULL COMMENT '接收人',
    `subject` VARCHAR(512) NOT NULL DEFAULT '' COMMENT '通知主题',
    `content` TEXT NOT NULL COMMENT '渲染后正文',
    `status` VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT '发送状态',
    `retry_count` BIGINT NOT NULL DEFAULT 0 COMMENT '已重试次数',
    `max_retries` BIGINT NOT NULL DEFAULT 3 COMMENT '最大重试次数',
    `error_message` TEXT NULL COMMENT '错误信息',
    `metadata_json` TEXT NULL COMMENT '扩展元数据 JSON',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `sent_at` DATETIME NULL COMMENT '发送时间',
    PRIMARY KEY (`id`),
    KEY `idx_event_type` (`event_type`),
    KEY `idx_channel` (`channel`),
    KEY `idx_status` (`status`),
    KEY `idx_status_retry` (`status`, `retry_count`),
    KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='通知发送记录表';

-- 用户通知渠道配置表
DROP TABLE IF EXISTS `user_notification_configs`;
CREATE TABLE `user_notification_configs` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `channel` VARCHAR(32) NOT NULL COMMENT '通知渠道（email/sms/dingtalk/feishu）',
    `recipient` VARCHAR(256) NOT NULL COMMENT '渠道接收人标识',
    `enabled` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    UNIQUE KEY `uk_user_channel` (`user_id`, `channel`),
    CONSTRAINT `fk_unc_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户通知渠道配置表';

SET FOREIGN_KEY_CHECKS = 1;