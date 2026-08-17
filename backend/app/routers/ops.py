from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..database import get_db
from ..models import User
from ..services import tasks

router = APIRouter(prefix="/ops", tags=["ops"])


class ExportIn(BaseModel):
    project_id: int | None = None  # None = 全部项目


@router.post("/verify")
def start_verify(_: User = Depends(require_admin)):
    return tasks.start_verify()


@router.get("/verify")
def verify_status(_: User = Depends(require_admin)):
    jobs = tasks.list_jobs("verify")
    return jobs[0] if jobs else {"status": "never", "result": None}


@router.post("/export")
def start_export(body: ExportIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return tasks.start_export(body.project_id)


@router.get("/export")
def export_jobs(_: User = Depends(require_admin)):
    jobs = tasks.list_jobs("export")[:20]
    return [{k: v for k, v in j.items()} for j in jobs]


@router.get("/export/{job_id}/download")
def download_export(job_id: str, _: User = Depends(require_admin)):
    job = tasks.get_job(job_id)
    if job is None or job["type"] != "export":
        raise HTTPException(status_code=404, detail="导出任务不存在")
    if job["status"] != "done" or not job.get("path"):
        raise HTTPException(status_code=400, detail=f"任务尚未完成（状态：{job['status']}）")
    path = Path(job["path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="导出文件已被清理")
    return FileResponse(path, filename=path.name, media_type="application/zip")
