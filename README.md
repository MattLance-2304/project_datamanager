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

### 修改端口

访问端口通过环境变量 `RDMS_PORT` 控制，`update.sh` 首次运行会自动创建 `.env` 并固定为 8100。如需更换端口，编辑项目目录下 `.env` 中的 `RDMS_PORT` 后重新 `docker compose up -d` 即可；也可临时指定 `RDMS_PORT=9000 docker compose up -d`。

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

## 内置 ImageJ 图像分析（一条龙）

系统内置了完整版 ImageJ 1.53（[ImageJ.js](https://imagej.net/software/imagej-js/)，基于 CheerpJ 在浏览器内运行 Java 版 ImageJ，**自托管于本系统容器内，不依赖外部网站**）：

1. 任意图像条目详情页点 **「ImageJ 分析」** → 打开浏览器内的 ImageJ 工作台
2. 点「把图像送入 ImageJ」自动注入（未成功时用「下载图像」+ 拖入 ImageJ 窗口，或 File → Open）
3. 在 ImageJ 中做常规分析：ROI 测量、WB 条带灰度定量（Analyze → Gels / Measure）、阈值分割、处理等
4. File → Save 保存结果到本机后，点 **「上传处理结果（存为派生文件）」** —— 结果自动作为当前图像的**派生数据**入库，继承元数据并建立谱系

> 首次打开需在浏览器内初始化 Java 运行时（约 10~60 秒）。ImageJ 本体与 Java 运行时（CheerpJ）已**全部内置并本地化**，运行不需要访问任何外部网络，完全适用于隔离内网的实验室服务器。

## 代码更新与数据安全（多服务器同步）

已录入的数据存放在 `pgdata`（元数据库）与 `filestore`（文件本体）两个 Docker 卷中，**代码更新只重建 app 容器，完全不碰这两个卷**。日常开发→部署流程：

```text
本机改代码 → git commit → git push → 服务器上执行 ./update.sh
```

服务器端（另一台机器）首次部署：

```bash
git clone https://github.com/MattLance-2304/project_datamanager.git zcode
cd zcode && docker compose up -d --build
```

之后每次同步更新只需执行项目目录下的 `update.sh`（内容：git pull + docker compose up -d --build），构建层缓存命中时通常几十秒内完成。

> ⚠️ **唯一禁忌：不要在服务器上执行 `docker compose down -v`**——`-v` 会删除数据卷，清空全部数据。`docker compose down`（不带 -v）和 `restart` 都是安全的。
>
> 建议按 README 前文的备份方案定期 pg_dump + rsync，多一重保险。

## 数据备份（系统级）

在「系统管理 → 运维」中配置，备份覆盖**全部上传的文件**（不再作为与原始/派生并列的数据类型）：

- **实时备份**：每个文件上传完成后自动复制一份到备份目录
- **定时备份**：每天在设定时刻执行增量备份（已备份过的文件自动跳过，内容寻址让增量天然高效）
- **手动**：「立即全量备份」按钮随时触发

备份目录默认为容器内 `/data/backup`（独立 Docker 卷 `backups`）。**更安全的做法是挂载到容器外**——编辑 `docker-compose.yml`：

```yaml
    volumes:
      - filestore:/data/files
      - /mnt/nas-backup/rdms:/data/backup   # 宿主机路径或 NAS 挂载点，替换 "- backups:/data/backup"
```

备份内容：`pool/`（全部文件本体）+ `metadata.json`（所有条目元数据快照）+ `manifest.json`（统计）。恢复时把 pool 内容复制回主存储并用 metadata.json 重建记录（完整恢复工具在后续版本提供，目前可联系数据管理员手工处理）。

> 数据库本身的备份仍建议保留每日 `pg_dump`（见下节），两者互补。

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
