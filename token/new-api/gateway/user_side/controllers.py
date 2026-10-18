"""gateway/user_side/controllers.py - 用户端控制器

用户端唯一的请求处理入口。所有 HTTP 方法都收敛到 _dispatch：
  permissions.resolve() 判定路由类别 →
    llm : services.forward(伪装转发)   —— 业务接口
    api : services.forward(普通转发)   —— 自助接口
    spa : services.forward(普通转发)   —— 前端静态/页面
    其余: 404（管理接口在用户端"不存在"）
"""

from http.server import BaseHTTPRequestHandler

from . import permissions, services


class UserSideHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'nginx'      # 不向外界暴露网关实现
    sys_version = ''

    def _dispatch(self):
        length = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(length) if length else None
        kind, _ = permissions.resolve(self.command, self.path)
        if kind is None:
            services.send_json(self, 404, {'message': 'Not Found'})
            services.log.info('%s %s -> 404 (blocked)', self.command, self.path)
            return
        services.forward(self, self.command, self.path, body, self.headers,
                         disguise=(kind == 'llm'))

    do_GET = _dispatch
    do_POST = _dispatch
    do_PUT = _dispatch
    do_DELETE = _dispatch
    do_PATCH = _dispatch
    do_OPTIONS = _dispatch

    def log_message(self, fmt, *args):
        pass  # 访问日志统一走 services.log（独立文件）
