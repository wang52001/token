#!/bin/zsh
# migrate-to-vps.sh - 把本机 new-api 体系一键迁移到 VPS 并上线
# 用法: ./migrate-to-vps.sh <服务器IP> <域名> [ssh用户，默认root]
# 示例: ./migrate-to-vps.sh 47.96.x.x api.example.com
set -e

SERVER_IP="$1"
DOMAIN="${2:-newapi.jdhsf.top}"  # 不传域名时默认 newapi.jdhsf.top
SSH_USER="${3:-root}"
LOCAL_DIR="/Users/wjw/Desktop/token/new-api"
DEPLOY_DIR="$LOCAL_DIR/deploy"
REMOTE_DIR="/root/saas"

[ -z "$SERVER_IP" ] && { echo "用法: $0 <服务器IP> [域名，默认 newapi.jdhsf.top] [ssh用户]"; exit 1; }

echo "==> 1/6 在线备份本地数据库"
BACKUP_DB="$DEPLOY_DIR/one-api.db"
/Users/wjw/.workbuddy/binaries/python/versions/3.13.12/bin/python3 - "$LOCAL_DIR/one-api.db" "$BACKUP_DB" <<'EOF'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1]); dst = sqlite3.connect(sys.argv[2])
src.backup(dst); dst.close(); src.close()
print("  已导出", sys.argv[2])
EOF

echo "==> 2/6 生成域名配置（$DOMAIN）"
printf '%s {\n\treverse_proxy shim:3001\n\tencode zstd gzip\n}\n' "$DOMAIN" > "$DEPLOY_DIR/Caddyfile"

echo "==> 3/6 上传部署包"
ssh -o StrictHostKeyChecking=accept-new "$SSH_USER@$SERVER_IP" "mkdir -p $REMOTE_DIR"
scp "$DEPLOY_DIR/docker-compose.yml" "$DEPLOY_DIR/Caddyfile" "$DEPLOY_DIR/codex_shim.py" "$BACKUP_DB" "$SSH_USER@$SERVER_IP:$REMOTE_DIR/"

echo "==> 4/6 安装 Docker（已装则跳过）"
ssh "$SSH_USER@$SERVER_IP" 'command -v docker >/dev/null 2>&1 || (curl -fsSL https://get.docker.com | sh)'

echo "==> 5/6 启动并灌入数据库"
ssh "$SSH_USER@$SERVER_IP" <<REMOTE
set -e
cd $REMOTE_DIR
docker compose up -d
sleep 8
docker cp one-api.db new-api:/data/one-api.db
docker compose restart new-api
sleep 5
REMOTE

echo "==> 6/6 验证"
ssh "$SSH_USER@$SERVER_IP" "curl -s --max-time 10 http://localhost:3000/api/status | head -c 200"
echo ""
echo "✅ 迁移完成！最后两步："
echo "   1. 阿里云 DNS 加 A 记录: 主机记录 newapi -> $SERVER_IP"
echo "   2. 等 1 分钟证书签发后访问 https://$DOMAIN 验证"
echo "   3. 收款 = 兑换码模式（见《收款SOP.md》）；「设置→系统设置」确认开放注册"
