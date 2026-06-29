#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖注入使用示例

本示例展示如何使用寒江（HanJiang） 的 DI 容器进行依赖注册和自动注入。

Usage:
    uv run python examples/di_usage.py
"""

from src.core.container import Container, Lifecycle, DependencyNotFoundError


# ============================================================
# 定义接口和实现
# ============================================================

class ICacheService:
    """缓存服务接口。"""

    def get(self, key: str) -> str | None:
        ...

    def set(self, key: str, value: str) -> None:
        ...


class RedisCacheService(ICacheService):
    """Redis 缓存服务实现。"""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, value: str) -> None:
        self._store[key] = value


class IEmailService:
    """邮件服务接口。"""

    def send(self, to: str, subject: str, body: str) -> str:
        ...


class SmtpEmailService(IEmailService):
    """SMTP 邮件服务实现。"""

    def send(self, to: str, subject: str, body: str) -> str:
        return f"Email sent to {to}: [{subject}] {body}"


class INotificationService:
    """通知服务接口。"""

    def notify(self, user_id: str, message: str) -> str:
        ...


class NotificationServiceImpl(INotificationService):
    """通知服务实现，依赖缓存和邮件服务。"""

    def __init__(self, cache_service: ICacheService, email_service: IEmailService) -> None:
        self._cache = cache_service
        self._email = email_service

    def notify(self, user_id: str, message: str) -> str:
        # 先查缓存，模拟去重
        if self._cache.get(f"notified:{user_id}"):
            return f"User {user_id} already notified (from cache)"

        # 发送邮件
        result = self._email.send(f"{user_id}@example.com", "Notification", message)

        # 标记已通知
        self._cache.set(f"notified:{user_id}", "true")

        return result


def main() -> None:
    """DI 使用示例主函数。"""
    # 创建容器（或使用全局单例 Container.get_instance()）
    container = Container()

    # ============================================================
    # 方式一：直接注册
    # ============================================================
    container.register(ICacheService, RedisCacheService, Lifecycle.SINGLETON)
    container.register(IEmailService, SmtpEmailService, Lifecycle.TRANSIENT)

    # ============================================================
    # 方式二：装饰器注册
    # ============================================================
    # @container.decorate(INotificationService, Lifecycle.SINGLETON)
    # class CustomNotificationService(INotificationService):
    #     ...
    container.register(INotificationService, NotificationServiceImpl, Lifecycle.SINGLETON)

    # ============================================================
    # 自动解析（wire）
    # ============================================================
    # NotificationServiceImpl 依赖 ICacheService 和 IEmailService
    # 容器会自动分析构造函数并注入依赖
    notification = container.resolve(INotificationService)

    # 第一次通知：发送邮件并缓存
    result1 = notification.notify("user-001", "You have a new message!")
    print(f"第一次通知: {result1}")

    # 第二次通知：命中缓存，不再发送
    result2 = notification.notify("user-001", "Another message")
    print(f"第二次通知: {result2}")

    # ============================================================
    # 验证单例模式
    # ============================================================
    cache1 = container.resolve(ICacheService)
    cache2 = container.resolve(ICacheService)
    print(f"\n单例验证: cache1 is cache2 = {cache1 is cache2}")  # True

    # ============================================================
    # 验证多例模式
    # ============================================================
    email1 = container.resolve(IEmailService)
    email2 = container.resolve(IEmailService)
    print(f"多例验证: email1 is email2 = {email1 is email2}")  # False

    print("\n依赖注入示例运行完成！")


if __name__ == "__main__":
    main()
