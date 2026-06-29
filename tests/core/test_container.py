#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖注入容器测试

测试 DI 容器的注册、解析、自动装配、生命周期管理等功能。
"""

import pytest

from src.core.container import (
    Container,
    DependencyNotFoundError,
    CircularDependencyError,
    Lifecycle,
)


# 测试用接口和实现类
class IEmailService:
    """邮件服务接口（测试用）。"""

    def send(self, to: str, content: str) -> str:
        ...


class EmailServiceImpl(IEmailService):
    """邮件服务实现（测试用）。"""

    def send(self, to: str, content: str) -> str:
        return f"Email sent to {to}: {content}"


class IUserRepository:
    """用户仓库接口（测试用）。"""

    def get_name(self) -> str:
        ...


class UserRepositoryImpl(IUserRepository):
    """用户仓库实现（测试用）。"""

    def get_name(self) -> str:
        return "test-user"


class IUserService:
    """用户服务接口（测试用）。"""

    def greet(self) -> str:
        ...


class UserServiceImpl(IUserService):
    """用户服务实现（测试用），依赖 IUserRepository。"""

    def __init__(self, user_repository: IUserRepository) -> None:
        self._repo = user_repository

    def greet(self) -> str:
        return f"Hello, {self._repo.get_name()}!"


class CircularA:
    """循环依赖测试类 A。"""

    def __init__(self, b: "CircularB") -> None:
        self.b = b


class CircularB:
    """循环依赖测试类 B。"""

    def __init__(self, a: CircularA) -> None:
        self.a = a


class TestContainer:
    """DI 容器测试。"""

    def setup_method(self) -> None:
        """每个测试方法前创建新的容器实例。"""
        self.container = Container()

    def test_register_and_resolve(self):
        """测试基本的注册和解析。"""
        self.container.register(IEmailService, EmailServiceImpl)
        instance = self.container.resolve(IEmailService)
        assert isinstance(instance, EmailServiceImpl)
        assert instance.send("test@test.com", "Hello") == "Email sent to test@test.com: Hello"

    def test_singleton_lifecycle(self):
        """测试单例模式：多次解析返回同一实例。"""
        self.container.register(IEmailService, EmailServiceImpl, Lifecycle.SINGLETON)

        instance1 = self.container.resolve(IEmailService)
        instance2 = self.container.resolve(IEmailService)

        assert instance1 is instance2

    def test_transient_lifecycle(self):
        """测试多例模式：每次解析返回新实例。"""
        self.container.register(IEmailService, EmailServiceImpl, Lifecycle.TRANSIENT)

        instance1 = self.container.resolve(IEmailService)
        instance2 = self.container.resolve(IEmailService)

        assert instance1 is not instance2

    def test_auto_wire(self):
        """测试自动装配：UserService 自动注入 UserRepository。"""
        self.container.register(IUserRepository, UserRepositoryImpl)
        self.container.register(IUserService, UserServiceImpl)

        service = self.container.resolve(IUserService)
        assert isinstance(service, UserServiceImpl)
        assert service.greet() == "Hello, test-user!"

    def test_dependency_not_found(self):
        """测试依赖未注册时抛出 DependencyNotFoundError。"""
        with pytest.raises(DependencyNotFoundError) as exc_info:
            self.container.resolve(IEmailService)

        assert exc_info.value.dependency_type == IEmailService

    def test_circular_dependency_detection(self):
        """测试循环依赖检测。"""
        self.container.register(CircularA, CircularA)
        self.container.register(CircularB, CircularB)

        with pytest.raises(CircularDependencyError):
            self.container.resolve(CircularA)

    def test_decorator_registration(self):
        """测试装饰器风格的注册。"""

        @self.container.decorate(IEmailService, Lifecycle.SINGLETON)
        class DecoratedEmailService(IEmailService):
            def send(self, to: str, content: str) -> str:
                return f"Decorated: {content}"

        instance = self.container.resolve(IEmailService)
        assert isinstance(instance, DecoratedEmailService)
        assert "Decorated" in instance.send("test@test.com", "Hello")

    def test_clear(self):
        """测试清空容器。"""
        self.container.register(IEmailService, EmailServiceImpl)
        self.container.resolve(IEmailService)

        self.container.clear()

        with pytest.raises(DependencyNotFoundError):
            self.container.resolve(IEmailService)

    def test_global_singleton(self):
        """测试全局容器单例。"""
        c1 = Container.get_instance()
        c2 = Container.get_instance()
        assert c1 is c2
