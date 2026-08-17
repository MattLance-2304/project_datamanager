#!/usr/bin/env bash
# 服务器端一键更新：拉取最新代码 → 重建并启动容器（不影响已录入数据）
# 用法：在项目目录（含 docker-compose.yml 的目录）执行  ./update.sh
set -e
cd "$(dirname "$0")"

echo "==> 拉取最新代码..."
git pull --ff-only

echo "==> 重建并启动容器（数据库与文件卷不受影响）..."
docker compose up -d --build

echo "==> 清理悬空构建缓存..."
docker image prune -f >/dev/null 2>&1 || true

echo "==> 当前状态："
docker compose ps
echo ""
echo "更新完成。若前端页面未变化，浏览器强制刷新（Ctrl+F5）即可。"
echo "提醒：永远不要使用 docker compose down -v，-v 会删除数据卷。"
