#!/usr/bin/env python3
"""Redis 分布式锁（废弃保留）。

该模块自项目重建起在 src/ 与 tests/ 中无任何引用，属死代码，已于 2026-09-30 清理为占位。
注意：旧实现直接耦合 redis 客户端且连接参数硬编码，如需分布式锁能力，
请按 LockProvider 抽象重新实现并复用统一 Redis 配置（settings.redis.url）。
"""
