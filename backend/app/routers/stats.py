from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..auth import get_current_user
from ..database import get_db
from ..models import Category, FileObj, Project, Record, User

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    active = Record.deleted_at.is_(None)

    total_records = db.query(Record).filter(active).count()
    used_count = db.query(Record).filter(active, Record.used_in_pub.is_(True)).count()
    # 存储量按去重后的物理文件计算
    total_size = db.query(func.coalesce(func.sum(FileObj.size), 0)).scalar() or 0
    project_count = db.query(Project).filter(Project.status == "active").count()

    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month = db.query(Record).filter(active, Record.created_at >= month_start).count()

    by_category = []
    rows = (db.query(Category, func.count(Record.id))
            .outerjoin(Record, (Record.category_id == Category.id) & active)
            .group_by(Category.id)
            .order_by(Category.sort_order, Category.id).all())
    for cat, cnt in rows:
        by_category.append({"id": cat.id, "name": cat.name, "color": cat.color, "count": cnt})

    by_project = []
    size_by_project: dict[int, int] = {}
    psize = (db.query(Record.project_id, FileObj.id, FileObj.size)
             .join(FileObj, Record.file_id == FileObj.id)
             .filter(active).all())
    seen_files: set[int] = set()
    for pid, fid, fsize in psize:
        if fid in seen_files:
            continue
        seen_files.add(fid)
        size_by_project[pid or 0] = size_by_project.get(pid or 0, 0) + (fsize or 0)
    prows = (db.query(Project, func.count(Record.id))
             .outerjoin(Record, (Record.project_id == Project.id) & active)
             .group_by(Project.id).order_by(func.count(Record.id).desc()).all())
    unassigned = total_records - sum(cnt for _, cnt in prows if cnt)
    for p, cnt in prows:
        by_project.append({"id": p.id, "code": p.code, "name": p.name, "count": cnt,
                           "size": size_by_project.get(p.id, 0)})
    if unassigned > 0:
        by_project.append({"id": None, "code": "未归属", "name": "未归属", "count": unassigned,
                           "size": size_by_project.get(0, 0)})

    recent = (db.query(Record).options(
        joinedload(Record.file), joinedload(Record.project), joinedload(Record.category),
        joinedload(Record.sample_object), joinedload(Record.creator))
        .filter(active).order_by(Record.created_at.desc(), Record.id.desc()).limit(8).all())
    recent_items = [{
        "id": r.id, "original_name": r.original_name, "title": r.title,
        "project_code": r.project.code if r.project else None,
        "category_name": r.category.name if r.category else None,
        "category_color": r.category.color if r.category else None,
        "creator_name": (r.creator.display_name or r.creator.username) if r.creator else None,
        "created_at": r.created_at, "used_in_pub": r.used_in_pub,
        "size": r.file.size if r.file else 0,
    } for r in recent]

    return {
        "total_records": total_records,
        "total_size": total_size,
        "used_count": used_count,
        "project_count": project_count,
        "this_month": this_month,
        "by_category": by_category,
        "by_project": by_project,
        "recent": recent_items,
    }
