from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..database import get_db
from ..models import BackupRun, BackupSetting, User
from ..services import tasks
from ..services.backup import backup_root, get_setting, run_full_backup

router = APIRouter(prefix="/ops", tags=["ops"])


class ExportIn(BaseModel):
    project_id: int | None = None  # None = 全部项目


class BackupSettingIn(BaseModel):
    mode: str  # off / realtime / scheduled
    run_at: str = "02:00"  # HH:MM


# ---------- 备份 ----------

@router.get("/backup")
def get_backup(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    st = get_setting(db)
    runs = (db.query(BackupRun).order_by(BackupRun.id.desc()).limit(20).all())
    return {
        "setting": {"mode": st.mode, "run_at": st.run_at, "last_run_date": st.last_run_date},
        "backup_dir": str(backup_root()),
        "runs": [{
            "id": r.id, "trigger": r.trigger, "status": r.status,
            "file_count": r.file_count, "total_size": r.total_size, "error": r.error,
            "started_at": r.started_at, "finished_at": r.finished_at,
        } for r in runs],
    }


@router.put("/backup")
def update_backup(body: BackupSettingIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if body.mode not in ("off", "realtime", "scheduled"):
        raise HTTPException(status_code=422, detail="备份模式只能是 off / realtime / scheduled")
    hh, _, mm = body.run_at.partition(":")
    try:
        assert 0 <= int(hh) <= 23 and 0 <= int(mm) <= 59
    except (ValueError, AssertionError):
        raise HTTPException(status_code=422, detail="时间格式应为 HH:MM")
    st = get_setting(db)
    st.mode = body.mode
    st.run_at = f"{int(hh):02d}:{int(mm):02d}"
    db.commit()
    return {"mode": st.mode, "run_at": st.run_at}


@router.post("/backup/run")
def backup_now(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    running = (db.query(BackupRun).filter(BackupRun.status == "running").count())
    if running:
        raise HTTPException(status_code=400, detail="已有备份任务在进行中")
    run_id = run_full_backup("manual")
    return {"run_id": run_id}


@router.get("/backup/run/{run_id}")
def backup_run_status(run_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    r = db.get(BackupRun, run_id)
    if r is None:
        raise HTTPException(status_code=404, detail="备份任务不存在")
    return {"id": r.id, "trigger": r.trigger, "status": r.status,
            "file_count": r.file_count, "total_size": r.total_size, "error": r.error,
            "started_at": r.started_at, "finished_at": r.finished_at}


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
