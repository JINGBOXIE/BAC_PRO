import redis
from pathlib import Path
import tomllib

def load_config():
    # 自动定位到 .streamlit/secrets.toml
    secrets_path = Path(__file__).parent / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        # 兼容在根目录或子目录下运行的情况
        secrets_path = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
    
    with open(secrets_path, "rb") as f:
        return tomllib.load(f)

def migrate():
    try:
        config = load_config()
        LOCAL_URL = config.get("LOCAL_REDIS_URL", "redis://localhost:6379/0")
        CLOUD_URL = config.get("UPSTASH_REDIS_URL")

        # 1. 建立连接 (7.4.0 版本标准写法)
        print(f"🔗 本地连接: {LOCAL_URL}")
        local_r = redis.from_url(LOCAL_URL, decode_responses=True)
        
        print(f"☁️ 云端连接: {CLOUD_URL.split('@')[-1]}")
        # 最新版 redis-py 处理 Upstash SSL 的标准参数
        remote_r = redis.from_url(
            CLOUD_URL, 
            decode_responses=True, 
            ssl_cert_reqs=None
        )

        # 2. 获取所有原始 Key (纯 Hash 格式)
        all_keys = local_r.keys("*")
        total = len(all_keys)
        print(f"🚀 准备原样迁移 {total} 条数据...")

        # 3. 开启非事务管道，保持 1:1 数据结构
        pipe = remote_r.pipeline(transaction=False)
        batch_size = 1000
        success_count = 0

        for i, key in enumerate(all_keys):
            # 过滤掉系统 Key，只处理你的长 Hash
            if len(key) < 30: continue

            k_type = local_r.type(key)
            
            # 原样搬运，不改变任何 Value 类型
            if k_type == 'string':
                pipe.set(key, local_r.get(key))
            elif k_type == 'hash':
                pipe.hset(key, mapping=local_r.hgetall(key))
            elif k_type == 'set':
                pipe.sadd(key, *local_r.smembers(key))
            elif k_type == 'list':
                pipe.rpush(key, *local_r.lrange(key, 0, -1))
            
            success_count += 1

            if (i + 1) % batch_size == 0 or (i + 1) == total:
                pipe.execute()
                print(f"📦 搬运进度: {i + 1}/{total} ({(i + 1)/total:.1%})")

        print("-" * 30)
        print(f"✅ 迁移完成！{success_count} 条数据格式已完全同步。")

    except Exception as e:
        print(f"❌ 运行出错: {str(e)}")

if __name__ == "__main__":
    print("=== BAC_PRO 数据 1:1 格式迁移 (终端运行版) ===")
    migrate()