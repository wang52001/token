// inspect_signin.js - 加载用户端登录页，检查注册入口是否存在
const { chromium } = require('playwright-core');

async function main() {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
  const ctx = browser.contexts()[0];
  const page = await ctx.newPage();
  const base = 'https://new-api.jdhsf.top';

  for (const path of ['/sign-in', '/sign-up', '/register']) {
    try {
      const resp = await page.goto(base + path, { waitUntil: 'networkidle', timeout: 20000 });
      await page.waitForTimeout(1500);
      // 提取页面上所有链接/按钮文本 + 是否出现"注册"
      const info = await page.evaluate(() => {
        const texts = Array.from(document.querySelectorAll('a,button,[role=button]'))
          .map(e => (e.innerText || e.textContent || '').trim())
          .filter(t => t);
        const hasRegister = document.body.innerText.includes('注册');
        const registerEls = Array.from(document.querySelectorAll('a,button,[role=button]'))
          .filter(e => (e.innerText || '').includes('注册'))
          .map(e => ({ text: e.innerText.trim(), href: e.getAttribute('href') || '' }));
        return { texts: texts.slice(0, 30), hasRegister, registerEls, url: location.pathname };
      });
      console.log(`\n### ${path} (HTTP ${resp && resp.status()}) -> 实际路由 ${info.url}`);
      console.log('  页面含"注册"字样:', info.hasRegister);
      console.log('  注册相关元素:', JSON.stringify(info.registerEls));
      console.log('  可见按钮/链接:', JSON.stringify(info.texts));
    } catch (e) {
      console.log(`\n### ${path} 加载失败:`, e.message.split('\n')[0]);
    }
  }
  await browser.close();
}
main().catch(e => { console.error('ERR', e.message); process.exit(1); });
