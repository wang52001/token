#!/bin/sh
# HF Space 单容器编排：new-api(3000 内部) + shim(7860 对外，HF 固定端口)
# shim 只改写 /v1 系请求注入身份，控制台网页等其余请求原样透传到 new-api
UPSTREAM_HOST=127.0.0.1 UPSTREAM_PORT=3000 LISTEN_HOST=0.0.0.0 LISTEN_PORT=7860 \
  python3 /opt/codex_shim.py &
exec /new-api
