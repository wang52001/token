"""gateway/admin_side/controllers.py - 管理端控制器

管理端唯一的请求处理入口。所有 HTTP 方法收敛到 _dispatch：
  permissions.resolve() 判定 →
    health : 200 探针
    None   : 404（业务接口在管理端"不存在"）
    web    : services.forward 普通转发（上游完成管理员鉴权）
"""

from http.server import BaseHTTPRequestHandler

from . import permissions, services


class AdminSideHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'nginx'
    sys_version = ''

    def _dispatch(self):
        length = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(length) if length else None
        auth_header = self.headers.get('Authorization')
        kind, _ = permissions.resolve(self.command, self.path, auth_header)

        if kind == 'health':
            services.send_json(self, 200, {'status': 'ok'})
        elif kind is None:
            services.log.info('%s %s -> 404 (business blocked)', self.command, self.path)
            services.send_json(self, 404, {'message': 'Not Found'})
        else:  # web
            services.forward(self, self.command, self.path, body, self.headers)

    do_GET = _dispatch
    do_POST = _dispatch
    do_PUT = _dispatch
    do_DELETE = _dispatch
    do_PATCH = _dispatch
    do_OPTIONS = _dispatch

    def log_message(self, fmt, *args):
        pass  # 访问日志统一走 services.log（独立文件）
