# 上线部署手册（jdhsf.top · 免费服务器 · 兑换码收款）

目标架构：`https://newapi.jdhsf.top` → Caddy（HTTPS）→ shim（身份伪装）→ new-api（用户端+管理端）

## 一、域名：用 newapi.jdhsf.top

一级域名 jdhsf.top 已在用作主站，API 服务用子域名 **newapi.jdhsf.top**（客户一眼看懂用途）。

> ⚠️ **重要：一级域名已在用，别整体迁 NS 到 Cloudflare！** 迁 NS 会把现有网站的所有 DNS 记录一起带走，重建前老站会断。两个安全做法：
> - **做法 A（推荐，零风险）**：DNS 留在阿里云，只加一条 A 记录 `newapi` → 服务器 IP。Caddy 自动签发 HTTPS 证书，完全够用
> - **做法 B（要 Cloudflare 防护时）**：迁 NS 到 Cloudflare，但先把现有所有记录逐条抄到 Cloudflare 再切换
> 起步选 A；以后想要 CDN/隐藏源站 IP 再做 B。

## 二、服务器：三条路线（2026-09-09 核实）

| 路线 | 费用 | 门槛 | 状态 |
|---|---|---|---|
| **ClawCloud Run**（首选） | $5/月赠送额度内 = 免费 | GitHub 满 180 天 ✅，**无需信用卡** | ⚠️ 平台宕机中（09-08 起），恢复后按《ClawCloud部署指南.md》走 |
| **Koyeb**（备选，不休眠） | 免费档 1 服务 + 1G Postgres | 多数地区**无需信用卡** | ✅ 可用，按《Koyeb部署指南.md》走 |
| **VPS**（稳定终态） | 阿里云轻量香港 ¥30+/月 | 免备案 | 随时可用，用本目录 `migrate-to-vps.sh` |

> Oracle Cloud 永久免费层（ARM 2核12G）需要 Visa/MasterCard 双币卡验证，你没有双币卡，此路已排除。
> 收费营业有稳定流水后，建议尽早迁 VPS（最省心、数据完全自控），`migrate-to-vps.sh` 一条命令搞定。

## 三、收款：兑换码模式（已定案，零费用）

不接任何支付平台，**钱 100% 直进你的微信/支付宝**：

```
客户转账给你（附言用户名）→ 你发兑换码 → 客户自助兑换 → 客户自建 key 使用
```

- 发码：本地环境用 `gen_code.py`；**上线后**用管理后台「运营 → 兑换码」页面直接生成（数据库在服务器上）
- 完整流程与话术见《收款SOP.md》
- 分组隔离已配好：客户注册落 default 组（只见 33 个假名），你在 vip 组（全部模型）
- 以后想自动收款再考虑：官方直清型易支付（约 ¥88 开户）或 V免签（零费率，需常开安卓机）——前期没必要

## 四、部署步骤（VPS 路线，服务器到手后）

```bash
# 1. 在 Mac 上执行（已配好 newapi.jdhsf.top）
cd /Users/wjw/Desktop/token/new-api/deploy
./migrate-to-vps.sh <服务器IP>

# 2. 阿里云域名控制台加 DNS 记录
#    类型 A，主机记录 newapi，记录值 = 服务器 IP

# 3. 等 1-2 分钟 Caddy 自动签证书，访问 https://newapi.jdhsf.top
```

免费平台路线不用这个脚本——ClawCloud 走《ClawCloud部署指南.md》，Koyeb 走《Koyeb部署指南.md》（全网页操作）。

## 五、上线后配置（管理后台）

1. **开放注册**：设置 → 系统设置 → 允许新用户注册（数据迁移后默认已开）
2. **收款**：兑换码模式，无需任何支付配置（合规门禁 terms v1 已确认，随数据迁移生效）
3. **模型可见性**：客户 default 组 = 33 个假名（已配好，随数据迁移生效）
4. **验收**：小号注册 → 兑换码充值 → 建 key → 调模型 → **身份回答必须是假名**

## 六、迁移后

- 本机 Mac 可保留为测试环境，或 `launchctl bootout gui/$(id -u)/com.newapi.local` 和 `com.codex-shim.local` 彻底停用
- VPS 上配每日备份（cron + 同目录 backup_db.sh 思路），上线后我帮你装
