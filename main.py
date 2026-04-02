# main.py
import streamlit as st
import os
import sys

# 1. 路径注入，确保能导入所有子目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# 导入翻译函数和子模块
from modules.i18n import t
from tabs.tab_practice import render_practice_tab

# 2. 全局页面配置 (必须是 Streamlit 命令的第一行)
st.set_page_config(
    layout="wide", 
    page_title="BACC-PRO 3.1 | JStudio", 
    page_icon="🤖" # 这里你可以换成更符合 JStudio 的图标
)

# 3. 初始化全局状态
if 'lang' not in st.session_state:
    st.session_state.lang = "CN"

# 4. 侧边栏导航控制 (主导航中心)

with st.sidebar:
    # 1. 确保文件名与本地文件完全一致（包括空格）
    logo_filename = "J Studio LOGO.PNG"
    
    # 获取当前文件所在目录，确保路径跨平台兼容
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(curr_dir, logo_filename)

    if os.path.exists(logo_path):
        # ✅ 使用 width="stretch" 替代 use_column_width
        st.image(logo_path, width="stretch")
    else:
        # 如果还是找不到，尝试直接用文件名（Streamlit 有时能自动处理相对路径）
        try:
            st.image(logo_filename, width=360)
            #st.image(logo_filename, width="stretch")
        except:
            st.subheader("J Studio") # 兜底显示文字
    
    st.divider()
        # 此滑块直接定义“拍照/观察范围” 
    st.session_state.hist_min = st.slider(
        "FINGERPRINT SCOPE (hist_min)",
        min_value=1,
        max_value=14,
        value=3,
        help="设定指纹生成的最小连单粒度。3代表忽略1-2连的噪音干扰。"
    )

    
    # ✅ 3. 唯一的语言切换器 (负责全局状态)
    # 定义一个映射字典
    lang_options = {"CN": "中文", "EN": "English"}

    # 在 sidebar 中渲染
    st.session_state.lang = st.radio(
        "语言 / LANGUAGE",
        options=list(lang_options.keys()), # 实际上选的是 "CN" 或 "EN"
        index=0 if st.session_state.lang == "CN" else 1,
        format_func=lambda x: lang_options[x], # 👈 关键：界面上显示的是 "中文" 或 "English"
        horizontal=True
    )
    
    st.divider()
    
    # ✅ 4. 功能菜单
    choice = st.radio(
        "MENU",
        [t("nav_practice", st.session_state.lang), 
         t("nav_ai", st.session_state.lang), 
         t("nav_knowledge", st.session_state.lang)],
        label_visibility="collapsed"
    )

# 5. 路由分发 (100% 隔离各个 Tab 的逻辑)
if choice == t("nav_practice", st.session_state.lang):
    # 调用转换后的练习模块，传入当前语言
    render_practice_tab(st.session_state.lang)

elif choice == t("nav_ai", st.session_state.lang):
    st.header(t("nav_ai", st.session_state.lang))
    st.info("AI 实战视觉模块正在接入中..." if st.session_state.lang == "CN" else "AI Vision Module connecting...")

elif choice == t("nav_knowledge", st.session_state.lang):
    st.header(t("nav_knowledge", st.session_state.lang))
    st.markdown("### 简单与专注 (Simplicity & Focus)")