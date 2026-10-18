#!/usr/bin/env python3
"""gateway/run.py - 双端隔离网关总装入口

分别装配两个完全独立的服务：
  用户端 :3001  —— user_side 包（路由/控制器/服务/权限自成一体）
  管理端 :3002  —— admin_side 包（路由/控制器/服务/权限自成一体）

两个服务各自持有独立的 ThreadingHTTPServer 实例与请求处理栈，
互不引用对方的任何模块（唯一的交集是 config.py 里的端口/凭据数据）。

替代原 codex_shim.py（其功能已完整并入 user_side/services.py）。
"""

import sys
import threading
from http.server import ThreadingHTTPServer

from user_side.controllers import UserSideHandler
from admin_side.controllers import AdminSideHandler
import config

import logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s')


def main():
    user_srv = ThreadingHTTPServer((config.USER_LISTEN_HOST, config.USER_LISTEN_PORT),
                                   UserSideHandler)
    admin_srv = ThreadingHTTPServer((config.ADMIN_LISTEN_HOST, config.ADMIN_LISTEN_PORT),
                                    AdminSideHandler)
    admin_srv.daemon_threads = True
    user_srv.daemon_threads = True

    t_admin = threading.Thread(target=admin_srv.serve_forever, daemon=True,
                               name='admin-side')
    t_admin.start()
    print(f'[gateway] admin  side listening on {config.ADMIN_LISTEN_HOST}:{config.ADMIN_LISTEN_PORT}', flush=True)
    print(f'[gateway] user   side listening on {config.USER_LISTEN_HOST}:{config.USER_LISTEN_PORT}', flush=True)
    print(f'[gateway] upstream -> {config.UPSTREAM_HOST}:{config.UPSTREAM_PORT}', flush=True)
    try:
        user_srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        admin_srv.shutdown()
        user_srv.shutdown()


if __name__ == '__main__':
    sys.exit(main())
