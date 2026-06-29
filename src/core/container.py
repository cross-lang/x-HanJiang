#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖注入容器模块

本模块实现类似 Go Wire 的依赖注入能力，提供统一的依赖注册与解析容器。
支持单例（Singleton）和多例（Transient）两种生命周期管理。

功能特性：
    - 接口到实现类的注册与自动解析
    - 单例/多例生命周期管理
    - 通过 inspect 自动分析构造函数签名实现自动装配（wire）
    - 装饰器风格的注册方式
    - 循环依赖检测

Usage:
    from src.core.container import Container, Lifecycle

    container = Container.get_instance()

    # 注册依赖
    container.register(IUserRepository, UserRepository, Lifecycle.SINGLETON)
    container.register(IUserService, UserService, Lifecycle.SINGLETON)

    # 解析依赖（自动装配构造函数参数）
    service = container.resolve(IUserService)

    # 装饰器注册
    @container.decorate(IUserService, Lifecycle.SINGLETON)
    class UserServiceImpl(IUserService):
        ...
"""

import inspect
from enum import Enum
from typing import Any, TypeVar, Optional, Type

T = TypeVar("T")


class Lifecycle(Enum):
    """组件生命周期枚举。

    Attributes:
        SINGLETON: 单例模式，全局只创建一个实例
        TRANSIENT: 多例模式，每次解析都创建新实例
    """

    SINGLETON = "singleton"
    TRANSIENT = "transient"


class DependencyNotFoundError(Exception):
    """依赖未找到异常。

    当容器无法解析某个依赖类型时抛出。

    Attributes:
        dependency_type: 未找到的依赖类型
    """

    def __init__(self, dependency_type: type) -> None:
        """初始化依赖未找到异常。

        Args:
            dependency_type: 未找到的依赖类型
        """
        self.dependency_type: type = dependency_type
        super().__init__(
            f"Dependency not found: {dependency_type.__name__}. "
            f"Please register it first using container.register()."
        )


class CircularDependencyError(Exception):
    """循环依赖异常。

    当检测到循环依赖时抛出。

    Attributes:
        dependency_chain: 依赖链
    """

    def __init__(self, dependency_chain: list[type]) -> None:
        """初始化循环依赖异常。

        Args:
            dependency_chain: 产生循环的依赖类型链
        """
        self.dependency_chain: list[type] = dependency_chain
        chain_str: str = " -> ".join(t.__name__ for t in dependency_chain)
        super().__init__(f"Circular dependency detected: {chain_str}")


class Container:
    """依赖注入容器。

    提供统一的依赖注册与解析功能，支持自动装配构造函数参数。
    容器本身采用单例模式，通过 get_instance() 获取全局实例。

    类似 Go Wire 的设计理念，通过类型映射实现接口到具体实现的绑定。
    """

    _instance: Optional["Container"] = None

    def __init__(self) -> None:
        """初始化容器，创建空的注册表和单例缓存。"""
        self._registry: dict[type, tuple[type, Lifecycle]] = {}
        self._singletons: dict[type, Any] = {}
        self._resolving: set[type] = set()

    def register(
        self,
        interface: Type[T],
        implementation: Type[T],
        lifecycle: Lifecycle = Lifecycle.SINGLETON,
    ) -> None:
        """注册接口到实现类的映射。

        Args:
            interface: 接口或基类类型
            implementation: 具体实现类类型
            lifecycle: 生命周期模式（默认单例）
        """
        self._registry[interface] = (implementation, lifecycle)

    def resolve(self, interface: Type[T]) -> T:
        """解析并返回指定接口类型的实例。

        对于单例模式，首次创建后缓存实例；对于多例模式，每次都创建新实例。
        自动通过 wire() 分析构造函数签名并注入依赖。

        Args:
            interface: 需要解析的接口或基类类型

        Returns:
            T: 解析得到的实例

        Raises:
            DependencyNotFoundError: 当依赖未注册时
            CircularDependencyError: 当检测到循环依赖时
        """
        if interface not in self._registry:
            raise DependencyNotFoundError(interface)

        implementation: type
        lifecycle: Lifecycle
        implementation, lifecycle = self._registry[interface]

        # 单例模式：返回已缓存的实例
        if lifecycle == Lifecycle.SINGLETON and interface in self._singletons:
            return self._singletons[interface]

        # 循环依赖检测
        if interface in self._resolving:
            chain: list[type] = list(self._resolving) + [interface]
            raise CircularDependencyError(chain)

        self._resolving.add(interface)
        try:
            instance: T = self._wire(implementation)

            if lifecycle == Lifecycle.SINGLETON:
                self._singletons[interface] = instance

            return instance
        finally:
            self._resolving.discard(interface)

    def _wire(self, implementation: type) -> Any:
        """通过分析构造函数签名自动解析并注入依赖。

        使用 typing.get_type_hints 获取构造函数的参数类型注解（自动解析前向引用），
        对每个带类型注解的参数递归调用 resolve() 进行注入。

        Args:
            implementation: 需要实例化的实现类

        Returns:
            Any: 自动装配后创建的实例
        """
        import typing

        try:
            hints: dict[str, Any] = typing.get_type_hints(implementation.__init__)
        except Exception:
            hints = {}

        kwargs: dict[str, Any] = {}

        for param_name, annotation in hints.items():
            if param_name == "return":
                continue

            # 尝试从容器解析依赖
            if isinstance(annotation, type) and annotation in self._registry:
                kwargs[param_name] = self.resolve(annotation)

        return implementation(**kwargs)

    def decorate(
        self,
        interface: Type[T],
        lifecycle: Lifecycle = Lifecycle.SINGLETON,
    ) -> Any:
        """装饰器风格的依赖注册。

        Args:
            interface: 接口或基类类型
            lifecycle: 生命周期模式

        Returns:
            装饰器函数
        """

        def decorator(cls: Type[T]) -> Type[T]:
            self.register(interface, cls, lifecycle)
            return cls

        return decorator

    def clear(self) -> None:
        """清空所有注册和单例缓存（主要用于测试）。"""
        self._registry.clear()
        self._singletons.clear()
        self._resolving.clear()

    @classmethod
    def get_instance(cls) -> "Container":
        """获取容器全局单例。

        Returns:
            Container: 全局容器实例
        """
        if cls._instance is None:
            cls._instance = Container()
        return cls._instance
