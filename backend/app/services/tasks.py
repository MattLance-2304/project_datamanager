"""后台任务：全库 SHA256 完整性校验、按项目导出归档。"""
import json
import threading
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from ..database import SessionLocal
from ..models import FileObj, Record
from .storage import storage

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)


def list_jobs(job_type: str | None = None) -> list[dict]:
    jobs = [j for j in _jobs.values() if job_type is None or j["type"] == job_type]
    return sorted(jobs, key=lambda j: j["started_at"], reverse=True)


def _run_job(job_id: str, fn) -> None:
    try:
        fn()
        with _lock:
            _jobs[job_id]["status"] = "done"
    except Exception as e:
        with _lock:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(e)


def start_verify() -> dict:
    with _lock:
        for j in _jobs.values():
            if j["type"] == "verify" and j["status"] == "running":
                return j
    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = {"id": job_id, "type": "verify", "status": "running",
                     "started_at": datetime.now().isoformat(timespec="seconds"),
                     "finished_at": None, "result": None, "error": None}
    threading.Thread(target=_run_job, args=(job_id, lambda: _verify_all(job_id)), daemon=True).start()
    return _jobs[job_id]


def _verify_all(job_id: str) -> None:
    db = SessionLocal()
    mismatches, missing = [], []
    checked = 0
    try:
        for f in db.query(FileObj).all():
            checked += 1
            actual = storage.hash_blob(f.sha256)
            if actual is None:
                missing.append({"file_id": f.id, "sha256": f.sha256, "name": f.original_name})
            elif actual != f.sha256:
                mismatches.append({"file_id": f.id, "sha256": f.sha256, "actual": actual,
                                   "name": f.original_name})
        result = {"checked": checked, "mismatched": len(mismatches), "missing_files": len(missing),
                  "mismatches": mismatches, "missing": missing,
                  "finished_at": datetime.now().isoformat(timespec="seconds")}
        with _lock:
            if job_id in _jobs:
                _jobs[job_id]["result"] = result
                _jobs[job_id]["finished_at"] = result["finished_at"]
    finally:
        db.close()


def start_export(project_id: int | None) -> dict:
    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = {"id": job_id, "type": "export", "status": "running",
                     "started_at": datetime.now().isoformat(timespec="seconds"),
                     "finished_at": None, "path": None, "error": None, "project_id": project_id}

    def job():
        _export_all(job_id, project_id)

    threading.Thread(target=_run_job, args=(job_id, job), daemon=True).start()
    return _jobs[job_id]


def _export_all(job_id: str, project_id: int | None) -> None:
    db = SessionLocal()
    try:
        out = storage.exports / f"export_{datetime.now():%Y%m%d_%H%M%S}_{job_id}.zip"
        meta = []
        included = 0
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            qry = db.query(Record).filter(Record.deleted_at.is_(None))
            if project_id is not None:
                qry = qry.filter(Record.project_id == project_id)
            for r in qry.order_by(Record.id).all():
                f = r.file
                project_code = r.project.code if r.project else "未归属"
                if f and Path(f.storage_path).exists():
                    zf.write(f.storage_path, f"{project_code}/{r.id:06d}_{r.original_name}")
                    included += 1
                meta.append({
                    "record_id": r.id, "文件名": r.original_name, "类型": r.kind,
                    "项目": project_code,
                    "实验分类": r.category.name if r.category else None,
                    "对象": r.sample_object.name if r.sample_object else None,
                    "实验日期": str(r.recorded_date) if r.recorded_date else None,
                    "标题": r.title, "备注": r.note, "派生说明": r.derive_note,
                    "自定义字段": r.custom_values or {},
                    "已用于发表": r.used_in_pub, "发表出处": r.publication_ref,
                    "SHA256": f.sha256 if f else None,
                    "大小": f.size if f else None,
                    "上传人": r.creator.display_name or r.creator.username if r.creator else None,
                    "上传时间": r.created_at.isoformat() if r.created_at else None,
                })
            zf.writestr("metadata.json", json.dumps(meta, ensure_ascii=False, indent=2))
        with _lock:
            if job_id in _jobs:
                _jobs[job_id]["path"] = str(out)
                _jobs[job_id]["finished_at"] = datetime.now().isoformat(timespec="seconds")
                _jobs[job_id]["included"] = included
    finally:
        db.close()
