#!/usr/bin/env python3
"""
基础设施层（Infrastructure Layer）

本层封装第三方中间件、客户端、连接生命周期、底层资源管理，
仅提供基础资源，不包含业务逻辑。

核心原则：
    - 每个模块基于抽象基类（ABC）定义标准接口
    - 业务层仅依赖抽象接口，实现类可动态替换解耦
    - infra 永不反向依赖 repository/service/api

统一风格：
    - XxxProvider(ABC)         — 抽象接口
    - YyyXxxProvider           — 具体实现
    - get_xxx_provider()       — 工厂函数（读配置创建实例）
    - get_cached_xxx_provider()— 单例缓存

子模块：
    - database: DatabaseProvider → MySqlProvider
    - cache:    CacheProvider → RedisCacheProvider
    - email:    EmailProvider → SmtpEmailProvider
    - http:     HttpProvider → RequestsHttpProvider
    - storage:  StorageProvider → LocalStorage / S3CompatibleStorage
"""

__all__ = ["cache", "database", "email", "http", "storage"]
