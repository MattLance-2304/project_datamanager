# ---------- 前端构建 ----------
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm install --registry=https://registry.npmmirror.com
COPY frontend/ .
RUN npm run build

# ---------- 运行时 ----------
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      libglib2.0-0 libvips42 libopenslide0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
      -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY backend/ .
COPY --from=frontend /build/dist ./static

ENV RDMS_DATA_DIR=/data/files \
    PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
