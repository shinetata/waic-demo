#!/usr/bin/env bash
# 一键重新打包并重启前后端（仅在 waic-demo 仓库内操作，不在父目录执行任何命令）
#
# 用法：
#   ./scripts/dev.sh          # 停旧进程 → 渲染页面素材 → 重新打包前端 → 重启引擎 + 前端预览
#   ./scripts/dev.sh stop     # 仅停止前后端
#   ./scripts/dev.sh install  # 安装依赖（pnpm，store 固定在仓库内）
#   RENDER=0 ./scripts/dev.sh # 跳过页面渲染（仅改了前端/引擎代码、未改 HTML 素材时更快）
#
# 页面渲染依赖 Playwright + 本地 chromium 缓存（apps/engine/.pw-browsers）；首次需联网拉取 playwright。
# 可用环境变量覆盖端口：ENGINE_PORT(默认8000) WEB_PORT(默认4173)

set -uo pipefail

# 确保中文/全角字符在任意 shell 环境下都能正确解析与显示
export LANG="${LANG:-en_US.UTF-8}"

# 仓库根 = 本脚本所在目录的上一级（保证无论从哪调用都在 waic-demo 内执行）
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENGINE_PORT="${ENGINE_PORT:-8000}"
WEB_PORT="${WEB_PORT:-4173}"
LOG_DIR="$ROOT/.logs"
mkdir -p "$LOG_DIR"

kill_port() {
  local port="$1" pids
  pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "  停止占用 :$port 的进程: $pids"
    kill $pids 2>/dev/null || true
    sleep 1
    pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
    if [ -n "$pids" ]; then kill -9 $pids 2>/dev/null || true; fi
  fi
}

wait_url() {
  local name="$1" url="$2" n=0
  until curl -sf -o /dev/null "$url"; do
    n=$((n + 1))
    if [ "$n" -ge 40 ]; then
      echo "  ⚠ ${name} 未就绪（${url}），请查看日志排查"
      return 1
    fi
    sleep 0.5
  done
  echo "  ✓ $name 就绪: $url"
}

stop_all() {
  echo "停止前后端…"
  kill_port "$ENGINE_PORT"
  kill_port "$WEB_PORT"
  echo "已停止。"
}

if [ "${1:-}" = "stop" ]; then
  stop_all
  exit 0
fi

if [ "${1:-}" = "install" ]; then
  echo "安装依赖（store 固定在仓库内 .pnpm-store，不污染父目录）…"
  pnpm install --store-dir "$ROOT/.pnpm-store"
  echo "完成。"
  exit 0
fi

echo "[1/5] 停止旧的前后端进程…"
kill_port "$ENGINE_PORT"
kill_port "$WEB_PORT"

echo "[2/5] 重新渲染页面素材（Playwright → assets/pages + manifests）…"
if [ "${RENDER:-1}" = "1" ]; then
  if ( cd apps/engine && PLAYWRIGHT_BROWSERS_PATH="$PWD/.pw-browsers" uv run --with playwright python tools/render_pages.py ) >"$LOG_DIR/render.log" 2>&1; then
    echo "  ✓ 渲染完成：$(grep -c 'rendered ' "$LOG_DIR/render.log" 2>/dev/null || echo '?') 页（日志 $LOG_DIR/render.log）"
  else
    echo "  ⚠ 渲染失败，沿用现有素材继续（日志末尾）："
    tail -n 8 "$LOG_DIR/render.log" 2>/dev/null | sed 's/^/    /'
  fi
else
  echo "  跳过渲染（RENDER=0）"
fi

echo "[3/5] 重新打包前端（pnpm -F @ap/web build）…"
pnpm -F @ap/web build

echo "[4/5] 启动引擎（后台, :${ENGINE_PORT}）…"
( cd apps/engine && nohup uv run uvicorn ap_engine.server:app --port "$ENGINE_PORT" >"$LOG_DIR/engine.log" 2>&1 & echo $! >"$LOG_DIR/engine.pid" )
echo "  pid=$(cat "$LOG_DIR/engine.pid" 2>/dev/null || echo '?')  log=$LOG_DIR/engine.log"

echo "[5/5] 启动前端预览（后台, :${WEB_PORT}）…"
nohup pnpm -F @ap/web preview --port "$WEB_PORT" >"$LOG_DIR/web.log" 2>&1 &
echo $! >"$LOG_DIR/web.pid"
echo "  pid=$(cat "$LOG_DIR/web.pid" 2>/dev/null || echo '?')  log=$LOG_DIR/web.log"

echo "等待服务就绪…"
wait_url "引擎" "http://127.0.0.1:$ENGINE_PORT/health" || true
wait_url "前端" "http://localhost:$WEB_PORT/" || true

echo
echo "完成 ✅  前端: http://localhost:$WEB_PORT   引擎: http://127.0.0.1:$ENGINE_PORT"
echo "日志: tail -f $LOG_DIR/engine.log  |  tail -f $LOG_DIR/web.log"
echo "停止: ./scripts/dev.sh stop"
