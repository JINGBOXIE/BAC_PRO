import streamlit as st
import os
import base64

def get_base64_img(relative_path):
    """🧱 路径兼容逻辑：自动寻找项目根目录并转码图片"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_path = os.path.join(base_dir, relative_path)
    if os.path.exists(full_path):
        with open(full_path, "rb") as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    return ""

def render_casino_table(last_outcome, lang="CN"):
    """🃏 初始化保留背景大小 + 暴力扫描比分"""
    
    # 1. 提取数据 (带暴力抓取逻辑)
    ps, bs = 0, 0
    winner = 'T'
    p_cards, b_cards = [], []
    
    if last_outcome:
        winner = getattr(last_outcome, 'winner', 'T')
        p_cards = getattr(last_outcome, 'player_cards', [])
        b_cards = getattr(last_outcome, 'banker_cards', [])
        # 暴力扫描属性获取比分
        try:
            for a in dir(last_outcome):
                val = getattr(last_outcome, a)
                if not isinstance(val, (int, float)): continue
                name = a.lower()
                if ('p_' in name or 'player' in name) and any(x in name for x in ['score', 'point', 'val']):
                    ps = int(val)
                if ('b_' in name or 'banker' in name) and any(x in name for x in ['score', 'point', 'val']):
                    bs = int(val)
        except: pass

    # 2. 颜色与文字逻辑
    # 发牌前默认灰色，发牌后根据结果变色
    if not last_outcome:
        banner_color = "#555"
        res_text = "等待发牌..." if lang == "CN" else "WAITING..."
    else:
        banner_color = "#1E90FF" if winner == 'P' else "#FF4500" if winner == 'B' else "#32CD32"
        win_map = {"P": "闲赢", "B": "庄赢", "T": "和局"} if lang == "CN" else {"P": "PLAYER WIN", "B": "BANKER WIN", "T": "TIE"}
        res_text = f"{'结果: ' if lang=='CN' else 'RESULT: '}{win_map.get(winner, '')}"

    # 3. 注入 CSS (固定高度，防止抖动)
    st.markdown(f"""
        <style>
            .result-banner {{ 
                text-align: center; background: #1a1a1a; color: {banner_color}; 
                padding: 12px; font-weight: bold; border-radius: 12px 12px 0 0; 
                border: 1px solid #333; font-size: 1.3rem; min-height: 55px;
            }}
            .table-container {{ 
                display: flex; justify-content: space-around; background: #072b11; 
                padding: 25px 10px; border-radius: 0 0 12px 12px; border: 1px solid #333; 
                min-height: 220px; /* 关键：保留原始大小 */
            }}
            .casino-card {{ 
                width: 60px; height: 90px; margin: 3px; border-radius: 4px; 
                display: inline-block; vertical-align: middle; 
                box-shadow: 2px 2px 8px rgba(0,0,0,0.5);
                background: rgba(255,255,255,0.05); /* 未发牌时的阴影占位 */
            }}
            .third-card-rotate {{ transform: rotate(90deg); margin: 0 -12px; position: relative; top: 8px; }}
            .winner-glow {{ border: 2px solid {banner_color}; box-shadow: 0 0 15px {banner_color}; }}
        </style>
    """, unsafe_allow_html=True)

    # 4. 生成牌面 HTML
    def get_cards_html(card_list, is_side_winner):
        if not card_list: # 发牌前显示两个半透明占位框
            return '<div class="casino-card"></div><div class="casino-card"></div>'
        
        html = ""
        IMG_DIR = "app/PIC/CARDS_PNG"
        suit_map = {"Hearts": "H", "Spades": "S", "Diamonds": "D", "Clubs": "C"}
        for idx, card_tuple in enumerate(card_list):
            c_str = str(card_tuple).replace("('", "").replace("')", "").replace("'", "").split(' of ')
            if len(c_str) == 2:
                filename = f"{c_str[0]}{suit_map.get(c_str[1], '')}.png"
                b64 = get_base64_img(f"{IMG_DIR}/{filename}")
                rotate = "third-card-rotate" if idx == 2 else ""
                win_class = "winner-glow" if is_side_winner else ""
                if b64:
                    html += f'<img src="{b64}" class="casino-card {win_class} {rotate}">'
        return html

    # 5. 渲染 UI
    st.markdown(f'<div class="result-banner">{res_text} (P:{ps} vs B:{bs})</div>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="table-container">
            <div style="text-align:center; flex:1;">
                <div style="color:#1E90FF; font-weight:bold; margin-bottom:12px; letter-spacing:2px;">PLAYER</div>
                <div>{get_cards_html(p_cards, winner == 'P')}</div>
            </div>
            <div style="text-align:center; flex:1;">
                <div style="color:#FF4500; font-weight:bold; margin-bottom:12px; letter-spacing:2px;">BANKER</div>
                <div>{get_cards_html(b_cards, winner == 'B')}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

def render_bias_panel(gold_sig, lang="CN"):
    """🎯 诊断面板：保持稳定布局"""
    if not gold_sig: gold_sig = {"hit": False}
    is_hit = gold_sig.get('hit', False)
    color = "#FFD700" if is_hit else "#32CD32"
    label = f"🎯 黄金序列: {gold_sig.get('side', 'SEARCH')}" if lang=="CN" else f"🎯 GOLDEN: {gold_sig.get('side', 'SEARCH')}"
    
    st.markdown(f"""
        <div style='border:2px solid {color}; padding:15px; border-radius:10px; 
                    background:rgba(0,0,0,0.2); margin-top:20px; text-align:center; min-height:80px;'>
            <div style='color:{color}; font-weight:bold; font-size:1.2rem;'>{label}</div>
        </div>
    """, unsafe_allow_html=True)