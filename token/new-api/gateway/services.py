"""gateway/admin_side/services.py - 管理端服务层

职责：把管理端请求普通转发到上游 new-api（不改写任何【请求】体——管理端
不需要也不允许身份伪装，看到的就是真实模型名/真实数据）。
唯一的【响应】改写：GET /api/status 的 server_address 钉为对外域名
（pin_server_address，供前端 CC Switch 等导入入口生成官网/端点）。

转发前剥离本网关的 Basic Auth 凭据头：避免上游 new-api 把
"Authorization: Basic ..." 误读为 API 令牌；上游真正的鉴权走会话
Cookie / New-Api-User 头 / Bearer 令牌，均原样透传。

本模块只被 admin_side/controllers.py 调用；user_side 有自己独立的
服务层，两边不共享转发实现。
"""

import http.client
import json
import logging
import os

import config

# ── 日志（管理端独立审计文件）────────────────────────────────────────
os.makedirs(os.path.dirname(config.ADMIN_LOG_FILE), exist_ok=True)
log = logging.getLogger('gateway.admin')
log.propagate = False
_h = logging.FileHandler(config.ADMIN_LOG_FILE)
_h.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
log.addHandler(_h)
log.setLevel(logging.INFO)


def pin_server_address(body, origin):
    """把 /api/status 响应里的 server_address 钉为本端对外域名。

    前端 CC Switch / Cherry Studio 等导入入口读 localStorage 里的
    status.server_address 生成"官网地址"与"API 端点"(endpoint=server_address+/v1)；
    该值缺失/为默认 localhost 时前端会把它缓存进 localStorage，导入配置即错。
    管理端钉为用户端公开域名（config.ADMIN_PUBLIC_ORIGIN，原因见 config 注释）：
    /v1 业务在本端 404，端点只有指用户端域名才调得通。
    解析失败或结构不符时原样返回（宁可放行也不弄坏接口）。
    """
    try:
        data = json.loads(body)
    except Exception:
        return body
    if isinstance(data, dict) and isinstance(data.get('data'), dict):
        data['data']['server_address'] = origin
        return json.dumps(data, ensure_ascii=False).encode('utf-8')
    return body


def forward(handler, method, path, body, headers):
    """普通转发（剥离 Basic 凭据头），支持 SSE 流式回传。"""
    fwd_headers = {k: v for k, v in headers.items()
                   if k.lower() not in ('host', 'content-length', 'connection',
                                        'transfer-encoding')}
    # 剥离网关自身的 Basic Auth 凭据（上游不认识它，且不该看到它）
    auth = fwd_headers.get('Authorization') or fwd_headers.get('authorization')
    if auth and auth.startswith('Basic '):
        fwd_headers.pop('Authorization', None)
        fwd_headers.pop('authorization', None)

    # /api/status：钉死 server_address 为对外域名（CC Switch 等导入入口的官网/端点来源）
    status_pin = method == 'GET' and path.split('?', 1)[0] == '/api/status'
    if status_pin:
        # 钉值需要明文 JSON：去掉 Accept-Encoding 让上游别 gzip
        fwd_headers.pop('Accept-Encoding', None)
        fwd_headers.pop('accept-encoding', None)

    conn = http.client.HTTPConnection(config.UPSTREAM_HOST, config.UPSTREAM_PORT,
                                      timeout=config.UPSTREAM_TIMEOUT)
    try:
        conn.request(method, path, body=body, headers=fwd_headers)
        resp = conn.getresponse()
    except Exception as e:
        log.error('upstream connect failed: %s %s %s', method, path, e)
        send_json(handler, 502, {'error': {'message': f'gateway upstream connect failed: {e}'}})
        return

    log.info('%s %s -> %s', method, path, resp.status)
    is_sse = 'text/event-stream' in (resp.getheader('Content-Type') or '')
    skip = ('connection', 'transfer-encoding', 'content-length', 'keep-alive')
    if status_pin:
        skip = skip + ('content-encoding',)
    handler.send_response(resp.status)
    for k, v in resp.getheaders():
        if k.lower() not in skip:
            handler.send_header(k, v)

    if is_sse:
        handler.send_header('Transfer-Encoding', 'chunked')
        handler.end_headers()
        try:
            while True:
                chunk = resp.read1(8192)
                if not chunk:
                    break
                handler.wfile.write(b'%x\r\n' % len(chunk) + chunk + b'\r\n')
                handler.wfile.flush()
            handler.wfile.write(b'0\r\n\r\n')
            handler.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
    else:
        data = resp.read()
        if status_pin:
            data = pin_server_address(data, config.ADMIN_PUBLIC_ORIGIN)
        handler.send_header('Content-Length', str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)
    conn.close()


def send_json(handler, status, obj):
    import json as _j
    msg = _j.dumps(obj).encode()
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json')
    handler.send_header('Content-Length', str(len(msg)))
    handler.end_headers()
    handler.wfile.write(msg)
