#!/usr/bin/env python3
"""开放网关鉴权服务测试（src/services/open/gateway_service.py）。

以内存 Fake 仓库 + 真实安全原语（SHA256 / 常量时间比对）覆盖鉴权全部分支：
    - 身份门槛：缺 X-App-Id / 应用不存在 / 已停用 / 未通过审批
    - 鉴权模式分流：明文 AppKey、HanJiang-1 签名、both 灰度、非法模式兜底
    - 签名解签：时间窗、解密失败、Authorization 格式错误、签名不一致
    - last_used_at 更新：成功记录 / 失败回滚均不阻断主流程
"""

from email.utils import formatdate

import pytest
from src.constants.constants import OPENAPI_CONTENT_TYPE
from src.constants.enums import AppAuthMode, AppStatus
from src.core import signature
from src.core.exceptions import AuthenticationException, AuthorizationException
from src.models.entities.app_entity import OpenApiAppEntity
from src.schemas.open.app import CurrentApp
from src.schemas.open.request_context import OpenApiAuthContext
from src.services.open.gateway_service import OpenGatewayService
from src.utils import security

# 明文模式约定的测试密钥（app_key_hash 由其派生）
_PLAIN_SECRET = "plain-secret-001"
# HMAC 模式约定的测试密钥（测试中通过 monkeypatch 让 decrypt_text 直接返回它）
_HMAC_SECRET = "hmac-secret-001"


class FakeGatewayRepo:
    """内存版应用仓库替身：仅实现网关鉴权用到的三个方法。"""

    def __init__(self, app: OpenApiAppEntity | None = None) -> None:
        self._app = app
        self.touch_calls: list[str] = []
        self.rollback_calls: int = 0
        # 是否让 touch_last_used 抛异常（覆盖失败回滚分支）
        self.touch_raises: bool = False

    def get_by_app_id(self, app_id: str) -> OpenApiAppEntity | None:
        return self._app

    def touch_last_used(self, app_id: str) -> None:
        if self.touch_raises:
            raise RuntimeError("模拟 last_used 更新失败")
        self.touch_calls.append(app_id)

    def rollback(self) -> None:
        self.rollback_calls += 1


def _make_app(**overrides) -> OpenApiAppEntity:
    """构造一个已启用、已审批的应用实体（测试可按需覆盖字段）。"""
    kwargs: dict = {
        "app_id": "hj_test_0001",
        "app_key_hash": security.sha256_hex(_PLAIN_SECRET),
        "app_key_encrypted": "fake-encrypted",
        "name": "测试应用",
        "description": "用于网关鉴权的测试应用",
        "owner_type": "admin",
        "owner_id": 1,
        "approved": True,
        "scopes": "user:read,user:write",
        "status": AppStatus.ACTIVE.value,
        "auth_mode": AppAuthMode.PLAIN.value,
        "rate_limit_per_minute": 60,
    }
    kwargs.update(overrides)
    return OpenApiAppEntity(**kwargs)


def _ctx(**overrides) -> OpenApiAuthContext:
    """构造鉴权上下文（默认 GET /api/open/v1/ping）。"""
    kwargs: dict = {
        "app_id": "hj_test_0001",
        "method": "GET",
        "uri": "/api/open/v1/ping",
    }
    kwargs.update(overrides)
    return OpenApiAuthContext(**kwargs)


def _valid_date() -> str:
    """当前 GMT RFC1123 时间（落在签名时间窗内）。"""
    return formatdate(timeval=None, usegmt=True)


def _hmac_authorization(app_id: str, date: str, *, secret: str = _HMAC_SECRET) -> str:
    """按 HanJiang-1 协议为当前请求计算合法签名，组装 Authorization 头。"""
    sig = signature.sign(
        app_key=secret,
        method="GET",
        uri="/api/open/v1/ping",
        content_type=OPENAPI_CONTENT_TYPE,
        date=date,
        body=b"",
    )
    return f"HanJiang-1 {app_id}:{sig}"


@pytest.fixture
def service() -> OpenGatewayService:
    """默认绑定一个已启用、已审批应用的网关服务。"""
    return OpenGatewayService(repo=FakeGatewayRepo(app=_make_app()))


# ── 身份门槛分支 ──────────────────────────────────────


@pytest.mark.asyncio
async def test_missing_app_id_rejected(service: OpenGatewayService) -> None:
    """缺少 X-App-Id → 抛 AuthenticationException。"""
    with pytest.raises(AuthenticationException, match="缺少请求头"):
        await service.authenticate(_ctx(app_id=""))


@pytest.mark.asyncio
async def test_app_not_found_rejected() -> None:
    """应用不存在 → 抛 AuthenticationException。"""
    svc = OpenGatewayService(repo=FakeGatewayRepo(app=None))
    with pytest.raises(AuthenticationException, match="App 无效或已停用"):
        await svc.authenticate(_ctx())


@pytest.mark.asyncio
async def test_app_disabled_rejected() -> None:
    """应用状态非 active → 抛 AuthenticationException。"""
    app = _make_app(status=AppStatus.DISABLED.value)
    svc = OpenGatewayService(repo=FakeGatewayRepo(app=app))
    with pytest.raises(AuthenticationException, match="App 无效或已停用"):
        await svc.authenticate(_ctx(plain_key=_PLAIN_SECRET))


@pytest.mark.asyncio
async def test_app_not_approved_rejected() -> None:
    """应用未通过创建审批 → 抛 AuthorizationException（授权门槛）。"""
    app = _make_app(approved=False)
    svc = OpenGatewayService(repo=FakeGatewayRepo(app=app))
    with pytest.raises(AuthorizationException, match="未通过审批"):
        await svc.authenticate(_ctx(plain_key=_PLAIN_SECRET))


# ── 明文 AppKey 分支 ──────────────────────────────────


@pytest.mark.asyncio
async def test_plain_key_success(service: OpenGatewayService) -> None:
    """plain 模式 + 正确明文密钥 → 返回 CurrentApp，并记录 last_used。"""
    result = await service.authenticate(_ctx(plain_key=_PLAIN_SECRET))

    assert isinstance(result, CurrentApp)
    assert result.app_id == "hj_test_0001"
    assert result.name == "测试应用"
    # scopes 由逗号串解析为列表
    assert result.scopes == ["user:read", "user:write"]
    assert result.auth_mode == AppAuthMode.PLAIN.value
    assert result.rate_limit_per_minute == 60
    assert service._repository.touch_calls == ["hj_test_0001"]


@pytest.mark.asyncio
async def test_plain_key_wrong_then_fail(service: OpenGatewayService) -> None:
    """plain 模式 + 错误密钥且无签名凭证 → 抛 AuthenticationException。"""
    with pytest.raises(AuthenticationException, match="应用鉴权失败"):
        await service.authenticate(_ctx(plain_key="wrong-secret"))


@pytest.mark.asyncio
async def test_invalid_auth_mode_falls_back_to_plain() -> None:
    """auth_mode 为非法值 → 兜底按 plain 处理，明文密钥仍可通过。"""
    app = _make_app(auth_mode="unknown-mode")
    svc = OpenGatewayService(repo=FakeGatewayRepo(app=app))

    result = await svc.authenticate(_ctx(plain_key=_PLAIN_SECRET))
    # 兜底模式枚举为 PLAIN
    assert result.auth_mode == AppAuthMode.PLAIN.value


# ── HanJiang-1 签名分支 ───────────────────────────────


@pytest.mark.asyncio
async def test_hmac_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """hmac 模式 + 合法签名 → 解签通过。"""
    monkeypatch.setattr("src.utils.security.decrypt_text", lambda ciphertext: _HMAC_SECRET)
    app = _make_app(auth_mode=AppAuthMode.HMAC.value)
    repo = FakeGatewayRepo(app=app)
    svc = OpenGatewayService(repo=repo)

    date = _valid_date()
    ctx = _ctx(authorization=_hmac_authorization(app.app_id, date), date=date)
    result = await svc.authenticate(ctx)

    assert result.auth_mode == AppAuthMode.HMAC.value
    assert repo.touch_calls == [app.app_id]


@pytest.mark.asyncio
async def test_hmac_missing_date_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """hmac 模式但缺少 X-App-Date → 时间窗校验失败，鉴权拒绝。"""
    monkeypatch.setattr("src.utils.security.decrypt_text", lambda ciphertext: _HMAC_SECRET)
    app = _make_app(auth_mode=AppAuthMode.HMAC.value)
    svc = OpenGatewayService(repo=FakeGatewayRepo(app=app))

    ctx = _ctx(authorization=_hmac_authorization(app.app_id, _valid_date()), date=None)
    with pytest.raises(AuthenticationException, match="应用鉴权失败"):
        await svc.authenticate(ctx)


@pytest.mark.asyncio
async def test_hmac_expired_date_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """hmac 模式但 X-App-Date 超出时间窗 → 防重放拒绝。"""
    monkeypatch.setattr("src.utils.security.decrypt_text", lambda ciphertext: _HMAC_SECRET)
    app = _make_app(auth_mode=AppAuthMode.HMAC.value)
    svc = OpenGatewayService(repo=FakeGatewayRepo(app=app))

    # 固定一个很久以前的时间，必然超出签名时间窗
    stale_date = "Mon, 01 Jan 2024 00:00:00 GMT"
    sig = signature.sign(
        app_key=_HMAC_SECRET,
        method="GET",
        uri="/api/open/v1/ping",
        content_type=OPENAPI_CONTENT_TYPE,
        date=stale_date,
        body=b"",
    )
    ctx = _ctx(authorization=f"HanJiang-1 {app.app_id}:{sig}", date=stale_date)
    with pytest.raises(AuthenticationException, match="应用鉴权失败"):
        await svc.authenticate(ctx)


@pytest.mark.asyncio
async def test_hmac_decrypt_failure_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """hmac 模式但密文解密失败（返回 None）→ 拒绝。"""
    monkeypatch.setattr("src.utils.security.decrypt_text", lambda ciphertext: None)
    app = _make_app(auth_mode=AppAuthMode.HMAC.value)
    svc = OpenGatewayService(repo=FakeGatewayRepo(app=app))

    date = _valid_date()
    ctx = _ctx(authorization=_hmac_authorization(app.app_id, date), date=date)
    with pytest.raises(AuthenticationException, match="应用鉴权失败"):
        await svc.authenticate(ctx)


@pytest.mark.asyncio
async def test_hmac_bad_authorization_format(monkeypatch: pytest.MonkeyPatch) -> None:
    """Authorization 缺冒号分隔 / 签名为空 → 拒绝。"""
    monkeypatch.setattr("src.utils.security.decrypt_text", lambda ciphertext: _HMAC_SECRET)
    app = _make_app(auth_mode=AppAuthMode.HMAC.value)
    svc = OpenGatewayService(repo=FakeGatewayRepo(app=app))
    date = _valid_date()

    # 情况一：没有冒号
    bad_ctx = _ctx(authorization="HanJiang-1 noseparator", date=date)
    with pytest.raises(AuthenticationException):
        await svc.authenticate(bad_ctx)

    # 情况二：冒号后签名为空
    empty_ctx = _ctx(authorization=f"HanJiang-1 {app.app_id}:", date=date)
    with pytest.raises(AuthenticationException):
        await svc.authenticate(empty_ctx)


@pytest.mark.asyncio
async def test_hmac_wrong_signature_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """时间窗与解密均通过，但签名值不一致 → 拒绝。"""
    monkeypatch.setattr("src.utils.security.decrypt_text", lambda ciphertext: _HMAC_SECRET)
    app = _make_app(auth_mode=AppAuthMode.HMAC.value)
    svc = OpenGatewayService(repo=FakeGatewayRepo(app=app))

    date = _valid_date()
    # 用错误密钥算出的签名
    wrong = _hmac_authorization(app.app_id, date, secret="other-secret")
    ctx = _ctx(authorization=wrong, date=date)
    with pytest.raises(AuthenticationException, match="应用鉴权失败"):
        await svc.authenticate(ctx)


# ── both 灰度模式 ──────────────────────────────────────


@pytest.mark.asyncio
async def test_both_mode_plain_preferred() -> None:
    """both 模式下，明文密钥正确即放行（明文分支先命中）。"""
    app = _make_app(auth_mode=AppAuthMode.BOTH.value)
    svc = OpenGatewayService(repo=FakeGatewayRepo(app=app))

    result = await svc.authenticate(_ctx(plain_key=_PLAIN_SECRET))
    assert result.auth_mode == AppAuthMode.BOTH.value


@pytest.mark.asyncio
async def test_both_mode_hmac_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """both 模式下，明文未提供但签名合法 → 走签名分支放行。"""
    monkeypatch.setattr("src.utils.security.decrypt_text", lambda ciphertext: _HMAC_SECRET)
    app = _make_app(auth_mode=AppAuthMode.BOTH.value)
    svc = OpenGatewayService(repo=FakeGatewayRepo(app=app))

    date = _valid_date()
    ctx = _ctx(authorization=_hmac_authorization(app.app_id, date), date=date)
    result = await svc.authenticate(ctx)
    assert result.auth_mode == AppAuthMode.BOTH.value


# ── last_used_at 失败回滚分支 ──────────────────────────


@pytest.mark.asyncio
async def test_touch_last_used_failure_triggers_rollback(service: OpenGatewayService) -> None:
    """last_used 更新抛异常 → 调用 rollback 且不阻断鉴权主流程。"""
    service._repository.touch_raises = True

    result = await service.authenticate(_ctx(plain_key=_PLAIN_SECRET))

    assert result.app_id == "hj_test_0001"
    assert service._repository.rollback_calls == 1
