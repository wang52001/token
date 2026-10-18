#!/usr/bin/env python3
"""gateway/edge.py - 云上单端口入口（Koyeb 免费档只有一个公开端口）

按 Host 头把请求分流到两端各自的独立处理栈：
  Host == ADMIN_DOMAIN → admin_side（Basic Auth + 管理面，两道门不变）
  其余一切 Host        → user_side（对外售卖面）

安全原则：默认分支永远是用户端——管理面只在精确匹配管理域名时出现，
宁可错放用户端也不向未知 Host 暴露管理面。

本地开发仍用 run.py 双端口模式；本文件只在容器/云上使用。
"""

import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config  # noqa: F401  （两端 services 导入时读取同一配置）
from user_side.controllers import UserSideHandler
from admin_side.controllers import AdminSideHandler

USER_DOMAIN = os.environ.get('USER_DOMAIN', 'new-api.jdhsf.top').lower()
ADMIN_DOMAIN = os.environ.get('ADMIN_DOMAIN', 'new-api-admin.jdhsf.top').lower()
LISTEN_PORT = int(os.environ.get('PORT', '3001'))


class EdgeHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'nginx'      # 不向外界暴露网关实现
    sys_version = ''

    def _dispatch(self):
        host = (self.headers.get('Host') or '').split(':', 1)[0].lower()
        if host == ADMIN_DOMAIN:
            AdminSideHandler._dispatch(self)
        else:
            UserSideHandler._dispatch(self)

    do_GET = _dispatch
    do_POST = _dispatch
    do_PUT = _dispatch
    do_DELETE = _dispatch
    do_PATCH = _dispatch
    do_OPTIONS = _dispatch

    def log_message(self, fmt, *args):
        pass  # 访问日志统一走两端各自的 services.log


def main():
    srv = ThreadingHTTPServer(('0.0.0.0', LISTEN_PORT), EdgeHandler)
    srv.daemon_threads = True
    print(f'[edge] listening on 0.0.0.0:{LISTEN_PORT} '
          f'(user=* admin={ADMIN_DOMAIN})', flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.shutdown()


if __name__ == '__main__':
    sys.exit(main())
