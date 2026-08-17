from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..database import get_db
from ..models import Project, Record, User
from ..schemas import ProjectIn, ProjectOut, ProjectUpdateIn

router = APIRouter(prefix="/projects", tags=["projects"])


def _record_counts(db: Session) -> dict[int, int]:
    counts: dict[int, int] = {}
    for pid, _ in db.query(Record.project_id, Record.id).filter(Record.deleted_at.is_(None)).all():
        counts[pid] = counts.get(pid, 0) + 1
    return counts


@router.get("")
def list_projects(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """所有登录用户可读（下拉菜单使用），record_count 供管理页展示。"""
    counts = _record_counts(db)
    out = []
    for p in db.query(Project).order_by(Project.id).all():
        item = ProjectOut.model_validate(p)
        item.record_count = counts.get(p.id, 0)
        out.append(item)
    return out


@router.post("")
def create_project(body: ProjectIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if db.query(Project).filter(Project.code == body.code).first():
        raise HTTPException(status_code=400, detail="项目编号已存在")
    p = Project(code=body.code, name=body.name or body.code, description=body.description,
                created_by=admin.id)
    db.add(p)
    db.commit()
    db.refresh(p)
    return ProjectOut.model_validate(p)


@router.put("/{project_id}")
def update_project(project_id: int, body: ProjectUpdateIn, db: Session = Depends(get_db),
                   _: User = Depends(require_admin)):
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    if body.code is not None and body.code != p.code:
        if db.query(Project).filter(Project.code == body.code).first():
            raise HTTPException(status_code=400, detail="项目编号已存在")
        p.code = body.code
    if body.name is not None:
        p.name = body.name
    if body.description is not None:
        p.description = body.description
    if body.status is not None:
        if body.status not in ("active", "archived"):
            raise HTTPException(status_code=422, detail="状态只能是 active 或 archived")
        p.status = body.status
    db.commit()
    db.refresh(p)
    return ProjectOut.model_validate(p)


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    used = db.query(Record.id).filter(Record.project_id == project_id).count()
    if used > 0:
        raise HTTPException(status_code=400, detail=f"该项目下仍有 {used} 条数据，请先迁移或改用“归档”")
    db.delete(p)
    db.commit()
    return {"ok": True}
