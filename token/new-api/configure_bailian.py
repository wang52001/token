#!/usr/bin/env python3
"""把阿里云百炼模型清单写入 new-api 数据库（channels / abilities / tokens）。"""
import sqlite3, secrets, time, sys

DB = "/Users/wjw/Desktop/token/new-api/one-api.db"
KEY = "REDACTED"
COMPAT = "https://dashscope.aliyuncs.com/compatible-mode/v1"
GROUP = "default"

# ---------- 1. 对话 / 多模态 VL / 代码 / 数学 / 翻译 / 全模态 ----------
CHAT = """
qwen-math-turbo qwen3.7-plus qwen3-vl-235b-a22b-thinking qwen3-vl-32b-thinking
qwen-plus-2025-07-28 deepseek-r1-distill-qwen-7b qwen-max glm-5 qwen-mt-flash
qwen3-vl-30b-a3b-thinking qwen3.6-plus qwen-vl-ocr-latest qwen3-32b qwen3.6-flash
deepseek-r1-distill-qwen-32b qwen-vl-plus qwen3.7-flash-2026-07-15 qwen-long
qwen3.5-35b-a3b glm-4.5-air qwen3-coder-480b-a35b-instruct qwen3-coder-plus
qwen3-vl-8b-thinking deepseek-v4-flash-0731 qwen3-vl-flash-2025-10-15 qwen-vl-ocr-1028
qwen3.5-flash-2026-02-23 qwen3-max-preview qwen3-8b qwen-plus-0112 qwen-plus qwen-math-plus
gui-plus qwen-turbo qvq-max qwen3-coder-flash qwen3-next-80b-a3b-thinking qwen3.5-27b
tongyi-xiaomi-analysis-flash deepseek-r1 qwen3-14b qwen-math-plus-0919 MiniMax-M2.5
qwen3-max-2025-09-23 qwen-plus-2025-12-01 qwen-plus-character qwen-flash-character
MiniMax-M2.1 deepseek-r1-distill-qwen-14b qwen3-30b-a3b-instruct-2507 qwen-flash
qwen-flash-2025-07-28 qwen3-235b-a22b-instruct-2507 qwen3-coder-plus-2025-07-22 kimi-k2.5
qwen3.5-plus-2026-04-20 qwen3.7-max qwen-vl-ocr qwen-long-latest kimi-k2.6
qwen-vl-ocr-2025-04-13 qwen-plus-1220 qwen-vl-ocr-2025-11-20 qwen3.5-122b-a10b
tongyi-intent-detect-v3 qwen3-max qwen3.5-plus-2026-02-15 qwen3-235b-a22b-thinking-2507
qwen3.7-max-2026-06-08 glm-5.1 qwen3.7-max-preview kimi-k2-thinking qwen3.6-max-preview
glm-5.2 kimi-k2.7-code deepseek-v3.1 qwen3.5-397b-a17b qwen3-vl-plus-2025-09-23
deepseek-v3.2 qwen-math-plus-0816 qwen3-coder-next tongyi-xiaomi-analysis-pro
qwen3.5-flash qwen3-vl-32b-instruct deepseek-v4-flash qwen3-30b-a3b-thinking-2507
qwen3-coder-plus-2025-09-23 qwen-plus-latest Moonshot-Kimi-K2-Instruct qwen3-max-2026-01-23
qwen-plus-2025-09-11 qwen3-vl-flash-2026-01-22 qwen3.7-max-2026-05-20
qwen3-vl-30b-a3b-instruct qwen3.7-plus-2026-05-26 qwen3.8-2.4t-a95b
qwen3-coder-30b-a3b-instruct qwen3-vl-235b-a22b-instruct qwen-flash-character-2026-02-26
qwen3.6-27b qwen3-235b-a22b qwen-coder-plus qwen-mt-lite qwen-plus-2025-01-25
qwen3.6-flash-2026-04-16 qwen3.7-max-2026-05-17 qwen3-30b-a3b glm-4.5 qwen-mt-plus glm-4.6
qwen-coder-turbo glm-4.7 qwen3-vl-8b-instruct qwen-vl-ocr-2025-08-28 qvq-plus
qwen3-coder-flash-2025-07-28 gui-plus-2026-02-26 deepseek-v3 qwen3-vl-plus-2025-12-19
qwen-plus-2025-04-28 qwen-mt-turbo qwen3.5-plus qwen3.5-ocr qwen-long-2025-01-25
qwen3.6-35b-a3b qwen3.7-flash qwen-math-plus-latest qwen-plus-2025-07-14 qwq-plus
qwen3.6-plus-2026-04-02 deepseek-r1-0528 qwen3.8-max qwen3-next-80b-a3b-instruct
deepseek-v3.2-exp
""".split()

# 全模态（非 realtime；realtime 走 websocket，中转站不支持）
OMNI = """
qwen3.5-omni-plus-2026-03-15 qwen3.5-omni-plus qwen3-omni-flash qwen3-omni-flash-2025-12-01
qwen3-omni-flash-2025-09-15 qwen3.5-omni-flash qwen3.5-omni-flash-2026-03-15 qwen-omni-turbo
qwen-omni-turbo-latest qwen-omni-turbo-2025-03-26 qwen-omni-turbo-2025-01-19 qwen2.5-omni-7b
qwen3-omni-30b-a3b-captioner
""".split()

# ---------- 2. 向量（Embedding）----------
EMBED = """
text-embedding-v1 text-embedding-v2 text-embedding-v3 text-embedding-v4
text-embedding-async-v1 text-embedding-async-v2 multimodal-embedding-v1
qwen3.7-text-embedding qwen2.5-vl-embedding qwen3-vl-embedding
tongyi-embedding-vision-plus tongyi-embedding-vision-plus-2026-03-06
tongyi-embedding-vision-flash tongyi-embedding-vision-flash-2026-03-06
""".split()

# ---------- 3. 重排（Rerank，走百炼原生接口）----------
RERANK = "gte-rerank-v2 qwen3-rerank qwen3-vl-rerank".split()

# ---------- 4. 图像 / 视频（走百炼原生接口）----------
IMAGE = """
wanx-v1 wanx2.0-t2i-turbo wanx2.1-t2i-plus wanx2.1-imageedit wanx2.1-vace-plus
wanx-sketch-to-image-lite wanx-style-repaint-v1 wanx-background-generation-v2
wanx-poster-generation-v1 wanx-virtualmodel wanx-x-painting
qwen-image qwen-image-plus qwen-image-plus-2026-01-09 qwen-image-2.0
qwen-image-2.0-2026-03-03 qwen-image-2.0-pro qwen-image-2.0-pro-2026-03-03
qwen-mt-image z-image-turbo
wan2.2-t2i-plus wan2.2-t2i-flash wan2.5-i2i-preview wan2.6-image wan2.6-t2i
wan2.7-image wan2.7-image-pro image-out-painting
emoji-v1 wordart-semantic wordart-texture
aitryon aitryon-plus aitryon-refiner aitryon-parsing-v1
liveportrait liveportrait-detect animate-anyone-gen2 animate-anyone-template-gen2
animate-anyone-detect-gen2 emo-v1 emo-detect-v1
video-style-transform happyhorse-1.0-video-edit
""".split()

# 视频生成（异步任务，接口与图像不同，单独列出供文档说明）
VIDEO = """
wan2.2-s2v wan2.2-s2v-detect wan2.2-animate-move wan2.2-animate-mix
wan2.6-r2v wan2.6-r2v-flash wan2.7-videoedit
wan2.7-t2v-2026-06-12 wan2.7-t2v-2026-04-25
""".split()

# ---------- 5. 语音（new-api 未适配，仅记录）----------
VOICE_UNSUPPORTED_NOTE = "TTS/ASR/cosyvoice/sambert/paraformer/fun-asr/fun-music 等语音模型 new-api 未适配，需直连百炼"


def main():
    now = int(time.time())
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # 清空旧的渠道与能力表，重新按本文件生成
    cur.execute("DELETE FROM abilities")
    cur.execute("DELETE FROM channels")

    channels = [
        # (id, type, name, key, base_url, models)
        (1, 1,  "百炼-对话",     KEY, COMPAT, CHAT + OMNI + EMBED),
        (2, 17, "百炼-图像视频", KEY, "",      IMAGE + VIDEO),
        (3, 17, "百炼-重排",     KEY, "",      RERANK),
    ]

    for cid, ctype, name, key, base_url, models in channels:
        models = sorted(set(models))
        cur.execute(
            "INSERT INTO channels (id,type,key,open_ai_organization,test_model,status,name,"
            "weight,created_time,test_time,response_time,base_url,other,balance,"
            "balance_updated_time,models,\"group\",used_quota,model_mapping,"
            "status_code_mapping,priority,auto_ban,other_info,tag,setting,param_override,"
            "header_override,remark,channel_info,settings) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (cid, ctype, key, "", "", 1, name, 0, now, 0, 0, base_url, "", 0.0, 0,
             ",".join(models), GROUP, 0, "", "", 0, 0, "", "", "", "", "", "", None, ""),
        )
        for m in models:
            cur.execute(
                "INSERT INTO abilities (\"group\",model,channel_id,enabled,priority,weight,tag) "
                "VALUES (?,?,?,?,?,?,?)",
                (GROUP, m, cid, 1, 0, 0, None),
            )
        print(f"{name:<14} type={ctype:<3} 模型数={len(models)}")

    # 生成 unlimited 令牌
    cur.execute("DELETE FROM tokens")
    token = "sk-" + secrets.token_hex(24)
    cur.execute(
        "INSERT INTO tokens (user_id,key,status,name,created_time,accessed_time,expired_time,"
        "remain_quota,unlimited_quota,model_limits_enabled,model_limits,allow_ips,used_quota,"
        "\"group\",cross_group_retry,auto_groups,deleted_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (1, token, 1, "本地默认令牌(无限额度)", now, 0, -1, 0, 1, 0, "", "", 0, GROUP, 0, "", None),
    )
    con.commit()
    con.close()

    print("\nAPI 令牌:", token)
    print(f"对话/向量模型 {len(set(CHAT+OMNI+EMBED))} 个 | 图像视频 {len(set(IMAGE+VIDEO))} 个 | 重排 {len(RERANK)} 个")


if __name__ == "__main__":
    main()
