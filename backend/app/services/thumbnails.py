"""缩略图生成：普通图片用 Pillow，大 TIFF / 全切片（.scn/.ndpi/.svs 等）用 pyvips。

pyvips 依赖系统 libvips（Docker 镜像已安装并编译了 OpenSlide 支持）；
本地开发环境缺失时自动降级，仅处理 Pillow 支持的格式。
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
# 超过该尺寸的 TIFF 不再用 Pillow 尝试，直接走 pyvips
PILLOW_TIFF_LIMIT = 256 * 1024 * 1024


def make_thumb_for_path(path: Path, out: Path, original_name: str) -> bool:
    """按原始文件名的扩展名选择生成方式（内容寻址 blob 文件名本身没有扩展名）。"""
    ext = Path(original_name).suffix.lower()
    size = path.stat().st_size if path.exists() else 0

    use_pillow = ext in PILLOW_EXTS and not (ext in (".tif", ".tiff") and size > PILLOW_TIFF_LIMIT)
    if ext in SLIDE_EXTS:
        use_pillow = False

    if use_pillow:
        try:
            with Image.open(path) as im:
                im = ImageOps.exif_transpose(im)
                im.thumbnail((THUMB_MAX, THUMB_MAX))
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                im.convert("RGB").save(out, "JPEG", quality=85)
                return True
        except Exception:
            pass  # 损坏文件或超大 TIFF，落到 pyvips

    if pyvips is not None and path.exists():
        try:
            thumb = pyvips.Image.thumbnail(str(path), THUMB_MAX)
            thumb.jpegsave(str(out), Q=85)
            return True
        except Exception:
            return False
    return False


def generate_thumbnail(file_id: int) -> None:
    db = SessionLocal()
    try:
        f = db.get(FileObj, file_id)
        if f is None or not f.storage_path:
            return
        out = storage.thumbs / f"{file_id}.jpg"
        if make_thumb_for_path(Path(f.storage_path), out, f.original_name or ""):
            f.thumb_path = str(out)
            db.commit()
    finally:
        db.close()


def spawn_thumbnail(file_id: int) -> None:
    threading.Thread(target=generate_thumbnail, args=(file_id,), daemon=True).start()
