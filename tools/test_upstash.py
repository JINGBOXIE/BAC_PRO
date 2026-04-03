import streamlit as st
import redis

# 获取配置
url = st.secrets["UPSTASH_REDIS_URL"]

try:
    # 终极兼容性写法：显式指定不验证证书
    r = redis.from_url(
        url, 
        decode_responses=True,
        ssl_cert_reqs=None  # 这行是解决 SSL: CERTIFICATE_VERIFY_FAILED 的关键
    )
    if r.ping():
        print("✅ 成功连接到 Upstash 云端 Redis!")
        print(f"当前数据库中的 Key 总数: {r.dbsize()}")
except Exception as e:
    print(f"❌ 连接仍然失败: {e}")