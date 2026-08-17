# 科研数据管理系统（RDMS）v1 实施方案

从零搭建一套 Docker 化的实验室科研数据管理系统：Web 界面 + FastAPI 后端 + PostgreSQL 元数据库 + 磁盘数据卷存文件，支持原始/派生/备份文件、项目与实验分类双维度组织、SHA256 校验、自定义字段、发表使用标记。

## 1. 总体架构

```
docker compose（2 个服务）
├── db    PostgreSQL 16（元数据，数据卷 pgdata 持久化）
└── app   单镜像：node 阶段构建 Vue3 前端 → python:3.11-slim 运行时，
          uvicorn 同时提供 /api 与前端静态页，端口 8000
卷：filestore → /data/files（文件本体，可挂 NAS/备份）
```

技术栈：
- 后端：FastAPI + SQLAlchemy 2 + Pydantic v2 + PyJWT + passlib/bcrypt + Pillow + pyvips（含 OpenSlide，支持 .scn/.ndpi/.svs 等全切片格式生成缩略图；pyvips 缺失时自动降级 Pillow）
- 前端：Vue3 + Vite + Element Plus + Pinia + Vue Router + Axios（UI 全中文）
- 数据库引擎通过 `DATABASE_URL` 切换：容器内用 PostgreSQL，本地冒烟测试可切 SQLite（JSON 字段用跨库兼容写法）

## 2. 数据模型（SQLAlchemy）

| 表 | 关键字段 |
|---|---|
| users | username、password_hash、display_name、role(admin/member)、is_active |
| projects | code(如 ProjectA)、name、description、status(active/archived) |
| categories | name(WB/PCR/统计数据/病理图片…)、color、sort_order、is_active |
| sample_objects | name(如 HEK293、C57小鼠-心脏)、kind(cell/animal/tissue/other)、aliases |
| custom_field_defs | category_id、field_key、label、type(text/number/date/select)、select_options(JSON)、is_required、sort_order |
| files | sha256、size、mime、original_name、storage_path、thumb_path、uploaded_by |
| records（核心） | file_id、kind(raw/derived/backup)、parent_record_id(派生谱系)、project_id(可改)、category_id、object_id、recorded_date(实验日期)、title、note、custom_values(JSON)、used_in_pub、publication_ref(如"论文X Fig.3B")、created_by、deleted_at(软删除→回收站) |
| tags / record_tags | 自由标签 |
| audit_logs | record_id、user_id、action、changes(JSON：字段旧值→新值)、时间 |

种子数据：默认 admin 账号（README 注明首件事改密码）、示例项目 ProjectA/ProjectB、默认分类 WB/PCR/统计数据/病理图片。

## 3. 文件存储与上传

- **内容寻址存储**：`/data/files/pool/ab/abcdef…`（按 SHA256 存放），相同文件自动去重；删除记录时引用计数为 0 才物理删除
- **分片上传**：POST /api/uploads 初始化 → PUT 逐片（5MB，断点可重试）→ complete 合并、服务端流式计算 SHA256 → 入库、后台线程生成缩略图；前端对 <512MB 文件先用浏览器 crypto 预查 SHA256 实现**秒传**
- **缩略图**：普通图（jpg/png/webp/小 tiff）用 Pillow；大 TIFF 与全切片（scn/ndpi/svs/mrxs 等）用 pyvips+OpenSlide 出 512px JPEG；失败则按分类显示占位图标

## 4. 后端 API（REST，JWT 鉴权）

- auth：登录、当前用户、改密；admin 用户管理
- 配置管理：projects / categories / sample_objects / custom_field_defs / tags 的 CRUD（字段定义、项目归档等管理操作限 admin）
- 上传：init/chunk/complete、SHA256 秒传查询
- records：创建（支持批量同元数据）、分页列表（筛选：项目、分类、对象、已用状态、实验日期范围、关键词、标签）、详情、编辑（含项目归属修改）、mark-used/unmark-used（填写论文/图号）、派生谱系树、审计历史、缩略图、下载
- 回收站：软删除、恢复、彻底删除（admin）
- 批量：打包 zip 下载、批量改项目、批量删除
- dashboard：总数/存储量/项目数/近期新增/各分类分布
- 运维：手动触发全库 SHA256 完整性校验（后台任务、防比特腐烂）、按项目导出 zip 归档（含 metadata.json）

发表保护逻辑：标记已用时必填出处；已用文件的派生上传、再次标记时给出明确警告；列表可筛选"未使用"，避免一图两发。

## 5. 前端页面（Vue3 + Element Plus，中文）

1. **登录页**
2. **仪表盘**：统计卡片 + 分类/项目分布条形图（纯 CSS，不引图表库）
3. **数据浏览**（核心页）：筛选栏（项目/分类/对象/已用/日期/关键词）+ 表格视图与缩略图卡片视图切换、批量操作（下载/改项目/删除）、行内快捷改项目
4. **上传页**：拖拽多文件 + 元数据表单（项目下拉、分类联动动态渲染自定义字段含下拉、对象可搜索下拉、实验日期、标签）；"作为派生文件"开关→搜索选择父文件+派生说明（如 WB 条带截取、200x 放大）；分片进度条与秒传提示
5. **文件详情页**：预览、元数据编辑、SHA256 复制、派生谱系树、审计时间线、下载、标记已用、从本页发起派生上传
6. **回收站**：恢复/彻底删除
7. **管理页**（admin，Tab 式）：项目、分类（含**自定义字段设计器**：字段名/类型/下拉选项编辑/必填/排序）、对象库、标签、用户、完整性校验与项目导出

## 6. 目录结构

```
zcode/
├── docker-compose.yml / Dockerfile（根，多阶段）
├── backend/app/{main,config,database,models,schemas,auth}.py
│   ├── routers/{auth,admin,projects,categories,objects,fields,uploads,records,stats}.py
│   └── services/{storage,thumbnails,tasks}.py
├── frontend/{package.json, vite.config.js, src/{api,stores,router,views,components}}
└── README.md（中文：部署、首次配置、备份建议 rsync/卷挂载说明）
```

## 7. 实施步骤

1. 后端：模型+鉴权+配置 CRUD → 分片上传/存储/缩略图 → records 全套 API → dashboard/校验/导出
2. 前端：脚手架与路由 → 登录/布局 → 上传页 → 数据浏览 → 详情 → 回收站/管理页 → 仪表盘
3. Docker：根 Dockerfile（node 构建前端 → python 运行时）、compose、README
4. 验证：本地起 SQLite 版后端跑接口冒烟测试（建号/建项目/上传/筛选/标记已用/软删除）；有 Docker 环境则 compose 构建启动验证

## 8. v1 不做（README 中列为后续版本）

WSI 在线缩放浏览（OpenSeadragon）、定时自动校验、Alembic 迁移、更细粒度权限、全文检索引擎。
