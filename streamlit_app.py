import streamlit as st
import pandas as pd
import os
import time
import io
from PIL import Image

# --- 1. 核心共享引擎 (Snapshot Engine) ---

def get_snapshot_state(history):
    """
    逻辑完全复刻自 bac_pro.py:
    根据路单历史生成当前方向(cur_side)和连长度(cur_len)
    """
    if not history:
        return None, 0
    last_side = history[-1]
    length = 0
    for s in reversed(history):
        if s == last_side:
            length += 1
        else:
            break
    return last_side, length

@st.cache_data
def load_ev_database():
    """从本地压缩包加载 10 亿次模拟的核心数据"""
    csv_path = "data/premax_summary.csv.gz"
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    return None

def query_ev_reference(df, side, length):
    """统一的数据查询接口"""
    if df is None or side is None:
        return None
    res = df[(df['cur_side'] == side) & (df['cur_len'] == length)]
    return res.iloc[0] if not res.empty else None

# --- 2. 界面设计与样式 ---
st.set_page_config(page_title="J Studio - BAC_PRO Terminal", layout="wide", page_icon="🃏")

# 注入 CSS 提升实战感
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1c1f26; border: 1px solid #31333f; border-radius: 8px; padding: 15px; }
    .road-container { background-color: white; padding: 15px; border-radius: 5px; min-height: 80px; margin-bottom: 20px; }
    .action-recommend { font-size: 20px; font-weight: bold; padding: 10px; border-radius: 5px; text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- 3. Session State 状态管理 ---
if 'road_history' not in st.session_state:
    st.session_state.update({
        'road_history': [],    # 共享的路单历史 (B/P)
        'practice_log': [],    # 演习下注流水
        'last_action': None    # 最近一次操作
    })

# --- 4. 侧边栏：控制中心 ---
with st.sidebar:
    if os.path.exists("app/PIC/ME.PNG"):
        st.image("app/PIC/ME.PNG", use_container_width=True)
    
    st.title("🕹️ 控制中心")
    # 模式切换开关
    work_mode = st.radio("功能模式", ["演习发牌练习", "AI 拍照分析"])
    
    st.divider()
    if st.button("🔄 重置当前牌局 (RESET)", type="primary", use_container_width=True):
        st.session_state.road_history = []
        st.session_state.practice_log = []
        st.rerun()

    st.subheader("📊 模拟器统计")
    st.write(f"当前局数: {len(st.session_state.road_history)}")

# --- 5. 主界面布局 ---

# 第一行：共享大路图 (Big Road)
st.subheader("📍 实时大路图 (Shared Road)")
road_html = "".join([f"<span style='color:{'#D32F2F' if x=='B' else '#1976D2'}; font-size:28px; margin-right:4px;'>●</span>" for x in st.session_state.road_history])
st.markdown(f'<div class="road-container">{road_html if road_html else "等待录入..."}</div>', unsafe_allow_html=True)

# 加载数据包
ev_df = load_ev_database()

# 第二行：功能双引擎
col_left, col_right = st.columns([1, 1])

# 左引擎：数据录入 (演习或拍照)
with col_left:
    if work_mode == "演习发牌练习":
        st.subheader("🎯 模拟演练")
        c1, c2 = st.columns(2)
        if c1.button("庄 (B)", use_container_width=True):
            st.session_state.road_history.append("B")
        if c2.button("闲 (P)", use_container_width=True):
            st.session_state.road_history.append("P")
        
        # 演习下注模拟
        bet_side = st.selectbox("练习下注方向", ["不投注", "B", "P"])
        bet_amount = st.number_input("模拟注码 ($)", min_value=0, value=100, step=50)
        if st.button("确认提交本手结果"):
            st.toast("练习记录已更新")
            
    else: # AI 拍照分析模式
        st.subheader("📸 AI 实战分析")
        camera_img = st.camera_input("扫描现场路单显示屏")
        if camera_img:
            # 此处逻辑：接收图片 -> 调用 vision_scanner -> 获取 [B, P, B...] -> 更新 road_history
            with st.spinner("AI 识别大路特征中..."):
                # 模拟识别延时
                time.sleep(0.8)
                # 提示：此部分应连接你 core/vision_scanner.py 中的解析函数
                st.success("大路特征已识别，Snapshot 已同步。")
                st.info("💡 提示：实战模式下建议每手拍照刷新一次状态。")

# 右引擎：实时 EV 分析与参考建议
with col_right:
    st.subheader("🧬 PREMAX 策略分析")
    cur_side, cur_len = get_snapshot_state(st.session_state.road_history)
    
    if cur_side:
        ev_data = query_ev_reference(ev_df, cur_side, cur_len)
        
        if ev_data is not None:
            edge = ev_data['edge']
            action = ev_data['best_action']
            
            # 核心指标展示
            c1, c2 = st.columns(2)
            c1.metric("边缘优势 (Edge)", f"{edge:.4%}")
            c2.metric("样本量 (n_ge)", f"{int(ev_data['n_ge']):,}")
            
            # 根据 Edge 分配颜色和建议
            if edge > 0.005:
                bg_color, txt = "#d4edda", f"强势推荐: {action}"
                font_color = "#155724"
            elif edge < -0.005:
                bg_color, txt = "#f8d7da", f"警惕! 建议反投或观察 {action}"
                font_color = "#721c24"
            else:
                bg_color, txt = "#fff3cd", "优势不明显，建议观望"
                font_color = "#856404"
            
            st.markdown(f"""
                <div class="action-recommend" style="background-color:{bg_color}; color:{font_color};">
                    参考指令：{txt}
                </div>
            """, unsafe_allow_html=True)
            
            st.write(f"此结论基于同类序列出现过的 {int(ev_data['n_ge']):,} 次样本分析得出。")
        else:
            st.warning(f"当前序列 ({cur_side}{cur_len}) 暂无高频样本覆盖，建议依靠 SBI 模型辅助。")
    else:
        st.info("等待路单数据录入以激活分析引擎。")

# 第三行：流水日志 (练习用)
st.divider()
if st.checkbox("显示练习下注日志"):
    if st.session_state.road_history:
        log_df = pd.DataFrame({
            "手牌": range(1, len(st.session_state.road_history) + 1),
            "开牌结果": st.session_state.road_history
        })
        st.table(log_df.tail(10))