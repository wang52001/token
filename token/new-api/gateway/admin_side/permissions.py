"""gateway/admin_side/permissions.py - 管理端权限校验

管理端入口的收口（只服务 admin_side，与 user_side 互不引用）：
  1. GET /healthz    → 存活探针，免鉴权
  2. 业务前缀 /v1 /v1beta /pg /mj → 404（业务接口只属于用户端）
  3. 其余一切请求    → 普通转发，由上游 new-api 自身的管理员鉴权（JWT role>=10）把关
"""

from . import routes as R


def _suspicious(bare):
    """路径穿越/编码绕过防护：合法客户端不会发送这些形态，一律 404。"""
    low = bare.lower()
    return ('..' in bare) or ('//' in bare) or ('%2e' in low) \
        or ('%2f' in low) or ('%5c' in low)


def resolve(method, path, auth_header):
    """路由解析。

    参数:
      method      —— HTTP 方法
      path        —— 原始路径（可含 query）
      auth_header —— 当前请求的 Authorization 头（保留参数，未使用）

    返回:
      ('health', None) —— 存活探针，控制器直接回 200
      (None, None)     —— 业务接口，404
      ('web', None)    —— 普通转发（控制台/管理API/静态）
    """
    bare = path.split('?', 1)[0]
    if _suspicious(bare):
        return None, None
    if method in ('GET', 'HEAD') and bare == R.HEALTH_PATH:
        return 'health', None
    if bare.startswith(R.BUSINESS_BLOCK_PREFIXES):
        return None, None
    return 'web', None
