from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .database import Base, SessionLocal, engine
from .routers import admin, auth, categories, objects, ops, projects, records, stats, uploads
from .seed import seed

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    from .services.backup import start_scheduler
    start_scheduler()
    yield


app = FastAPI(title="科研数据管理系统 RDMS", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = "/api"
app.include_router(auth.router, prefix=api_prefix)
app.include_router(admin.router, prefix=api_prefix)
app.include_router(projects.router, prefix=api_prefix)
app.include_router(categories.router, prefix=api_prefix)
app.include_router(categories.fields_router, prefix=api_prefix)
app.include_router(objects.router, prefix=api_prefix)
app.include_router(objects.tags_router, prefix=api_prefix)
app.include_router(uploads.router, prefix=api_prefix)
app.include_router(records.router, prefix=api_prefix)
app.include_router(stats.router, prefix=api_prefix)
app.include_router(ops.router, prefix=api_prefix)


@app.get("/api/{rest:path}", include_in_schema=False)
def api_fallback(rest: str):
    raise HTTPException(status_code=404, detail=f"接口不存在：/api/{rest}")


# ---- 前端静态资源（Docker 镜像内由构建阶段生成） ----
if (STATIC_DIR / "index.html").exists():

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        target = (STATIC_DIR / full_path).resolve()
        # 防目录穿越
        if str(target).startswith(str(STATIC_DIR.resolve())) and target.is_file():
            return FileResponse(target)
        return FileResponse(STATIC_DIR / "index.html")
