#!/bin/sh
# Render 单容器编排：new-api(127.0.0.1:3000 内部) + 双端隔离网关(0.0.0.0:$PORT 对外)
# 关键：new-api 会读环境变量 PORT（Render 注入的对外端口），必须显式把它
# 的内部端口改回 3000，否则它和网关抢同一个端口，流量绕过网关直达管理面。
cd /opt/gateway && python3 edge.py &
PORT=3000 exec /new-api --port 3000
