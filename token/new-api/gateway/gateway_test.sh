#!/bin/bash
# gateway_test.sh - 双端隔离网关请求级回归（可指定端口）
# 用法: bash gateway_test.sh [USER_PORT] [ADMIN_PORT]
set -u
UP=${1:-3101}
AP=${2:-3102}
CC_KEY="REDACTED"   # cc-claude（11 假名）
GEMINI_KEY="REDACTED"
ADMIN_BASIC="REDACTED"
BASE_U="http://127.0.0.1:$UP"
BASE_A="http://127.0.0.1:$AP"
PASS=0; FAIL=0
probe() { # probe <desc> <expected> <actual>
  if [ "$3" = "$2" ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "  ✗ $1 (want $2 got $3)"; fi
}
ne() { # ne <desc> <forbidden> <actual>   —— 断言“不是某值”（用于“路由可达≠404”）
  if [ "$3" != "$2" ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "  ✗ $1 (got $3, must != $2)"; fi
}
code() { curl -s --noproxy '*' -o /dev/null -w '%{http_code}' --max-time 8 "$@"; }

echo "=== 用户端 $BASE_U ==="
# 放行面
probe "GET /api/status"         200 "$(code "$BASE_U/api/status")"
probe "GET /(SPA)"              200 "$(code "$BASE_U/")"
probe "GET /api/pricing"        200 "$(code "$BASE_U/api/pricing")"
probe "GET /api/setup(只读)"    200 "$(code "$BASE_U/api/setup")"
probe "GET /api/models(需登录)" 401 "$(code "$BASE_U/api/models")"
probe "GET /api/user/self"      401 "$(code "$BASE_U/api/user/self")"
probe "GET /api/token/"         401 "$(code "$BASE_U/api/token/")"
probe "GET /api/log/self"       401 "$(code "$BASE_U/api/log/self")"
probe "POST /api/user/topup"    401 "$(code -X POST "$BASE_U/api/user/topup")"
probe "POST /api/user/login"    200 "$(code -X POST -H 'Content-Type: application/json' -d '{"username":"__nobody__","password":"x"}' "$BASE_U/api/user/login")"
ne   "POST /api/user/register(可达)" 404 "$(code -X POST -H 'Content-Type: application/json' -d '{}' "$BASE_U/api/user/register")"
probe "GET /console/token(SPA)" 200 "$(code "$BASE_U/console/token")"
probe "GET /console/log(SPA)"   200 "$(code "$BASE_U/console/log")"
probe "GET /v1/models(无key)"   401 "$(code "$BASE_U/v1/models")"
# 管理面必须 404
probe "GET /api/channel/"           404 "$(code "$BASE_U/api/channel/")"
probe "GET /api/channel/test"       404 "$(code "$BASE_U/api/channel/test")"
probe "GET /api/option/"            404 "$(code "$BASE_U/api/option/")"
probe "GET /api/redemption/"        404 "$(code "$BASE_U/api/redemption/")"
probe "GET /api/user/(列表)"        404 "$(code "$BASE_U/api/user/")"
probe "GET /api/user/123"           404 "$(code "$BASE_U/api/user/123")"
probe "GET /api/user/search"        404 "$(code "$BASE_U/api/user/search")"
probe "POST /api/user/manage"       404 "$(code -X POST "$BASE_U/api/user/manage")"
probe "GET /api/user/topup(管理)"   404 "$(code "$BASE_U/api/user/topup")"
probe "GET /api/log/(全部日志)"     404 "$(code "$BASE_U/api/log/")"
probe "GET /api/log/stat"           404 "$(code "$BASE_U/api/log/stat")"
probe "GET /api/models/xyz(元数据)" 404 "$(code "$BASE_U/api/models/xyz")"
probe "GET /api/group/"             404 "$(code "$BASE_U/api/group/")"
probe "GET /api/audit"              404 "$(code "$BASE_U/api/audit")"
probe "GET /api/status/test"        404 "$(code "$BASE_U/api/status/test")"
probe "POST /api/setup"             404 "$(code -X POST "$BASE_U/api/setup")"
probe "GET /api/vendors/"           404 "$(code "$BASE_U/api/vendors/")"
probe "GET /api/deployments/"       404 "$(code "$BASE_U/api/deployments/")"
probe "GET /api/plugin/task"        404 "$(code "$BASE_U/api/plugin/task")"
probe "GET /console/channel(SPA)"   404 "$(code "$BASE_U/console/channel")"
probe "GET /console/user(SPA)"      404 "$(code "$BASE_U/console/user")"
probe "GET /console/setting(SPA)"   404 "$(code "$BASE_U/console/setting")"
probe "GET /system-settings(SPA)"   404 "$(code "$BASE_U/system-settings")"
probe "GET /admin(SPA)"             404 "$(code "$BASE_U/admin")"
probe "路径穿越 /v1/../api/user/"   404 "$(code --path-as-is "$BASE_U/v1/../api/user/")"
# LLM 业务：cc-claude 令牌 → 11 个假名
ML=$(curl -s --noproxy '*' -H "Authorization: Bearer $CC_KEY" --max-time 8 "$BASE_U/v1/models")
MC=$(echo "$ML" | /Users/wjw/.workbuddy/binaries/python/versions/3.13.12/bin/python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('data',[])))" 2>/dev/null)
echo "  cc-claude /v1/models 模型数: $MC"
probe "  无真实名泄露(qwen)"  "0" "$(echo "$ML" | grep -ci qwen || true)"

echo "=== 管理端 $BASE_A ==="
probe "GET /healthz(免鉴权)"      200 "$(code "$BASE_A/healthz")"
probe "GET /api/status(无凭据)"   401 "$(code "$BASE_A/api/status")"
probe "GET /api/status(错凭据)"   401 "$(code -u 'admin:wrongpass' "$BASE_A/api/status")"
probe "GET /api/status(正确)"     200 "$(code -u "$ADMIN_BASIC" "$BASE_A/api/status")"
probe "GET /(正确)"               200 "$(code -u "$ADMIN_BASIC" "$BASE_A/")"
probe "GET /console(正确)"        200 "$(code -u "$ADMIN_BASIC" "$BASE_A/console")"
probe "GET /console/channel(正确)" 200 "$(code -u "$ADMIN_BASIC" "$BASE_A/console/channel")"
probe "GET /api/channel/(正确)"   401 "$(code -u "$ADMIN_BASIC" "$BASE_A/api/channel/")"  # 过了 Basic 门，上游仍需管理员 JWT
probe "业务/v1/models(正确)"     404 "$(code -u "$ADMIN_BASIC" "$BASE_A/v1/models")"
probe "业务/chat/completions"     404 "$(code -u "$ADMIN_BASIC" -X POST "$BASE_A/v1/chat/completions")"
probe "业务/pg/chat"              404 "$(code -u "$ADMIN_BASIC" -X POST "$BASE_A/pg/chat/completions")"
probe "业务/mj"                   404 "$(code -u "$ADMIN_BASIC" "$BASE_A/mj/submit/imagine")"
probe "业务/v1beta"               404 "$(code -u "$ADMIN_BASIC" "$BASE_A/v1beta/models/gemini-2.5-pro:generateContent")"

echo ""
echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" = "0" ]
