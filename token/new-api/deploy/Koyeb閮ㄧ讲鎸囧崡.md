# Koyeb 免费部署指南（无需信用卡 · 不休眠 · 全网页操作）

> 适用场景：ClawCloud 宕机等不及 / 想要常驻不休眠的免费方案。
> Koyeb 免费档（2026-09 核实）：1 个 Web 服务（512MB / 0.1vCPU）**不休眠** + 1 个免费 PostgreSQL（1GB）+ 5 个自定义域名，多数地区注册**不需要信用卡**。
> 本方案已通过本地端到端演练：SQLite → PostgreSQL 迁移脚本实测 15 表 853 行零误差，迁移后令牌/分组/调用全部正常。

## 架构

```
客户 → https://newapi.jdhsf.top（CNAME 到 Koyeb）→ 单容器 [shim:3001 对外 → new-api:3000 内部] → 百炼上游
数据：Koyeb 免费 PostgreSQL（客户/令牌/兑换码/日志全在里面，不依赖容器磁盘）
```

> ⚠️ 为什么不能像 ClawCloud 那样用 SQLite：Koyeb 免费实例的磁盘是**临时的**，重启/重新部署即清空。客户余额数据必须放 Postgres。

## 第 1 步：注册 Koyeb（2 分钟）

1. 打开 https://www.koyeb.com ，用 **GitHub 账号**登录（就是 ClawCloud 用的那个，已满 180 天）
2. 如果弹出绑卡要求，告诉我换备选（HF Spaces + Neon）；多数账号不会要

## 第 2 步：GitHub 仓库补 2 个文件（3 分钟）

进你之前建的 `api-shim` 仓库（ClawCloud 指南第 2 步那个）：

1. **Add file → Create new file**，文件名填 `koyeb/Dockerfile`（带斜杠会自动建目录），内容粘贴本目录 `koyeb/Dockerfile` 全文 → Commit
2. 同样方法建 `koyeb/start.sh`，粘贴本目录 `koyeb/start.sh` 全文 → Commit

> 仓库里原有的 `Dockerfile`、`codex_shim.py` 别动；`db.enc` 不需要（那是 SQLite 路线），已删更好。

## 第 3 步：建免费 PostgreSQL（2 分钟）

Koyeb 控制台 → **Databases** → **Create Database**：
- 规格选 **Free**（1GB 存储）
- 区域就近（ Singapore > US West > Frankfurt，以实际可选为准）
- 创建后进入详情页，**复制 Connection String**（`postgresql://用户:密码@主机/库名` 形式，先存到备忘录）

## 第 4 步：部署 Web Service（5 分钟）

控制台 → **Create Service** → 选 **GitHub**：
- 仓库：`api-shim`，分支 main
- Builder：**Dockerfile**，Dockerfile path 填 `koyeb/Dockerfile`，Build context 留 `/`
- Instance：选 **Free**（0.1 vCPU / 512MB）
- 区域：和数据库选同一个
- **Environment Variables** 加一条：`SQL_DSN` = 第 3 步复制的连接串
- **Ports**：把 `3001` 设为 Public（平台自动给 `xxx.koyeb.app` 域名和 HTTPS）
- Deploy。首次启动 new-api 会在空数据库里**自动建表**（日志看到 `New API started` 即成功）

## 第 5 步：灌入全部现有数据（Mac 上跑 3 行命令）

在 Mac 终端执行（把连接串换成你的）：

```bash
/Users/wjw/.workbuddy/binaries/python/versions/3.13.12/bin/python3 -m venv ~/pgvenv
~/pgvenv/bin/pip install psycopg2-binary
~/pgvenv/bin/python /Users/wjw/Desktop/token/new-api/deploy/koyeb/migrate_sqlite_to_pg.py --dsn "postgresql://你的连接串"
```

- 看到 `✅ 行数校验全部一致` 即成功（渠道/别名/令牌/用户/定价/合规确认全部原样搬入）
- 若提示目标库已有数据，确认无误后加 `--force` 重跑
- 回 Koyeb 控制台把服务 **Redeploy**（或 Restart）一次，让缓存刷新

## 第 6 步：绑域名

1. 服务详情页 → **Domains** → 添加 `newapi.jdhsf.top`，复制 Koyeb 给的 CNAME 目标
2. 阿里云域名控制台 → DNS：类型 **CNAME**，主机记录 `newapi`，记录值 = 该目标
3. 等 1-2 分钟，访问 https://newapi.jdhsf.top 应看到 new-api 登录页（管理员账号密码和本地一样）

## 第 7 步：开业配置

数据已随迁移就位，只需验收：

1. 小号全流程：注册 → 后台「运营 → 兑换码」发码（**上线后发码用后台页面**，本地 `gen_code.py` 只管本地环境）→ 兑换 → 建 key → 调模型 → **身份回答必须是假名**
2. 验收通过 → 把《客户接入指南.md》发给客户即可（地址已是 https://newapi.jdhsf.top）

## 两个要知道的取舍

1. **延迟**：免费档区域离国内较远，每个请求比本地/香港 VPS 多 150-250ms——聊天感知不强，但客户量大或在意速度时迁阿里云香港 VPS（`migrate-to-vps.sh` 一条命令）
2. **额度**：免费 PG 1GB 对这套系统是天量（现有全部数据才 1MB 出头），放心用

## 卡住了？

每步做完都可以叫我——把界面截图发来，我告诉你点哪里。
