#!/usr/bin/env python3
# 视觉回落端到端测试（本机 :3001 -> 真实百炼上游）
import base64, json, struct, subprocess, sys, urllib.request, zlib

GW = 'http://127.0.0.1:3001'
DB = '/Users/wjw/Desktop/token/new-api/one-api.db'

def sql(q):
    return subprocess.check_output(
        ['sqlite3', '-cmd', '.timeout 10000', DB, q], text=True).strip()

ALI = sql("SELECT key FROM tokens WHERE id=2")          # vip, 无 model_limits
CC = sql("SELECT key FROM tokens WHERE name='cc-claude'")  # vip, 限 claude 假名

def make_png():
    # 64x64 纯红 PNG
    raw = b''.join(b'\x00' + b'\xff\x00\x00' * 64 for _ in range(64))
    def chunk(t, d):
        c = t + d
        return struct.pack('>I', len(d)) + c + struct.pack('>I', zlib.crc32(c))
    ihdr = struct.pack('>IIBBBBB', 64, 64, 8, 2, 0, 0, 0)
    return base64.b64encode(
        b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
        + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')).decode()

IMG_B64 = make_png()
DATA_URL = 'data:image/png;base64,' + IMG_B64
PASS, FAIL = [], []

def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('  PASS ' if cond else '  FAIL ') + name + (f' | {detail}' if detail else ''))

def post(path, key, payload, stream=False):
    req = urllib.request.Request(GW + path, data=json.dumps(payload).encode(),
                                 headers={'Authorization': 'Bearer sk-' + key,
                                          'Content-Type': 'application/json'})
    try:
        resp = urllib.request.urlopen(req, timeout=120)
        raw = resp.read().decode('utf-8', 'replace')
        return resp.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')

def chat_payload(model, text_only=False, stream=False):
    if text_only:
        content = '只回复一个字:在'
    else:
        content = [
            {'type': 'image_url', 'image_url': {'url': DATA_URL}},
            {'type': 'text', 'text': '这张图的主要颜色是什么?用一个字回答'},
        ]
    p = {'model': model, 'messages': [{'role': 'user', 'content': content}],
         'max_tokens': 30}
    if stream:
        p['stream'] = True
    return p

print('== 1. vip无限模令牌 + 图片(chat/completions, 非流式) ==')
st, raw = post('/v1/chat/completions', ALI, chat_payload('gpt-6-astra'))
try:
    d = json.loads(raw)
    check('http200', st == 200, f'st={st}')
    check('响应model=假名', d.get('model') == 'gpt-6-astra', d.get('model'))
    txt = (d.get('choices') or [{}])[0].get('message', {}).get('content', '')
    check('回答含"红"', '红' in txt, txt[:40])
    check('无真实名泄漏', 'qwen' not in raw and 'glm' not in raw, '')
except Exception as e:
    check('JSON解析', False, f'{e}: {raw[:200]}')

print('== 2. 同上但流式 ==')
st, raw = post('/v1/chat/completions', ALI, chat_payload('gpt-6-astra', stream=True))
check('http200', st == 200, f'st={st}')
check('SSE块model=假名', '"model":"gpt-6-astra"' in raw.replace(' ', ''), '')
check('SSE无真实名', 'qwen-vl' not in raw and 'glm-5.2' not in raw, '')

print('== 3. 纯文本(回归: 仍走原映射 + model恢复假名) ==')
st, raw = post('/v1/chat/completions', ALI, chat_payload('gpt-6-astra', text_only=True))
d = json.loads(raw)
check('http200', st == 200, f'st={st}')
check('响应model=假名(原为glm-5.2泄漏)', d.get('model') == 'gpt-6-astra', d.get('model'))

print('== 4. 限模令牌(cc-claude) + 图片(应兜底重试→原生行为, 无真实名泄漏) ==')
st, raw = post('/v1/chat/completions', CC, {
    'model': 'claude-sonnet-5',
    'messages': [{'role': 'user', 'content': [
        {'type': 'image_url', 'image_url': {'url': DATA_URL}},
        {'type': 'text', 'text': '这是什么'}]}],
    'max_tokens': 30})
check('兜底为原生行为(200或模态报错)',
      st == 200 or 'modality' in raw.lower(), f'st={st}')
check('无真实名泄漏', 'qwen-vl' not in raw and '"model":"glm' not in raw.replace(' ', ''),
      raw.get('model') if isinstance(raw, dict) else '')

print('== 5. default组临时无限模令牌 + 图片 ==')
import secrets, string, time
tk = 'gwv' + ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(40))
now = int(time.time())
sql(f"INSERT INTO tokens (user_id, key, status, name, created_time, accessed_time,"
    f" expired_time, remain_quota, unlimited_quota, \"group\") VALUES "
    f"(1, '{tk}', 1, 'gw-vision-test', {now}, {now}, -1, 0, 1, 'default')")
try:
    st, raw = post('/v1/chat/completions', tk, chat_payload('gemini-3.8-flash'))
    d = json.loads(raw)
    check('http200', st == 200, f'st={st} {raw[:120]}')
    check('响应model=假名', d.get('model') == 'gemini-3.8-flash', d.get('model'))
finally:
    sql(f"DELETE FROM tokens WHERE key='{tk}'")

print('== 6. Gemini 协议 + inline_data 图片 ==')
st, raw = post('/v1beta/models/gemini-3.1-pro:generateContent', ALI, {
    'contents': [{'role': 'user', 'parts': [
        {'inline_data': {'mime_type': 'image/png', 'data': IMG_B64}},
        {'text': '这张图的主要颜色是什么?用一个字回答'}]}]})
check('http200', st == 200, f'st={st} {raw[:150]}')
check('无真实名泄漏', 'qwen-vl' not in raw, '')

print()
print(f'通过 {len(PASS)}/{len(PASS)+len(FAIL)}')
sys.exit(1 if FAIL else 0)
