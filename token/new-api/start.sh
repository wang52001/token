#!/bin/bash
# new-api 本地中转站管理脚本
# 用法: ./start.sh start | stop | restart | status | log

set -u

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN="$BASE_DIR/new-api-macos"
SHIM="$BASE_DIR/gateway/run.py"
PYTHON_BIN="${PYTHON_BIN:-/Users/wjw/.workbuddy/binaries/python/versions/3.13.12/bin/python3}"
LOG_DIR="$BASE_DIR/logs"
DATA_DIR="$BASE_DIR/data"
PID_FILE="$BASE_DIR/new-api.pid"
SHIM_PID_FILE="$BASE_DIR/gateway.pid"
PORT="${PORT:-3000}"

export TZ=Asia/Shanghai

# 清除从外部环境继承的代理变量，避免上游请求被指向无效代理导致 502 Connection refused
# （如果上游确实需要代理，请使用下面的 HTTP_PROXY 配置显式指定）
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy 2>/dev/null || true

# 如果上游是 OpenAI / Anthropic 等需要代理才能访问的服务，取消注释并改成你的代理地址
# export HTTP_PROXY=http://127.0.0.1:7890
# export HTTPS_PROXY=http://127.0.0.1:7890
# export NO_PROXY=localhost,127.0.0.1

mkdir -p "$LOG_DIR" "$DATA_DIR"

is_running() {
  if [ -f "$PID_FILE" ]; then
    local pid
    pid=$(cat "$PID_FILE")
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  # 兼容未写 pid 文件的情况
  pgrep -f "$BIN" >/dev/null 2>&1 && return 0
  return 1
}

do_start() {
  if is_running; then
    echo "new-api 已在运行 (pid: $(cat "$PID_FILE" 2>/dev/null || pgrep -f "$BIN" | head -1))"
    echo "访问: http://localhost:$PORT"
    return 0
  fi
  cd "$BASE_DIR" || exit 1
  nohup "$BIN" --port "$PORT" --log-dir "$LOG_DIR" >>"$LOG_DIR/stdout.log" 2>&1 &
  echo $! >"$PID_FILE"
  # 双端隔离网关（3001 用户端 + 3002 管理端，替代原 codex_shim）
  if [ -f "$SHIM" ]; then
    (cd "$BASE_DIR/gateway" && nohup "$PYTHON_BIN" -u run.py >>"$LOG_DIR/gateway.log" 2>&1 &)
    echo $! >"$SHIM_PID_FILE"
  fi
  # Cloudflare Tunnel（未在运行时才拉起，避免与 LaunchAgent 重复）
  if ! pgrep -f "cloudflared tunnel run" >/dev/null 2>&1 && [ -x "$BASE_DIR/run_tunnel.sh" ]; then
    nohup "$BASE_DIR/run_tunnel.sh" >>"$LOG_DIR/cloudflared.log" 2>&1 &
    echo $! >"$BASE_DIR/cloudflared.pid"
  fi
  sleep 3
  if is_running; then
    echo "new-api 已启动 (pid: $(cat "$PID_FILE"))"
    echo "控制台:  http://localhost:$PORT"
    echo "API 地址: http://localhost:$PORT/v1"
  else
    echo "启动失败，请查看日志: $LOG_DIR/stdout.log"
    exit 1
  fi
}

do_stop() {
  if [ -f "$PID_FILE" ]; then
    kill "$(cat "$PID_FILE")" 2>/dev/null
  fi
  pkill -f "$BIN" 2>/dev/null
  if [ -f "$SHIM_PID_FILE" ]; then
    kill "$(cat "$SHIM_PID_FILE")" 2>/dev/null
  fi
  pkill -f "gateway/run.py" 2>/dev/null
  pkill -f "cloudflared tunnel run" 2>/dev/null
  rm -f "$BASE_DIR/cloudflared.pid"
  sleep 1
  rm -f "$PID_FILE" "$SHIM_PID_FILE"
  echo "new-api 已停止"
}

do_status() {
  if is_running; then
    echo "运行中 (pid: $(cat "$PID_FILE" 2>/dev/null || pgrep -f "$BIN" | head -1))"
    curl -s --noproxy '*' -o /dev/null -w "首页 HTTP 状态: %{http_code}\n" --max-time 5 "http://localhost:$PORT/"
  else
    echo "未运行"
  fi
}

case "${1:-status}" in
  start)   do_start ;;
  stop)    do_stop ;;
  restart) do_stop; do_start ;;
  status)  do_status ;;
  log)     tail -n 100 -f "$LOG_DIR/stdout.log" ;;
  *)       echo "用法: $0 start|stop|restart|status|log" ; exit 1 ;;
esac
