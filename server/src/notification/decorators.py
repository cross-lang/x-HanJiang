"""通知装饰器 — 用切面方式自动触发通知，业务代码不再手写通知逻辑。

Usage:
    @notify(NotificationEvent.USER_CREATED, target=("self", "operator"))
    def create(self, data, operator=None):
        ...
    target="self"            → 从返回值.id 取接收人（被操作用户本人）
    target="operator"        → 从 kwargs.operator 取 operator_id（操作者）
    target=1                 → 固定通知 user_id=1
    target=callable(result)  → 自定义函数从返回值解析接收人 user_id
    target=("self", "operator") → 多目标派发（自动按 user_id 去重）
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, Concatenate, ParamSpec, TypeVar, cast

from src.constants.notification import NotificationEvent, NotificationSource
from src.core.logger import logger

_P = ParamSpec("_P")
_R = TypeVar("_R")


def _resolve_target(target: Any, result: Any, kwargs: dict[str, Any]) -> int | None:
    """从返回值或调用参数解析接收人 user_id。"""
    if callable(target):
        resolved = target(result)
        return resolved if isinstance(resolved, int) else None
    if isinstance(target, int):
        return target
    if target == "self":
        return getattr(result, "id", None)
    if target == "operator":
        # 操作者上下文由 API 层以 kwargs.operator 传入（operator_id/operator_name/ip_address）
        operator = kwargs.get("operator") or {}
        operator_id = operator.get("operator_id")
        return operator_id if isinstance(operator_id, int) else None
    return None


def _build_vars(vars_extractor: Callable[[Any], dict[str, Any]] | None, result: Any) -> dict[str, Any]:
    """从返回值提取通知模板变量。"""
    if vars_extractor is None:
        return {}
    try:
        return vars_extractor(result) or {}
    except Exception:
        return {}


def notify(
    event_type: NotificationEvent,
    target: Any = "self",
    vars_extractor: Callable[[Any], dict[str, Any]] | None = None,
) -> Callable[[Callable[Concatenate[Any, _P], _R]], Callable[Concatenate[Any, _P], _R]]:
    """方法执行成功后自动发通知。

    Args:
        event_type: 通知事件枚举
        target: "self"=通知返回值.id 对应用户; int=固定 user_id; callable(result)->int
        vars_extractor: 从返回值提取模板变量

    Returns:
        保持原方法签名的装饰器。
    """

    def decorator(func: Callable[Concatenate[Any, _P], _R]) -> Callable[Concatenate[Any, _P], _R]:
        @wraps(func)
        def wrapper(self: Any, *args: _P.args, **kwargs: _P.kwargs) -> _R:
            result = func(self, *args, **kwargs)
            # 异步发通知，不阻塞主流程；多目标派发按 user_id 去重
            try:
                dispatcher = getattr(self, "_dispatcher", None)
                if dispatcher is None:
                    return result
                targets = tuple(target) if isinstance(target, (tuple, list)) else (target,)
                vars_ = _build_vars(vars_extractor, result)
                seen: set[int] = set()
                for single_target in targets:
                    uid = _resolve_target(single_target, result, kwargs)
                    if uid is None or uid in seen:
                        continue
                    seen.add(uid)
                    dispatcher.dispatch_for_user(
                        user_id=uid,
                        event_type=event_type,
                        variables=vars_,
                        source=NotificationSource.MANUAL.value,
                    )
            except Exception as exc:
                logger.debug("notify decorator skipped: {}", exc)
            return result

        return cast(Callable[Concatenate[Any, _P], _R], wrapper)

    return decorator
