## 必须将本文件复制到项目根目录 BAC_PRO下 fingerprint_redis_connection_test.py

import streamlit as st
import pandas as pd
import redis
import time
from itertools import groupby
from core.snapshot_engine import get_fp_components, apply_v8_sampling_logic
from core.db_adapter import RedisAdapter, generate_fp_hash
import sys
import os
from pathlib import Path

# 定位到当前脚本的祖父目录（即 BAC_PRO 根目录）
root_repo = Path(__file__).resolve().parent.parent
if str(root_repo) not in sys.path:
    sys.path.insert(0, str(root_repo))

# 现在你可以优雅地导入 core 了
from core.snapshot_engine import get_fp_components, apply_v8_sampling_logic

def main():
    st.set_page_config(page_title="V8 物理链路审计", layout="wide")
    st.title("🧪 V8 物理链路全过程审计")

    # --- 1. 数据输入 ---
    with st.sidebar:
        st.header("配置参数")
        default_seq = "B,P,B,B,P,B,B,B,B" 
        raw_str = st.text_area("原始路单:", default_seq, height=100)
        h_min = st.slider("HIST_MIN (门槛)", 2, 5, 3)

    clean_seq = [x.strip().upper() for x in raw_str.split(",") if x.strip() in ['B', 'P']]

    # --- 2. 📡 第一阶段：Redis 连接审计 ---
    st.subheader("1. Redis 物理连接检查")
    redis_url = st.secrets.get("LOCAL_REDIS_URL", "redis://localhost:6379/0")
    
    with st.status("正在尝试物理连接...", expanded=True) as status:
        try:
            adapter = RedisAdapter(redis_url)
            if adapter.client.ping():
                st.success(f"✅ 物理连接成功！目标: `{redis_url}`")
            status.update(label="Redis 连接就绪", state="complete")
        except Exception as e:
            st.error(f"❌ 物理连接失败: {e}")
            return

    # --- 3. 🧬 第二阶段：指纹特征计算审计 ---
    st.subheader("2. 指纹特征计算过程")
    c_side, c_len, hB_raw, hP_raw = get_fp_components(clean_seq)
    
    # 物理过滤与类型对齐
    hB_f = {str(k): v for k, v in apply_v8_sampling_logic(hB_raw).items() if int(k) >= h_min}
    hP_f = {str(k): v for k, v in apply_v8_sampling_logic(hP_raw).items() if int(k) >= h_min}
    
    state_hash = generate_fp_hash(c_side, c_len, hB_f, hP_f, h_min)
    
    st.write("**当前计算生成的 ID (SHA256):**")
    st.info(f"`{state_hash}`")

    # --- 4. 🔍 第三阶段：数据库检索审计 ---
    st.subheader("3. 数据库检索审计")
    st.markdown("**发送给 Redis 的查询语句：**")
    st.code(f"HGETALL {state_hash}", language="bash")
    
    start_time = time.time()
    decision = adapter.get_state_decision(state_hash)
    duration = time.time() - start_time

    if decision:
        st.success(f"🎯 **物理命中！** (耗时: {duration:.4f}s)")
        st.markdown("**查询返回的结果：**")
        st.json(decision)
        st.balloons()
    else:
        st.error(f"⚠️ **未命中 (NOT FOUND)** (耗时: {duration:.4f}s)")
        st.warning(f"请检查终端 `redis-cli` 中是否存在该 Key。")

if __name__ == "__main__":
    main()