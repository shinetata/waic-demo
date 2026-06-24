#!/usr/bin/env bash
# 一键重新打包并重启前后端（仅在 waic-demo 仓库内操作，不在父目录执行任何命令）
#
# 用法：
#   ./scripts/dev.sh         # 停旧进程 → 重新打包前端 → 重启引擎 + 前端预览
#   ./scripts/dev.sh stop    # 仅停止前后端
#
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

echo "[1/4] 停止旧的前后端进程…"
kill_port "$ENGINE_PORT"
kill_port "$WEB_PORT"

echo "[2/4] 重新打包前端（pnpm -F @ap/web build）…"
pnpm -F @ap/web build

echo "[3/4] 启动引擎（后台, :${ENGINE_PORT}）…"
( cd apps/engine && nohup uv run uvicorn ap_engine.server:app --port "$ENGINE_PORT" >"$LOG_DIR/engine.log" 2>&1 & echo $! >"$LOG_DIR/engine.pid" )
echo "  pid=$(cat "$LOG_DIR/engine.pid" 2>/dev/null || echo '?')  log=$LOG_DIR/engine.log"

echo "[4/4] 启动前端预览（后台, :${WEB_PORT}）…"
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
