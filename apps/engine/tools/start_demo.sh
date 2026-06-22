#!/usr/bin/env bash
# 启动引擎(8000) + 前端 dev(5173)，常驻后台，等就绪后打印地址。
set -u

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"   # -> demo/
ENGINE="$ROOT/apps/engine"
WEB="$ROOT/apps/web"

PIDS="$(lsof -ti tcp:8000 tcp:5173 2>/dev/null || true)"
[ -n "$PIDS" ] && kill -9 $PIDS 2>/dev/null || true
sleep 1

( cd "$ENGINE" && exec .venv/bin/python -m uvicorn ap_engine.server:app --host 127.0.0.1 --port 8000 ) > "$ENGINE/engine.run.log" 2>&1 &
disown
( cd "$WEB" && exec node_modules/.bin/vite --host 127.0.0.1 --port 5173 ) > "$WEB/web.run.log" 2>&1 &
disown

E=000; W=000
for _ in $(seq 1 30); do
  E=$(curl -s -o /dev/null -w "%{http_code}" --max-time 1 http://127.0.0.1:8000/health 2>/dev/null || echo 000)
  W=$(curl -s -o /dev/null -w "%{http_code}" --max-time 1 http://127.0.0.1:5173/ 2>/dev/null || echo 000)
  [ "$E" = "200" ] && [ "$W" = "200" ] && break
  sleep 1
done

echo "engine=$E  web=$W"
echo "引擎 API : http://127.0.0.1:8000"
echo "前端 UI  : http://127.0.0.1:5173"
[ "$E" != "200" ] && { echo "--- engine.run.log ---"; tail -10 "$ENGINE/engine.run.log"; }
[ "$W" != "200" ] && { echo "--- web.run.log ---"; tail -10 "$WEB/web.run.log"; }
