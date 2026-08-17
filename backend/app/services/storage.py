"""内容寻址文件存储。

文件本体按 SHA256 存放于 pool/ab/abcdef...，相同内容自动去重；
tmp/ 存放分片上传的临时数据；thumbs/ 存放缩略图；exports/ 存放导出归档。
"""
import hashlib
import os
import shutil
import uuid
from pathlib import Path

from ..config import settings


class Storage:
    def __init__(self, data_dir: str):
        self.root = Path(data_dir)
        self.pool = self.root / "pool"
        self.thumbs = self.root / "thumbs"
        self.previews = self.root / "previews"
        self.tmp = self.root / "tmp"
        self.exports = self.root / "exports"
        for d in (self.root, self.pool, self.thumbs, self.previews, self.tmp, self.exports):
            d.mkdir(parents=True, exist_ok=True)

    def blob_path(self, sha256: str) -> Path:
        return self.pool / sha256[:2] / sha256

    def new_upload(self, filename: str, size: int) -> dict:
        upload_id = uuid.uuid4().hex
        (self.tmp / upload_id).mkdir(parents=True)
        return {"upload_id": upload_id, "filename": filename, "size": size,
                "dir": self.tmp / upload_id, "received": set()}

    def write_chunk(self, upload_id: str, index: int, data: bytes) -> None:
        d = self.tmp / upload_id
        if not d.is_dir():
            raise FileNotFoundError("上传会话不存在或已过期")
        with open(d / f"{index:06d}", "wb") as f:
            f.write(data)

    def merge_and_hash(self, upload_id: str) -> tuple[str, int, Path]:
        """按分片序号合并，边合并边计算 SHA256。返回 (sha256, size, 合并后临时文件路径)。"""
        d = self.tmp / upload_id
        indexes = sorted(int(p.name) for p in d.iterdir())
        merged = self.tmp / f"{upload_id}.merged"
        h = hashlib.sha256()
        size = 0
        with open(merged, "wb") as out:
            for i in indexes:
                with open(d / f"{i:06d}", "rb") as chunk:
                    while True:
                        buf = chunk.read(4 * 1024 * 1024)
                        if not buf:
                            break
                        h.update(buf)
                        size += len(buf)
                        out.write(buf)
        shutil.rmtree(d, ignore_errors=True)
        return h.hexdigest(), size, merged

    def put_blob(self, tmp_path: Path, sha256: str) -> bool:
        """将临时文件移入存储池。已存在同内容文件时删除临时文件并返回 False（去重）。"""
        dst = self.blob_path(sha256)
        if dst.exists():
            tmp_path.unlink(missing_ok=True)
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.replace(tmp_path, dst)
        return True

    def delete_blob(self, sha256: str) -> None:
        self.blob_path(sha256).unlink(missing_ok=True)

    def hash_blob(self, sha256: str) -> str | None:
        """重算文件 SHA256（完整性校验用）；文件不存在返回 None。"""
        p = self.blob_path(sha256)
        if not p.exists():
            return None
        h = hashlib.sha256()
        with open(p, "rb") as f:
            while True:
                buf = f.read(4 * 1024 * 1024)
                if not buf:
                    break
                h.update(buf)
        return h.hexdigest()

    def cleanup_upload(self, upload_id: str) -> None:
        shutil.rmtree(self.tmp / upload_id, ignore_errors=True)
        (self.tmp / f"{upload_id}.merged").unlink(missing_ok=True)


storage = Storage(settings.data_dir)
