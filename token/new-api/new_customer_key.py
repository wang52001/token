#!/usr/bin/env python3
# new_customer_key.py - 为客户开通独立 API key（继承 cc-* 主令牌的假名白名单）
# 用法示例:
#   python3 new_customer_key.py 张三                          # 全线模型, $50 额度, 30 天有效
#   python3 new_customer_key.py 李四 --line claude            # 仅 Claude 线
#   python3 new_customer_key.py 王五 --quota-usd 100 --days 90
#   python3 new_customer_key.py --list                        # 列出所有客户 key 用量
import sqlite3, secrets, string, sys, time, argparse, json, subprocess

DB = '/Users/wjw/Desktop/token/new-api/one-api.db'
MASTER = {'claude': 'cc-claude', 'gemini': 'cc-gemini', 'codex': 'cc-codex'}
QUOTA_PER_USD = 500000  # new-api: $1 = 500,000 quota

def get_conn():
    return sqlite3.connect(DB)

def master_limits(conn, line):
    if line == 'all':
        out = []
        for m in MASTER.values():
            lim = conn.execute("SELECT model_limits FROM tokens WHERE name=?", (m,)).fetchone()[0]
            out += [x for x in lim.split(',') if x]
        return sorted(set(out))
    lim = conn.execute("SELECT model_limits FROM tokens WHERE name=?", (MASTER[line],)).fetchone()[0]
    return [x for x in lim.split(',') if x]

def lan_ip():
    for iface in ('en0', 'en1'):
        try:
            ip = subprocess.check_output(['ipconfig', 'getifaddr', iface], text=True).strip()
            if ip:
                return ip
        except Exception:
            pass
    return '<你的局域网IP>'

def create_key(args):
    conn = get_conn()
    name = f"客-{args.name}"
    if conn.execute("SELECT 1 FROM tokens WHERE name=? AND deleted_at IS NULL", (name,)).fetchone():
        print(f"错误：客户「{args.name}」已存在有效 key，请先吊销再重建"); sys.exit(1)
    alphabet = string.ascii_letters + string.digits  # key 不能含 '-'（new-api 分段解析坑）
    key = ''.join(secrets.choice(alphabet) for _ in range(48))
    limits = master_limits(conn, args.line)
    quota = -1 if args.unlimited else int(args.quota_usd * QUOTA_PER_USD)
    expired = -1 if args.days <= 0 else int(time.time()) + args.days * 86400
    conn.execute(
        "INSERT INTO tokens (user_id, key, status, name, created_time, accessed_time, expired_time,"
        " remain_quota, unlimited_quota, model_limits_enabled, model_limits, used_quota, \"group\")"
        " VALUES (1, ?, 1, ?, ?, 0, ?, ?, ?, 1, ?, 0, 'default')",
        (key, name, int(time.time()), expired, quota, 1 if args.unlimited else 0, ','.join(limits)))
    conn.commit()
    exp_txt = '永不过期' if expired == -1 else time.strftime('%Y-%m-%d', time.localtime(expired))
    quota_txt = '不限量' if args.unlimited else f"${args.quota_usd}（{quota:,} quota）"
    print(f"✅ 客户「{args.name}」已开通")
    print(f"   key:        sk-{key}")
    print(f"   产品线:     {args.line}（{len(limits)} 个模型，全部假名）")
    print(f"   额度:       {quota_txt}   有效期至: {exp_txt}")
    print(f"   Base URL:   http://{lan_ip()}:3001  （必须走 3001 伪装层，不能用 3000）")

def list_keys(_):
    conn = get_conn()
    rows = conn.execute(
        "SELECT name, status, remain_quota, used_quota, expired_time, unlimited_quota"
        " FROM tokens WHERE name LIKE '客-%' AND deleted_at IS NULL").fetchall()
    if not rows:
        print('暂无客户 key'); return
    print(f"{'客户':<12}{'状态':<6}{'已用额度':>12}{'剩余额度':>14}  有效期至")
    for name, status, rq, uq, exp, unlim in rows:
        exp_txt = '永不过期' if exp == -1 else time.strftime('%Y-%m-%d', time.localtime(exp))
        rq_txt = '不限' if unlim else f"${rq/QUOTA_PER_USD:.2f}"
        print(f"{name:<12}{'启用' if status==1 else '停用':<6}{uq/QUOTA_PER_USD:>11.2f}${rq_txt:>13}  {exp_txt}")

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='客户独立 key 开通工具')
    p.add_argument('name', nargs='?', help='客户名（自动加 客- 前缀）')
    p.add_argument('--line', choices=['claude', 'gemini', 'codex', 'all'], default='all')
    p.add_argument('--quota-usd', type=float, default=50.0, help='额度（美元），默认 50')
    p.add_argument('--days', type=int, default=30, help='有效天数，0=永不过期，默认 30')
    p.add_argument('--unlimited', action='store_true', help='不限额度（谨慎）')
    p.add_argument('--list', action='store_true', help='列出所有客户 key')
    args = p.parse_args()
    if args.list:
        list_keys(args)
    elif args.name:
        create_key(args)
    else:
        p.print_help()
