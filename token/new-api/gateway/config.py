"""gateway/config.py - 双端网关纯配置

本文件是 user_side 与 admin_side 唯一共享的模块，且只共享"配置数据"，
不共享任何路由 / 控制器 / 服务 / 权限逻辑（接口定义层面的彻底隔离）。

所有取值支持环境变量覆盖，便于在测试端口先行验证后再切生产。
"""

import os

# 支持从 gateway/.env 读取敏感配置（.env 不进 git；云上由平台环境变量注入）
_env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(_env_file):
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _, _v = _line.partition('=')
                os.environ.setdefault(_k.strip(), _v.strip())

# ── 上游（new-api 本体，编译二进制，不可改内部路由）──────────────────
UPSTREAM_HOST = os.environ.get('UPSTREAM_HOST', '127.0.0.1')
UPSTREAM_PORT = int(os.environ.get('UPSTREAM_PORT', '3000'))
UPSTREAM_TIMEOUT = 600  # 秒，与原 codex_shim 保持一致

# ── 用户端（对外售卖入口）───────────────────────────────────────────
USER_LISTEN_HOST = os.environ.get('USER_LISTEN_HOST', '0.0.0.0')
USER_LISTEN_PORT = int(os.environ.get('USER_LISTEN_PORT', '3001'))
USER_LOG_FILE = os.environ.get(
    'USER_LOG_FILE',
    '/Users/wjw/Desktop/token/new-api/logs/gateway-user.log')

# ── 管理端（内部运营入口）───────────────────────────────────────────
# 只绑 127.0.0.1：仅本机与 Cloudflare Tunnel（localhost 回源）可达，
# 不暴露到局域网/公网。
ADMIN_LISTEN_HOST = os.environ.get('ADMIN_LISTEN_HOST', '127.0.0.1')
ADMIN_LISTEN_PORT = int(os.environ.get('ADMIN_LISTEN_PORT', '3002'))
ADMIN_LOG_FILE = os.environ.get(
    'ADMIN_LOG_FILE',
    '/Users/wjw/Desktop/token/new-api/logs/gateway-admin.log')

# 管理端鉴权由上游 new-api 自身的管理员登录（JWT role>=10）把关。

# ── 多级回落链（上游额度/限流/端点不支持时自动切换，用户端无感知）─────
# 视觉链（带图请求）：按 协议族 × 假名档位（large=旗舰 / small=轻量）。
# 依据 2026-09-11 百炼 compatible-mode 实测矩阵：
#   /responses 端点不支持 qwen-vl-*（报 Unsupported model），qwen3.8 系在
#   /responses 与 chat 两端点均原生多模态；chat 端点 qwen-vl-*/kimi-k3 亦可看图。
VISION_CHAINS = {
    'responses_large': ['qwen3.8-max', 'qwen3.7-plus', 'qwen3.8-flash'],
    'responses_small': ['qwen3.8-flash', 'qwen3.7-plus', 'qwen3.8-max'],
    'chat_large': ['qwen-vl-max', 'qwen3.8-max', 'qwen-vl-plus', 'qwen3.8-flash'],
    'chat_small': ['qwen-vl-plus', 'qwen3.8-flash', 'qwen-vl-max', 'qwen3.8-max'],
}
# 文本备选链（无图请求）：首选映射在 new-api 渠道 model_mapping（网关不参与），
# 这里只列备选——上游对首选返回额度/限流/模型级错误时按序切换。
TEXT_CHAINS = {
    'large': ['qwen3.8-max', 'qwen3-max', 'kimi-k3'],
    'small': ['qwen3.8-flash', 'qwen3-coder-flash'],
}
# 链上全部模型都必须：① 在 default 组 abilities 有行（线上走"阿里云百炼-视觉"
# 专用渠道承载，本机走 SQL 行）② 在 cc-* 令牌 model_limits 内——否则该跳被
# new-api 拒绝后只会继续消耗链长。新增链模型时三处同步（此处+能力表+令牌）。

# ── 各端对外"官网地址"（钉进 /api/status 的 server_address）────────────
# 前端 CC Switch / Cherry Studio 等导入入口读取该值生成：
#   官网地址 = server_address，API 端点 = server_address + "/v1"（Codex）。
# 用户端：客户唯一公开业务入口。
USER_PUBLIC_ORIGIN = os.environ.get('USER_PUBLIC_ORIGIN', 'https://new-api.jdhsf.top')
# 管理端：默认也钉为用户端域名 —— 管理端对 /v1 业务一律 404，
# 若钉成管理域名，导入的 API 端点根本调不通；官网地址同样应指向公开站点。
ADMIN_PUBLIC_ORIGIN = os.environ.get('ADMIN_PUBLIC_ORIGIN', USER_PUBLIC_ORIGIN)
