import redis
from pathlib import Path
import tomllib

def load_config():
    secrets_path = Path(__file__).parent / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        secrets_path = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
    with open(secrets_path, "rb") as f:
        return tomllib.load(f)

def migrate():
    try:
        config = load_config()
        LOCAL_URL = config.get("LOCAL_REDIS_URL", "redis://localhost:6379/0")
        CLOUD_URL = config.get("UPSTASH_REDIS_URL")

        print(f"🔗 本地: {LOCAL_URL}")
        local_r = redis.from_url(LOCAL_URL, decode_responses=True)
        
        print(f"☁️ 云端: {CLOUD_URL.split('@')[-1]}")
        # 使用 7.4.0 兼容的参数
        remote_r = redis.from_url(CLOUD_URL, decode_responses=True, ssl_cert_reqs=None)

        all_keys = local_r.keys("*")
        total = len(all_keys)
        print(f"🚀 准备原样迁移 {total} 条数据...")

        success_count = 0
        batch_size = 1000
        pipe = remote_r.pipeline(transaction=False)

        for i, key in enumerate(all_keys):
            if len(key) < 30: continue
            
            k_type = local_r.type(key)
            if k_type == 'string':
                pipe.set(key, local_r.get(key))
            elif k_type == 'hash':
                pipe.hset(key, mapping=local_r.hgetall(key))
            elif k_type == 'set':
                pipe.sadd(key, *local_r.smembers(key))
            
            success_count += 1
            if (i + 1) % batch_size == 0 or (i + 1) == total:
                pipe.execute()
                print(f"📦 进度: {i + 1}/{total} ({(i + 1)/total:.1%})")

        print(f"✅ 成功搬运: {success_count} 条数据。")

    except Exception as e:
        print(f"❌ 运行失败: {str(e)}")

if __name__ == "__main__":
    migrate()
