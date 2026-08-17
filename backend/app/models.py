from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# SQLite 兼容的 JSON 列（PostgreSQL 下自动用 JSONB）
JSONType = JSON().with_variant(postgresql.JSONB(), "postgresql")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    display_name: Mapped[str] = mapped_column(String(64), default="")
    role: Mapped[str] = mapped_column(String(16), default="member")  # admin / member
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # 如 ProjectA
    name: Mapped[str] = mapped_column(String(128), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="active")  # active / archived
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Category(Base):
    """实验类型分类：WB / PCR / 统计数据 / 病理图片……"""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    color: Mapped[str] = mapped_column(String(16), default="#409EFF")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class CustomFieldDef(Base):
    """某个实验分类下的自定义元数据字段定义。"""

    __tablename__ = "custom_field_defs"
    __table_args__ = (UniqueConstraint("category_id", "field_key", name="uq_field_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), index=True)
    field_key: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(128))
    field_type: Mapped[str] = mapped_column(String(16), default="text")  # text / number / date / select
    select_options: Mapped[list | None] = mapped_column(JSONType, nullable=True)  # select 类型的选项列表
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SampleObject(Base):
    """实验对象：细胞系 / 动物 / 组织等，供下拉选择与检索。"""

    __tablename__ = "sample_objects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    kind: Mapped[str] = mapped_column(String(16), default="other")  # cell / animal / tissue / other
    aliases: Mapped[str] = mapped_column(Text, default="")  # 别名，逗号分隔，便于检索
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FileObj(Base):
    """物理文件（内容寻址 blob）：同一 SHA256 只存一份。"""

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    size: Mapped[int] = mapped_column(BigInteger, default=0)
    mime: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    original_name: Mapped[str] = mapped_column(String(255), default="")
    storage_path: Mapped[str] = mapped_column(String(512), default="")
    thumb_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Record(Base):
    """数据条目：一次上传的科研数据及其元数据。"""

    __tablename__ = "records"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), index=True)
    original_name: Mapped[str] = mapped_column(String(255), default="")
    kind: Mapped[str] = mapped_column(String(16), default="raw")  # raw / derived / backup
    parent_record_id: Mapped[int | None] = mapped_column(ForeignKey("records.id"), nullable=True, index=True)
    derive_note: Mapped[str] = mapped_column(String(255), default="")  # 派生说明，如“WB 条带截取”“200x 放大”

    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True, index=True)
    object_id: Mapped[int | None] = mapped_column(ForeignKey("sample_objects.id"), nullable=True, index=True)

    recorded_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # 实验日期
    title: Mapped[str] = mapped_column(String(255), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    custom_values: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

    used_in_pub: Mapped[bool] = mapped_column(Boolean, default=False)
    publication_ref: Mapped[str] = mapped_column(String(255), default="")  # 如 “论文X Fig.3B”

    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    file: Mapped["FileObj"] = relationship()
    project: Mapped["Project | None"] = relationship()
    category: Mapped["Category | None"] = relationship()
    sample_object: Mapped["SampleObject | None"] = relationship()
    creator: Mapped["User | None"] = relationship()

    __table_args__ = (
        Index("ix_records_project_deleted", "project_id", "deleted_at"),
        Index("ix_records_category_deleted", "category_id", "deleted_at"),
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)


class RecordTag(Base):
    __tablename__ = "record_tags"
    __table_args__ = (UniqueConstraint("record_id", "tag_id", name="uq_record_tag"),)

    record_id: Mapped[int] = mapped_column(ForeignKey("records.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    # 条目被彻底删除后置空（SET NULL），审计痕迹保留在 changes 快照中
    record_id: Mapped[int | None] = mapped_column(
        ForeignKey("records.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(32))  # create/update/mark_used/unmark_used/delete/restore/hard_delete
    changes: Mapped[dict | None] = mapped_column(JSONType, nullable=True)  # {字段: {old, new}}
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
