import pandas as pd
import hashlib
import redis
import streamlit as st
from core.snapshot_engine import build_state_key

# --- 核心适配器 ---

class RedisAdapter:
    def __init__(self, redis_url):
        # 强制开启 SSL 以适配 Upstash
        self.client = redis.from_url(
            redis_url, 
            decode_responses=True,
            ssl_cert_reqs=None
        )

    def get_state_decision(self, state_hash):
        """
        从 Redis 获取指纹决策数据 (fp:v8:xxx)
        """
        try:
            raw_val = self.client.get(f"fp:v8:{state_hash}")
            if not raw_val:
                return None
            
            # 解析脱水字符串: action|edge|ev_cut|ev_cont
            parts = raw_val.split('|')
            return {
                "action": parts[0],
                "edge": float(parts[1]),
                "ev_cut": float(parts[2]),
                "ev_cont": float(parts[3])
            }
        except Exception as e:
            print(f"Redis Query Error: {e}")
            return None

# --- 工具函数 ---

def generate_fp_hash(cur_side, cur_len, hist_B, hist_P, hist_min=3):
    """
    [规格文档 1.2 对齐] 应用动态 hist_min 截断并生成 SHA256 哈希
    """
    # 过滤掉小于 hist_min 的柱子
    f_B = {k: v for k, v in hist_B.items() if int(k) >= hist_min}
    f_P = {k: v for k, v in hist_P.items() if int(k) >= hist_min}
    
    # 构造原始 Key
    raw_key = build_state_key(
        cur_side=cur_side,
        cur_len=cur_len,
        hist_B=f_B,
        hist_P=f_P
    )
    
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

# --- 兼容性封装 (线上版本主要调用这个) ---

def get_fingerprint_advice(cur_side, cur_len, hist_B, hist_P, hist_min=3):
    """
    统一的指纹查询入口，优先从 Redis 获取
    """
    state_hash = generate_fp_hash(cur_side, cur_len, hist_B, hist_P, hist_min)
    
    # 从 Streamlit Secrets 获取 Redis URL
    redis_url = st.secrets.get("UPSTASH_REDIS_URL")
    if not redis_url:
        return {"match": False, "fp_id": state_hash, "error": "No Redis URL"}

    adapter = RedisAdapter(redis_url)
    res = adapter.get_state_decision(state_hash)

    if res:
        return {
            "match": True,
            "fp_id": state_hash,
            "action": res['action'],
            "edge": res['edge'],
            "ev_info": {
                "斩 (Cut)": res['ev_cut'],
                "跟 (Cont)": res['ev_cont']
            }
        }
    
    return {"match": False, "fp_id": state_hash}

# 占位符，保持与其他模块的兼容
def get_ev_data(side, length):
    pass