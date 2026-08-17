import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..database import get_db
from ..models import Category, CustomFieldDef, Record, User
from ..schemas import CategoryIn, CategoryOut, CustomFieldIn, CustomFieldOut

router = APIRouter(prefix="/categories", tags=["categories"])
fields_router = APIRouter(prefix="/custom-fields", tags=["custom-fields"])


def slugify_key(label: str, fallback: str = "field") -> str:
    """自定义字段的 key：保留中英文与数字，其余替换为下划线。"""
    key = re.sub(r"[^\w\u4e00-\u9fff]+", "_", label.strip(), flags=re.UNICODE).strip("_")
    return key or fallback


# ---------- 分类 ----------

@router.get("")
def list_categories(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    field_counts: dict[int, int] = {}
    for fid, cid in db.query(CustomFieldDef.id, CustomFieldDef.category_id).all():
        field_counts[cid] = field_counts.get(cid, 0) + 1
    out = []
    for c in db.query(Category).order_by(Category.sort_order, Category.id).all():
        item = CategoryOut.model_validate(c)
        item.field_count = field_counts.get(c.id, 0)
        out.append(item)
    return out


@router.post("")
def create_category(body: CategoryIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if db.query(Category).filter(Category.name == body.name).first():
        raise HTTPException(status_code=400, detail="分类名称已存在")
    c = Category(**body.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return CategoryOut.model_validate(c)


@router.put("/{category_id}")
def update_category(category_id: int, body: CategoryIn, db: Session = Depends(get_db),
                    _: User = Depends(require_admin)):
    c = db.get(Category, category_id)
    if c is None:
        raise HTTPException(status_code=404, detail="分类不存在")
    dup = db.query(Category).filter(Category.name == body.name, Category.id != category_id).first()
    if dup:
        raise HTTPException(status_code=400, detail="分类名称已存在")
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return CategoryOut.model_validate(c)


@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    c = db.get(Category, category_id)
    if c is None:
        raise HTTPException(status_code=404, detail="分类不存在")
    used = db.query(Record.id).filter(Record.category_id == category_id).count()
    if used > 0:
        raise HTTPException(status_code=400, detail=f"该分类下仍有 {used} 条数据，无法删除（可停用）")
    db.query(CustomFieldDef).filter(CustomFieldDef.category_id == category_id).delete()
    db.delete(c)
    db.commit()
    return {"ok": True}


# ---------- 自定义字段定义 ----------

@fields_router.get("")
def list_fields(category_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    fields = (db.query(CustomFieldDef).filter(CustomFieldDef.category_id == category_id)
              .order_by(CustomFieldDef.sort_order, CustomFieldDef.id).all())
    return [CustomFieldOut.model_validate(f) for f in fields]


@fields_router.post("")
def create_field(body: CustomFieldIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    category = db.get(Category, body.category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="分类不存在")
    if body.field_type not in ("text", "number", "date", "select"):
        raise HTTPException(status_code=422, detail="字段类型只能是 text / number / date / select")
    if body.field_type == "select" and not body.select_options:
        raise HTTPException(status_code=422, detail="下拉字段必须提供选项")
    field_key = body.field_key or slugify_key(body.label)
    dup = (db.query(CustomFieldDef)
           .filter(CustomFieldDef.category_id == body.category_id,
                   CustomFieldDef.field_key == field_key).first())
    if dup:
        raise HTTPException(status_code=400, detail="该分类下已存在同名字段")
    f = CustomFieldDef(category_id=body.category_id, field_key=field_key, label=body.label,
                       field_type=body.field_type,
                       select_options=body.select_options or None,
                       is_required=body.is_required, sort_order=body.sort_order)
    db.add(f)
    db.commit()
    db.refresh(f)
    return CustomFieldOut.model_validate(f)


@fields_router.put("/{field_id}")
def update_field(field_id: int, body: CustomFieldIn, db: Session = Depends(get_db),
                 _: User = Depends(require_admin)):
    f = db.get(CustomFieldDef, field_id)
    if f is None:
        raise HTTPException(status_code=404, detail="字段不存在")
    if body.field_type not in ("text", "number", "date", "select"):
        raise HTTPException(status_code=422, detail="字段类型只能是 text / number / date / select")
    if body.field_type == "select" and not body.select_options:
        raise HTTPException(status_code=422, detail="下拉字段必须提供选项")
    field_key = body.field_key or slugify_key(body.label)
    dup = (db.query(CustomFieldDef)
           .filter(CustomFieldDef.category_id == f.category_id,
                   CustomFieldDef.field_key == field_key,
                   CustomFieldDef.id != field_id).first())
    if dup:
        raise HTTPException(status_code=400, detail="该分类下已存在同名字段")
    f.field_key = field_key
    f.label = body.label
    f.field_type = body.field_type
    f.select_options = body.select_options or None
    f.is_required = body.is_required
    f.sort_order = body.sort_order
    db.commit()
    db.refresh(f)
    return CustomFieldOut.model_validate(f)


@fields_router.delete("/{field_id}")
def delete_field(field_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    f = db.get(CustomFieldDef, field_id)
    if f is None:
        raise HTTPException(status_code=404, detail="字段不存在")
    db.delete(f)
    db.commit()
    return {"ok": True}
