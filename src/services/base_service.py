#!/usr/bin/env python3
"""
业务逻辑层抽象基类

本模块定义了业务逻辑层的标准接口契约，所有 Service 实现类必须继承此基类。
提供通用的业务操作接口定义，确保业务逻辑层的统一规范。

类型参数：
    T: DTO 响应类型
    ID: 主键类型

Classes:
    BaseService: 业务逻辑层抽象基类
"""

from abc import ABC
from typing import Generic, TypeVar

T = TypeVar("T")
ID = TypeVar("ID")


class BaseService(ABC, Generic[T, ID]):
    """业务逻辑层抽象基类。

    定义标准业务操作接口，所有业务逻辑实现类必须继承此基类。
    业务逻辑层负责处理业务规则、数据校验和 Entity→DTO 转换。

    抽象方法声明见各子类的具体实现（get_by_id / get_all / create / update / delete）。
    此基类不再强制声明抽象方法，以支持不同业务模型的差异化接口。

    Type Parameters:
        T: DTO 响应类型
        ID: 主键类型
    """
