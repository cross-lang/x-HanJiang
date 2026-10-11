#!/usr/bin/env python3
"""短信发送基础设施：支持本地模拟 / 腾讯云短信 / 阿里云短信。

封装范式与 infras/email.py、infras/database.py 保持一致：
    - SmsProvider 抽象基类：业务层仅依赖此抽象，切换厂商只需改配置
    - MockSmsProvider：本地模拟（不调用云 API，前后端联调用，验证码日志可见）
    - TencentCloudSmsProvider / AliyunSmsProvider：短信 SDK 实现（延迟导入，可选依赖）
    - get_sms_provider / get_cached_sms_provider：工厂函数 + 应用级单例

使用方式（业务层）：
    from src.infras.sms import get_cached_sms_provider

    provider = get_cached_sms_provider()
    if provider is not None:
        provider.send_sms("13800138000", "TEMPLATE_1", {"code": "123456"})

依赖安装（未配置/未安装时给出明确报错，不影响模块导入）：
    腾讯云: pip install tencentcloud-sdk-python
    阿里云短信: pip install alibabacloud-dysmsapi20170525 alibabacloud-tea-openapi
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from src.core.config import settings
from src.core.logger import logger


# ============================================================
# 抽象基类
# ============================================================
class SmsProvider(ABC):
    """短信发送抽象接口。
    所有短信后端必须实现此接口。业务层仅依赖此抽象，
    切换短信厂商（腾讯云/阿里云）只需修改配置，无需改动任何业务代码。
    """

    @abstractmethod
    def send_sms(
        self,
        phone: str,
        template_code: str,
        template_params: dict[str, str] | None = None,
        sign_name: str = "",
    ) -> bool:
        """发送短信。

        Args:
            phone: 接收手机号（国内 11 位，不带 +86 前缀）
            template_code: 短信模板编码/ID（厂商侧审核通过后使用）
            template_params: 模板变量（键值对，各厂商实现负责转换）
            sign_name: 短信签名（留空使用全局配置的默认签名）

        Returns:
            bool: 发送是否成功
        """


# ============================================================

# 腾讯云实现

# ============================================================


class TencentCloudSmsProvider(SmsProvider):
    """腾讯云短信发送实现（tencentcloud-sdk-python，接口 v20210111）。"""

    def __init__(
        self,
        secret_id: str,
        secret_key: str,
        sdk_app_id: str,
        region: str = "ap-guangzhou",
        sign_name: str = "",
    ) -> None:
        self._secret_id = secret_id
        self._secret_key = secret_key
        self._sdk_app_id = sdk_app_id
        self._region = region
        self._sign_name = sign_name

    def send_sms(
        self,
        phone: str,
        template_code: str,
        template_params: dict[str, str] | None = None,
        sign_name: str = "",
    ) -> bool:
        """发送短信（腾讯云 SendSmsMessage，支持模板变量名）。"""
        if not self._secret_id or not self._secret_key or not self._sdk_app_id:
            logger.warning("腾讯云短信配置不完整（SMS_TENCENT_*），跳过发送")
            return False
        try:
            from tencentcloud.common import credential
            from tencentcloud.common.profile.client_profile import ClientProfile
            from tencentcloud.common.profile.http_profile import HttpProfile
            from tencentcloud.sms.v20210111 import models, sms_client
        except ImportError as exc:  # pragma: no cover - 依赖缺失路径
            raise RuntimeError("未安装腾讯云短信 SDK，请执行：pip install tencentcloud-sdk-python") from exc
        try:
            cred = credential.Credential(self._secret_id, self._secret_key)
            http_profile = HttpProfile()
            http_profile.endpoint = "sms.tencentcloudapi.com"
            client_profile = ClientProfile()
            client_profile.httpProfile = http_profile
            client = sms_client.SmsClient(cred, self._region, client_profile)

            req = models.SendSmsMessageRequest()
            req.PhoneNumberSet = [f"+86{phone}"]
            req.SmsSdkAppId = self._sdk_app_id
            req.SignName = sign_name or self._sign_name
            req.TemplateId = template_code
            if template_params:
                req.TemplateParamSet = json.dumps(
                    [{"name": k, "value": v} for k, v in template_params.items()],
                    ensure_ascii=False,
                )
            resp = client.SendSmsMessage(req)
            status = (resp.SendStatusSet or [None])[0]
            ok = bool(status and getattr(status, "Code", None) == "Ok")
            logger.info(
                f"腾讯云短信发送{'成功' if ok else '失败'}: phone={phone}, code={getattr(status, 'Code', None)}"
            )
            return ok
        except Exception as exc:  # noqa: BLE001
            logger.error(f"腾讯云短信发送异常: {exc}")
            raise


# ============================================================

# 阿里云实现

# ============================================================


class AliyunSmsProvider(SmsProvider):
    """阿里云短信发送实现（alibabacloud_dysmsapi20170525）。"""

    def __init__(
        self,
        access_key_id: str,
        access_key_secret: str,
        endpoint: str = "dysmsapi.aliyuncs.com",
        sign_name: str = "",
    ) -> None:
        self._access_key_id = access_key_id
        self._access_key_secret = access_key_secret
        self._endpoint = endpoint
        self._sign_name = sign_name

    def send_sms(
        self,
        phone: str,
        template_code: str,
        template_params: dict[str, str] | None = None,
        sign_name: str = "",
    ) -> bool:
        """发送短信（阿里云 SendSms，模板变量为 JSON 字符串）。"""
        if not self._access_key_id or not self._access_key_secret:
            logger.warning("阿里云短信配置不完整（SMS_ALIYUN_*），跳过发送")
            return False
        try:
            from alibabacloud_dysmsapi20170525 import models as dysmsapi_models
            from alibabacloud_dysmsapi20170525.client import Client
            from alibabacloud_tea_openapi.models import Config
        except ImportError as exc:  # pragma: no cover - 依赖缺失路径
            raise RuntimeError(
                "未安装阿里云短信 SDK，请执行：pip install alibabacloud-dysmsapi20170525 alibabacloud-tea-openapi"
            ) from exc
        try:
            config = Config(
                access_key_id=self._access_key_id,
                access_key_secret=self._access_key_secret,
                endpoint=self._endpoint,
            )
            client = Client(config)
            req = dysmsapi_models.SendSmsRequest(
                phone_numbers=phone,
                sign_name=sign_name or self._sign_name,
                template_code=template_code,
                template_param=(json.dumps(template_params, ensure_ascii=False) if template_params else None),
            )
            resp = client.send_sms(req)
            ok = bool(resp.body and resp.body.code == "OK")
            logger.info(
                f"阿里云短信发送{'成功' if ok else '失败'}: phone={phone}, code={getattr(resp.body, 'code', None)}"
            )
            return ok
        except Exception as exc:  # noqa: BLE001
            logger.error(f"阿里云短信发送异常: {exc}")
            raise


# ============================================================

# 本地模拟实现

# ============================================================


class MockSmsProvider(SmsProvider):
    """本地模拟短信提供者：不调用任何云 API。

    前后端联调 / 本地开发使用：send_sms 仅打印日志并记录发送记录，
    验证码可直接从日志或 last_code() / sent_records 中读取，无需真实短信。
    联调时把 provider 配置为 "mock" 即可。
    """

    def __init__(self) -> None:
        self._sent_records: list[dict[str, Any]] = []

    def send_sms(
        self,
        phone: str,
        template_code: str,
        template_params: dict[str, str] | None = None,
        sign_name: str = "",
    ) -> bool:
        """模拟发送：打印日志 + 记录发送明细，永远返回成功。"""
        params = template_params or {}
        code = params.get("code", "")
        record: dict[str, Any] = {
            "phone": phone,
            "template_code": template_code,
            "template_params": params,
            "sign_name": sign_name,
            "code": code,
        }
        self._sent_records.append(record)
        logger.info(
            "【Mock短信】phone=%s template=%s params=%s sign=%s 验证码=%s",
            phone,
            template_code,
            params,
            sign_name,
            code,
        )
        return True

    @property
    def sent_records(self) -> list[dict[str, Any]]:
        """全部发送记录（联调 / 测试断言用）。"""
        return list(self._sent_records)

    def last_code(self) -> str:
        """最近一次发送的验证码（无记录时返回空串）。"""
        return self._sent_records[-1].get("code", "") if self._sent_records else ""


# ============================================================

# 工厂函数

# ============================================================


def get_sms_provider() -> SmsProvider | None:
    """根据配置创建短信提供者实例。

    配置字段（settings.sms，前缀 SMS_）：
        provider: "mock" | "tencent" | "aliyun" | "none"（未启用时返回 None）
        腾讯云: tencent_secret_id / tencent_secret_key / tencent_sdk_app_id / tencent_region
        阿里云: aliyun_access_key_id / aliyun_access_key_secret / aliyun_endpoint
        公共:   sign_name（默认短信签名）
    """
    cfg = settings.sms
    if cfg.provider == "mock":
        return MockSmsProvider()
    if cfg.provider == "tencent":
        return TencentCloudSmsProvider(
            secret_id=cfg.tencent_secret_id,
            secret_key=cfg.tencent_secret_key,
            sdk_app_id=cfg.tencent_sdk_app_id,
            region=cfg.tencent_region,
            sign_name=cfg.sign_name,
        )
    if cfg.provider == "aliyun":
        return AliyunSmsProvider(
            access_key_id=cfg.aliyun_access_key_id,
            access_key_secret=cfg.aliyun_access_key_secret,
            endpoint=cfg.aliyun_endpoint,
            sign_name=cfg.sign_name,
        )
    if cfg.provider in ("", "none", "disabled"):
        logger.info("短信服务未启用（SMS_PROVIDER=none），业务调用将收到 None")
        return None
    raise ValueError(f"不支持的短信服务商: {cfg.provider!r}（可选 mock / tencent / aliyun / none）")


# 模块级缓存实例

_sms_provider: SmsProvider | None = None


def get_cached_sms_provider() -> SmsProvider | None:
    """获取缓存的短信提供者（应用级单例）。未启用时返回 None。"""
    global _sms_provider
    if _sms_provider is None:
        _sms_provider = get_sms_provider()
    return _sms_provider


__all__ = [
    "SmsProvider",
    "MockSmsProvider",
    "TencentCloudSmsProvider",
    "AliyunSmsProvider",
    "get_sms_provider",
    "get_cached_sms_provider",
]
