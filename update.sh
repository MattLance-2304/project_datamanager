#!/usr/bin/env bash
# 一键同步更新：停止容器 → 拉取最新代码 → 重建启动（不影响已录入数据）
# 用法：在项目目录执行  ./update.sh
# 端口：默认 8100；如需更换，编辑项目目录下 .env 中的 RDMS_PORT
set -u
cd "$(dirname "$0")"

# ---- 端口固化：首次运行自动创建 .env，默认 8100 ----
if [ ! -f .env ]; then
  echo "RDMS_PORT=8100" > .env
  echo "==> 已创建 .env（RDMS_PORT=8100）"
fi
# shellcheck disable=SC1091
. ./.env 2>/dev/null || true
PORT="${RDMS_PORT:-8100}"

echo "==> 1/4 停止容器（保留数据卷，不会动任何数据）..."
docker compose down

echo "==> 2/4 拉取最新代码..."
if git pull --ff-only; then
  echo "    代码已更新"
else
  echo "!! git pull 失败（网络不通或本地有改动）。"
  echo "   常见原因：服务器未开代理 —— 先执行  source ~/proxy_copy.sh  再重试。"
  echo "   本次将使用现有代码继续启动，不影响数据。"
fi

echo "==> 3/4 构建并启动（端口 ${PORT}）..."
docker compose up -d --build

docker image prune -f >/dev/null 2>&1 || true

echo "==> 4/4 健康检查..."
sleep 4
if curl -s -o /dev/null --max-time 10 "http://127.0.0.1:${PORT}/"; then
  echo "    服务已就绪：http://<服务器IP>:${PORT}/"
else
  echo "    服务可能仍在启动中，稍后浏览器访问 http://<服务器IP>:${PORT}/ 确认；"
  echo "    若持续无响应，查看日志：docker compose logs app --tail 50"
fi

echo ""
docker compose ps
echo ""
echo "提醒：浏览器端请 Ctrl+F5 强制刷新；永远不要执行 docker compose down -v（-v 会删除数据卷）。"
