import redis
from concurrent.futures import ThreadPoolExecutor

# 1. 配置连接
# 本地连接
local_r = redis.Redis(host='localhost', port=6379, decode_responses=False) 

# 云端连接 (使用你刚才测试成功的 URI)
CLOUD_URI = "rediss://default:gQAAAAAAAWFKAAIncDE5YzQ4Zjg3NGVlY2M0M2Q3Yjg4ODZmZTAwYThlNzJkNnAxOTA0NDI@model-mullet-90442.upstash.io:6379"
remote_r = redis.from_url(CLOUD_URI, ssl_cert_reqs=None)

def sync_key(key):
    try:
        # 获取生存时间 (ms)
        ttl = local_r.pttl(key)
        if ttl < 0: ttl = 0
        
        # 1:1 二进制导出
        raw_data = local_r.dump(key)
        
        # 1:1 二进制导入 (replace=True 确保覆盖旧数据)
        remote_r.restore(key, ttl, raw_data, replace=True)
        return True
    except Exception as e:
        # print(f"Error syncing {key}: {e}")
        return False

def main():
    print("🔍 正在扫描本地 Key...")
    all_keys = local_r.keys("*")
    total = len(all_keys)
    print(f"🚀 准备同步 {total} 条数据 (DUMP/RESTORE 模式)")

    # 使用 20 个并发线程，速度提升约 20 倍
    # 1.47M 数据预计耗时 1-2 小时
    success = 0
    with ThreadPoolExecutor(max_workers=20) as executor:
        for i, result in enumerate(executor.map(sync_key, all_keys)):
            if result: success += 1
            if (i + 1) % 1000 == 0:
                print(f"📦 进度: {i + 1}/{total} ({(i + 1)/total:.1%}) | 成功: {success}")

    print(f"\n✅ 迁移完成！成功搬运: {success}/{total}")

if __name__ == "__main__":
    main()