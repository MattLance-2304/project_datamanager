from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ---------- auth / users ----------

class LoginIn(BaseModel):
    username: str
    password: str


class PasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreateIn(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6)
    display_name: str = ""
    role: str = "member"


class UserUpdateIn(BaseModel):
    display_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6)


# ---------- projects ----------

class ProjectIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = ""
    description: str = ""


class ProjectUpdateIn(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    status: str | None = None  # active / archived


class ProjectOut(BaseModel):
    id: int
    code: str
    name: str
    description: str
    status: str
    created_at: datetime
    record_count: int = 0

    model_config = {"from_attributes": True}


# ---------- categories / custom fields ----------

class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    color: str = "#409EFF"
    sort_order: int = 0
    is_active: bool = True


class CategoryOut(BaseModel):
    id: int
    name: str
    color: str
    sort_order: int
    is_active: bool
    field_count: int = 0

    model_config = {"from_attributes": True}


class CustomFieldIn(BaseModel):
    category_id: int
    field_key: str = ""
    label: str = Field(min_length=1, max_length=128)
    field_type: str = "text"  # text / number / date / select
    select_options: list[str] = []
    is_required: bool = False
    sort_order: int = 0


class CustomFieldOut(BaseModel):
    id: int
    category_id: int
    field_key: str
    label: str
    field_type: str
    select_options: list[str] = []
    is_required: bool
    sort_order: int
    recent_values: list[str] = []  # 该字段历史上输入过的值，按最近使用排序（MRU）

    model_config = {"from_attributes": True}

    @field_validator("select_options", "recent_values", mode="before")
    @classmethod
    def _none_to_list(cls, v):
        return v or []


# ---------- sample objects / tags ----------

class ObjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    kind: str = "other"  # cell / animal / tissue / other
    aliases: str = ""
    description: str = ""


class TagIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)


# ---------- uploads ----------

class UploadInitIn(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    size: int = -1  # -1 表示未知大小


class HashCheckIn(BaseModel):
    sha256: str = Field(min_length=64, max_length=64)


# ---------- records ----------

class RecordCreateIn(BaseModel):
    file_ids: list[int] = Field(min_length=1)
    kind: str = "raw"  # raw / derived / backup
    parent_record_id: int | None = None
    derive_note: str = ""
    project_id: int | None = None
    category_id: int | None = None
    object_id: int | None = None
    recorded_date: date | None = None
    title: str = ""
    note: str = ""
    custom_values: dict[str, Any] = {}
    tag_ids: list[int] = []


class RecordUpdateIn(BaseModel):
    original_name: str | None = None
    project_id: int | None = None
    category_id: int | None = None
    object_id: int | None = None
    recorded_date: date | None = None
    title: str | None = None
    note: str | None = None
    custom_values: dict[str, Any] | None = None
    tag_ids: list[int] | None = None


class MarkUsedIn(BaseModel):
    publication_ref: str = Field(min_length=1, max_length=255)


class BatchIn(BaseModel):
    ids: list[int] = Field(min_length=1)
    action: str  # delete / restore / project / download / mark_used
    project_id: int | None = None
    publication_ref: str = ""


class RecordOut(BaseModel):
    id: int
    original_name: str
    kind: str
    parent_record_id: int | None
    derive_note: str
    project_id: int | None
    project_code: str | None = None
    category_id: int | None
    category_name: str | None = None
    category_color: str | None = None
    object_id: int | None
    object_name: str | None = None
    object_kind: str | None = None
    recorded_date: date | None
    title: str
    note: str
    custom_values: dict | None
    used_in_pub: bool
    publication_ref: str
    created_by: int | None
    creator_name: str | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    sha256: str | None = None
    size: int = 0
    mime: str = ""
    has_thumb: bool = False
    tags: list[str] = []
    child_count: int = 0
