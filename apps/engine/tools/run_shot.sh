#!/usr/bin/env bash
# 启动引擎 + 前端预览，等端口就绪后截图 D0 页面，然后清理。
set -u

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"   # -> demo/
ENGINE="$ROOT/apps/engine"
WEB="$ROOT/apps/web"
OUT="${1:-$ENGINE/shot_d0.png}"
MODE="${2:-d0}"

PIDS="$(lsof -ti tcp:8000 tcp:4173 2>/dev/null || true)"
[ -n "$PIDS" ] && kill -9 $PIDS 2>/dev/null || true
sleep 1

( cd "$ENGINE" && exec .venv/bin/python -m uvicorn ap_engine.server:app --port 8000 --log-level warning ) >"$ENGINE/engine.log" 2>&1 &
ENG=$!
( cd "$WEB" && exec node_modules/.bin/vite preview --host 127.0.0.1 --port 4173 ) >"$WEB/preview.log" 2>&1 &
WEBPID=$!

E=000; W=000
for _ in $(seq 1 25); do
  E=$(curl -s -o /dev/null -w "%{http_code}" --max-time 1 localhost:8000/health 2>/dev/null || echo 000)
  W=$(curl -s -o /dev/null -w "%{http_code}" --max-time 1 localhost:4173/ 2>/dev/null || echo 000)
  [ "$E" = "200" ] && [ "$W" = "200" ] && break
  sleep 1
done
echo "ready: engine=$E web=$W"
[ "$W" != "200" ] && { echo "--- preview.log ---"; tail -12 "$WEB/preview.log"; }

( cd "$ENGINE" && .venv/bin/python tools/shot.py "http://127.0.0.1:4173" "$OUT" "$MODE" ) 2>&1 | tail -6

kill "$ENG" "$WEBPID" 2>/dev/null || true
wait 2>/dev/null || true
ls -la "$OUT" 2>&1
