#!/usr/bin/env python3
# migrate_sqlite_to_pg.py - new-api SQLite -> PostgreSQL 数据迁移（Koyeb/Neon/任意 PG）
# 原理：new-api 先在空 PG 上启动一次自动建表（GORM 原生 schema 最标准），
#       本脚本只负责把 SQLite 数据按目标列类型安全灌入并重置自增序列。
# 用法:
#   python3 migrate_sqlite_to_pg.py --dsn "postgresql://user:pass@host:5432/newapi?sslmode=require"
#   python3 migrate_sqlite_to_pg.py --dsn ... --sqlite /path/to/one-api.db --force
# 依赖: psycopg2（pip install psycopg2-binary）

import argparse
import os
import sqlite3
import sys
import tempfile

try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extras import execute_values
except ImportError:
    sys.exit("缺少依赖，先执行: pip install psycopg2-binary")

DEFAULT_SQLITE = '/Users/wjw/Desktop/token/new-api/one-api.db'
SKIP_TABLES = {'sqlite_sequence', 'schema_migrations', 'goose_db_version'}


def snapshot_sqlite(path):
    """用 backup API 在线快照（网关正在运行/WAL 未合并也安全）。"""
    tmp = tempfile.NamedTemporaryFile(prefix='oneapi-snap-', suffix='.db', delete=False)
    tmp.close()
    src = sqlite3.connect(path)
    dst = sqlite3.connect(tmp.name)
    src.backup(dst)
    dst.close()
    src.close()
    return tmp.name


def main():
    ap = argparse.ArgumentParser(description='new-api SQLite -> PostgreSQL 迁移')
    ap.add_argument('--dsn', default=os.environ.get('PG_DSN') or os.environ.get('SQL_DSN'),
                    help='PostgreSQL 连接串（也可用环境变量 PG_DSN）')
    ap.add_argument('--sqlite', default=DEFAULT_SQLITE, help='SQLite 源库路径')
    ap.add_argument('--force', action='store_true', help='目标表非空时先 TRUNCATE 再灌')
    args = ap.parse_args()
    if not args.dsn:
        ap.error('缺少 --dsn（或环境变量 PG_DSN）')
    if not os.path.exists(args.sqlite):
        sys.exit(f'源库不存在: {args.sqlite}')

    snap = snapshot_sqlite(args.sqlite)
    print(f'==> 已在线快照 SQLite: {args.sqlite}')
    sq = sqlite3.connect(snap)
    pg = psycopg2.connect(args.dsn)
    pg.autocommit = False
    cur = pg.cursor()

    # 目标 schema 必须由 new-api 先建好（空库启动一次即可）
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    pg_tables = {r[0] for r in cur.fetchall()}
    if 'users' not in pg_tables or 'tokens' not in pg_tables:
        sys.exit('目标库还没有 new-api 表结构。先把服务用 SQL_DSN 指向这个库启动一次（自动建表），再跑本脚本。')

    # 目标列类型映射（boolean/bytea 转换用）
    cur.execute("SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema='public'")
    col_types = {}
    for t, c, dt in cur.fetchall():
        col_types.setdefault(t, {})[c] = dt

    # 尽量关掉 FK/触发器（权限不足则跳过——new-api 一般无 FK 约束，无妨）
    try:
        cur.execute("SET session_replication_role = replica")
    except psycopg2.Error:
        pg.rollback()

    # 已有数据检查
    non_empty = []
    for t in sorted(pg_tables - SKIP_TABLES):
        cur.execute(sql.SQL('SELECT COUNT(*) FROM {}').format(sql.Identifier(t)))
        n = cur.fetchone()[0]
        if n:
            non_empty.append((t, n))
    if non_empty and not args.force:
        sys.exit(f'目标库已有数据: {non_empty[:5]}... 确认要覆盖请加 --force（会先清空）')
    if non_empty and args.force:
        for t, _ in non_empty:
            cur.execute(sql.SQL('TRUNCATE TABLE {} RESTART IDENTITY CASCADE').format(sql.Identifier(t)))
        print(f'==> 已清空 {len(non_empty)} 张目标表（--force）')

    sq_tables = {r[0] for r in sq.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    moved, skipped = [], []
    for t in sorted(pg_tables - SKIP_TABLES):
        if t not in sq_tables:
            skipped.append(t)
            continue
        cols_pg = list(col_types.get(t, {}).keys())
        sq_cols = [d[1] for d in sq.execute(f'PRAGMA table_info("{t}")')]
        cols = [c for c in cols_pg if c in sq_cols]
        if not cols:
            skipped.append(t)
            continue
        quoted = ','.join('"' + c + '"' for c in cols)
        rows = sq.execute(f'SELECT {quoted} FROM "{t}"').fetchall()
        if not rows:
            continue
        bool_idx = {i for i, c in enumerate(cols) if col_types[t][c] == 'boolean'}
        if bool_idx:
            rows = [tuple((bool(v) if (i in bool_idx and v is not None) else v)
                          for i, v in enumerate(r)) for r in rows]
        stmt = sql.SQL('INSERT INTO {} ({}) VALUES %s').format(
            sql.Identifier(t), sql.SQL(', ').join(map(sql.Identifier, cols)))
        execute_values(cur, stmt.as_string(pg), rows, page_size=500)
        # 重置自增序列（否则下次插入撞主键）
        if 'id' in cols:
            cur.execute(sql.SQL("""
                SELECT setval(pg_get_serial_sequence(%(tname)s, 'id'),
                              COALESCE((SELECT MAX(id) FROM {}), 1),
                              (SELECT MAX(id) FROM {}) IS NOT NULL)
            """).format(sql.Identifier(t), sql.Identifier(t)), {'tname': t})
        moved.append((t, len(rows)))
    pg.commit()

    # 校验：源/目标行数一致
    bad = []
    for t, n in moved:
        cur.execute(sql.SQL('SELECT COUNT(*) FROM {}').format(sql.Identifier(t)))
        m = cur.fetchone()[0]
        if m != n:
            bad.append((t, n, m))
    os.unlink(snap)
    print(f'==> 迁移完成: {len(moved)} 张表，共 {sum(n for _, n in moved)} 行')
    for t, n in moved:
        print(f'    {t:<28} {n} 行')
    if skipped:
        print(f'    （跳过，源库无此表或无共同列: {", ".join(sorted(skipped))}）')
    if bad:
        sys.exit(f'❌ 行数不一致: {bad}')
    print('✅ 行数校验全部一致')


if __name__ == '__main__':
    main()
