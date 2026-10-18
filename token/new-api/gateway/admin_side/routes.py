"""gateway/admin_side/routes.py - 管理端路由表

管理端对外接口面的【唯一定义处】。user_side 不得引用本表，反之亦然。

管理端只承载两 类接口：
  1. web —— 控制台 SPA（/console 页面 + 静态资源 + /）
  2. api —— 管理 API（/api/* 全量：渠道/用户/兑换码/选项/日志/……）
             鉴权=网关 Basic Auth（第一道）+ new-api 管理员登录（第二道）

LLM 业务接口（/v1 /v1beta /pg /mj）在管理端【不存在】——业务接口只属于
用户端入口。管理员要实测业务，用用户端域名 + 测试令牌（这正是"两端不
互调"约束下管理员的正确体验路径）。

唯一豁免：GET /healthz —— 无鉴权存活探针，仅返回 200，不泄露任何信息。
"""

# 业务接口封禁前缀（返回 404，与用户端封禁管理接口的方式对称）
BUSINESS_BLOCK_PREFIXES = ('/v1', '/v1beta', '/pg', '/mj')

# 无鉴权存活探针（仅 GET）
HEALTH_PATH = '/healthz'

# 其余全部：Basic Auth 门 → 普通转发到上游
