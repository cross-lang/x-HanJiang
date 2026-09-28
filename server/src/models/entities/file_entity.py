"""文件记录实体。"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infras.database import Base


class FileEntity(Base):
    """文件记录表。"""

    __tablename__ = "files"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="文件ID")
    file_key: Mapped[str] = mapped_column(String(500), nullable=False, comment="存储键（唯一）")
    original_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="原始文件名")
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="存储文件名")
    extension: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="扩展名")
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="MIME 类型")
    size_bytes: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0"), comment="文件大小（字节）"
    )
    folder: Mapped[str] = mapped_column(String(100), nullable=False, server_default="general", comment="所属目录")
    storage_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default="local", comment="存储类型")
    url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="访问 URL")
    uploaded_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="上传人用户ID")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("0"), comment="是否公开访问")
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("0"), comment="是否已软删除")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        comment="上传时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="更新时间",
    )
    __table_args__ = (
        Index("uk_file_key", "file_key", unique=True),
        Index("idx_uploaded_by", "uploaded_by"),
        Index("idx_folder", "folder"),
        Index("idx_created_at", "created_at"),
    )
