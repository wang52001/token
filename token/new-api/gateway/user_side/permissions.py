"""gateway/user_side/permissions.py - 用户端权限校验

用户端入口的三层收口逻辑（只服务 user_side，admin_side 有自己的独立实现）：
  1. LLM 业务前缀 → 交业务控制器（鉴权由上游 new-api 的 TokenAuth 完成）
  2. /api 白名单（方法+路径精确匹配）→ 放行；其余 /api 一律 404
  3. SPA 静态/页面 → 管理页前缀 404，其余放行

任何管理类接口（渠道/选项/兑换码管理/用户管理/模型元数据……）在本入口
一律表现为 404 Not Found —— "接口不存在"，而非 403 —— 不向外界泄露
管理面的存在。
"""

from . import routes as R


def _suspicious(bare):
    """路径穿越/编码绕过防护：合法客户端不会发送这些形态，一律 404。"""
    low = bare.lower()
    return ('..' in bare) or ('//' in bare) or ('%2e' in low) \
        or ('%2f' in low) or ('%5c' in low)


def _match_action(sub, pattern):
    """子路径模式匹配：'*' 结尾=末段通配一个路径段，其余精确。"""
    if pattern.endswith('/*'):
        head = pattern[:-2]
        return sub.startswith(head + '/') and '/' not in sub[len(head) + 1:]
    return sub == pattern


def api_allowed(method, path):
    """判定 /api/* 请求是否属于用户自助面。path 以 /api 开头。"""
    exact = ('GET', path) if method == 'HEAD' else (method, path)
    if exact in R.API_EXACT or exact in R.API_SELF_EXACT:
        return True
    for p in R.API_PREFIXES:
        if path == p or path.startswith(p if p.endswith('/') else p + '/'):
            return True
    # /api/user/<sub> 按动作白名单
    rest = path[len('/api/user'):]
    if rest.startswith('/'):
        sub = rest[1:].rstrip('/')
        if sub:  # 空子路径(=用户列表/建用户)不匹配任何动作 → 拒绝
            for m, pat in R.API_USER_ACTIONS:
                if m == method and _match_action(sub, pat):
                    return True
    # /api/task/{id}/artifacts（用户查看自己任务产物）
    if method == 'GET':
        parts = path.rstrip('/').split('/')
        if len(parts) == 5 and parts[1] == 'api' and parts[2] == 'task' \
                and parts[4] == 'artifacts':
            return True
    return False


def spa_blocked(path):
    """SPA 管理页封禁（前缀匹配，仅影响页面可达性，不影响 API 面）。"""
    for p in R.SPA_ADMIN_BLOCK_PREFIXES:
        if path == p or path.startswith(p + '/') or path.startswith(p + '?'):
            return True
    return False


def resolve(method, path):
    """路由解析：返回 ('llm'|'api'|'spa', None) 或 (None, None) 表示 404。

    仅 path（不含 query）参与前缀判定；query 原样透传。
    """
    bare = path.split('?', 1)[0]
    if _suspicious(bare):
        return None, None
    if bare.startswith(R.LLM_PREFIXES):
        return 'llm', None
    if bare == '/api' or bare.startswith('/api/'):
        if api_allowed(method, bare):
            return 'api', None
        return None, None  # 管理接口 → 404
    if spa_blocked(bare):
        return None, None  # 管理页面 → 404
    return 'spa', None
