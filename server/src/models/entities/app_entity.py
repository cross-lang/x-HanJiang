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

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class OpenApiAppEntity(Base):
    """开放平台应用表。"""

    __tablename__ = "openapi_apps"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    # ── 身份标识 ──────────────────────────────────────────
    app_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="对外应用ID，明文，带前缀如 hj_live_xxx")
    # SHA256(app_key)；明文模式下用它做常量时间比对。高熵随机串无需 salt。
    app_key_hash: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="AppKey 的 SHA256 哈希，用于明文模式校验"
    )
    # Fernet 加密后的明文 app_key；仅在 HMAC 签名校验时解密取回明文 secret。
    # 当前 plain 模式不读这一列，但落库时一并写入，未来升级 HMAC 零迁移成本。
    app_key_encrypted: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Fernet 加密的明文 AppKey，HMAC 模式解密用"
    )
    # 明文 AppKey 最近一次查看时间：NULL=尚未查看过（审批通过后可查看一次）；
    # 非 NULL=已展示过一次，此后只能通过重置密钥再次获取新明文。
    app_key_viewed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="AppKey 明文最近一次查看时间（NULL=未查看过）"
    )
    # ── 元信息 ──────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="应用名")
    description: Mapped[str] = mapped_column(String(255), nullable=False, comment="应用描述")
    # 归属：owner_type 区分两类来源（developer=开发者门户自助 / admin=管理员分配），
    # owner_id 按类型指向 developers.id 或 users.id。
    owner_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="admin",
        comment="归属类型：developer 开发者自助创建 / admin 管理员分配",
    )
    owner_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="归属方ID：developer→developers.id / admin→users.id"
    )
    # ── 授权状态 ──────────────────────────────────────────
    # 应用级"是否已通过创建审批"标记（网关放行门槛）：
    # 开发者自助创建的应用须审批通过后 approved=True 方可被调用；管理端自建应用无审批概念，直接 True。
    # 每次创建/修改申请的内容快照与审批结果（批次）记录在 openapi_app_registrations 表，
    # 修改类申请审批通过后按其快照覆盖本表 name/description/scopes/auth_mode。
    approved: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="0", comment="是否已通过创建审批（应用级授权状态）"
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
        String(10),
        nullable=False,
        server_default="plain",
        comment="鉴权模式：plain/hmac/both",
    )
    # ── 限流 ────────────────────────────────────────────
    rate_limit_per_minute: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="60", comment="每分钟限流次数"
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最近一次成功鉴权时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.current_timestamp(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="软删除时间")
    __table_args__ = (
        Index("uk_app_id", "app_id", unique=True),
        Index("idx_owner", "owner_type", "owner_id"),
    )


class OpenApiScopeEntity(Base):
    """开放平台 scope 元数据表。
    启动时自动扫描开放平台路由的 @app_scope 装饰器，upsert 到本表。
    管理后台创建/编辑应用时，从本表拉取可选 scope 列表。
    """

    __tablename__ = "openapi_scopes"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    scope_code: Mapped[str] = mapped_column(String(100), nullable=False, comment="Scope 编码，如 user:read")
    scope_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="Scope 中文名")
    module: Mapped[str] = mapped_column(String(50), nullable=False, comment="所属模块")
    operation: Mapped[str] = mapped_column(String(20), nullable=False, comment="操作类型")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="说明")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", comment="排序序号")
    is_deprecated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="0", comment="是否已废弃（路由中不再使用）"
    )
    __table_args__ = (
        Index("uk_scope_code", "scope_code", unique=True),
        Index("idx_module", "module"),
    )
