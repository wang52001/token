# ClawCloud Run 免费部署指南（无需信用卡 · 全网页操作）

> 前提：GitHub 账号注册满 180 天 ✅（已确认）
> 全程不用敲命令、不用装 git，浏览器点完即可。部署文件都在本目录 `shim-image/` 里。

## 架构

```
客户 → https://newapi.jdhsf.top（CNAME 到平台）→ shim 容器:3001 → new-api 容器:3000 → 百炼上游
```

## 第 1 步：注册 ClawCloud（3 分钟）

1. 打开 https://claw.cloud ，用 **GitHub 账号**登录（不需要填任何卡片）
2. 右上角头像 → Plan，确认 **Monthly Gift = $5**
3. 区域选 **Japan**（其次 Singapore）

## 第 2 步：GitHub 建仓库传文件（3 分钟）

1. github.com → 右上角 + → New repository → 名字 `api-shim` → **Public** → Create
2. 进仓库 → **Add file → Upload files**，把 `shim-image/` 里的 **3 个文件**都拖进去提交：
   - `Dockerfile`
   - `codex_shim.py`
   - `db.enc`（这是加密后的网关数据，密码在最后一步用）

## 第 3 步：部署 new-api 容器

ClawCloud 控制台 → App Launchpad → **Create App**：
- Image：`calciumion/new-api:latest`
- 端口：`3000`，**不开公网**（internal only）
- 规格：1 CPU / 1G 内存
- Storage → Add Volume：5G，挂载路径 `/data` ⚠️ 这步不能省
- 部署后进入应用详情页，**记下它的内部地址**（形如 `new-api-xxx.ns-xxx`），下一步要用

## 第 4 步：部署 shim 容器

App Launchpad → **Create App** → 选 **从源码构建 / Dockerfile**：
- 连你的 `api-shim` 仓库，分支 main，Dockerfile 路径 `/Dockerfile`
- 端口：`3001`，**开启公网**（平台自动分配 https 域名）
- 环境变量两条：
  - `UPSTREAM_HOST` = 上一步记下的 new-api 内部地址
  - `UPSTREAM_PORT` = `3000`
- 规格选最小（0.2C / 128M 够）

## 第 5 步：灌入数据（客户/别名/密钥全保留）

1. ClawCloud 控制台打开 **new-api 容器 → Web 终端**，依次执行：

```bash
apt-get update && apt-get install -y wget openssl
wget https://raw.githubusercontent.com/你的GitHub用户名/api-shim/main/db.enc -O /tmp/db.enc
openssl enc -d -aes-256-cbc -pbkdf2 -in /tmp/db.enc -out /data/one-api.db -pass pass:'REDACTED'
```

2. 控制台把 **两个容器都 Restart**
3. ⚠️ 回 GitHub 仓库**把 db.enc 删掉**（Delete file），密码随即作废

## 第 6 步：绑域名

1. shim 应用详情页 → **Custom Domain** → 填 `newapi.jdhsf.top`，复制平台给的 CNAME 目标
2. 阿里云域名控制台 → DNS：类型 **CNAME**，主机记录 `newapi`，记录值 = 该目标
3. 等 1-2 分钟，访问 https://newapi.jdhsf.top 应看到 new-api 界面

## 第 7 步：开业配置

1. 后台（https://newapi.jdhsf.top 登录你的管理员账号，密码和本地一样）：
   - 设置 → 系统设置 → 确认允许新用户注册（默认已开）
   - **收款方式 = 兑换码**（已定案，见《收款SOP.md》）：客户微信/支付宝转账给你 → 你用 `gen_code.py` 发码 → 客户自助兑换。零平台费用
   - 数据随 db.enc 迁移而来：分组隔离（default=33 假名 / vip=全部）、定价（$20/1M）、合规确认（terms v1）全部已就位，无需重配
2. 小号全流程验收：注册 → 兑换 → 建 key → 调模型 → **身份回答必须是假名**
3. 验收通过 → 把《客户接入指南.md》发给客户即可（地址已是 https://newapi.jdhsf.top）

## 卡住了？

每步做完都可以叫我——把你看到的界面截图发来，我告诉你点哪里。
