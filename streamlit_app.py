import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt

# 页面配置
st.set_page_config(page_title="BAC_PRO 智能终端", layout="wide")

# 数据加载逻辑
@st.cache_data
def load_data():
    csv_path = "data/premax_summary.csv.gz"
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    return None

df_ev = load_data()

# --- 主界面 ---
st.title("🃏 BAC_PRO 策略看板")
st.markdown("基于 **10亿次** 模拟数据的实时策略建议")

if df_ev is not None:
    # 侧边栏：输入
    st.sidebar.title("🎮 实战输入")
    side = st.sidebar.selectbox("当前方向 (Current Side)", ["B", "P"])
    length = st.sidebar.slider("连长度 (Streak Length)", 1, 15, 1)

    # 逻辑处理
    res = df_ev[(df_ev['cur_side'] == side) & (df_ev['cur_len'] == length)]
    
    if not res.empty:
        row = res.iloc[0]
        
        # 指标展示
        c1, c2, c3 = st.columns(3)
        with c1:
            edge = row['edge']
            color = "inverse" if edge > 0 else "normal"
            st.metric("边缘优势 (Edge)", f"{edge:.4%}")
        with c2:
            st.metric("建议动作 (Action)", row['best_action'])
        with c3:
            st.metric("模拟样本量 (n_ge)", f"{int(row['n_ge']):,}")
            
        # 图表展示
        st.divider()
        st.write("### 概率分布 (Cut vs Continue)")
        prob_df = pd.DataFrame({
            "场景": ["切牌 (Cut)", "连牌 (Continue)"],
            "概率": [row['p_cut'], 1 - row['p_cut']]
        })
        st.bar_chart(prob_df.set_index("场景"))
    else:
        st.warning(f"数据库备份中暂无方向 {side} 长度 {length} 的记录。")
else:
    st.error("❌ 未找到数据文件！请确保已运行 python3 app/tools/export_core_ev.py 且生成了 data/ 目录。")
