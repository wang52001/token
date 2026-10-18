"""gateway/user_side/routes.py - 用户端路由表

用户端对外接口面的【唯一定义处】。admin_side 不得引用本表，反之亦然。

路由分三类（均只属于用户端）：
  1. llm  —— LLM 业务协议接口（OpenAI/Claude/Gemini/Codex 四族），带身份伪装转发
  2. api  —— Web 自助服务接口（注册/登录/兑换码/自建令牌/自身日志），普通转发
  3. spa  —— 前端静态资源与页面（自助控制台），普通转发；管理页面路径返回 404

/api 白名单之外的任何 /api 路径一律 404 —— 管理端接口在用户端入口"不存在"。
路径判定不含方法的部分由 permissions.py 按方法精确收口（例如
GET /api/user/topup 是管理接口→404，POST /api/user/topup 是自助兑换→放行）。
"""

# ── 1. LLM 业务协议前缀（转发到上游并做请求体身份伪装注入）─────────
LLM_PREFIXES = ('/v1', '/v1beta', '/pg', '/mj')

# ── 2. 自助 API：精确路径（方法, 路径）──────────────────────────────
#      来源：new-api v1.0.0-rc.35 router/api-router.go 全量路由逐条分级
API_EXACT = {
    # 公开状态/内容（SPA 启动与展示需要）
    ('GET', '/api/status'),
    ('GET', '/api/uptime/status'),
    ('GET', '/api/notice'),
    ('GET', '/api/user-agreement'),
    ('GET', '/api/privacy-policy'),
    ('GET', '/api/about'),
    ('GET', '/api/home_page_content'),
    ('GET', '/api/pricing'),
    ('GET', '/api/rankings'),         # 公开排行榜；响应经 filter_model_listing 过滤为假名
    ('GET', '/api/perf-metrics'),
    ('GET', '/api/perf-metrics/summary'),
    ('GET', '/api/verification'),
    ('GET', '/api/reset_password'),
    ('GET', '/api/ratio_config'),
    ('GET', '/api/setup'),            # 只读查询初始化状态；POST 已初始化会被后端拒
    ('GET', '/api/models'),           # 精确路径=用户面板模型列表；/api/models/* 子路径是管理接口
    # 登录/注册/找回
    ('POST', '/api/user/reset'),
    ('POST', '/api/oauth/state'),
    ('GET', '/api/verify/methods'),
    ('POST', '/api/verify'),
}

# 前缀放行（该前缀下所有子路径、所有方法均为自助性质）
API_PREFIXES = (
    '/api/token',        # 用户自建令牌 CRUD（后端按会话限定本人数据）
    '/api/oauth/',       # 第三方登录跳转（未配置的 provider 由后端自行报错）
)

# /api/user/* 自助动作白名单：(方法, 子路径模式)
#   '*' 结尾 = 末段通配一个路径段；其余为精确匹配。
#   管理动作（用户列表/搜用户/改删用户/manage/GET topup 等）不在表内 → 404。
API_USER_ACTIONS = {
    ('POST', 'auth/refresh'),
    ('POST', 'auth/logout'),
    ('POST', 'register'),
    ('GET', 'login/encryption-key'),
    ('POST', 'login'),
    ('POST', 'login/2fa'),
    ('POST', 'login/verify'),
    ('POST', 'login/passkey/begin'),
    ('POST', 'login/passkey/finish'),
    ('POST', 'passkey/login/begin'),
    ('POST', 'passkey/login/finish'),
    ('GET', 'groups'),
    ('GET', 'self'),
    ('PUT', 'self'),
    ('DELETE', 'self'),
    ('GET', 'self/groups'),
    ('GET', 'models'),
    ('GET', 'token'),
    ('POST', 'token'),
    ('DELETE', 'token'),
    ('GET', 'token/status'),
    ('GET', 'sessions'),
    ('POST', 'sessions/revoke-others'),
    ('DELETE', 'sessions/*'),
    ('GET', 'passkey'),
    ('DELETE', 'passkey'),
    ('POST', 'passkey/register/begin'),
    ('POST', 'passkey/register/finish'),
    ('POST', 'passkey/verify/begin'),
    ('POST', 'passkey/verify/finish'),
    ('GET', 'aff'),
    ('POST', 'aff_transfer'),
    ('GET', 'topup/info'),
    ('GET', 'topup/self'),
    ('POST', 'topup'),          # 兑换码兑换（业务核心）
    ('POST', 'topup/complete'), # 支付回流后完成订单（自助）
    ('POST', 'amount'),         # 易支付金额试算（钱包页）
    ('POST', 'pay'),            # 易支付下单
    ('POST', 'stripe/amount'),
    ('POST', 'stripe/pay'),
    ('POST', 'creem/pay'),
    ('POST', 'waffo/amount'),
    ('POST', 'waffo/pay'),
    ('POST', 'waffo-pancake/amount'),
    ('POST', 'waffo-pancake/pay'),
    ('PUT', 'setting'),
    ('GET', '2fa/status'),
    ('POST', '2fa/setup'),
    ('POST', '2fa/enable'),
    ('POST', '2fa/disable'),
    ('POST', '2fa/backup_codes'),
    ('GET', 'checkin'),
    ('POST', 'checkin'),
    ('GET', 'oauth/bindings'),
    ('DELETE', 'oauth/bindings/*'),
}

# 其余明确放行的自助接口（自身数据类）
API_SELF_EXACT = {
    ('GET', '/api/log/self'),
    ('GET', '/api/log/self/stat'),
    ('GET', '/api/log/self/search'),
    ('GET', '/api/log/token'),       # TokenAuthReadOnly：用 sk- 令牌查自身用量
    ('GET', '/api/audit/self'),
    ('GET', '/api/data/self'),
    ('GET', '/api/data/flow/self'),
    ('GET', '/api/mj/self'),
    ('GET', '/api/task/self'),
    ('GET', '/api/usage/token'),
    # 分组只读（钱包/订阅页加载会调；new-api 会把 /api/group 301 到 /api/group/）
    ('GET', '/api/group'),
    ('GET', '/api/group/'),
    # 订阅自助（钱包页加载需要；/api/subscription/admin/* 管理面仍 404）
    ('GET', '/api/subscription/plans'),
    ('GET', '/api/subscription/self'),
    ('PUT', '/api/subscription/self/preference'),
    ('POST', '/api/subscription/balance/pay'),
    ('POST', '/api/subscription/epay/pay'),
    ('POST', '/api/subscription/stripe/pay'),
    ('POST', '/api/subscription/creem/pay'),
    ('POST', '/api/subscription/waffo-pancake/pay'),
}

# ── 3. SPA 管理页封禁前缀（情报伪装：管理功能在用户端不可见）────────
SPA_ADMIN_BLOCK_PREFIXES = (
    '/console/channel',
    '/console/user',
    '/console/redemption',
    '/console/setting',
    '/console/settings',
    '/console/system-settings',
    '/console/vendors',
    '/console/deployments',
    '/console/models',
    '/console/performance',
    '/console/audit',
    '/console/authz',
    '/console/plugin',
    '/console/group',
    '/console/prefill-group',
    '/console/subscription',
    '/admin',
    '/system-settings',
)
