# 科研数据管理系统（RDMS）

面向实验室的自托管科研数据管理平台：Web 界面 + 元数据库 + 磁盘文件存储，Docker 一键部署。

## 功能概览

- **数据组织**：按项目（ProjectA/B…）与实验分类（WB / PCR / 统计数据 / 病理图片…）双维度归类，均可自定义
- **三种数据**：原始数据（仪器原始输出）、派生数据（WB 条带截取、不同放大倍数的病理图等，挂到父文件形成**派生谱系树**）、备份文件
- **元数据**：SHA256 校验值、实验日期、实验对象（细胞/动物/组织，可搜索可新建）、项目归属（随时可改，列表内直接下拉改）、标签、备注
- **自定义字段**：每个实验分类可定义任意文本/数字/日期/**下拉**字段（如 WB 的抗体下拉、病理的染色方法与放大倍数下拉）
- **发表保护**：一键"标记已用于发表"并注明出处（论文/图号）；同一图像或其谱系再次用于其他论文时系统给出**一图两用警告**；可按"未使用"筛选可用图像
- **上传**：浏览器拖拽批量上传，大文件自动**分片**，相同内容 **SHA256 秒传**；内容寻址存储自动去重
- **预览**：jpg/png/tiff 等在线预览；病理全切片（.scn/.ndpi/.svs/.mrxs 等）自动生成缩略图
- **完整性**：全库 SHA256 定期校验（发现磁盘静默损坏），按项目导出 zip 归档（含 metadata.json）
- **多用户**：管理员 / 成员两种角色，所有元数据修改都有**审计日志**
- **回收站**：软删除 + 恢复；彻底删除仅管理员，且引用清零后才清理物理文件

## 快速部署（服务器上需有 Docker 与 Docker Compose）

```bash
# 1. 获取代码后进入目录
cd zcode

# 2. 启动（首次会自动构建镜像，需几分钟）
docker compose up -d --build

# 3. 访问
# http://<服务器IP>:8000
# 默认管理员账号：admin / admin123
```

### 修改端口（8000 被占用时）

访问端口通过环境变量 `RDMS_PORT` 控制，默认 8000。两种方式任选：

```bash
# 方式一：临时指定端口启动
RDMS_PORT=8100 docker compose up -d

# 方式二：持久化 —— 复制 .env.example 为 .env 并修改其中的 RDMS_PORT=8100，之后正常 docker compose up -d
```

> **首次登录后请立即在右上角「修改密码」修改 admin 密码**，并在「系统管理 → 用户管理」中为实验室成员建立账号。

### 服务器无法访问 Docker Hub 时（国内网络常见）

构建前先通过镜像源拉取基础镜像并重打标签（npm / pip 已在 Dockerfile 内使用国内源）：

```bash
for img in postgres:16-alpine node:20-alpine python:3.11-slim; do
  docker pull docker.m.daocloud.io/library/$img && docker tag docker.m.daocloud.io/library/$img $img
done
```

### 生产环境建议修改

编辑 `docker-compose.yml`：

1. `RDMS_JWT_SECRET`：改为 ≥32 字符的随机串（`openssl rand -hex 32` 生成）
2. 端口：如需只在内网访问，将 `"8000:8000"` 改为 `"127.0.0.1:8000:8000"` 再用反向代理（nginx）加 HTTPS
3. 数据库密码（`POSTGRES_PASSWORD` 与 `RDMS_DATABASE_URL` 中对应位置同步修改）

## 数据存放位置与备份

| 内容 | 位置（容器卷） | 说明 |
|---|---|---|
| 文件本体 | `filestore` 卷 → `/data/files/pool/` | 按 SHA256 内容寻址存放，天然去重 |
| 缩略图 | `filestore` 卷 → `/data/files/thumbs/` | |
| 导出归档 | `filestore` 卷 → `/data/files/exports/` | |
| 元数据库 | `pgdata` 卷 | PostgreSQL 数据 |

**备份建议**：

```bash
# 数据库备份（建议每日定时）
docker compose exec db pg_dump -U rdms rdms > rdms_$(date +%F).sql

# 文件卷备份到 NAS / 其他磁盘（rsync 增量）
docker run --rm -v zcode_filestore:/data -v /path/to/nas:/backup alpine \
  sh -c "cp -a /data/. /backup/rdms-files/"

# 恢复完整性确认：系统管理 → 运维 → 启动全库校验
```

## 数据卷直接挂载宿主机目录（可选）

不使用命名卷、直接把数据放到宿主机路径（便于现有备份体系接管）：

```yaml
    volumes:
      - /data/rdms-files:/data/files   # 替换 "- filestore:/data/files"
```

## 本地开发

```bash
# 后端（SQLite + 本地 data 目录，自动建表与种子数据）
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows；Linux/macOS 为 .venv/bin/pip
.venv/Scripts/python -m uvicorn app.main:app --port 8000

# 后端冒烟测试（65 项全流程检查）
.venv/Scripts/python scripts/smoke_test.py

# 前端（开发服务器，/api 自动代理到 8000）
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## 技术栈

- 后端：FastAPI + SQLAlchemy 2 + PostgreSQL（本地开发可用 SQLite）+ PyJWT + bcrypt + Pillow + pyvips/OpenSlide
- 前端：Vue 3 + Vite + Element Plus + Pinia
- 部署：Docker Compose（app + postgres 两个服务）

## 主要 API（前缀 /api，JWT Bearer 认证）

完整交互文档见运行后的 `http://<host>:8000/docs`（FastAPI 自动生成）。

## 后续版本规划（v1 未包含）

- 病理全切片在线缩放浏览（OpenSeadragon + 金字塔切片）
- 定时自动完整性校验（当前为手动触发）
- Alembic 数据库迁移
- 更细粒度权限（如删除/导出仅 PI）
