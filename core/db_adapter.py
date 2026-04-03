import redis
import json
import hashlib

class RedisAdapter:
    def __init__(self, redis_url):
        """
        初始化 Redis 连接 - 已移除兼容性冲突参数
        """
        try:
            # 移除 ssl_cert_reqs 以兼容旧版 redis-py
            self.client = redis.from_url(
                redis_url, 
                decode_responses=True
            )
        except Exception as e:
            print(f"Redis Connection Error: {e}")
    
    def get_state_decision(self, state_hash):
        """
        物理对齐版本：优先处理 Hash 类型
        """
        try:
            target_key = state_hash.strip()
            
            # 1. 尝试 HGETALL (针对终端显示的 hash 结构)
            data = self.client.hgetall(target_key)
            
            if data and isinstance(data, dict) and "action" in data:
                return {
                    "action": data.get("action"),
                    "edge": float(data.get("edge", 0)),
                    "ev_cut": float(data.get("ev_cut", 0)),
                    "ev_cont": float(data.get("ev_cont", 0))
                }

            # 2. 备选：尝试 String 协议
            raw_data = self.client.get(target_key)
            if raw_data:
                parts = raw_data.split('|')
                return {
                    "action": parts[0],
                    "edge": float(parts[1]),
                    "ev_cut": float(parts[2]),
                    "ev_cont": float(parts[3])
                }
            return None
        except Exception as e:
            return None

def generate_fp_hash(side, length, hB, hP, h_min):
    """
    生成物理指纹哈希
    """
    hB_str = json.dumps(hB, separators=(',', ':'), sort_keys=True)
    hP_str = json.dumps(hP, separators=(',', ':'), sort_keys=True)
    raw_key = f"{side}|{min(length, 15)}|HB={hB_str}|HP={hP_str}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()