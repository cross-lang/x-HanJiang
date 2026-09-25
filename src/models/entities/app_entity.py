"""开放平台（面向应用）身份数据实体。

与面向用户的 UserEntity 平行：
- UserEntity 代表"终端人"，用 JWT 鉴权；
- ApiAppEntity 代表"调用方应用/服务"，用 AppId+AppKey（当前）或 HMAC 签名（未来）鉴权。

表结构已为 HMAC 升级预留：
- app_key_hash:         SHA256(app_key)，明文模式下走索引快查，不存明文；
- app_key_encrypted:    Fernet 加密后的明文 app_key，HMAC 模式解密出来重算签名用；
- auth_mode:            "plain" | "hmac" | "both"，升级时改这个字段即可，无需改代码。
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class OpenApiAppEntity(Base):
    """开放平台应用表。"""

    __tablename__ = "openapi_apps"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True, comment="主键ID"
    )

    # ── 身份标识 ──────────────────────────────────────────
    app_id: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="对外应用ID，明文，带前缀如 hj_live_xxx"
    )
    # SHA256(app_key)；明文模式下用它做常量时间比对。高熵随机串无需 salt。
    app_key_hash: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="AppKey 的 SHA256 哈希，用于明文模式校验"
    )
    # Fernet 加密后的明文 app_key；仅在 HMAC 签名校验时解密取回明文 secret。
    # 当前 plain 模式不读这一列，但落库时一并写入，未来升级 HMAC 零迁移成本。
    app_key_encrypted: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Fernet 加密的明文 AppKey，HMAC 模式解密用"
    )

    # ── 元信息 ──────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="应用名")
    owner_user_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="归属人（内部管理员用户ID）"
    )
    scopes: Mapped[str] = mapped_column(
        String(500), nullable=False, server_default="", comment="逗号分隔的权限范围，如 order:read,order:write"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="active", comment="状态：active/disabled"
    )

    # ── 鉴权模式（HMAC 升级开关）────────────────────────
    # plain：仅接受 X-App-Key 明文；hmac：仅接受 HMAC 签名；both：两者都接受（灰度期）。
    auth_mode: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="plain",
        comment="鉴权模式：plain/hmac/both",
    )

    # ── 限流 ────────────────────────────────────────────
    rate_limit_per_minute: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="60", comment="每分钟限流次数"
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="最近一次成功鉴权时间"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.current_timestamp(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="软删除时间"
    )

    __table_args__ = (
        Index("uk_app_id", "app_id", unique=True),
        Index("idx_owner_user_id", "owner_user_id"),
    )
