import redis
from concurrent.futures import ThreadPoolExecutor

# 1. 连接配置
# 本地使用 decode_responses=True，因为我们要读取真实内容
local_r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# 云端连接
CLOUD_URI = "rediss://default:gQAAAAAAAWFKAAIncDE5YzQ4Zjg3NGVlY2M0M2Q3Yjg4ODZmZTAwYThlNzJkNnAxOTA0NDI@model-mullet-90442.upstash.io:6379"
remote_r = redis.from_url(CLOUD_URI, decode_responses=True, ssl_cert_reqs=None)

def sync_key(key):
    try:
        k_type = local_r.type(key)
        
        if k_type == 'string':
            val = local_r.get(key)
            remote_r.set(key, val)
        elif k_type == 'hash':
            val = local_r.hgetall(key)
            remote_r.hset(key, mapping=val)
        elif k_type == 'set':
            val = local_r.smembers(key)
            remote_r.sadd(key, *val)
        elif k_type == 'list':
            val = local_r.lrange(key, 0, -1)
            remote_r.rpush(key, *val)
        else:
            return False
        return True
    except Exception as e:
        # 如果报错，我们至少能看到为什么失败
        # print(f"Error: {e}") 
        return False

def main():
    print("🔍 重新扫描本地 Key...")
    all_keys = local_r.keys("*")
    total = len(all_keys)
    print(f"🚀 启动 1:1 格式搬运 (HSET/SET 模式) | 总计: {total}")

    success = 0
    # 稍微调低一点并发，确保稳定性
    with ThreadPoolExecutor(max_workers=10) as executor:
        for i, result in enumerate(executor.map(sync_key, all_keys)):
            if result: success += 1
            if (i + 1) % 500 == 0:
                print(f"📦 进度: {i + 1}/{total} ({(i + 1)/total:.1%}) | 成功: {success}")

    print(f"\n✅ 迁移完成！成功: {success}/{total}")

if __name__ == "__main__":
    main()