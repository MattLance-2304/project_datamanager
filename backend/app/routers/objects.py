from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..database import get_db
from ..models import Record, SampleObject, Tag, User
from ..schemas import ObjectIn, TagIn

router = APIRouter(prefix="/objects", tags=["objects"])
tags_router = APIRouter(prefix="/tags", tags=["tags"])


# ---------- 实验对象 ----------

@router.get("")
def list_objects(q: str = "", kind: str = "", db: Session = Depends(get_db),
                 _: User = Depends(get_current_user)):
    qry = db.query(SampleObject)
    if kind:
        qry = qry.filter(SampleObject.kind == kind)
    if q:
        like = f"%{q}%"
        qry = qry.filter(SampleObject.name.ilike(like) | SampleObject.aliases.ilike(like))
    return [{"id": o.id, "name": o.name, "kind": o.kind, "aliases": o.aliases,
             "description": o.description} for o in qry.order_by(SampleObject.kind, SampleObject.name).all()]


@router.post("")
def create_object(body: ObjectIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """所有成员都可以快速新建对象（上传时常用），便于实验室日常使用。"""
    if body.kind not in ("cell", "animal", "tissue", "other"):
        raise HTTPException(status_code=422, detail="对象类型只能是 cell / animal / tissue / other")
    if db.query(SampleObject).filter(SampleObject.name == body.name).first():
        raise HTTPException(status_code=400, detail="对象已存在")
    o = SampleObject(**body.model_dump())
    db.add(o)
    db.commit()
    db.refresh(o)
    return {"id": o.id, "name": o.name, "kind": o.kind, "aliases": o.aliases, "description": o.description}


@router.put("/{object_id}")
def update_object(object_id: int, body: ObjectIn, db: Session = Depends(get_db),
                  _: User = Depends(require_admin)):
    o = db.get(SampleObject, object_id)
    if o is None:
        raise HTTPException(status_code=404, detail="对象不存在")
    if body.kind not in ("cell", "animal", "tissue", "other"):
        raise HTTPException(status_code=422, detail="对象类型只能是 cell / animal / tissue / other")
    dup = db.query(SampleObject).filter(SampleObject.name == body.name,
                                        SampleObject.id != object_id).first()
    if dup:
        raise HTTPException(status_code=400, detail="对象名称已存在")
    for k, v in body.model_dump().items():
        setattr(o, k, v)
    db.commit()
    return {"ok": True}


@router.delete("/{object_id}")
def delete_object(object_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    o = db.get(SampleObject, object_id)
    if o is None:
        raise HTTPException(status_code=404, detail="对象不存在")
    used = db.query(Record.id).filter(Record.object_id == object_id).count()
    if used > 0:
        raise HTTPException(status_code=400, detail=f"仍有 {used} 条数据使用该对象，无法删除")
    db.delete(o)
    db.commit()
    return {"ok": True}


# ---------- 标签 ----------

@tags_router.get("")
def list_tags(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return [{"id": t.id, "name": t.name} for t in db.query(Tag).order_by(Tag.name).all()]


@tags_router.post("")
def create_tag(body: TagIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    existing = db.query(Tag).filter(Tag.name == body.name).first()
    if existing:
        return {"id": existing.id, "name": existing.name}
    t = Tag(name=body.name)
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id, "name": t.name}


@tags_router.delete("/{tag_id}")
def delete_tag(tag_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    t = db.get(Tag, tag_id)
    if t is None:
        raise HTTPException(status_code=404, detail="标签不存在")
    db.delete(t)
    db.commit()
    return {"ok": True}
