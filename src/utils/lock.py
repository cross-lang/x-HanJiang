#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Redis 分布式锁模块

提供基于 Redis 的分布式锁实现，支持单锁与批量锁（msetnx）两种使用方式，并包含超时自动释放策略。
"""

import time
import redis as redis_db
from typing import Any

_pool_db0 = redis_db.ConnectionPool(host="", port=0, password="", db=0)
_redis_client = redis_db.StrictRedis(connection_pool=_pool_db0)


def _get_redis() -> Any:
    # keep backward compatibility with existing module-level client
    return _redis_client


class MRedisLock:
    """
    批量分布式锁，也可用于单条数据加锁
    """

    def __init__(self, prefix: str, err_msg: str, ex: int, redis_client: Any | None = None) -> None:
        self.prefix = prefix
        self.err_msg = err_msg
        self.ex = ex
        self._redis = redis_client or _get_redis()

    def m_acquire(self, suffix_ls: list[str]) -> tuple[bool, str]:
        """
        批量抢锁，一个失败则全失败，全部成功才成功
        失败时会通过判断过期时间做二次抢锁，避免因为宕机导致无法释放锁
        """
        if not suffix_ls:
            return True, ""
        if self.ex <= 0:
            raise ValueError("ex must be > 0")

        while True:
            curr_time = int(time.time())
            mapping: dict[str, int] = {f"{self.prefix}:{suffix}": curr_time for suffix in suffix_ls}
            if self._redis.msetnx(**mapping):
                for k in mapping.keys():
                    self._redis.expire(k, self.ex)
                return True, ""

            # 抢锁失败时，尝试通过时间解锁，成功解锁时重新抢锁
            ex_release = any(self.release_by_ex(curr_time=curr_time, key=k) for k in mapping.keys())
            if not ex_release:
                return False, self.err_msg

    def release_by_ex(self, curr_time: int, key: str) -> bool:
        """
        判断key是否超时，超时则解锁
        成功解锁了超时的key时返回True
        """
        val = self._redis.get(key)
        if val and ((curr_time - int(val.decode('utf-8'))) >= self.ex):
            self._redis.delete(key)
            return True
        return False

    def release(self, suffix_ls: list[str]) -> None:
        """
        手动释放锁
        """
        if not suffix_ls:
            return
        keys = [f"{self.prefix}:{suffix}" for suffix in suffix_ls]
        self._redis.delete(*keys)


class RedisLock:
    """使用setnx实现的redis分布式锁

    :param key_prefix: str, 加锁前缀, 对应某个功能, 形如`supplier_clearing`
    :param error_message: str, 加锁失败的报错消息
    :param lock_period: int, 占锁时间
    """

    def __init__(
        self,
        key_prefix: str,
        error_message: str,
        lock_period: int,
        redis_client: Any | None = None,
    ) -> None:
        self.key_prefix = key_prefix
        self.error_message = error_message
        self.lock_period = lock_period
        self._redis = redis_client or _get_redis()

    def acquire(self, key_suffix: str) -> tuple[bool, str]:
        """抢锁, 如果抢锁失败返回对应的报错信息

        :param key_suffix: 加锁后缀, 传递给单例的参数
        """
        if self.lock_period <= 0:
            raise ValueError("lock_period must be > 0")

        key = f"{self.key_prefix}:{key_suffix}"
        # if not redis.setnx(key, 1):
        #     return False, self.error_message
        # redis.expire(key, self.lock_period)
        if not self._redis.set(key, 1, ex=self.lock_period, nx=True):
            return False, self.error_message
        return True, ""

    def release(self, key_suffix: str) -> None:
        """ 手动释放锁 """
        self._redis.delete(f"{self.key_prefix}:{key_suffix}")

    def check(self, key_suffix: str) -> bool:
        """检查当前是否有锁（不抢锁），如果锁被占用，返回True，否则返回False"""
        key = f"{self.key_prefix}:{key_suffix}"
        return bool(self._redis.get(key))


if __name__ == '__main__':
    sale_order_lock = RedisLock("sale_order", "已开票，请勿重复提交", 120)

    # 加锁
    success, errmsg = sale_order_lock.acquire("xxxx")
    if not success:
        raise Exception

    # 业务处理

    # 释放锁
    sale_order_lock.release("xxxx")
