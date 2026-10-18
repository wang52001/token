# -*- coding: utf-8 -*-
"""网关侧联网抓取：把用户消息里的 URL 抓成正文摘录，注入请求上下文。

解决：纯聊天无 tools、以及 Codex curl 只能下到 SPA 空壳（如 WorkBuddy）的问题。
抓取在网关进程内完成，不向客户端暴露 tool_call。
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

log = logging.getLogger('gateway.user')

_URL_RE = re.compile(r'https?://[^\s<>\"\'）\]\u3001\u3002，。！？]+', re.I)
_WB_SHARE_RE = re.compile(r'workbuddy\.link/p/([^/?#]+)', re.I)
_MAX_URLS = 2
_MAX_CHARS = 14000
_TIMEOUT = 25
_MAX_BYTES = 6_000_000  # WorkBuddy conversation-data.json 可达数 MB
_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._chunks = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript') and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._skip:
            return
        t = data.strip()
        if t:
            self._chunks.append(t)

    def text(self):
        return '\n'.join(self._chunks)


def _http_get(url, timeout=_TIMEOUT):
    req = urllib.request.Request(url, headers={
        'User-Agent': _UA,
        'Accept': 'text/html,application/json,*/*;q=0.8',
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read(_MAX_BYTES + 1)
        ctype = (resp.headers.get('Content-Type') or '').lower()
    if len(raw) > _MAX_BYTES:
        raw = raw[:_MAX_BYTES]
    return raw, ctype


def _html_to_text(raw: bytes) -> str:
    try:
        html = raw.decode('utf-8', 'replace')
    except Exception:
        html = raw.decode('latin-1', 'replace')
    p = _TextExtractor()
    try:
        p.feed(html)
        p.close()
    except Exception:
        return re.sub(r'<[^>]+>', ' ', html)
    return p.text()


def _summarize_workbuddy_conversation(data: dict) -> str:
    """把 conversation-data.json 压成可读摘要。"""
    lines = []
    name = data.get('name') or data.get('shareCode') or ''
    if name:
        lines.append('分享标题：' + str(name))
    msgs = data.get('messages') or []
    lines.append('消息条数：%d' % len(msgs))
    # 取用户/助手文本片段
    n = 0
    for m in msgs:
        if n >= 12:
            lines.append('…（其余消息已省略）')
            break
        content = m.get('content')
        texts = []
        if isinstance(content, str):
            texts = [content]
        elif isinstance(content, list):
            for part in content:
                if not isinstance(part, dict):
                    continue
                t = part.get('type')
                if t == 'text' and part.get('text'):
                    texts.append(str(part['text']))
                elif t == 'reasoning' and part.get('text'):
                    # 跳过长思考，只留短提示
                    continue
        if not texts:
            continue
        blob = '\n'.join(texts).strip()
        if not blob or blob.startswith('{"'):
            continue
        # 粗略角色
        role = '消息'
        low = blob[:80]
        if '【WorkBuddy】' in blob or blob.startswith('http'):
            role = '用户'
        elif 'tool-call' in blob or '"tool"' in blob:
            role = '助手(工具)'
            continue
        lines.append('[%s] %s' % (role, blob[:800]))
        n += 1
    return '\n'.join(lines)


def _parse_json_bytes(raw):
    """完整 JSON；若被截断则尽量从碎片里抽文本。"""
    text = raw.decode('utf-8', 'replace')
    try:
        return json.loads(text)
    except Exception:
        # 截断兜底：抽出若干 "text":"..." 片段
        snippets = []
        for m in re.finditer(r'"text"\s*:\s*"((?:\\.|[^"\\]){20,800})"', text):
            try:
                snippets.append(json.loads('"%s"' % m.group(1)))
            except Exception:
                snippets.append(m.group(1)[:400])
            if len(snippets) >= 16:
                break
        if snippets:
            return {'_partial': True, 'name': '', 'messages': [
                {'content': [{'type': 'text', 'text': s}]} for s in snippets
            ]}
        raise


def _fetch_workbuddy(share_id):
    """优先拉 conversation-data.json；失败再退回 HTML 正文。"""
    # 常见静态产物路径（与 WorkBuddy 分享页 bootstrap 一致）
    candidates = [
        'https://workbuddy-space-static.codebuddy.work/page/%s/0/conversation-data.json' % share_id,
        'https://workbuddy-space-static.codebuddy.work/page/%s/1/conversation-data.json' % share_id,
    ]
    for u in candidates:
        try:
            raw, ctype = _http_get(u)
            if b'{' not in raw[:20] and 'json' not in (ctype or ''):
                continue
            data = _parse_json_bytes(raw)
            if isinstance(data, dict) and (data.get('messages') is not None):
                text = _summarize_workbuddy_conversation(data)
                log.info('web_fetch workbuddy ok share=%s chars=%d', share_id, len(text))
                return text, None
        except Exception as e:
            log.info('web_fetch workbuddy miss %s: %s', u, e)
    # HTML bootstrap 里可能有 artifact url
    page = 'https://workbuddy.link/p/%s' % share_id
    try:
        raw, _ = _http_get(page)
        html = raw.decode('utf-8', 'replace')
        m = re.search(r'https://workbuddy-space-static[^\"\']+conversation-data\.json', html)
        if m:
            raw2, _ = _http_get(m.group(0))
            data = _parse_json_bytes(raw2)
            return _summarize_workbuddy_conversation(data), None
        text = _html_to_text(raw)
        if len(text) > 40:
            return text[:_MAX_CHARS], None
        return None, 'WorkBuddy 页面为前端渲染，未拿到会话数据'
    except Exception as e:
        return None, str(e)


def fetch_url(url):
    """返回 (text, error)。"""
    url = url.rstrip(')。.,，、；;]')
    m = _WB_SHARE_RE.search(url)
    if m:
        return _fetch_workbuddy(m.group(1))
    try:
        raw, ctype = _http_get(url)
    except urllib.error.HTTPError as e:
        return None, 'HTTP %s' % e.code
    except Exception as e:
        return None, str(e)
    if 'json' in (ctype or '') or (raw[:1] in (b'{', b'[')):
        try:
            obj = json.loads(raw.decode('utf-8', 'replace'))
            text = json.dumps(obj, ensure_ascii=False, indent=2)
            return text[:_MAX_CHARS], None
        except Exception:
            pass
    text = _html_to_text(raw) if ('html' in (ctype or '') or raw.lstrip()[:1] == b'<') \
        else raw.decode('utf-8', 'replace')
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    if not text:
        return None, '页面无可用文本（可能是需登录或纯前端应用）'
    return text[:_MAX_CHARS], None


def _iter_strings(obj, out, depth=0):
    if depth > 8:
        return
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _iter_strings(v, out, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            _iter_strings(v, out, depth + 1)


def _urls_in_text(text):
    found = []
    if not isinstance(text, str):
        return found
    for m in _URL_RE.finditer(text):
        u = m.group(0).rstrip(')。.,，、；;]')
        found.append(u)
    return found


def _host_of(url):
    try:
        # 避免依赖 urllib 解析异常；简单截取
        rest = url.split('://', 1)[-1]
        return rest.split('/', 1)[0].split('?', 1)[0].split(':', 1)[0].lower()
    except Exception:
        return ''


# 历史/测试残留，不应抢占用户真实链接名额
_LOW_PRIORITY_HOSTS = frozenset({
    'example.com', 'example.org', 'example.net',
    'localhost', '127.0.0.1', '0.0.0.0',
})
_SEARCH_INTENT_RE = re.compile(
    r'(搜索|联网|上网|查一下|帮我查|放开网络|网络权限|百度|必应|google|搜一下|上网查)',
    re.I,
)
_MAX_USER_TURNS = 8


def _is_low_priority_url(url):
    h = _host_of(url)
    if not h:
        return True
    return h in _LOW_PRIORITY_HOSTS


def _is_user_item(item):
    if not isinstance(item, dict):
        return False
    if item.get('role') == 'user':
        return True
    return item.get('type') == 'message' and item.get('role') == 'user'


def _recent_user_blobs(data, limit=_MAX_USER_TURNS):
    """最近若干条用户消息（新→旧），用于抽 URL / 搜索词。"""
    turns = []
    msgs = data.get('messages')
    if isinstance(msgs, list):
        for m in reversed(msgs):
            if isinstance(m, dict) and m.get('role') == 'user':
                blobs = []
                _iter_strings(m.get('content'), blobs)
                turns.append(blobs)
                if len(turns) >= limit:
                    break
        return turns
    inp = data.get('input')
    if isinstance(inp, list):
        for item in reversed(inp):
            if _is_user_item(item):
                blobs = []
                _iter_strings(item.get('content'), blobs)
                turns.append(blobs)
                if len(turns) >= limit:
                    break
        return turns
    contents = data.get('contents')
    if isinstance(contents, list):
        for c in reversed(contents):
            if isinstance(c, dict) and (c.get('role') or '').lower() in ('user',):
                blobs = []
                _iter_strings(c, blobs)
                turns.append(blobs)
                if len(turns) >= limit:
                    break
    return turns


def _latest_user_blobs(data):
    turns = _recent_user_blobs(data, limit=1)
    return turns[0] if turns else []


def extract_urls(data: dict) -> list[str]:
    """只从「最近用户消息」抽链接；绝不扫 assistant/developer 历史（防占位摘录回流）。"""
    if not isinstance(data, dict):
        return []
    found = []
    seen = set()
    for blobs in _recent_user_blobs(data):
        for b in blobs:
            for u in _urls_in_text(b):
                if u in seen:
                    continue
                # 用户自己发的 example.com 仍保留；其余低优先级跳过
                seen.add(u)
                found.append(u)
                if len(found) >= _MAX_URLS:
                    return found
        # 最新几轮已有真链接就停，避免更早轮次的噪声
        if found and any(not _is_low_priority_url(u) for u in found):
            return [u for u in found if not _is_low_priority_url(u)][:_MAX_URLS] or found[:_MAX_URLS]
    # 若全是低优先级（用户真问了 example.com）
    return found[:_MAX_URLS]


def _latest_user_text(data):
    return '\n'.join(_latest_user_blobs(data)).strip()


def _wants_web_search(data):
    text = _latest_user_text(data)
    return bool(text and _SEARCH_INTENT_RE.search(text))


def _search_query_from_data(data):
    """从最新用户话里抽搜索词；若只是「放开网络」则回溯上一句实质内容。"""
    turns = _recent_user_blobs(data)
    if not turns:
        return ''
    latest = '\n'.join(turns[0]).strip()
    q = _SEARCH_INTENT_RE.sub(' ', latest)
    q = _URL_RE.sub(' ', q)
    q = re.sub(r'\s+', ' ', q).strip(' ，,。．！？、')
    if len(q) >= 2:
        return q[:200]
    # 回溯：找带实质问题或 URL 说明的上一轮用户话
    for blobs in turns[1:]:
        t = '\n'.join(blobs).strip()
        if not t:
            continue
        # 若有 URL，用「URL 内容」作查询意图——实际仍走 fetch_url
        if _URL_RE.search(t):
            return ''
        t2 = _SEARCH_INTENT_RE.sub(' ', t)
        t2 = re.sub(r'\s+', ' ', t2).strip(' ，,。．！？、')
        if len(t2) >= 2:
            return t2[:200]
    return ''


def web_search(query, max_results=5):
    """DuckDuckGo HTML 搜索，无 API Key。返回可读摘要或错误。"""
    if not query or len(query.strip()) < 2:
        return None, 'empty query'
    q = query.strip()[:200]
    url = 'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(q)
    try:
        raw, _ = _http_get(url, timeout=20)
    except Exception as e:
        return None, str(e)
    html = raw.decode('utf-8', 'replace')
    # 结果块：class="result__a" 标题 + result__snippet
    titles = re.findall(
        r'class="result__a"[^>]*>(.*?)</a>', html, re.I | re.S)
    snippets = re.findall(
        r'class="result__snippet"[^>]*>(.*?)</a>|class="result__snippet"[^>]*>(.*?)</',
        html, re.I | re.S)
    links = re.findall(
        r'class="result__url"[^>]*>(.*?)</|<a[^>]+class="result__a"[^>]+href="([^"]+)"',
        html, re.I | re.S)
    def _strip(s):
        s = re.sub(r'<[^>]+>', '', s or '')
        return re.sub(r'\s+', ' ', s).strip()

    lines = ['搜索词：' + q]
    n = 0
    # 简化：按标题列表对齐
    for i, title_html in enumerate(titles[:max_results]):
        title = _strip(title_html)
        snip = ''
        if i < len(snippets):
            snip = _strip(snippets[i][0] or snippets[i][1])
        href = ''
        if i < len(links):
            href = _strip(links[i][0] or links[i][1])
        if not title:
            continue
        lines.append('%d. %s' % (n + 1, title))
        if href:
            lines.append('   链接：' + href)
        if snip:
            lines.append('   摘要：' + snip[:300])
        n += 1
    if n == 0:
        # 退化：纯文本截取
        text = _html_to_text(raw)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        if len(text) < 40:
            return None, 'no results'
        return ('搜索词：%s\n%s' % (q, text[:3000])), None
    return '\n'.join(lines), None


def build_web_context(data: dict) -> str:
    urls = extract_urls(data)
    blocks = []
    ok_urls = []
    for u in urls:
        if _is_low_priority_url(u) and len(urls) > 1:
            continue
        text, err = fetch_url(u)
        if text:
            ok_urls.append(u)
            blocks.append('【已联网抓取：%s】\n%s' % (u, text))
        else:
            blocks.append('【联网抓取失败：%s】%s' % (u, err or 'unknown'))

    # 自动搜索：用户明确要求联网/搜索，或只有低优先级/失败时补搜索
    do_search = _wants_web_search(data)
    query = _search_query_from_data(data) if do_search else ''
    if do_search and not query and not ok_urls:
        # 「放开网络权限」且上文有 WorkBuddy 等链接：链接已在 urls 里抓过
        pass
    if do_search and query:
        stext, serr = web_search(query)
        if stext:
            blocks.append('【已联网搜索：%s】\n%s' % (query, stext))
        else:
            blocks.append('【联网搜索失败：%s】%s' % (query, serr or 'unknown'))

    if not blocks:
        return ''
    head = (
        '以下是网关代为联网抓取/搜索的结果（已自动完成，无需申请网络权限）。'
        '请依据下列摘录完整回答；不要输出 tool_call、request_permissions、curl 或声称无法联网。\n'
    )
    if ok_urls:
        head += (
            '【强制】禁止再对下列 URL 执行 curl/wget/Invoke-WebRequest/functions.exec；'
            '直接根据摘录回答：\n- ' + '\n- '.join(ok_urls) + '\n'
        )
    return head + '\n' + '\n\n'.join(blocks)


def _responses_dev_item(text):
    """构造 Responses input 里的 developer 消息（兼容纯字符串 content）。"""
    return {
        'type': 'message',
        'role': 'developer',
        'content': [{'type': 'input_text', 'text': text}],
    }


def _append_hint_to_last_user(input_list, hint):
    """在最后一条 user 消息末尾追加提示，提高模型可见度。"""
    if not isinstance(input_list, list):
        return
    for item in reversed(input_list):
        if not isinstance(item, dict) or item.get('role') != 'user':
            continue
        c = item.get('content')
        if isinstance(c, str):
            item['content'] = c + '\n\n' + hint
            return
        if isinstance(c, list):
            c.append({'type': 'input_text', 'text': hint})
            return
        return


def _strip_stale_web_items(input_list):
    """去掉历史里网关注入的旧 developer 摘录，避免模型看到 example.com 等过期内容。"""
    if not isinstance(input_list, list):
        return
    keep = []
    for item in input_list:
        if not isinstance(item, dict):
            keep.append(item)
            continue
        if item.get('role') != 'developer':
            keep.append(item)
            continue
        text = ''
        c = item.get('content')
        if isinstance(c, str):
            text = c
        elif isinstance(c, list):
            bits = []
            for p in c:
                if isinstance(p, dict) and p.get('text'):
                    bits.append(str(p['text']))
                elif isinstance(p, str):
                    bits.append(p)
            text = '\n'.join(bits)
        if '【已联网抓取：' in text or '网关代为联网抓取' in text \
                or '【已联网搜索：' in text or '网关代为联网抓取/搜索' in text:
            continue
        keep.append(item)
    input_list[:] = keep


def inject_web_context(data):
    """把抓取摘录写入 system / instructions / Responses input。

    成功返回摘录原文（非空 str），失败返回 ''。
    """
    if not isinstance(data, dict):
        return ''
    # 先清历史里的旧摘录，再按「最新用户链接」抓取（顺序：清历史 → 抽 URL → 注入）
    if isinstance(data.get('input'), list):
        _strip_stale_web_items(data['input'])
    ctx = build_web_context(data)
    if not ctx:
        return ''

    # Responses（Codex）：instructions + input 双通道，避免模型无视 instructions 去 curl
    if isinstance(data.get('input'), list):
        existing = data.get('instructions')
        # 去掉 instructions 里上次残留的网关摘录头，避免越堆越长
        if isinstance(existing, str) and '网关代为联网抓取' in existing:
            # 保留摘录块之后的原始 instructions（若有双换行分隔）
            parts = existing.split('\n\n', 1)
            # 粗暴：从最后一个身份声明/非摘录段起保留——若整段都是摘录则清空
            if '你是' in existing:
                idx = existing.rfind('你是')
                existing = existing[idx:]
            elif '【强制】' in existing:
                existing = ''
            else:
                existing = parts[-1] if len(parts) > 1 and '已联网抓取' not in parts[-1] else ''
        data['instructions'] = ctx + (
            '\n\n' + existing if isinstance(existing, str) and existing else '')
        data['input'] = [_responses_dev_item(ctx)] + list(data['input'])
        _append_hint_to_last_user(
            data['input'],
            '（系统提示：上方 developer 消息已含该链接的网关抓取摘录，'
            '请直接依据摘录回答，不要再 curl/下载。）',
        )
        log.info('web_fetch injected into responses instructions+input (%d chars)', len(ctx))
        return ctx

    if 'instructions' in data and not isinstance(data.get('messages'), list) \
            and not isinstance(data.get('contents'), list):
        existing = data.get('instructions')
        data['instructions'] = ctx + (
            '\n\n' + existing if isinstance(existing, str) and existing else '')
        log.info('web_fetch injected into instructions (%d chars)', len(ctx))
        return ctx

    # Chat Completions / Anthropic Messages
    msgs = data.get('messages')
    if isinstance(msgs, list):
        s = data.get('system')
        # Anthropic：优先写 system 字段
        if isinstance(s, str):
            data['system'] = ctx + '\n\n' + s
        elif isinstance(s, list):
            data['system'] = [{'type': 'text', 'text': ctx}] + s
        elif data.get('max_tokens') is not None and 'system' in data:
            data['system'] = ctx
        elif msgs and isinstance(msgs[0], dict) and msgs[0].get('role') == 'system':
            c = msgs[0].get('content')
            if isinstance(c, str):
                msgs[0]['content'] = ctx + '\n\n' + c
            elif isinstance(c, list):
                msgs[0]['content'] = [{'type': 'text', 'text': ctx}] + c
            else:
                msgs.insert(0, {'role': 'system', 'content': ctx})
        else:
            msgs.insert(0, {'role': 'system', 'content': ctx})
        log.info('web_fetch injected into messages/system (%d chars)', len(ctx))
        return ctx

    # Gemini
    if isinstance(data.get('contents'), list):
        si = data.get('systemInstruction')
        part = {'text': ctx}
        if isinstance(si, dict):
            parts = si.get('parts')
            if isinstance(parts, list):
                si['parts'] = [part] + parts
            else:
                si['parts'] = [part]
        else:
            data['systemInstruction'] = {'parts': [part]}
        log.info('web_fetch injected into gemini systemInstruction (%d chars)', len(ctx))
        return ctx
    return ''


def format_web_user_answer(ctx):
    """把注入用的抓取上下文转成给用户看的回答（模型敷衍时网关兜底）。"""
    if not isinstance(ctx, str):
        return ''
    if '【已联网抓取：' not in ctx and '【已联网搜索：' not in ctx:
        return ''
    parts = []
    for marker, label in (('【已联网抓取：', '来源'), ('【已联网搜索：', '搜索')):
        for block in ctx.split(marker)[1:]:
            if '】' not in block:
                continue
            url, rest = block.split('】', 1)
            rest = rest.strip()
            if not rest:
                continue
            parts.append('%s：%s\n%s' % (label, url.strip(), rest))
    if not parts:
        return ''
    body = '\n\n'.join(parts)
    if len(body) > 12000:
        body = body[:12000] + '\n…（摘录已截断）'
    return '已根据联网结果整理如下：\n\n' + body
