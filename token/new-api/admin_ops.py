#!/usr/bin/env python3
"""new-api 管理 API 运维工具（线上/本机通用）：
用法:
  NEWAPI_ADMIN_PASS=... python3 admin_ops.py BASE_URL dry|run|status|rollback
  本机: python3 admin_ops.py http://127.0.0.1:3000 status（本机自动绕代理）
  线上: NEWAPI_ADMIN_PASS=... python3 admin_ops.py https://new-api-admin.jdhsf.top run
原用途（视觉回落配套三件套）:
1. 新建"阿里云百炼-视觉"渠道（models=qwen-vl-max,plus / group=default）
2. wjw 用户分组 -> vip
3. cc-* 主令牌 + 客-* 客户key 限模 += qwen-vl-max,qwen-vl-plus
用法: admin_ops.py BASE_URL dry|run|status|rollback
"""
import json, os, sys, urllib.request, urllib.error

BASE = sys.argv[1].rstrip('/')
CMD = sys.argv[2]
VISION = ['qwen-vl-max', 'qwen-vl-plus']

# 本机地址绕过代理（http_proxy 会造假 502），公网域名走系统代理（fake-ip DNS）
NO_PROXY = BASE.startswith('http://127.') or 'localhost' in BASE

def _opener():
    if NO_PROXY:
        return urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener()

def login():
    if not os.environ.get('NEWAPI_ADMIN_PASS'):
        print('请先设置管理员密码环境变量: NEWAPI_ADMIN_PASS=... python3 admin_ops.py ...')
        sys.exit(2)
    r = urllib.request.Request(BASE + '/api/user/login',
        data=json.dumps({'username': 'wjw', 'password': os.environ.get('NEWAPI_ADMIN_PASS', '')}).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    with _opener().open(r, timeout=20) as resp:
        return json.loads(resp.read().decode())['data']['access_token']

TOK = login()

def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method,
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + TOK})
    try:
        with _opener().open(r, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read().decode())
        except Exception: return e.code, None

def get_tokens():
    st, b = req('GET', '/api/token/?p=1&page_size=200')
    d = b['data']
    items = d['items'] if isinstance(d, dict) and 'items' in d else d
    return items

def need_vision(t):
    """需要加视觉限模的令牌：有限模的（cc-* 与 客-*，即 model_limits 非空）"""
    ml = (t.get('model_limits') or '').strip()
    if not ml:
        return False
    have = set(x.strip() for x in ml.split(',') if x.strip())
    return not set(VISION).issubset(have)

def append_vision(ml):
    have = [x.strip() for x in ml.split(',') if x.strip()]
    for v in VISION:
        if v not in have:
            have.append(v)
    return ','.join(have)

def get_self_user():
    st, b = req('GET', '/api/user/self')
    return b['data']

def admin_get_user(uid):
    st, b = req('GET', '/api/user/%d' % uid)
    return b['data'] if b and b.get('success') else None

def do_channel():
    key = open('/tmp/ch2.key').read().strip()
    payload = {
        'mode': 'single',
        'channel': {
            'type': 1,
            'name': '阿里云百炼-视觉',
            'key': key,
            'base_url': 'https://dashscope.aliyuncs.com/compatible-mode',
            'models': ','.join(VISION),
            'group': 'default',
            'status': 1,
            'priority': 0,
            'weight': 0,
            'auto_ban': 1,
            'test_model': 'qwen-vl-plus',
            'model_mapping': '',
            'other': '',
        }
    }
    return req('POST', '/api/channel/', payload)

def find_vision_channel():
    st, b = req('GET', '/api/channel/?p=1&page_size=100')
    d = b['data']
    items = d['items'] if isinstance(d, dict) and 'items' in d else d
    for c in items or []:
        if c['name'] == '阿里云百炼-视觉':
            return c
    return None

# ---------- status ----------
if CMD == 'status':
    me = get_self_user()
    print('== wjw: group=%s role=%s' % (me.get('group'), me.get('role')))
    u = admin_get_user(me['id'])
    if u: print('   admin view: group=%s' % u.get('group'))
    vc = find_vision_channel()
    print('== 视觉渠道:', (vc['id'], vc['name'], vc.get('group'), vc.get('status')) if vc else '不存在')
    ts = get_tokens()
    print('== 令牌 %d 个:' % len(ts))
    for t in ts:
        ml = (t.get('model_limits') or '').strip()
        has_v = all(v in ml for v in VISION)
        print('   id=%-3d %-12s limits=%s' % (t['id'], t['name'], ('含视觉✓' if ml and has_v else ('空' if not ml else '缺视觉 ✗')) if ml else '空'))
    sys.exit(0)

# ---------- dry run ----------
if CMD == 'dry':
    me = get_self_user()
    vc = find_vision_channel()
    print('计划:')
    print(' 1. 视觉渠道:', '已存在 id=%s 跳过' % vc['id'] if vc else '将创建（models=%s, group=default）' % ','.join(VISION))
    print(' 2. wjw 分组: 当前=%s -> %s' % (me.get('group'), 'vip（已是则跳过）'))
    n = 0
    for t in get_tokens():
        if need_vision(t):
            n += 1
            print('    令牌 id=%d %s 限模 %d 个模型 += 视觉' % (t['id'], t['name'], len([x for x in (t.get('model_limits') or '').split(',') if x])))
    print(' 3. 需加视觉限模的令牌: %d 个' % n)
    sys.exit(0)

# ---------- run ----------
if CMD == 'run':
    # 1. 视觉渠道
    vc = find_vision_channel()
    if vc:
        print('1. 视觉渠道已存在 id=%s，跳过' % vc['id'])
    else:
        st, r = do_channel()
        print('1. 创建视觉渠道 ->', st, json.dumps(r, ensure_ascii=False)[:200])
        assert r and r.get('success'), '创建失败'
        vc = find_vision_channel()
        print('   新渠道 id=%s group=%s status=%s' % (vc['id'], vc.get('group'), vc.get('status')))
    # 2. wjw -> vip
    me = get_self_user()
    if me.get('group') == 'vip':
        print('2. wjw 已是 vip，跳过')
    else:
        st, r = req('PUT', '/api/user/', {'id': me['id'], 'username': me['username'], 'group': 'vip'})
        print('2. wjw -> vip:', st, json.dumps(r, ensure_ascii=False)[:200])
        assert r and r.get('success'), '改分组失败'
    # 3. 令牌限模
    ok = fail = 0
    for t in get_tokens():
        ml = (t.get('model_limits') or '').strip()
        if not ml or not need_vision(t):
            continue
        new_ml = append_vision(ml)
        payload = {
            'id': t['id'], 'name': t['name'], 'expired_time': t.get('expired_time', -1),
            'remain_quota': t.get('remain_quota', 0), 'unlimited_quota': bool(t.get('unlimited_quota')),
            'model_limits_enabled': bool(t.get('model_limits_enabled')),
            'model_limits': new_ml, 'group': t.get('group') or 'default',
            'allow_ips': t.get('allow_ips'), 'cross_group_retry': bool(t.get('cross_group_retry')),
        }
        st, r = req('PUT', '/api/token/', payload)
        good = r and r.get('success')
        ok += 1 if good else 0
        fail += 0 if good else 1
        print('3. 令牌 id=%-3d %-12s -> %s' % (t['id'], t['name'], '✓' if good else '✗ ' + json.dumps(r, ensure_ascii=False)[:150]))
    print('完成: 成功 %d / 失败 %d' % (ok, fail))
    sys.exit(0)

# ---------- rollback（删除视觉渠道，用于本机演练清理）----------
if CMD == 'rollback':
    vc = find_vision_channel()
    if not vc:
        print('无视觉渠道'); sys.exit(0)
    st, r = req('DELETE', '/api/channel/%d' % vc['id'])
    print('删除视觉渠道 id=%s ->' % vc['id'], st, json.dumps(r, ensure_ascii=False)[:200])
    sys.exit(0)

print('unknown cmd')
