"""缩略图与大预览图生成：普通图片用 Pillow，大 TIFF / 全切片（.scn/.ndpi/.svs 等）用 pyvips。

pyvips 依赖系统 libvips（Docker 镜像已安装并编译了 OpenSlide 支持）；
本地开发环境缺失时自动降级，仅处理 Pillow 支持的格式。

每个图像文件生成两份：thumbs/{id}.jpg（512px，列表用）与 previews/{id}.jpg
（1600px，详情页在线预览用，按约定路径存放，无需数据库迁移）。
"""
import threading
from pathlib import Path

from PIL import Image, ImageOps

from ..database import SessionLocal
from ..models import FileObj
from .storage import storage

try:
    import pyvips
except Exception:  # pragma: no cover - 本地无 libvips 时降级
    pyvips = None

Image.MAX_IMAGE_PIXELS = None  # 科研图像像素数极大，跳过 Pillow 的安全限制

PILLOW_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
# 直接交给 pyvips/OpenSlide 的全切片及显微镜格式
SLIDE_EXTS = {".svs", ".scn", ".ndpi", ".mrxs", ".vms", ".vmu", ".bif", ".vsi", ".lif", ".czi"}
THUMB_MAX = 512
PREVIEW_MAX = 1600
# 超过该尺寸的 TIFF 不再用 Pillow 尝试，直接走 pyvips
PILLOW_TIFF_LIMIT = 256 * 1024 * 1024


def make_image_for_path(path: Path, out: Path, original_name: str, max_px: int) -> bool:
    """按原始文件名的扩展名选择方式（内容寻址 blob 文件名本身没有扩展名）。"""
    ext = Path(original_name).suffix.lower()
    size = path.stat().st_size if path.exists() else 0

    use_pillow = ext in PILLOW_EXTS and not (ext in (".tif", ".tiff") and size > PILLOW_TIFF_LIMIT)
    if ext in SLIDE_EXTS:
        use_pillow = False

    if use_pillow:
        try:
            with Image.open(path) as im:
                im = ImageOps.exif_transpose(im)
                im.thumbnail((max_px, max_px))
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                im.convert("RGB").save(out, "JPEG", quality=88)
                return True
        except Exception:
            pass  # 损坏文件或超大 TIFF，落到 pyvips

    if pyvips is not None and path.exists():
        try:
            thumb = pyvips.Image.thumbnail(str(path), max_px)
            thumb.jpegsave(str(out), Q=88)
            return True
        except Exception:
            return False
    return False


def make_thumb_for_path(path: Path, out: Path, original_name: str) -> bool:
    return make_image_for_path(path, out, original_name, THUMB_MAX)


def preview_path_for(file_id: int) -> Path:
    return storage.previews / f"{file_id}.jpg"


def generate_thumbnail(file_id: int) -> None:
    db = SessionLocal()
    try:
        f = db.get(FileObj, file_id)
        if f is None or not f.storage_path:
            return
        src = Path(f.storage_path)
        name = f.original_name or ""
        thumb = storage.thumbs / f"{file_id}.jpg"
        if make_image_for_path(src, thumb, name, THUMB_MAX):
            f.thumb_path = str(thumb)
            db.commit()
        # 1600px 大预览图（仅当它比缩略图更有信息量时生成，避免小图重复占空间）
        if src.exists() and src.stat().st_size > 300 * 1024:
            make_image_for_path(src, preview_path_for(file_id), name, PREVIEW_MAX)
    finally:
        db.close()


def spawn_thumbnail(file_id: int) -> None:
    threading.Thread(target=generate_thumbnail, args=(file_id,), daemon=True).start()
