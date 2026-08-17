"""系统级备份：实时同步 / 定时全量 / 手动全量。

备份目录结构（内容寻址天然增量：同名 sha 文件已存在即跳过）：
    <backup_dir>/pool/ab/abcdef...     文件本体（与主存储同构）
    <backup_dir>/metadata.json         全部数据条目的元数据快照
    <backup_dir>/manifest.json         本次备份统计信息
"""
import json
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

from ..config import settings
from ..database import SessionLocal
from ..models import BackupRun, BackupSetting, FileObj, Record

_loop_started = False


def backup_root() -> Path:
    root = Path(settings.backup_dir) if settings.backup_dir else Path(settings.data_dir) / "backup"
    root.mkdir(parents=True, exist_ok=True)
    (root / "pool").mkdir(exist_ok=True)
    return root


def get_setting(db) -> BackupSetting:
    s = db.get(BackupSetting, 1)
    if s is None:
        s = BackupSetting(id=1)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def _copy_blob(sha256: str) -> bool:
    """把一个 blob 复制到备份池；已备份过则跳过。返回是否新复制。"""
    from .storage import storage

    src = storage.blob_path(sha256)
    if not src.exists():
        return False
    dst = backup_root() / "pool" / sha256[:2] / sha256
    if dst.exists() and dst.stat().st_size == src.stat().st_size:
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(".part")
    shutil.copy2(src, tmp)
    tmp.replace(dst)
    return True


def spawn_realtime_backup(sha256: str) -> None:
    """实时备份模式：上传完成后异步复制。"""
    db = SessionLocal()
    try:
        if get_setting(db).mode != "realtime":
            return
    finally:
        db.close()
    threading.Thread(target=_copy_blob, args=(sha256,), daemon=True).start()


def export_metadata_json() -> dict:
    db = SessionLocal()
    try:
        from ..models import RecordTag, Tag
        tag_map: dict[int, list[str]] = {}
        for rid, name in (db.query(RecordTag.record_id, Tag.name)
                          .join(Tag, RecordTag.tag_id == Tag.id).all()):
            tag_map.setdefault(rid, []).append(name)
        meta = []
        for r in db.query(Record).order_by(Record.id).all():
            f = r.file
            meta.append({
                "record_id": r.id, "kind": r.kind, "original_name": r.original_name,
                "parent_record_id": r.parent_record_id, "derive_note": r.derive_note,
                "project_id": r.project_id, "category_id": r.category_id, "object_id": r.object_id,
                "recorded_date": str(r.recorded_date) if r.recorded_date else None,
                "title": r.title, "note": r.note, "custom_values": r.custom_values or {},
                "used_in_pub": r.used_in_pub, "publication_ref": r.publication_ref,
                "created_by": r.created_by,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "deleted_at": r.deleted_at.isoformat() if r.deleted_at else None,
                "sha256": f.sha256 if f else None, "size": f.size if f else 0,
                "tags": tag_map.get(r.id, []),
            })
        return meta
    finally:
        db.close()


def run_full_backup(trigger: str) -> int:
    """全量备份（增量复制）：文件池 + 元数据快照。返回 BackupRun.id。"""
    db = SessionLocal()
    run = BackupRun(trigger=trigger, status="running", target=str(backup_root()))
    db.add(run)
    db.commit()
    run_id = run.id
    db.close()

    def job():
        sess = SessionLocal()
        try:
            files = sess.query(FileObj).all()
            copied = 0
            total_size = 0
            for f in files:
                if _copy_blob(f.sha256):
                    copied += 1
                total_size += f.size
            root = backup_root()
            meta = export_metadata_json()
            (root / "metadata.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            (root / "manifest.json").write_text(json.dumps({
                "finished_at": datetime.now().isoformat(timespec="seconds"),
                "trigger": trigger, "files_total": len(files),
                "files_copied_this_run": copied, "total_size": total_size,
            }, ensure_ascii=False, indent=2), encoding="utf-8")

            run = sess.get(BackupRun, run_id)
            run.status = "done"
            run.file_count = len(files)
            run.total_size = total_size
            run.finished_at = datetime.now()
            if trigger == "scheduled":
                st = get_setting(sess)
                st.last_run_date = datetime.now().strftime("%Y-%m-%d")
            sess.commit()
        except Exception as e:  # noqa: BLE001
            run = sess.get(BackupRun, run_id)
            if run:
                run.status = "error"
                run.error = str(e)
                run.finished_at = datetime.now()
                sess.commit()
        finally:
            sess.close()

    threading.Thread(target=job, daemon=True).start()
    return run_id


def scheduler_loop() -> None:
    """常驻线程：定时模式下每天在设定时刻触发一次全量备份。"""
    global _loop_started
    if _loop_started:
        return
    _loop_started = True
    while True:
        time.sleep(30)
        try:
            db = SessionLocal()
            try:
                st = get_setting(db)
                if st.mode != "scheduled":
                    continue
                now = datetime.now()
                today = now.strftime("%Y-%m-%d")
                if st.last_run_date == today:
                    continue
                hhmm = now.strftime("%H:%M")
                if hhmm >= st.run_at:
                    # 防并发：先占住日期
                    st.last_run_date = today
                    db.commit()
                    run_full_backup("scheduled")
            finally:
                db.close()
        except Exception:  # noqa: BLE001
            continue


def start_scheduler() -> None:
    threading.Thread(target=scheduler_loop, daemon=True).start()
