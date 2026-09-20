#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
接口鉴权模块

提供基于时间窗口与共享密钥的简单 token 生成与校验能力，适用于轻量级接口鉴权场景。
"""


import datetime
import hashlib
import hmac


AUTH_API_SECRETKEY: str = ""


class AuthFunc:
    """ 简单接口鉴权 """

    @classmethod
    def _calc_token(cls, timestr: str) -> str:
        """token计算方式，使用 HMAC-SHA256"""
        return hmac.new(
            AUTH_API_SECRETKEY.encode("utf-8"),
            timestr.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    @classmethod
    def gen_token(cls) -> str:
        """生成token"""
        timestr = datetime.datetime.now().strftime("%Y%m%d%H")
        return cls._calc_token(timestr)

    @classmethod
    def verify_token(cls, token: str) -> bool:
        """验证token"""
        # 上一小时的token在这一小时的前5分钟内仍然有效
        token_expire_delay = 5
        now = datetime.datetime.now()
        tokens: set[datetime.datetime] = {now}
        if now.minute <= token_expire_delay:
            tokens.add(now - datetime.timedelta(hours=1))
        return token in {cls._calc_token(dt.strftime("%Y%m%d%H")) for dt in tokens}
