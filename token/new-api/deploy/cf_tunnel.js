// cf_tunnel.js - 通过 Edge CDP 会话操作 Cloudflare 面板内部 API
// 用法: node cf_tunnel.js <action> [args]
//   status      - 列出隧道与当前 ingress 配置
//   token       - 获取隧道 connector token
//   ingress     - 写入双域名 ingress（用户端 3001 / 管理端 3002）
//   dns         - 为管理域名建 CNAME

const { chromium } = require('playwright-core');

const ACCT = '0bd1c630df5e907adf68b09c0ca6b2f0';
const ZONE = 'e17f0499e2f59c7850704eb95e4e2bfc';
const USER_HOST = 'new-api.jdhsf.top';
const ADMIN_HOST = 'new-api-admin.jdhsf.top';

async function withPage(fn) {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
  const ctx = browser.contexts()[0];
  const page = await ctx.newPage();
  try {
    return await fn(page);
  } finally {
    await page.close();
    await browser.close();
  }
}

async function api(page, method, url, body) {
  const opts = { method, headers: { 'accept': 'application/json' } };
  if (body !== undefined) {
    opts.headers['content-type'] = 'application/json';
    opts.data = JSON.stringify(body);
  }
  const resp = await page.request.fetch(url, opts);
  const text = await resp.text();
  let json;
  try { json = JSON.parse(text); } catch (e) { json = { raw: text.slice(0, 500) }; }
  return { status: resp.status(), json };
}

async function main() {
  const action = process.argv[2];
  await withPage(async (page) => {
    // 1. 确认登录态
    const resp = await page.request.fetch(`https://dash.cloudflare.com/api/v4/accounts/${ACCT}/cfd_tunnel`, { headers: { accept: 'application/json' } });
    const txt = await resp.text();
    let data;
    try { data = JSON.parse(txt); } catch (e) { console.log('NOT_JSON', resp.status(), txt.slice(0, 300)); process.exit(2); }
    if (!data.success) {
      console.log('SESSION_INVALID', resp.status(), JSON.stringify(data.errors || data).slice(0, 300));
      process.exit(3);
    }
    const tunnels = data.result || [];
    console.log('tunnels:', tunnels.map(t => `${t.id} name=${t.name} status=${t.status} conns=${(t.connections || []).length}`).join('\n         '));
    // 找有 new-api ingress 的隧道（本项目唯一隧道）
    let tunnel = tunnels[0];
    if (!tunnel) { console.log('NO_TUNNEL'); process.exit(4); }

    if (action === 'status') {
      const cfg = await api(page, 'GET', `https://dash.cloudflare.com/api/v4/accounts/${ACCT}/cfd_tunnel/${tunnel.id}/configurations`);
      console.log('config:', JSON.stringify(cfg.json, null, 2));
      const dns = await api(page, 'GET', `https://dash.cloudflare.com/api/v4/zones/${ZONE}/dns_records?per_page=100`);
      console.log('dns:', (dns.json.result || []).map(r => `${r.type} ${r.name} -> ${r.content} proxied=${r.proxied}`).join('\n      '));
    } else if (action === 'token') {
      const tk = await api(page, 'GET', `https://dash.cloudflare.com/api/v4/accounts/${ACCT}/cfd_tunnel/${tunnel.id}/token`);
      if (tk.json && tk.json.success) {
        console.log('TUNNEL_ID=' + tunnel.id);
        console.log('TOKEN=' + tk.json.result);
      } else {
        console.log('TOKEN_FAIL', tk.status, JSON.stringify(tk.json).slice(0, 300));
        process.exit(5);
      }
    } else if (action === 'ingress') {
      const cfg = {
        config: {
          ingress: [
            { hostname: ADMIN_HOST, service: 'http://localhost:3002' },
            { hostname: USER_HOST, service: 'http://localhost:3001' },
            { service: 'http_status:404' }
          ],
          'warp-routing': { enabled: false }
        }
      };
      const put = await api(page, 'PUT', `https://dash.cloudflare.com/api/v4/accounts/${ACCT}/cfd_tunnel/${tunnel.id}/configurations`, cfg);
      console.log('ingress_put:', put.status, JSON.stringify(put.json).slice(0, 400));
    } else if (action === 'dns') {
      // 查重
      const dns = await api(page, 'GET', `https://dash.cloudflare.com/api/v4/zones/${ZONE}/dns_records?name=${ADMIN_HOST}`);
      const exist = (dns.json.result || []).filter(r => r.name === ADMIN_HOST);
      if (exist.length) {
        console.log('dns_exists:', exist.map(r => `${r.type} ${r.name} -> ${r.content}`).join(', '));
        return;
      }
      const rec = { type: 'CNAME', name: ADMIN_HOST, content: `${tunnel.id}.cfargotunnel.com`, proxied: true, ttl: 1, comment: 'new-api admin entry (gateway :3002)' };
      const post = await api(page, 'POST', `https://dash.cloudflare.com/api/v4/zones/${ZONE}/dns_records`, rec);
      console.log('dns_post:', post.status, JSON.stringify(post.json).slice(0, 300));
    } else {
      console.log('unknown action');
    }
  });
}

main().catch(e => { console.error('ERR', e.message); process.exit(1); });
