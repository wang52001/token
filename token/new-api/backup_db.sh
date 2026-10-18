#!/bin/zsh
# backup_db.sh - one-api.db 每日备份（保留最近 14 份）
set -e
SRC="/Users/wjw/Desktop/token/new-api/one-api.db"
DIR="/Users/wjw/Desktop/token/new-api/backups"
mkdir -p "$DIR"
TS=$(date +%Y%m%d-%H%M%S)
# 用 sqlite3 在线备份，避免拷到写入一半的 db
/Users/wjw/.workbuddy/binaries/python/versions/3.13.12/bin/python3 - "$SRC" "$DIR/one-api-$TS.db" <<'EOF'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1])
dst = sqlite3.connect(sys.argv[2])
src.backup(dst)
dst.close(); src.close()
print(f"备份完成: {sys.argv[2]}")
EOF
# 轮转：只留最新 14 份
cd "$DIR" && ls -t one-api-*.db 2>/dev/null | tail -n +15 | while read f; do rm -f -- "$f"; done
ls -lh "$DIR" | tail -3
