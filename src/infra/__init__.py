#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础设施层（Infrastructure Layer）

本层封装第三方中间件、客户端、连接生命周期、底层资源管理，
仅提供基础资源，不包含业务逻辑。

核心原则：
    - 数据库、缓存、MQ等核心基础设施必须基于抽象基类定义标准接口
    - 业务层仅依赖抽象，实现类可动态替换解耦
    - infra 永不反向依赖 repository/service/api

子模块：
    - database: 数据库引擎、连接池、会话工厂、事务封装
    - cache: Redis客户端初始化、序列化、连接复用管理
    - http_client: 通用HTTP请求客户端
"""

__all__ = ["database", "cache", "http_client"]