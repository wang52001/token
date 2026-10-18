#!/usr/bin/env python3
# gen_code.py - 兑换码生成工具（兑换码模式收款）
# 用法:
#   python3 gen_code.py 50              # 生成 1 个 $50 兑换码
#   python3 gen_code.py 50 -n 5         # 一次生成 5 个
#   python3 gen_code.py 100 --name 张三包月  # 备注客户/批次
#   python3 gen_code.py --list          # 查看最近 20 个码及状态
import sqlite3, sys, time, uuid, argparse

DB = '/Users/wjw/Desktop/token/new-api/one-api.db'
QUOTA_PER_USD = 500000

def gen(args):
    conn = sqlite3.connect(DB)
    name = args.name or time.strftime('%m%d批次')
    for _ in range(args.n):
        code = uuid.uuid4().hex
        conn.execute("INSERT INTO redemptions (user_id, key, status, name, quota, created_time, expired_time) VALUES (1, ?, 1, ?, ?, ?, 0)",
                     (code, name, int(args.usd * QUOTA_PER_USD), int(time.time())))
        print(code)
    conn.commit()
    print(f"--- 已生成 {args.n} 个 ${args.usd} 兑换码（备注：{name}），直接发给客户即可", file=sys.stderr)

def list_codes(_):
    conn = sqlite3.connect(DB)
    rows = conn.execute("SELECT key, name, quota, status, redeemed_time FROM redemptions ORDER BY id DESC LIMIT 20").fetchall()
    if not rows:
        print('还没有兑换码'); return
    st = {1: '未使用', 2: '已使用', 3: '已作废'}
    print(f"{'兑换码':<34}{'备注':<10}{'面值':>6}  {'状态':<6}  使用时间")
    for key, name, quota, status, rt in rows:
        t = time.strftime('%m-%d %H:%M', time.localtime(rt)) if rt else '-'
        print(f"{key:<34}{name:<10}${quota/QUOTA_PER_USD:>5.0f}  {st.get(status, status):<6}  {t}")

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='兑换码生成工具')
    p.add_argument('usd', type=float, nargs='?', default=10, help='面值（美元），默认 10')
    p.add_argument('-n', type=int, default=1, help='生成数量，默认 1')
    p.add_argument('--name', help='备注（客户名/批次名）')
    p.add_argument('--list', action='store_true', help='查看最近 20 个码')
    args = p.parse_args()
    list_codes(args) if args.list else gen(args)
