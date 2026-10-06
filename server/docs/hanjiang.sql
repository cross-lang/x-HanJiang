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
    `status`  ENUM('enabled','disabled')  NOT NULL  DEFAULT 'enabled'  COMMENT '状态：enabled 启用 / disabled 禁用',
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

-- 系统通知投递明细表（投递实况 + 失败重试队列）
DROP TABLE IF EXISTS `system_notice_delivery`;
CREATE TABLE `system_notice_delivery` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `system_notification_id` BIGINT NULL COMMENT '关联系统通知ID（非系统通知来源为空）',
    `source` VARCHAR(32) NOT NULL COMMENT '通知来源（system_notice/station/alert/openapi_app）',
    `event_type` VARCHAR(64) NOT NULL COMMENT '事件类型',
    `user_id` BIGINT NULL COMMENT '目标用户ID（渠道级投递如告警webhook为空）',
    `channel` VARCHAR(32) NOT NULL COMMENT '发送渠道',
    `recipient` VARCHAR(256) NOT NULL COMMENT '接收人（发送时实际地址快照）',
    `status` VARCHAR(16) NOT NULL DEFAULT 'pending' COMMENT '发送状态',
    `retry_count` BIGINT NOT NULL DEFAULT 0 COMMENT '已重试次数',
    `max_retries` BIGINT NOT NULL DEFAULT 3 COMMENT '最大重试次数',
    `error_message` TEXT NULL COMMENT '错误信息',
    `receive_at` DATETIME NULL COMMENT '送达/接收时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_delivery_notification` (`system_notification_id`),
    KEY `idx_delivery_user` (`user_id`),
    KEY `idx_delivery_status_retry` (`status`, `retry_count`),
    KEY `idx_delivery_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统通知投递明细表';

-- 管理系统用户站内信表（独立收件箱）
DROP TABLE IF EXISTS `station_messages`;
CREATE TABLE `station_messages` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `user_id` BIGINT NOT NULL COMMENT '接收用户ID',
    `operator_id` BIGINT NULL COMMENT '发送人用户ID（系统自动为空）',
    `subject` VARCHAR(200) NOT NULL COMMENT '消息标题',
    `content` TEXT NOT NULL COMMENT '消息正文',
    `source` VARCHAR(32) NOT NULL COMMENT '消息来源（system_notice/station/alert/openapi_app）',
    `event_type` VARCHAR(64) NULL COMMENT '事件类型（前端跳转依据）',
    `is_read` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已读',
    `read_at` DATETIME NULL COMMENT '阅读时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    KEY `idx_station_user` (`user_id`),
    KEY `idx_station_user_read` (`user_id`, `is_read`),
    KEY `idx_station_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='管理系统用户站内信表';

-- 系统通知主表（发布/撤回）
DROP TABLE IF EXISTS `system_notifications`;
CREATE TABLE `system_notifications` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `title` VARCHAR(200) NOT NULL COMMENT '通知标题',
    `content` TEXT NOT NULL COMMENT '通知正文',
    `notice_type` VARCHAR(32) NOT NULL DEFAULT 'notice' COMMENT '通知类型（notice/maintenance）',
    `maintenance_time` DATETIME NULL COMMENT '维护开始时间',
    `duration` VARCHAR(64) NULL COMMENT '预计持续时长',
    `reason` VARCHAR(500) NULL COMMENT '维护原因',
    `event_type` VARCHAR(64) NOT NULL DEFAULT 'system.notice' COMMENT '事件类型',
    `status` VARCHAR(16) NOT NULL DEFAULT 'published' COMMENT '发布状态（published/withdrawn）',
    `operator_id` BIGINT NULL COMMENT '操作人用户ID',
    `operator_name` VARCHAR(64) NULL COMMENT '操作人用户名',
    `sent_at` DATETIME NULL COMMENT '首次投递时间',
    `metadata_json` JSON NULL COMMENT '扩展元数据',
    `published_at` DATETIME NULL COMMENT '发布时间',
    `withdrawn_at` DATETIME NULL COMMENT '撤回时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    KEY `idx_notice_status` (`status`),
    KEY `idx_notice_type` (`notice_type`),
    KEY `idx_notice_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统通知表';

-- 用户通知渠道配置表
DROP TABLE IF EXISTS `user_notification_configs`;
CREATE TABLE `user_notification_configs` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `channel` VARCHAR(32) NOT NULL COMMENT '通知渠道（email/sms/dingtalk/feishu）',
    `recipient` JSON NOT NULL COMMENT '渠道接收人列表 JSON，如 [{"recipient":"xxx@qq.com","label":"私人邮箱","enabled":1}]（enabled 1=启用 0=禁用）',
    `enabled` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    UNIQUE KEY `uk_user_channel` (`user_id`, `channel`),
    CONSTRAINT `fk_unc_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户通知渠道配置表';

-- 系统通知渠道配置表（全局共用，非用户级）
DROP TABLE IF EXISTS `system_notification_configs`;
CREATE TABLE `system_notification_configs` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `channel` VARCHAR(32) NOT NULL COMMENT '渠道（dingtalk/feishu/email）',
    `config` JSON NOT NULL COMMENT '渠道配置对象，如webhook地址、密钥等',
    `enabled` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_channel` (`channel`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统通知渠道配置表';

SET FOREIGN_KEY_CHECKS = 1;