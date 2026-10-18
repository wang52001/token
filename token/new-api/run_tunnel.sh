#!/bin/bash
# Cloudflare Tunnel 启动包装（供 LaunchAgent / start.sh 调用）
# 强制 HTTP/2：本机代理的 TUN 模式拦截 DNS（fake-ip），QUIC/UDP 7844 无法建连
exec /opt/homebrew/bin/cloudflared tunnel run --protocol http2 --token eyJhIjoiMGJkMWM2MzBkZjVlOTA3YWRmNjhiMDljMGNhNmIyZjAiLCJ0IjoiZjYxYTY0MzAtNjE3MC00NzBlLWFkYzItZDE3YmIzN2RmZmMyIiwicyI6IllqUTBNbUZsWTJVdFlUazBOaTAwTmpnMUxXRTRaRFl0TlRaallXSXlaR0l5TmpkayJ9
