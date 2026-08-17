import zipfile
from datetime import date as date_cls
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..auth import get_current_user, require_admin
from ..database import get_db
from ..models import AuditLog, Category, CustomFieldDef, FileObj, Project, Record, RecordTag, \
    SampleObject, Tag, User
from ..schemas import BatchIn, MarkUsedIn, RecordCreateIn, RecordOut, RecordUpdateIn
from ..services.storage import storage
from ..services.thumbnails import preview_path_for

router = APIRouter(prefix="/records", tags=["records"])

# 允许浏览器直接预览的 MIME（WSI/大 TIFF 走缩略图 + 下载）
PREVIEWABLE_MIME = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp",
                    "application/pdf", "text/plain"}
PREVIEWABLE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".pdf", ".txt", ".csv", ".log"}


def _audit(db: Session, record_id: int, user_id: int | None, action: str,
           changes: dict | None = None) -> None:
    db.add(AuditLog(record_id=record_id, user_id=user_id, action=action, changes=changes))


def _validate_custom(db: Session, category_id: int | None, values: dict) -> list[str]:
    """校验自定义字段：必填、数值与日期格式。下拉字段允许自由输入（不强制选自预设选项）。"""
    if not category_id:
        return []
    errors = []
    fields = (db.query(CustomFieldDef)
              .filter(CustomFieldDef.category_id == category_id)
              .order_by(CustomFieldDef.sort_order).all())
    for f in fields:
        v = (values or {}).get(f.field_key)
        empty = v is None or v == ""
        if f.is_required and empty:
            errors.append(f"必填字段“{f.label}”未填写")
            continue
        if empty:
            continue
        if f.field_type == "number":
            try:
                float(v)
            except (TypeError, ValueError):
                errors.append(f"字段“{f.label}”必须是数字")
        elif f.field_type == "date":
            try:
                date_cls.fromisoformat(str(v))
            except (TypeError, ValueError):
                errors.append(f"字段“{f.label}”必须是日期（YYYY-MM-DD）")
    return errors


def _tag_names(db: Session, record_ids: list[int]) -> dict[int, list[str]]:
    if not record_ids:
        return {}
    rows = (db.query(RecordTag.record_id, Tag.name)
            .join(Tag, RecordTag.tag_id == Tag.id)
            .filter(RecordTag.record_id.in_(record_ids)).all())
    out: dict[int, list[str]] = {}
    for rid, name in rows:
        out.setdefault(rid, []).append(name)
    return out


def _child_counts(db: Session, record_ids: list[int]) -> dict[int, int]:
    if not record_ids:
        return {}
    rows = (db.query(Record.parent_record_id, Record.id)
            .filter(Record.parent_record_id.in_(record_ids)).all())
    out: dict[int, int] = {}
    for pid, _ in rows:
        out[pid] = out.get(pid, 0) + 1
    return out


def _serialize(r: Record, tags: list[str], child_count: int) -> RecordOut:
    return RecordOut(
        id=r.id,
        original_name=r.original_name,
        kind=r.kind,
        parent_record_id=r.parent_record_id,
        derive_note=r.derive_note,
        project_id=r.project_id,
        project_code=r.project.code if r.project else None,
        category_id=r.category_id,
        category_name=r.category.name if r.category else None,
        category_color=r.category.color if r.category else None,
        object_id=r.object_id,
        object_name=r.sample_object.name if r.sample_object else None,
        object_kind=r.sample_object.kind if r.sample_object else None,
        recorded_date=r.recorded_date,
        title=r.title,
        note=r.note,
        custom_values=r.custom_values or {},
        used_in_pub=r.used_in_pub,
        publication_ref=r.publication_ref,
        created_by=r.created_by,
        creator_name=(r.creator.display_name or r.creator.username) if r.creator else None,
        created_at=r.created_at,
        updated_at=r.updated_at or r.created_at,
        deleted_at=r.deleted_at,
        sha256=r.file.sha256 if r.file else None,
        size=r.file.size if r.file else 0,
        mime=r.file.mime if r.file else "",
        has_thumb=bool(r.file and r.file.thumb_path and Path(r.file.thumb_path).exists()),
        tags=tags,
        child_count=child_count,
    )


def _get_record(db: Session, rid: int) -> Record:
    r = db.query(Record).options(joinedload(Record.file), joinedload(Record.project),
                                 joinedload(Record.category), joinedload(Record.sample_object),
                                 joinedload(Record.creator)).filter(Record.id == rid).first()
    if r is None:
        raise HTTPException(status_code=404, detail="数据条目不存在")
    return r


@router.get("")
def list_records(
    page: int = 1,
    page_size: int = 20,
    project_id: int | None = None,
    category_id: int | None = None,
    object_id: int | None = None,
    kind: str | None = None,
    used: bool | None = None,
    recorded_from: date_cls | None = None,
    recorded_to: date_cls | None = None,
    q: str | None = None,
    tag_id: int | None = None,
    parent_id: int | None = None,
    deleted: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    qry = db.query(Record).options(
        joinedload(Record.file), joinedload(Record.project), joinedload(Record.category),
        joinedload(Record.sample_object), joinedload(Record.creator))
    qry = qry.filter(Record.deleted_at.isnot(None) if deleted else Record.deleted_at.is_(None))
    if project_id is not None:
        qry = qry.filter(Record.project_id == project_id)
    if category_id is not None:
        qry = qry.filter(Record.category_id == category_id)
    if object_id is not None:
        qry = qry.filter(Record.object_id == object_id)
    if kind:
        qry = qry.filter(Record.kind == kind)
    if used is not None:
        qry = qry.filter(Record.used_in_pub == used)
    if recorded_from:
        qry = qry.filter(Record.recorded_date >= recorded_from)
    if recorded_to:
        qry = qry.filter(Record.recorded_date <= recorded_to)
    if parent_id is not None:
        qry = qry.filter(Record.parent_record_id == parent_id)
    if tag_id is not None:
        qry = qry.filter(Record.id.in_(
            db.query(RecordTag.record_id).filter(RecordTag.tag_id == tag_id)))
    if q:
        like = f"%{q.strip()}%"
        qry = qry.join(FileObj, Record.file_id == FileObj.id).filter(or_(
            Record.original_name.ilike(like),
            Record.title.ilike(like),
            Record.note.ilike(like),
            Record.publication_ref.ilike(like),
            Record.derive_note.ilike(like),
            FileObj.sha256.ilike(like),
        ))
    total = qry.count()
    rows = (qry.order_by(Record.created_at.desc(), Record.id.desc())
            .offset((page - 1) * page_size).limit(page_size).all())
    ids = [r.id for r in rows]
    tag_map = _tag_names(db, ids)
    child_map = _child_counts(db, ids)
    items = [_serialize(r, tag_map.get(r.id, []), child_map.get(r.id, 0)) for r in rows]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.post("")
def create_records(body: RecordCreateIn, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    if body.kind not in ("raw", "derived", "backup"):
        raise HTTPException(status_code=422, detail="类型只能是 raw / derived / backup")
    parent = None
    if body.kind == "derived":
        if not body.parent_record_id:
            raise HTTPException(status_code=422, detail="派生文件必须指定父文件")
        parent = db.get(Record, body.parent_record_id)
        if parent is None:
            raise HTTPException(status_code=404, detail="父文件不存在")
        if parent.deleted_at is not None:
            raise HTTPException(status_code=400, detail="父文件已在回收站中")

    warnings = []
    if parent is not None and parent.used_in_pub:
        warnings.append(f"注意：父文件已用于发表（{parent.publication_ref or '未注明出处'}），"
                        f"请勿在其他论文中重复使用该图像")

    if body.category_id is not None and db.get(Category, body.category_id) is None:
        raise HTTPException(status_code=404, detail="实验分类不存在")
    if body.project_id is not None and db.get(Project, body.project_id) is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    if body.object_id is not None and db.get(SampleObject, body.object_id) is None:
        raise HTTPException(status_code=404, detail="对象不存在")

    errors = _validate_custom(db, body.category_id, body.custom_values)
    if errors:
        raise HTTPException(status_code=422, detail="；".join(errors))

    created = []
    for fid in body.file_ids:
        f = db.get(FileObj, fid)
        if f is None:
            raise HTTPException(status_code=404, detail=f"文件 {fid} 不存在，可能上传会话已失效")
        r = Record(
            file_id=fid,
            original_name=f.original_name or body.title,
            kind=body.kind,
            parent_record_id=parent.id if parent else None,
            derive_note=body.derive_note if body.kind == "derived" else "",
            # 派生文件未显式指定时继承父文件的关键归属信息
            project_id=body.project_id if body.project_id is not None else (parent.project_id if parent else None),
            category_id=body.category_id if body.category_id is not None else (parent.category_id if parent else None),
            object_id=body.object_id if body.object_id is not None else (parent.object_id if parent else None),
            recorded_date=body.recorded_date or (parent.recorded_date if parent else None),
            title=body.title,
            note=body.note,
            custom_values=body.custom_values or {},
            created_by=user.id,
        )
        db.add(r)
        db.flush()
        for tid in body.tag_ids:
            if db.get(Tag, tid) is not None:
                db.add(RecordTag(record_id=r.id, tag_id=tid))
        _audit(db, r.id, user.id, "create", {
            "kind": r.kind, "original_name": r.original_name,
            "project": r.project.code if r.project else None,
            "parent_record_id": r.parent_record_id,
        })
        created.append(r)

    db.commit()
    ids = [r.id for r in created]
    for r in created:
        db.refresh(r)
    tag_map = _tag_names(db, ids)
    child_map = _child_counts(db, ids)
    return {"items": [_serialize(r, tag_map.get(r.id, []), child_map.get(r.id, 0)) for r in created],
            "warnings": warnings}


@router.get("/batch/zip")
def batch_zip(ids: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """按 id 列表打包下载（GET 便于浏览器直接下载）。"""
    try:
        id_list = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=422, detail="id 列表格式错误")
    if not id_list:
        raise HTTPException(status_code=422, detail="id 列表为空")
    rows = (db.query(Record).options(joinedload(Record.file), joinedload(Record.project))
            .filter(Record.id.in_(id_list), Record.deleted_at.is_(None)).all())
    if not rows:
        raise HTTPException(status_code=404, detail="没有可下载的文件")
    out = storage.exports / f"batch_{datetime.now():%Y%m%d_%H%M%S}.zip"
    seen_names: set[str] = set()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in rows:
            f = r.file
            if f is None or not Path(f.storage_path).exists():
                continue
            arcname = f"{r.id:06d}_{r.original_name}"
            while arcname in seen_names:
                arcname = "_" + arcname
            seen_names.add(arcname)
            zf.write(f.storage_path, arcname)
    return FileResponse(out, filename=out.name, media_type="application/zip")


@router.post("/batch")
def batch_action(body: BatchIn, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    rows = (db.query(Record).filter(Record.id.in_(body.ids)).all())
    found = {r.id for r in rows}
    missing = [i for i in body.ids if i not in found]
    if missing:
        raise HTTPException(status_code=404, detail=f"以下条目不存在：{missing}")

    if body.action == "delete":
        for r in rows:
            r.deleted_at = datetime.now()
            _audit(db, r.id, user.id, "delete", None)
        db.commit()
        return {"ok": True, "affected": len(rows)}

    if body.action == "restore":
        for r in rows:
            r.deleted_at = None
            _audit(db, r.id, user.id, "restore", None)
        db.commit()
        return {"ok": True, "affected": len(rows)}

    if body.action == "project":
        if body.project_id is None:
            raise HTTPException(status_code=422, detail="缺少目标项目")
        target = db.get(Project, body.project_id)
        if target is None:
            raise HTTPException(status_code=404, detail="目标项目不存在")
        for r in rows:
            old = r.project.code if r.project else None
            if old != target.code:
                _audit(db, r.id, user.id, "update", {"project": {"old": old, "new": target.code}})
            r.project_id = body.project_id
        db.commit()
        return {"ok": True, "affected": len(rows)}

    if body.action == "mark_used":
        if not body.publication_ref:
            raise HTTPException(status_code=422, detail="标记已用于发表时必须填写出处")
        for r in rows:
            old = r.publication_ref
            r.used_in_pub = True
            r.publication_ref = body.publication_ref
            _audit(db, r.id, user.id, "mark_used",
                   {"publication_ref": {"old": old, "new": body.publication_ref}})
        db.commit()
        return {"ok": True, "affected": len(rows)}

    raise HTTPException(status_code=422, detail="不支持的操作")


@router.get("/{rid}")
def get_record(rid: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    r = _get_record(db, rid)
    tag_map = _tag_names(db, [r.id])
    child_map = _child_counts(db, [r.id])
    data = _serialize(r, tag_map.get(r.id, []), child_map.get(r.id, 0))

    parent = None
    if r.parent_record_id:
        p = _get_record(db, r.parent_record_id)
        parent = {"id": p.id, "original_name": p.original_name, "kind": p.kind,
                  "used_in_pub": p.used_in_pub, "publication_ref": p.publication_ref}
    children = (db.query(Record).filter(Record.parent_record_id == rid)
                .order_by(Record.id).all())
    data_children = [{"id": c.id, "original_name": c.original_name, "kind": c.kind,
                      "derive_note": c.derive_note, "used_in_pub": c.used_in_pub,
                      "publication_ref": c.publication_ref,
                      "deleted": c.deleted_at is not None} for c in children]

    custom_fields = []
    if r.category_id:
        defs = (db.query(CustomFieldDef).filter(CustomFieldDef.category_id == r.category_id)
                .order_by(CustomFieldDef.sort_order, CustomFieldDef.id).all())
        custom_fields = [{"field_key": d.field_key, "label": d.label, "field_type": d.field_type,
                          "select_options": d.select_options or [], "is_required": d.is_required}
                         for d in defs]
    return {"record": data, "parent": parent, "children": data_children, "custom_fields": custom_fields}


@router.patch("/{rid}")
def update_record(rid: int, body: RecordUpdateIn, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    r = _get_record(db, rid)
    provided = body.model_fields_set
    changes: dict = {}

    def set_field(attr: str, new_val, label: str):
        old_val = getattr(r, attr)
        if old_val != new_val:
            changes[label] = {"old": str(old_val) if old_val is not None else None,
                              "new": str(new_val) if new_val is not None else None}
            setattr(r, attr, new_val)

    for attr in ("original_name", "title", "note"):
        if attr in provided and getattr(body, attr) is not None:
            set_field(attr, getattr(body, attr), attr)

    if "project_id" in provided:
        if body.project_id is not None and db.get(Project, body.project_id) is None:
            raise HTTPException(status_code=404, detail="项目不存在")
        old = r.project.code if r.project else None
        set_field("project_id", body.project_id, "project")
        if "project" in changes:
            new_p = db.get(Project, body.project_id) if body.project_id else None
            changes["project"] = {"old": old, "new": new_p.code if new_p else None}

    if "object_id" in provided:
        if body.object_id is not None and db.get(SampleObject, body.object_id) is None:
            raise HTTPException(status_code=404, detail="对象不存在")
        old = r.sample_object.name if r.sample_object else None
        set_field("object_id", body.object_id, "object")
        if "object" in changes:
            new_o = db.get(SampleObject, body.object_id) if body.object_id else None
            changes["object"] = {"old": old, "new": new_o.name if new_o else None}

    new_category_id = r.category_id
    if "category_id" in provided:
        if body.category_id is not None and db.get(Category, body.category_id) is None:
            raise HTTPException(status_code=404, detail="分类不存在")
        if r.category_id != body.category_id:
            old = r.category.name if r.category else None
            new_c = db.get(Category, body.category_id) if body.category_id else None
            changes["category"] = {"old": old, "new": new_c.name if new_c else None}
            r.category_id = body.category_id
        new_category_id = body.category_id

    if "recorded_date" in provided:
        set_field("recorded_date", body.recorded_date, "recorded_date")

    if "custom_values" in provided and body.custom_values is not None:
        merged = dict(r.custom_values or {})
        merged.update(body.custom_values)
        # 换分类后按新分类校验必填（合并旧值后仍缺失则报错）
        errors = _validate_custom(db, new_category_id, merged)
        if errors:
            raise HTTPException(status_code=422, detail="；".join(errors))
        if merged != (r.custom_values or {}):
            changes["custom_values"] = {"old": r.custom_values or {}, "new": merged}
            r.custom_values = merged
    elif "category_id" in provided and body.category_id != r.category_id:
        errors = _validate_custom(db, new_category_id, r.custom_values or {})
        if errors:
            raise HTTPException(status_code=422, detail="；".join(errors))

    if "tag_ids" in provided and body.tag_ids is not None:
        db.query(RecordTag).filter(RecordTag.record_id == rid).delete()
        for tid in body.tag_ids:
            if db.get(Tag, tid) is not None:
                db.add(RecordTag(record_id=rid, tag_id=tid))

    if changes:
        _audit(db, rid, user.id, "update", changes)
        db.commit()
    db.refresh(r)
    tag_map = _tag_names(db, [r.id])
    child_map = _child_counts(db, [r.id])
    return _serialize(r, tag_map.get(r.id, []), child_map.get(r.id, 0))


def _family_refs(db: Session, r: Record, exclude_id: int) -> list[str]:
    """收集谱系（祖先+后代）中已用于发表、且出处不同的引用。"""
    refs = []
    cur = r
    while cur.parent_record_id:
        p = db.get(Record, cur.parent_record_id)
        if p is None:
            break
        if p.used_in_pub and p.publication_ref and p.id != exclude_id:
            refs.append(p.publication_ref)
        cur = p
    stack = [r.id]
    while stack:
        pid = stack.pop()
        for child in db.query(Record).filter(Record.parent_record_id == pid).all():
            if child.used_in_pub and child.publication_ref and child.id != exclude_id:
                refs.append(child.publication_ref)
            stack.append(child.id)
    return list(dict.fromkeys(refs))


@router.post("/{rid}/mark-used")
def mark_used(rid: int, body: MarkUsedIn, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    r = _get_record(db, rid)
    warnings = []
    family = _family_refs(db, r, exclude_id=rid)
    other_refs = [x for x in family if x != body.publication_ref]
    if other_refs:
        warnings.append("注意：该文件谱系中已有用于其他发表的文件（" + "、".join(other_refs) + "），"
                        "请确认没有一图两用")
    old_used = r.used_in_pub
    old_ref = r.publication_ref
    r.used_in_pub = True
    r.publication_ref = body.publication_ref
    _audit(db, rid, user.id, "mark_used",
           {"used_in_pub": {"old": old_used, "new": True},
            "publication_ref": {"old": old_ref, "new": body.publication_ref}})
    db.commit()
    return {"ok": True, "warnings": warnings}


@router.post("/{rid}/unmark-used")
def unmark_used(rid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = _get_record(db, rid)
    old = r.publication_ref
    r.used_in_pub = False
    r.publication_ref = ""
    _audit(db, rid, user.id, "unmark_used",
           {"used_in_pub": {"old": True, "new": False}, "publication_ref": {"old": old, "new": ""}})
    db.commit()
    return {"ok": True}


@router.get("/{rid}/lineage")
def lineage(rid: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    r = _get_record(db, rid)
    root = r
    while root.parent_record_id:
        p = db.get(Record, root.parent_record_id)
        if p is None:
            break
        root = p

    def node(rec: Record) -> dict:
        children = db.query(Record).filter(Record.parent_record_id == rec.id).order_by(Record.id).all()
        return {
            "id": rec.id,
            "original_name": rec.original_name,
            "kind": rec.kind,
            "derive_note": rec.derive_note,
            "used_in_pub": rec.used_in_pub,
            "publication_ref": rec.publication_ref,
            "deleted": rec.deleted_at is not None,
            "is_current": rec.id == rid,
            "children": [node(c) for c in children],
        }

    return {"current_id": rid, "tree": node(root)}


@router.get("/{rid}/audit")
def record_audit(rid: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    _get_record(db, rid)
    logs = (db.query(AuditLog).filter(AuditLog.record_id == rid)
            .order_by(AuditLog.id.desc()).limit(200).all())
    out = []
    for lg in logs:
        u = db.get(User, lg.user_id) if lg.user_id else None
        out.append({"id": lg.id, "action": lg.action, "changes": lg.changes,
                    "user": (u.display_name or u.username) if u else None,
                    "created_at": lg.created_at})
    return out


@router.get("/{rid}/thumbnail")
def thumbnail(rid: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    r = _get_record(db, rid)
    if r.file and r.file.thumb_path and Path(r.file.thumb_path).exists():
        return FileResponse(r.file.thumb_path, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="暂无缩略图")


@router.get("/{rid}/preview")
def preview(rid: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """在线预览：浏览器可直接渲染的格式返回原文件；scn/大 TIFF 等返回 1600px 预览图；再退到缩略图。"""
    r = _get_record(db, rid)
    f = r.file
    if f is None or not Path(f.storage_path).exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    ext = Path(r.original_name).suffix.lower()
    if f.mime in PREVIEWABLE_MIME or ext in PREVIEWABLE_EXT:
        return FileResponse(f.storage_path, media_type=f.mime)
    big = preview_path_for(f.id)
    if big.exists():
        return FileResponse(big, media_type="image/jpeg")
    if f.thumb_path and Path(f.thumb_path).exists():
        return FileResponse(f.thumb_path, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="该格式不支持在线预览，请下载后查看")


@router.get("/{rid}/download")
def download(rid: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    r = _get_record(db, rid)
    f = r.file
    if f is None or not Path(f.storage_path).exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(f.storage_path, filename=r.original_name or f.original_name,
                        media_type=f.mime or "application/octet-stream")


@router.post("/{rid}/delete")
def soft_delete(rid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = _get_record(db, rid)
    if r.deleted_at is not None:
        raise HTTPException(status_code=400, detail="该条目已在回收站中")
    r.deleted_at = datetime.now()
    _audit(db, rid, user.id, "delete", None)
    db.commit()
    return {"ok": True}


@router.post("/{rid}/restore")
def restore(rid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = _get_record(db, rid)
    if r.deleted_at is None:
        raise HTTPException(status_code=400, detail="该条目不在回收站中")
    r.deleted_at = None
    _audit(db, rid, user.id, "restore", None)
    db.commit()
    return {"ok": True}


@router.delete("/{rid}")
def hard_delete(rid: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    r = _get_record(db, rid)
    children = db.query(Record.id).filter(Record.parent_record_id == rid).count()
    if children > 0:
        raise HTTPException(status_code=400, detail=f"仍有 {children} 个派生文件引用该条目，请先处理派生文件")
    # 先落审计（含条目快照），删除后 record_id 由数据库置空但日志保留
    _audit(db, rid, admin.id, "hard_delete",
           {"original_name": r.original_name, "sha256": r.file.sha256 if r.file else None})
    file_id = r.file_id
    db.query(RecordTag).filter(RecordTag.record_id == rid).delete()
    db.flush()
    db.delete(r)
    db.commit()
    # 引用计数为 0 时清理物理文件
    remaining = db.query(Record.id).filter(Record.file_id == file_id).count()
    if remaining == 0:
        f = db.get(FileObj, file_id)
        if f:
            storage.delete_blob(f.sha256)
            if f.thumb_path:
                Path(f.thumb_path).unlink(missing_ok=True)
            db.delete(f)
            db.commit()
    return {"ok": True}
