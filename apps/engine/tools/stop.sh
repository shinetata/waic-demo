#!/usr/bin/env bash
# 停止引擎/前端进程（lsof 在本环境不可靠，改用 ps 匹配）
PIDS="$(ps -Ao pid,args 2>/dev/null | grep -iE 'uvicorn ap_engine|vite\.js|bin/vite|vite --host|vite preview' | grep -v grep | awk '{print $1}')"
if [ -n "$PIDS" ]; then
  kill -9 $PIDS 2>/dev/null || true
  echo "killed: $(echo $PIDS | tr '\n' ' ')"
else
  echo "none"
fi
sleep 1
