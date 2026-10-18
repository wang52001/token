-- 目的：把渠道 12（test）的剩余额度写进余额列，后台「渠道」页实时可见
-- 当前实测：1000 key × 5元 = 5000 元总额度；used_quota=1761917 → 已消耗 ¥25.72 → 剩余 ¥4974.28

-- ── 方式 A：自计算（推荐，重跑即可刷新）────────────────
-- 500000 = QuotaPerUnit（$1 = 500000 quota）
-- 7.3    = USDExchangeRate（汇率变了就改这里）
UPDATE channels SET balance = 5000 - (used_quota / 500000.0 * 7.3) WHERE id = 12;

-- ── 方式 B：直接写死当前值（4974.28）──────────────────
-- UPDATE channels SET balance = 4974.28 WHERE id = 12;

-- 若想让后台按「$」标签显示得名副其实，改用美元值 681.41：
-- UPDATE channels SET balance = 681.41 WHERE id = 12;

-- ── 怎么跑（宿主机 shell）─────────────────────────────
-- SQLite（容器内 /data/one-api.db）：
--   sqlite3 /data/one-api.db "UPDATE channels SET balance = 5000 - (used_quota / 500000.0 * 7.3) WHERE id = 12;"
-- Postgres（Koyeb 持久化库）：
--   psql "$DATABASE_URL" -c "UPDATE channels SET balance = 5000 - (used_quota / 500000.0 * 7.3) WHERE id = 12;"

-- ── 验证 ─────────────────────────────────────────────
-- SELECT id, name, balance, used_quota FROM channels WHERE id = 12;
