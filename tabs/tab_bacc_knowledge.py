#tabs/tab_bacc_knowledge.py
import streamlit as st
import os

def render_knowledge_tab(lang):
    """
    渲染知识库与哲学中心 (The Great Way, Made Simple)
    """
    is_cn = lang == "CN"
    
    # --- 1. 核心哲学内容 ---
    if is_cn:
        st.markdown("""
        ### 🧘 大道至简 
        
        > "⚠️百家乐百科正在建设中..."
        
        - **核心逻辑**：BacPro V8 并非预测运气，而是通过大数据识别胜率偏移。
        - **系统目标**：在概率的起伏中，寻找确定性的瞬间。
        - **修行准则**：纪律先行，概率为王。
        """)
    else:
        st.markdown("""
        ### 🧘 Simplicity & Focus 
        
        > "    ⚠️ Baccarat Wiki under construction..."
        
        - **Core Logic**: BacPro V8 is not about predicting luck, but identifying win-rate deviations via Big Data。
        - **System Goal**: To find moments of certainty amidst the fluctuations of probability。
        - **Discipline**: Discipline first; Probability is King。
        """)

    st.divider() # 视觉分割线

    # --- 2. J Studio 品牌展示 ---

    # 1. 确定当前文件位置
    curr_file_path = os.path.abspath(__file__)
    # 2. 找到 tabs 文件夹的父目录（即根目录）
    root_dir = os.path.dirname(os.path.dirname(curr_file_path))
    
    # 3. 这里的名称必须与你磁盘上的文件名完全一致（注意大小写和后缀）
    # 截图显示你上传的文件名是 "J Studio LOGO.jpg"
    logo_filename = "J Studio LOGO.PNG" 
    logo_path = os.path.join(root_dir, logo_filename)

    # 调试用：如果没显示，请取消下面这行的注释，运行后看看页面显示的路径对不对
    # st.write(f"正在尝试加载路径: {logo_path}")

    if os.path.exists(logo_path):
        st.image(logo_path, width=600, caption="Where Imagination Meets Execution")
    else:
        # 如果路径存在但仍不显示，可能是格式问题，尝试直接用 root 相对路径
        # 兜底显示
        st.caption("J Studio | The Great Way, Made Simple")