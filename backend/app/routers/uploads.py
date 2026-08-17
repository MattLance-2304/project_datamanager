import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import settings
from ..database import get_db
from ..models import FileObj, User
from ..schemas import HashCheckIn, UploadInitIn
from ..services.storage import storage
from ..services.thumbnails import spawn_thumbnail

router = APIRouter(prefix="/uploads", tags=["uploads"])

# 分片上传会话（内存态；服务重启后未完成的上传需重新开始）
_sessions: dict[str, dict] = {}


@router.post("")
def init_upload(body: UploadInitIn, _: User = Depends(get_current_user)):
    info = storage.new_upload(body.filename, body.size)
    _sessions[info["upload_id"]] = info
    return {"upload_id": info["upload_id"], "chunk_size": settings.chunk_size}


@router.post("/check-hash")
def check_hash(body: HashCheckIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """秒传：前端已算出 SHA256 时先查询，命中则无需再传。"""
    f = db.query(FileObj).filter(FileObj.sha256 == body.sha256).first()
    if f and Path(f.storage_path).exists():
        return {"exists": True, "file_id": f.id, "sha256": f.sha256,
                "size": f.size, "mime": f.mime, "dedup": True}
    return {"exists": False}


@router.put("/{upload_id}/{index}")
async def put_chunk(upload_id: str, index: int, request: Request,
                    _: User = Depends(get_current_user)):
    if upload_id not in _sessions:
        raise HTTPException(status_code=404, detail="上传会话不存在或已过期，请重新上传")
    if index < 0:
        raise HTTPException(status_code=422, detail="分片序号无效")
    data = await request.body()
    if not data:
        raise HTTPException(status_code=422, detail="空分片")
    storage.write_chunk(upload_id, index, data)
    _sessions[upload_id]["received"].add(index)
    return {"upload_id": upload_id, "index": index, "received_chunks": len(_sessions[upload_id]["received"])}


@router.post("/{upload_id}/complete")
def complete_upload(upload_id: str, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    sess = _sessions.get(upload_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="上传会话不存在或已过期，请重新上传")
    try:
        sha256, size, merged = storage.merge_and_hash(upload_id)
    except FileNotFoundError:
        _sessions.pop(upload_id, None)
        raise HTTPException(status_code=400, detail="没有收到任何分片")

    existing = db.query(FileObj).filter(FileObj.sha256 == sha256).first()
    if existing and Path(existing.storage_path).exists():
        storage.put_blob(merged, sha256)  # 已有同内容文件，丢弃新副本
        if not existing.thumb_path:
            spawn_thumbnail(existing.id)
        _sessions.pop(upload_id, None)
        return {"file_id": existing.id, "sha256": sha256, "size": existing.size,
                "mime": existing.mime, "dedup": True}

    storage.put_blob(merged, sha256)
    mime = mimetypes.guess_type(sess["filename"])[0] or "application/octet-stream"
    f = FileObj(sha256=sha256, size=size, mime=mime, original_name=sess["filename"],
                storage_path=str(storage.blob_path(sha256)), uploaded_by=user.id)
    db.add(f)
    try:
        db.commit()
    except IntegrityError:
        # 并发上传同一文件的竞争：回退为复用已有记录
        db.rollback()
        f = db.query(FileObj).filter(FileObj.sha256 == sha256).first()
        _sessions.pop(upload_id, None)
        return {"file_id": f.id, "sha256": sha256, "size": f.size, "mime": f.mime, "dedup": True}
    db.refresh(f)
    spawn_thumbnail(f.id)
    _sessions.pop(upload_id, None)
    return {"file_id": f.id, "sha256": sha256, "size": size, "mime": mime, "dedup": False}


@router.post("/{upload_id}/cancel")
def cancel_upload(upload_id: str, _: User = Depends(get_current_user)):
    sess = _sessions.pop(upload_id, None)
    if sess is None:
        raise HTTPException(status_code=404, detail="上传会话不存在")
    storage.cleanup_upload(upload_id)
    return {"ok": True}
