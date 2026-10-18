#!/bin/bash
# persist.sh - 把双端网关 + Cloudflare Tunnel 常驻化到 launchd（开机自启 + 崩溃自愈）
# 用法：在本机【你自己的终端】里运行（不要在 AI 沙箱里跑）：
#   bash /Users/wjw/Desktop/token/new-api/persist.sh
#
# 说明：AI 沙箱内 launchctl bootstrap 会被系统拒绝(error 5)，只有你在真实终端里执行才生效。
set -e
echo "== 1/3 停止当前临时实例（释放端口） =="
lsof -nP -tiTCP:3001 -sTCP:LISTEN 2>/dev/null | xargs kill 2>/dev/null || true
lsof -nP -tiTCP:3002 -sTCP:LISTEN 2>/dev/null | xargs kill 2>/dev/null || true
pkill -f 'cloudflared tunnel run' 2>/dev/null || true
sleep 2

echo "== 2/3 常驻化两个服务 =="
launchctl bootout gui/501/com.codex-shim.local   2>/dev/null || true
launchctl bootout gui/501/com.cloudflare.tunnel  2>/dev/null || true
launchctl bootstrap gui/501 "$HOME/Library/LaunchAgents/com.codex-shim.local.plist"
launchctl bootstrap gui/501 "$HOME/Library/LaunchAgents/com.cloudflare.tunnel.plist"
sleep 4

echo "== 3/3 验证 =="
echo "监听端口："
lsof -nP -iTCP:3000 -iTCP:3001 -iTCP:3002 -sTCP:LISTEN 2>/dev/null || true
echo ""
echo "用户端： https://new-api.jdhsf.top        （客户入口，管理接口已 404）"
echo "管理端： https://new-api-admin.jdhsf.top   （管理入口，需 Basic Auth + 管理员登录）"
echo ""
echo "建议再执行（防休眠断网）： sudo pmset -a sleep 0 disksleep 0"
