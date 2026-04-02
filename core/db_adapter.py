import pandas as pd
import hashlib
import redis
import streamlit as st
from core.snapshot_engine import build_state_key
import json    # <--- 必须加上这一行

# --- 核心适配器 ---
class RedisAdapter:
    def __init__(self, redis_url):
        import redis
        # 必须包含这三个关键参数
        self.client = redis.from_url(
            redis_url, 
            decode_responses=True, 
            ssl_cert_reqs=None
        )

    def get_state_decision(self, state_hash):
        """
        从 Redis 获取指纹决策数据
        """
        try:
            # 这里的 Key 构造必须与你之前命令行 keys 查出来的一致
            full_key = f"fp:v8:{state_hash}"
            raw_val = self.client.get(full_key)
            
            if not raw_val:
                return None
            
            # 解析数据: ACTION|EDGE|EV_CUT|EV_CONT
            parts = raw_val.split('|')
            return {
                "action": parts[0],
                "edge": float(parts[1]),
                "ev_cut": float(parts[2]),
                "ev_cont": float(parts[3])
            }
        except Exception as e:
            # 方便在线上日志中查看错误
            print(f"Redis Error: {e}")
            return None

# --- 工具函数 ---
def generate_fp_hash(c_side, c_len, hB_f, hP_f, h_min):
    """
    生成指纹哈希（强制排序版）
    """
    payload = {
        "side": c_side,
        "len": c_len,
        "hB": hB_f,
        "hP": hP_f,
        "h_min": h_min
    }
    # 这一行就是报错来源，现在有了 import json 就好了
    data_str = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(data_str.encode()).hexdigest()



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