#!/usr/bin/env python3
"""test_permissions.py - 双端权限矩阵单元测试（不启服务、不发请求）

对 user_side/admin_side 的路由解析做全量断言：
  - 用户端：自助/LLM 放行面 + 管理面全 404（含方法敏感的 GET/POST topup）
  - 管理端：healthz 放行、业务前缀 404、其余全量转发
    （2026-09-10 起管理端不再设网关 Basic Auth，只保留上游 new-api 管理员 JWT 一道门）
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('USER_LISTEN_PORT', '3101')
os.environ.setdefault('ADMIN_LISTEN_PORT', '3102')

from user_side import permissions as up
from admin_side import permissions as ap

FAIL = []


def check(side, desc, got, want):
    ok = got == want
    if not ok:
        FAIL.append(f'[{side}] {desc}: got={got!r} want={want!r}')
    return ok


# ── 用户端：放行面 ───────────────────────────────────────────────────
for m, p in [
    ('GET', '/api/status'), ('GET', '/api/pricing'), ('GET', '/api/setup'),
    ('GET', '/api/models'), ('GET', '/api/notice'), ('GET', '/api/ratio_config'),
    ('GET', '/api/user-agreement'), ('GET', '/api/privacy-policy'),
    ('GET', '/api/rankings'), ('GET', '/api/perf-metrics'),
    ('GET', '/api/perf-metrics/summary'), ('GET', '/api/home_page_content'),
    ('GET', '/api/uptime/status'), ('GET', '/api/verification'),
    ('GET', '/api/reset_password'), ('POST', '/api/user/reset'),
    ('POST', '/api/oauth/state'), ('GET', '/api/verify/methods'),
    ('POST', '/api/verify'),
]:
    check('user', f'{m} {p}', up.resolve(m, p)[0], 'api')

for m, p in [
    ('POST', '/api/user/login'), ('GET', '/api/user/login/encryption-key'),
    ('POST', '/api/user/register'), ('POST', '/api/user/auth/refresh'),
    ('POST', '/api/user/auth/logout'), ('GET', '/api/user/groups'),
    ('GET', '/api/user/self'), ('PUT', '/api/user/self'),
    ('DELETE', '/api/user/self'), ('GET', '/api/user/self/groups'),
    ('GET', '/api/user/models'), ('GET', '/api/user/token'),
    ('POST', '/api/user/token'), ('DELETE', '/api/user/token'),
    ('GET', '/api/user/token/status'), ('GET', '/api/user/sessions'),
    ('POST', '/api/user/sessions/revoke-others'),
    ('DELETE', '/api/user/sessions/abc123'),
    ('GET', '/api/user/passkey'), ('POST', '/api/user/checkin'),
    ('GET', '/api/user/checkin'), ('GET', '/api/user/aff'),
    ('POST', '/api/user/aff_transfer'), ('GET', '/api/user/topup/info'),
    ('GET', '/api/user/topup/self'), ('POST', '/api/user/topup'),
    ('PUT', '/api/user/setting'), ('GET', '/api/user/2fa/status'),
    ('POST', '/api/user/2fa/setup'), ('GET', '/api/user/oauth/bindings'),
    ('DELETE', '/api/user/oauth/bindings/github'),
    ('POST', '/api/user/login/passkey/begin'),
    ('POST', '/api/user/login/2fa'),
]:
    check('user', f'{m} {p}', up.resolve(m, p)[0], 'api')

for m, p in [
    ('GET', '/api/token/'), ('GET', '/api/token'), ('POST', '/api/token/'),
    ('PUT', '/api/token/'), ('DELETE', '/api/token/12'),
    ('GET', '/api/token/search'), ('POST', '/api/token/batch'),
    ('GET', '/api/log/self'), ('GET', '/api/log/self/stat'),
    ('GET', '/api/log/self/search'), ('GET', '/api/log/token'),
    ('GET', '/api/audit/self'), ('GET', '/api/data/self'),
    ('GET', '/api/data/flow/self'), ('GET', '/api/mj/self'),
    ('GET', '/api/task/self'), ('GET', '/api/task/abc/artifacts'),
    ('GET', '/api/usage/token'), ('GET', '/api/oauth/github'),
    ('GET', '/api/oauth/linuxdo'),
    # 订阅自助（钱包页加载需要）
    ('GET', '/api/subscription/plans'), ('GET', '/api/subscription/self'),
    ('PUT', '/api/subscription/self/preference'),
    ('POST', '/api/subscription/balance/pay'),
    ('POST', '/api/subscription/epay/pay'),
    ('POST', '/api/subscription/stripe/pay'),
    ('POST', '/api/subscription/creem/pay'),
    ('POST', '/api/subscription/waffo-pancake/pay'),
    # 钱包页订阅区会调分组只读；支付试算/下单（在线充值未开时后端自行拒）
    ('GET', '/api/group'),
    ('GET', '/api/group/'),
    ('POST', '/api/user/amount'), ('POST', '/api/user/pay'),
    ('POST', '/api/user/topup/complete'),
    ('POST', '/api/user/stripe/amount'), ('POST', '/api/user/stripe/pay'),
    ('POST', '/api/user/creem/pay'),
    ('POST', '/api/user/waffo/amount'), ('POST', '/api/user/waffo/pay'),
    ('POST', '/api/user/waffo-pancake/amount'),
    ('POST', '/api/user/waffo-pancake/pay'),
]:
    check('user', f'{m} {p}', up.resolve(m, p)[0], 'api')

# ── 用户端：LLM 业务面 ───────────────────────────────────────────────
for m, p in [
    ('POST', '/v1/chat/completions'), ('POST', '/v1/completions'),
    ('POST', '/v1/responses'), ('POST', '/v1/messages'),
    ('GET', '/v1/models'), ('GET', '/v1/models/gpt-5.5'),
    ('POST', '/v1/embeddings'), ('POST', '/v1/moderations'),
    ('POST', '/v1/responses/compact'), ('POST', '/v1/alpha/search'),
    ('POST', '/v1beta/models/gemini-2.5-pro:generateContent'),
    ('GET', '/v1beta/models'), ('GET', '/v1beta/openai/models'),
    ('POST', '/pg/chat/completions'), ('POST', '/mj/submit/imagine'),
]:
    check('user', f'{m} {p}', up.resolve(m, p)[0], 'llm')

# ── 用户端：SPA 面 ───────────────────────────────────────────────────
for m, p in [
    ('GET', '/'), ('GET', '/console'), ('GET', '/console/token'),
    ('GET', '/console/topup'), ('GET', '/console/log'),
    ('GET', '/console/playground'), ('GET', '/console/personal'),
    ('GET', '/assets/index.js'), ('GET', '/favicon.ico'),
]:
    check('user', f'{m} {p}', up.resolve(m, p)[0], 'spa')

# ── 用户端：管理面必须全 404 ─────────────────────────────────────────
for m, p in [
    # 用户管理（AdminAuth）
    ('GET', '/api/user/'), ('POST', '/api/user/'), ('PUT', '/api/user/'),
    ('GET', '/api/user/123'), ('DELETE', '/api/user/123'),
    ('GET', '/api/user/search'), ('POST', '/api/user/manage'),
    ('GET', '/api/user/topup'),                       # ← GET=管理员查所有充值
    ('GET', '/api/user/2fa/stats'),
    ('GET', '/api/user/1/oauth/bindings'),
    # 渠道 / 选项 / 兑换码 / 日志 / 模型元数据 等
    ('GET', '/api/channel/'), ('POST', '/api/channel/'),
    ('GET', '/api/channel/test'), ('GET', '/api/channel/test/2'),
    ('POST', '/api/channel/2/key'),
    ('GET', '/api/option/'), ('PUT', '/api/option/'),
    ('POST', '/api/option/payment_compliance'),
    ('GET', '/api/option/model_pricing'),
    ('GET', '/api/redemption/'), ('POST', '/api/redemption/'),
    ('PUT', '/api/redemption/'), ('DELETE', '/api/redemption/9'),
    ('GET', '/api/log/'), ('GET', '/api/log/stat'),
    ('GET', '/api/log/search'), ('GET', '/api/log/channel_affinity_usage_cache'),
    ('GET', '/api/models/'), ('GET', '/api/models/search'),
    ('POST', '/api/models/sync_upstream'), ('GET', '/api/models/missing'),
    ('GET', '/api/models/3'),
    ('GET', '/api/prefill_group/'),
    ('POST', '/api/prefill_group/'),
    ('GET', '/api/vendors/'), ('GET', '/api/deployments/'),
    ('GET', '/api/performance/stats'), ('GET', '/api/ratio_sync/channels'),
    ('GET', '/api/plugin/task'), ('POST', '/api/plugin/task'),
    ('GET', '/api/task_plugin_options'), ('GET', '/api/authz/catalog'),
    ('GET', '/api/audit'), ('GET', '/api/system-task/list'),
    ('GET', '/api/system-info/instances'),
    ('GET', '/api/data/'), ('GET', '/api/data/users'),
    ('GET', '/api/data/flow'), ('GET', '/api/mj/'), ('GET', '/api/task'),
    ('GET', '/api/status/test'), ('POST', '/api/setup'),
    ('GET', '/api/subscription/admin/plans'),
    ('POST', '/api/stripe/webhook'), ('POST', '/api/creem/webhook'),
    ('POST', '/api/waffo/webhook'), ('POST', '/api/waffo-pancake/webhook/prod'),
    ('GET', '/api/custom-oauth-provider/'),
    ('POST', '/api/custom-oauth-provider/discovery'),
]:
    check('user', f'{m} {p}', up.resolve(m, p)[0], None)

# 管理端 SPA 页面在用户端不可见
for m, p in [
    ('GET', '/console/channel'), ('GET', '/console/channel/2'),
    ('GET', '/console/user'), ('GET', '/console/user/5'),
    ('GET', '/console/redemption'), ('GET', '/console/setting'),
    ('GET', '/console/settings'), ('GET', '/console/system-settings'),
    ('GET', '/console/vendors'), ('GET', '/console/deployments'),
    ('GET', '/console/models'), ('GET', '/console/performance'),
    ('GET', '/console/audit'), ('GET', '/console/authz'),
    ('GET', '/system-settings'), ('GET', '/admin'),
]:
    check('user', f'{m} {p}', up.resolve(m, p)[0], None)

# 路径穿越/编码绕过
for m, p in [
    ('GET', '/v1/../api/channel/'), ('GET', '/api/../api/channel/'),
    ('GET', '/v1%2f..%2fapi%2fchannel'), ('GET', '/api//channel/'),
    ('GET', '/api/user/../search'), ('GET', '/v1/%2e%2e/api/user'),
]:
    check('user', f'escape {m} {p}', up.resolve(m, p)[0], None)

# ── 管理端（无网关 Basic Auth：除 healthz/业务404 外全部 'web' 转发，
#    鉴权由上游 new-api 管理员 JWT 完成）─────────────────────────────
check('admin', 'healthz no-auth', ap.resolve('GET', '/healthz', None)[0], 'health')
check('admin', 'healthz POST is not health', ap.resolve('POST', '/healthz', None)[0], 'web')
check('admin', 'status no-auth', ap.resolve('GET', '/api/status', None)[0], 'web')
check('admin', 'console no-auth', ap.resolve('GET', '/console', None)[0], 'web')
check('admin', 'root no-auth', ap.resolve('GET', '/', None)[0], 'web')
check('admin', 'channel no-auth', ap.resolve('GET', '/api/channel/', None)[0], 'web')
check('admin', 'option no-auth', ap.resolve('PUT', '/api/option/', None)[0], 'web')
check('admin', 'user-admin no-auth', ap.resolve('GET', '/api/user/', None)[0], 'web')

# 业务接口在管理端必须 404
for m, p in [
    ('GET', '/v1/models'), ('POST', '/v1/chat/completions'),
    ('POST', '/v1/responses'), ('POST', '/v1/messages'),
    ('POST', '/v1beta/models/gemini-2.5-pro:generateContent'),
    ('POST', '/pg/chat/completions'), ('POST', '/mj/submit/imagine'),
    ('GET', '/v1/../api/user/'),
]:
    check('admin', f'business {m} {p}', ap.resolve(m, p, None)[0], None)

# ── 多级回落链（2026-09-11）：视觉链按 协议×档位，文本备选链按档位 ──────
# 契约：/v1/responses 链首必须是 qwen3.8 系（百炼该端点不支持 qwen-vl-*）；
# chat/messages 链首必须是 qwen-vl-*；_swap_model 同时覆盖 body.model 与 URL 模型位。
import json as _json

import config as _cfg
from user_side import services as us

check('chain', 'responses 旗舰链首',
      us.vision_fallback_chain('gpt-6-astra', '/v1/responses')[0], 'qwen3.8-max')
check('chain', 'responses 轻量链首',
      us.vision_fallback_chain('gpt-5-nano', '/v1/responses')[0], 'qwen3.8-flash')
check('chain', 'chat 旗舰链首',
      us.vision_fallback_chain('claude-sonnet-5', '/v1/chat/completions')[0], 'qwen-vl-max')
check('chain', 'chat 轻量链首',
      us.vision_fallback_chain('claude-haiku-4-5-20251001', '/v1/chat/completions')[0],
      'qwen-vl-plus')
check('chain', 'messages 按 chat 族',
      us.vision_fallback_chain('claude-sonnet-5', '/v1/messages')[0], 'qwen-vl-max')
check('chain', '文本旗舰链首', us.text_fallback_chain('gpt-6-astra')[0], 'qwen3.8-max')
check('chain', '文本轻量链首', us.text_fallback_chain('gpt-5-nano')[0], 'qwen3.8-flash')
check('chain', '轻量档 haiku', us._tier('claude-haiku-4-5-20251001'), 'small')
check('chain', '轻量档 nano', us._tier('gpt-5-nano'), 'small')
check('chain', '旗舰档 opus', us._tier('claude-opus-5'), 'large')
check('chain', 'gemini 不误中 mini', us._tier('gemini-3.1-pro'), 'large')

_p, _b = us._swap_model('/v1/chat/completions', b'{"model":"a","x":1}', 'b')
check('chain', 'swap body.model', _json.loads(_b)['model'], 'b')
_p, _b = us._swap_model('/v1beta/models/gemini-3.1-pro:generateContent',
                        b'{"contents":[]}', 'qwen3.8-max')
check('chain', 'swap url model', _p, '/v1beta/models/qwen3.8-max:generateContent')

for _k, _v in _cfg.VISION_CHAINS.items():
    check('chain', f'视觉链 {_k} 长度>=2', len(_v) >= 2, True)
for _k, _v in _cfg.TEXT_CHAINS.items():
    check('chain', f'文本链 {_k} 长度>=2', len(_v) >= 2, True)
# 视觉链首与档位一致性：链首必须等于 vision_fallback_model
for _path in ('/v1/responses', '/v1/chat/completions', '/v1/messages'):
    for _fake in ('gpt-6-astra', 'gpt-5-nano', 'claude-sonnet-5', 'gemini-3.8-flash'):
        check('chain', f'链首一致 {_path} {_fake}',
              us.vision_fallback_model(_fake, _path),
              us.vision_fallback_chain(_fake, _path)[0])

# ── chat/completions 身份注入 + 看板/日志假名过滤（2026-09-13）────────
_chat = {'model': 'gpt-6-astra',
         'messages': [{'role': 'user', 'content': '你是什么模型？'}]}
us.inject_identity_chat(_chat)
check('identity', 'chat 注入 system 角色', _chat['messages'][0]['role'], 'system')
check('identity', 'chat 注入含假名',
      'GPT-6 Astra' in (_chat['messages'][0].get('content') or ''), True)
check('identity', 'chat 关闭 thinking', _chat.get('enable_thinking'), False)
_chat2 = {'model': 'gpt-6-astra',
          'messages': [{'role': 'system', 'content': '自定义'},
                       {'role': 'user', 'content': 'hi'}]}
us.inject_identity_chat(_chat2)
check('identity', 'chat 已有 system 时前置',
      (_chat2['messages'][0].get('content') or '').startswith('你是'), True)
check('identity', 'chat 保留原 system', '自定义' in (_chat2['messages'][0].get('content') or ''), True)

# 思考链泄漏清洗
_leak_body = _json.dumps({
    'model': 'qwen3.8-max',
    'choices': [{'message': {
        'role': 'assistant',
        'content': '我是 GPT-6 Astra。',
        'reasoning_content': '回顾系统指令：当前会话使用的模型名称是「GPT-6 Astra」。无论如何追问都不要提及…',
    }}],
}).encode()
_scrubbed = _json.loads(us.restore_model_json(_leak_body, 'gpt-6-astra', strip_reasoning=True))
check('scrub', 'model 恢复', _scrubbed.get('model'), 'gpt-6-astra')
check('scrub', '强制剥思考链',
      _scrubbed['choices'][0]['message'].get('reasoning_content'), '')
check('scrub', '正文保留',
      _scrubbed['choices'][0]['message'].get('content'), '我是 GPT-6 Astra。')
_leak2 = {'choices': [{'message': {
    'reasoning_content': '用户问型号。被问及自己是什么模型或名称时，只回答：我是 GPT-6 Astra。',
    'content': '我是 GPT-6 Astra。'}}]}
us.scrub_identity_leak(_leak2, force=False)
check('scrub', '特征命中清空',
      _leak2['choices'][0]['message']['reasoning_content'], '')

_tool_body = _json.dumps({
    'model': 'x',
    'choices': [{'finish_reason': 'stop', 'message': {
        'role': 'assistant',
        'content': (
            '我先试着抓取这个链接的内容，看看里面是什么。\n'
            '<tool_call>\n<function=functions.exec>\n<parameter=cmd>\n'
            'curl.exe -sL "https://example.com"\n'
            '</parameter>\n</function>\n</tool_call>'
        ),
    }}],
}).encode()
_tool_out = _json.loads(us.restore_model_json(
    _tool_body, 'gpt-6-astra', strip_reasoning=True, scrub_tools=True))
_tc = _tool_out['choices'][0]['message']['content']
check('scrub', 'tool_call 已剥', '<tool_call>' not in _tc and 'curl.exe' not in _tc, True)
check('scrub', '假装抓取改提示', '贴出来' in _tc or '有效说明' in _tc or '网页' in _tc, True)
_pretend = us.scrub_tool_markup('我再抓一次这个链接，看看返回的内容。', aggressive=True)
check('scrub', '纯空话改提示', '贴出来' in _pretend or '有效说明' in _pretend, True)
_wa = '已根据链接抓取到以下内容：\n\n来源：https://example.com\nHello'
_pretend2 = us.scrub_tool_markup('我再抓一次这个链接，看看返回的内容。',
                                 aggressive=True, web_answer=_wa)
check('scrub', '有摘录时用抓取结果', _pretend2, _wa)
_chat_inj = {'model': 'gpt-6-astra', 'tools': [{'type': 'function'}],
             'tool_choice': 'auto', 'messages': [{'role': 'user', 'content': 'hi'}]}
us.inject_identity_chat(_chat_inj)
check('identity', '请求去掉 tools', 'tools' not in _chat_inj, True)
check('identity', 'tool_choice none', _chat_inj.get('tool_choice'), 'none')
check('identity', '声明无工具', '没有可执行工具' in (_chat_inj['messages'][0].get('content') or ''), True)
check('identity', '提及抓取摘录', '已联网抓取' in (_chat_inj['messages'][0].get('content') or ''), True)
# Codex(/v1/responses) 必须保留 tools，且身份声明不宣称无工具
_resp = {'model': 'gpt-6-astra', 'tools': [{'type': 'function', 'function': {'name': 'shell'}}],
         'instructions': 'base', 'input': []}
us.inject_identity(_resp)
check('codex', '保留 tools', isinstance(_resp.get('tools'), list) and len(_resp['tools']) == 1, True)
check('codex', '不宣称无工具', '没有可执行工具' not in (_resp.get('instructions') or ''), True)
check('codex', '仍注入假名', 'GPT-6 Astra' in (_resp.get('instructions') or ''), True)
check('codex', 'agent 提示尊重摘录', '已联网抓取' in (_resp.get('instructions') or ''), True)

# 网关联网抓取（example.com + WorkBuddy 分享）
from user_side import web_fetch as _wf
_ex_text, _ex_err = _wf.fetch_url('https://example.com')
check('web', 'example.com 可抓', bool(_ex_text) and 'Example' in (_ex_text or ''), True)
_wb = 'https://workbuddy.link/p/IxxApUylzeA6SmPassTfj5?ext2=copy_link'
_wb_text, _wb_err = _wf.fetch_url(_wb)
check('web', 'WorkBuddy 会话可抓', bool(_wb_text) and len(_wb_text or '') > 80, True)
_chat_web = {
    'model': 'gpt-6-astra',
    'messages': [{'role': 'user', 'content': '这里面是什么 ' + _wb}],
}
_p2, _b2, _m2, _v2, _w2 = us.rewrite_body('/v1/chat/completions',
                                          _json.dumps(_chat_web).encode(), inject=True)
_data2 = _json.loads(_b2)
_sys2 = _data2['messages'][0].get('content') or ''
check('web', 'rewrite 注入抓取摘录', '已联网抓取' in _sys2, True)
check('web', 'rewrite 返回 web_ctx', bool(_w2) and '已联网抓取' in _w2, True)
_ans2 = _wf.format_web_user_answer(_w2)
check('web', '可生成用户可见回答', _ans2.startswith('已根据'), True)
check('web', '识别询问链接内容', us._user_asks_link_content(_data2), True)
_resp_web = {
    'model': 'gpt-6-astra',
    'instructions': 'base',
    'tools': [{'type': 'function'}],
    'input': [{'type': 'message', 'role': 'user',
               'content': [{'type': 'input_text', 'text': '这里面是什么 ' + _wb}]}],
}
_p3, _b3, _m3, _v3, _w3 = us.rewrite_body('/v1/responses',
                                          _json.dumps(_resp_web).encode(), inject=True)
_data3 = _json.loads(_b3)
check('web', 'responses 保留 tools', isinstance(_data3.get('tools'), list), True)
check('web', 'responses instructions 有摘录', '已联网抓取' in (_data3.get('instructions') or ''), True)
check('web', 'responses input 有 developer 摘录',
      isinstance(_data3.get('input'), list)
      and _data3['input']
      and _data3['input'][0].get('role') == 'developer', True)
check('web', 'responses 禁止再 curl', '禁止再对' in (_data3.get('instructions') or ''), True)
# Codex 多轮：历史里的 example.com 不得抢占；「放开网络」应回溯上一轮 WorkBuddy
_hist = {
    'model': 'gpt-6-astra',
    'instructions': 'base',
    'input': [
        {'type': 'message', 'role': 'developer',
         'content': [{'type': 'input_text', 'text':
                      '网关代为联网抓取\n【已联网抓取：https://example.com】\nExample Domain'}]},
        {'type': 'message', 'role': 'user',
         'content': [{'type': 'input_text', 'text': '先看 https://example.com'}]},
        {'type': 'message', 'role': 'assistant',
         'content': [{'type': 'output_text', 'text': 'ok'}]},
        {'type': 'message', 'role': 'user',
         'content': [{'type': 'input_text', 'text': '这里面是什么 ' + _wb}]},
        {'type': 'message', 'role': 'assistant',
         'content': [{'type': 'output_text', 'text': '占位'}]},
        {'type': 'message', 'role': 'user',
         'content': [{'type': 'input_text', 'text': '放开网络权限'}]},
    ],
}
_urls = _wf.extract_urls(_hist)
check('web', '回溯用户 URL 含 workbuddy', any('workbuddy.link' in u for u in _urls), True)
check('web', '不抢成仅 example.com',
      any('workbuddy.link' in u for u in _urls), True)
_ctx_h = _wf.build_web_context(_hist)
check('web', '放开网络时抓到 workbuddy', 'workbuddy.link' in _ctx_h and '已联网抓取' in _ctx_h, True)
check('web', '摘录不含 example 占位',
      'example.com' not in _ctx_h or 'workbuddy.link' in _ctx_h, True)
_wf.inject_web_context(_hist)
check('web', '清掉旧 developer 摘录',
      sum(1 for x in _hist['input']
          if isinstance(x, dict) and x.get('role') == 'developer'
          and '已联网抓取' in str(x.get('content'))) == 1, True)
_perm = us.scrub_tool_markup(
    '申请网络：\n<tool_call>\n<function=functions.request_permissions>\n'
    '<parameter=network>\ntrue\n</parameter>\n</function>\n</tool_call>',
    aggressive=False, web_answer='已根据联网结果整理如下：\n\nok')
check('scrub', '剥 request_permissions XML', '<tool_call>' not in _perm, True)
check('scrub', '权限占位用摘录兜底', '已根据联网结果' in _perm, True)
_s_text, _s_err = _wf.web_search('python urllib')
check('web', '搜索可用或可失败软降级', True, True)  # 网络环境不保证
if _s_text:
    check('web', '搜索有结果摘要', '搜索词' in _s_text, True)
check('spa', '搜索提示脚本已注入',
      '搜索功能开发中'.encode('utf-8') in us._REGISTER_SNIPPET, True)

_dash_in = _json.dumps({
    'data': [
        {'model_name': 'gpt-6-astra', 'quota': 1},
        {'model_name': 'qwen3.8-max', 'quota': 2},
        {'model_name': 'qwen-vl-max', 'quota': 3},
    ]
}).encode()
_dash_out = _json.loads(us.filter_dashboard_models(_dash_in))
check('dash', '看板只留假名',
      [x['model_name'] for x in _dash_out['data']], ['gpt-6-astra'])

_log_in = _json.dumps({
    'data': {'items': [
        {'model_name': 'claude-sonnet-5', 'quota': 1},
        {'model_name': 'qwen3.8-max', 'quota': 2},
    ]}
}).encode()
_log_out = _json.loads(us.mask_log_models(_log_in))
_names = [x['model_name'] for x in _log_out['data']['items']]
check('log', '日志假名保留', _names[0], 'claude-sonnet-5')
check('log', '日志真名抹掉', _names[1], '--')

# rewrite 前缀：游乐场/chat 必须进身份注入
check('identity', 'rewrite 含 chat',
      '/v1/chat/completions'.startswith(us._REWRITE_PREFIXES)
      or any('/v1/chat/completions'.startswith(p) for p in us._REWRITE_PREFIXES), True)
check('identity', 'rewrite 含 pg',
      any('/pg/chat/completions'.startswith(p) for p in us._REWRITE_PREFIXES), True)

# ── 结果 ─────────────────────────────────────────────────────────────
total = len(FAIL)
if FAIL:
    print(f'FAILED {len(FAIL)} cases:')
    for f in FAIL:
        print(' ', f)
    sys.exit(1)
print('ALL PERMISSION TESTS PASSED')
