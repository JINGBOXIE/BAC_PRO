import streamlit as st
import os
import sys
import pandas as pd
import random
import redis

# 1. 路径注入
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from modules.i18n import TRANSLATIONS
from modules.road_renderer import render_big_road
from modules.stats_manager import update_shoe_stats
from modules.bankroll_engine import initialize_bankroll, settle_hand
from dealer.baccarat_dealer import BaccaratDealer, ShoeFactory
from modules.ui_components import render_casino_table, render_bias_panel, render_snapshot_ai
from core.sbi_full_model import compute_sbi_ev_from_counts
from core.snapshot_engine import get_fp_components
from core.db_adapter import RedisAdapter, generate_fp_hash 
def render_practice_tab(lang):

    # --- 1. 全局 UI 样式配置 (放在这里) ---
    container_style = """
        padding: 18px; 
        border: 2px solid #1E90FF; 
        border-radius: 15px; 
        background-color: rgba(10, 20, 30, 0.6); 
        box-shadow: 0 4px 15px rgba(0,0,0,0.3); 
        min-height: 250px; 
        font-family: sans-serif;
    """

    header_style = """
        font-weight: bold; 
        color: #1E90FF; 
        font-size: 1.1rem; 
        letter-spacing: 1px; 
        margin-bottom: 12px; 
        border-bottom: 1px solid #1E90FF44; 
        padding-bottom: 8px; 
        display: flex; 
        justify-content: space-between; 
        align-items: center;
    """

    # tabs/tab_practice.py 内部初始化部分
    if 'clean_results' not in st.session_state:
        st.session_state.clean_results = []  # 专门存放剔除 T 后的序列
    # 抽取翻译工具函数（适配当前 session_state.lang）
    def t(key): return TRANSLATIONS.get(st.session_state.lang, {}).get(key, key)

    # --- 3. CSS 样式 (保持原样) ---
    
    st.markdown("""
    <style>
        [data-testid="stSidebarContent"] { padding-top: 1rem !important; }
        [data-testid="stVerticalBlock"] > div { gap: 0.5rem !important; }
        
        /* ✅ 删除或注释掉下面这一行 */
        /* [data-testid="stNumberInput"] label { height: 0px; overflow: hidden; display: none; } */
        
        hr { margin-top: 0.8rem !important; margin-bottom: 0.8rem !important; }
    </style>
""", unsafe_allow_html=True)
    
    def handle_deal_click():
        # 获取当前下注额
        bet_b = st.session_state.get("bet_input_red", 0)
        bet_p = st.session_state.get("bet_input_blue", 0)
        current_bets = {"B": int(bet_b), "P": int(bet_p), "T": 0}
        total_bet = sum(current_bets.values())

        if total_bet <= st.session_state.balance:
            try:
                # 1. 执行发牌
                oc = st.session_state.dealer.deal_one_hand(st.session_state.shoe)
                st.session_state.last_outcome_obj = oc
                
                # 2. 更新统计和路单
                st.session_state.rank_counts, st.session_state.stats = update_shoe_stats(
                    oc, st.session_state.rank_counts, st.session_state.stats
                )
                st.session_state.results.append(oc.winner)
                if oc.winner in ['B', 'P']:
                    st.session_state.clean_results.append(oc.winner)
                
                # 3. 财务结算
                new_bal, net_profit, _ = settle_hand(oc.winner, current_bets, st.session_state.balance)
                st.session_state.balance = new_bal
                
                # 4. 记录历史
                if total_bet > 0:
                    st.session_state.bet_history.append({
                        "hand_no": len(st.session_state.results),
                        "winner": oc.winner,
                        "net": net_profit
                    })

                # 🔥 重点：在回调中直接清零，这是合法的
                st.session_state.bet_input_red = 0
                st.session_state.bet_input_blue = 0

            except IndexError:
                st.session_state.end_shoe = True
    # tabs/tab_practice.py

    def reset_logic():
        import random
        # 核心物理重置
        if 'clean_results' not in st.session_state:
            st.session_state.clean_results = []
        
        # 确保 factory 已存在
        if 'factory' not in st.session_state:
            from core.deal_adapter import ShoeFactory # 假设类名
            st.session_state.factory = ShoeFactory()

        st.session_state.shoe = st.session_state.factory.create_shoe()
        st.session_state.results = []
        st.session_state.stats = {"B": 0, "P": 0, "T": 0}
        st.session_state.rank_counts = {i: (128 if i == 0 else 32) for i in range(10)}
        st.session_state.last_outcome_obj = None
        
        # 切牌线重置
        st.session_state.cut_card_at = random.randint(60, 80)
        st.session_state.end_shoe = False
        
        # 🚨 核心修改：清空当前牌靴的投注记录
        st.session_state.bet_history = []
        

        # 🚨 必须强制赋值为空列表，不能只用 if not in
        st.session_state.clean_results = [] 
        st.session_state.results = []
        
        # 🚨 同步重置状态
        st.session_state.last_fp_advice = {
            "match": False, 
            "fp_id": "READY", 
            "action": "WAIT", 
            "edge": 0.0, 
            "ev_info": {}
        }

    if 'bac_pro_v8_final' not in st.session_state:
        st.session_state.dealer = BaccaratDealer()
        st.session_state.factory = ShoeFactory(decks=8)
        st.session_state.balance = 10000.0
        reset_logic()
        st.session_state.bac_pro_v8_final = True



# --- 5. 侧边栏 (请确保此行相对于函数定义有正确的缩进) ---
    with st.sidebar:
        # --- 5.A 顶部：下注区分割线 (中英双语) ---
        divider_text = "BETTING ZONE" if st.session_state.lang == "EN" else "下注区"
        st.markdown(f"""
            <div style="display: flex; align-items: center; margin: 10px 0px 15px 0px;">
                <div style="flex-grow: 1; height: 1px; background: #444;"></div>
                <span style="padding: 0 10px; color: #888; font-size: 0.75rem; font-weight: bold; letter-spacing: 1px;">{divider_text}</span>
                <div style="flex-grow: 1; height: 1px; background: #444;"></div>
            </div>
        """, unsafe_allow_html=True)

        # --- 5.B 实时下注数额显示面板 ---
        current_b = st.session_state.get('bet_input_red', 0)
        current_p = st.session_state.get('bet_input_blue', 0)

        side_label_b = "🔴 BANKER" if st.session_state.lang == "EN" else "🔴 庄"
        side_label_p = "🔵 PLAYER" if st.session_state.lang == "EN" else "🔵 闲"

        st.markdown(f"""
            <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; border: 1px solid #444; margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                    <span style="font-size: 0.7rem; color: #888;">{side_label_b}</span>
                    <span style="font-size: 1.1rem; font-weight: bold; color: #FF4500;">${current_b:,.0f}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 0.7rem; color: #888;">{side_label_p}</span>
                    <span style="font-size: 1.1rem; font-weight: bold; color: #1E90FF;">${current_p:,.0f}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # --- 5.C 核心样式注入：物理抹除 Label + 强制注入背景色 ---
        # 针对 InputContextContainer 染色是解决“白色底色”的关键
        st.markdown("""
        <style>
            /* 1. 彻底隐藏所有 number_input 的标签 (B/P) */
            section[data-testid="stSidebar"] div[data-testid="stNumberInput"] label {
                display: none !important;
                height: 0px !important;
                visibility: hidden !important;
            }

            /* 2. 庄 (B) 输入框强力染色：使用 :has 穿透到背景层 */
            section[data-testid="stSidebar"] div.stNumberInput:has(input[aria-label="B"]) div[data-testid="stNumberInput-InputContextContainer"] {
                background-color: rgba(255, 69, 0, 0.25) !important;
                border: 1px solid rgba(255, 69, 0, 0.5) !important;
                border-radius: 4px !important;
            }
            section[data-testid="stSidebar"] div.stNumberInput:has(input[aria-label="B"]) input {
                color: #FF4500 !important;
                font-weight: bold !important;
            }

            /* 3. 闲 (P) 输入框强力染色 */
            section[data-testid="stSidebar"] div.stNumberInput:has(input[aria-label="P"]) div[data-testid="stNumberInput-InputContextContainer"] {
                background-color: rgba(30, 144, 255, 0.25) !important;
                border: 1px solid rgba(30, 144, 255, 0.5) !important;
                border-radius: 4px !important;
            }
            section[data-testid="stSidebar"] div.stNumberInput:has(input[aria-label="P"]) input {
                color: #1E90FF !important;
                font-weight: bold !important;
            }

            /* 4. 解决部分版本白色底色残留问题 */
            section[data-testid="stSidebar"] input {
                background-color: transparent !important;
            }
        </style>
        """, unsafe_allow_html=True)

        # --- 5.D 物理输入框区 ---
        sb2, sb1 = st.columns(2)
        # 这里的 "B" 和 "P" 是 CSS 识别的关键钥匙
        bet_b = sb1.number_input("B", min_value=0, step=100, key="bet_input_red")
        bet_p = sb2.number_input("P", min_value=0, step=100, key="bet_input_blue")

        # --- 5.E 剩余牌数与投注记录 ---
        remaining = len(st.session_state.shoe)
        if remaining <= st.session_state.cut_card_at:
            st.session_state.end_shoe = True
        
        st.caption(f"Remaining: {remaining} (Cut: {st.session_state.cut_card_at})")

        exp_title = "💰 Betting History" if st.session_state.lang == "EN" else "💰 投注记录"
        with st.expander(exp_title, expanded=True):
            st.metric("Balance (USD)", f"${st.session_state.balance:,.2f}")
            if st.session_state.get('bet_history'):
                history_html = ""
                for rec in reversed(st.session_state.bet_history):
                    net_color = "#00FFAA" if rec['net'] > 0 else "#FF4444" if rec['net'] < 0 else "#888"
                    history_html += f"""
                    <div style='font-size:0.8rem; margin-bottom:8px; border-bottom:1px solid #444; padding-bottom:4px; font-family:monospace;'>
                        <span style='color:#888;'>#{rec['hand_no']}</span> | <b>{rec['winner']}</b> | 
                        <span style='color:{net_color};'>${rec['net']:+,.2f}</span>
                    </div>"""
                st.markdown(f'<div style="height: 200px; overflow-y: auto;">{history_html}</div>', unsafe_allow_html=True)
            else:
                st.caption("No records." if st.session_state.lang == "EN" else "本靴暂无记录")

        if st.session_state.end_shoe:
            st.warning("🟥 切牌线已到" if st.session_state.lang == "CN" else "🟥 CUT CARD REACHED")

    # --- 6. 主界面渲染 ---
    # 获取当前语言字典 (与 i18n.py 键值对齐)
    lt = TRANSLATIONS.get(st.session_state.lang, {})
    # 第一步：渲染牌桌（发牌图片）
    render_casino_table(st.session_state.get('last_outcome_obj'), lang=st.session_state.lang)
    # --- 2. 核心：并排按钮区 (视觉焦点 2) ---
    st.markdown("<br>", unsafe_allow_html=True) 
    
    _, btn_container, _ = st.columns([1, 2, 1])
    
    with btn_container:
        c1, c2 = st.columns(2)
        with c1:
            # 使用 on_click 绑定刚才定义的函数
            st.button(
                lt.get("btn_deal", "发牌 (DEAL)"), 
                use_container_width=True, 
                type="primary", 
                disabled=st.session_state.end_shoe,
                on_click=handle_deal_click  # 绑定回调
            )
                
        with c2:
            if st.button(lt.get("btn_new_shoe", "洗牌 (NEW SHOE)"), use_container_width=True):
                reset_logic()
                st.balloons()
                st.rerun()

    # --- 3. 大路演示图 (视觉焦点 3 - CSS 物理擦除标签) ---
    st.markdown("""
        <style>
        /* 强制隐藏渲染函数中可能带有的 subheader (h3) */
        [data-testid="stVerticalBlock"] > div:nth-child(n) h3 {
            display: none !important;
        }
        /* 极致缩减路图与按钮之间的间距 */
        hr { margin-top: 0.2rem !important; margin-bottom: 0.5rem !important; }
        .stPlotlyChart { margin-top: -10px !important; }
        </style>
    """, unsafe_allow_html=True)
    
# --- 2.5 实时统计：[B | T | P] 终极防漏 + 多语言版 ---
    stats = st.session_state.get('stats', {"B": 0, "P": 0, "T": 0})
    total_hands = sum(stats.values())
    
    # 定义清洗函数：核心是去掉字符串中连续的空格，防止触发 Markdown 代码块识别
    def clean_translate(text):
        import re
        # 将多个空格替换为一个空格，并移除换行
        return re.sub(r'\s+', ' ', text).strip()

    # 获取并清洗翻译
    txt_b = clean_translate(lt.get('stat_b', 'BANKER'))
    txt_t = clean_translate(lt.get('stat_t', 'TIE'))
    txt_p = clean_translate(lt.get('stat_p', 'PLAYER'))

    def get_pct(val):
        if total_hands == 0: return "0%"
        return f"{(val/total_hands)*100:.1f}%"

    # 构造 HTML：严格物理顺序 B | T | P
    # 注意：div 标签必须紧贴左侧，不要有任何前置空格或 Tab
    stats_html = f"""
<div style="display: flex; justify-content: space-around; background: rgba(255,255,255,0.03); padding: 12px; border-radius: 12px; margin: 10px 0; border: 1px solid #444; align-items: center;">
<div style="text-align: center; flex: 1;">
<div style="font-size: 0.75rem; color: #BBB; margin-bottom: 5px;">{txt_b}</div>
<div style="display: flex; align-items: baseline; justify-content: center; gap: 6px;">
<span style="font-size: 1.4rem; font-weight: bold; color: #FF4500;">{stats['B']}</span>
<span style="font-size: 0.9rem; color: #FF4500CC;">({get_pct(stats['B'])})</span>
</div>
</div>
<div style="text-align: center; flex: 1; border-left: 1px solid #444; border-right: 1px solid #444; padding: 0 5px;">
<div style="font-size: 0.75rem; color: #BBB; margin-bottom: 5px;">{txt_t}</div>
<div style="display: flex; align-items: baseline; justify-content: center; gap: 6px;">
<span style="font-size: 1.4rem; font-weight: bold; color: #00FFAA;">{stats['T']}</span>
<span style="font-size: 0.9rem; color: #00FFAACC;">({get_pct(stats['T'])})</span>
</div>
</div>
<div style="text-align: center; flex: 1;">
<div style="font-size: 0.75rem; color: #BBB; margin-bottom: 5px;">{txt_p}</div>
<div style="display: flex; align-items: baseline; justify-content: center; gap: 6px;">
<span style="font-size: 1.4rem; font-weight: bold; color: #1E90FF;">{stats['P']}</span>
<span style="font-size: 0.9rem; color: #1E90FFCC;">({get_pct(stats['P'])})</span>
</div>
</div>
</div>
"""
    # 🚨 这里的关键：直接渲染，不留任何被识别为代码块的机会
    st.markdown(stats_html.strip(), unsafe_allow_html=True)




    # 第二步：紧贴渲染 Big Road (路单)
    st.subheader(t("big_road"))
    render_big_road(st.session_state.results)

    st.divider()

    
    # --- 7. 双核诊断面板 ---
    col_left, col_right = st.columns(2)
    with col_left:
            # A. 生成 18位 Key
            out_rk_list = [f"{(32 - st.session_state.rank_counts.get(i, 32)):02d}" for i in range(1, 10)]
            current_rk = "".join(out_rk_list).strip()
            
            # B. 加载数据
            if 'golden_pool' not in st.session_state or not st.session_state.golden_pool:
                try:
                    import json
                    import os
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    json_path = os.path.join(current_dir, "bac_rank_bias_gold.json")
                    if os.path.exists(json_path):
                        with open(json_path, "r") as f:
                            raw_data = json.load(f)
                            st.session_state.golden_pool = {str(item['rank_state_key']).strip(): item for item in raw_data}
                    else:
                        st.session_state.golden_pool = {}
                except:
                    st.session_state.golden_pool = {}

            # C. 获取数据与多语言定义
            is_cn = st.session_state.lang == "CN"
            label_theoretical = "理论模型 (SBI)" if is_cn else "THEORETICAL (SBI)"
            label_historical = "大数据字典 (DICT)" if is_cn else "HISTORICAL (DICT)"
            label_init = "初始状态" if is_cn else "INITIAL STATE"
            label_miss = "未命中" if is_cn else "MISS"
            display_title = "🎯 双核算牌分析" if is_cn else "🎯 RANK BIAS DUAL-CORE"

            # D. 计算 SBI 算法核心
            sbi_res = compute_sbi_ev_from_counts(total_decks=8, rank_counts=st.session_state.rank_counts)
            sbi_p = sbi_res.get('ev_p', -0.0124) * 100
            sbi_b = sbi_res.get('ev_b_comm', -0.0106) * 100
            
            gold_match = st.session_state.golden_pool.get(current_rk)
            
            # E. 状态逻辑判定
            if gold_match:
                dict_p, dict_b = gold_match.get('ev_p', 0) * 100, gold_match.get('ev_b', 0) * 100
                sample_size = gold_match.get('sample_size', 0)
                dict_status = f"HIT (n={sample_size:,.0f})"
                dict_color, val_style = "#FFD700", "color: #FFD700; font-weight: bold;"
            elif current_rk == "000000000000000000":
                dict_p, dict_b = -1.24, -1.06
                dict_status = label_init
                dict_color, val_style = "#00FFAA", "color: #ffffff;"
            else:
                dict_p, dict_b = 0.0, 0.0
                dict_status = f"{label_miss} (DB:{len(st.session_state.golden_pool)})"
                dict_color, val_style = "#888888", "color: #666666;"

            # F. 构建纯净 HTML 字符串 (杜绝换行符和非法空格导致的渲染失败)
            h = f'<div style="{container_style}">'
            h += f'<div style="{header_style}"><span>{display_title}</span>'
            h += '<span style="font-size:0.6rem;color:#555;background:rgba(0,0,0,0.2);padding:2px 6px;border-radius:4px;">SBI-PRO</span></div>'
            h += f'<div style="font-size:0.8rem;color:#aaa;margin-bottom:15px;font-family:\'Courier New\',monospace;background:rgba(255,255,255,0.07);padding:6px;border-radius:5px;border:1px solid #444;">'
            h += f'Fingerprint: <span style="color:#00FFAA;">{current_rk}</span></div>'
            h += f'<div style="margin-bottom:18px;border-left:4px solid #1E90FF;padding-left:12px;">'
            h += f'<div style="font-size:0.7rem;color:#1E90FF;font-weight:bold;letter-spacing:1px;">{label_theoretical}</div>'
            h += f'<div style="font-size:1.2rem;margin-top:3px;"><span style="color:#ffffff;">P: {sbi_p:+.2f}%</span> | <span style="color:#ffffff;">B: {sbi_b:+.2f}%</span></div></div>'
            h += f'<div style="border-left:4px solid {dict_color};padding-left:12px;">'
            h += f'<div style="font-size:0.7rem;color:{dict_color};font-weight:bold;letter-spacing:1px;">{label_historical} - {dict_status}</div>'
            h += f'<div style="font-size:1.2rem;margin-top:3px;{val_style}"><span>P: {dict_p:+.2f}%</span> | <span>B: {dict_b:+.2f}%</span></div></div></div>'

            # G. 强制清洗并渲染 (关键步骤)
            clean_h = h.replace('\xa0', ' ').replace('\n', '').strip()
            st.markdown(clean_h, unsafe_allow_html=True)              
    with col_right:
            # 1. 语言配置
            is_cn = st.session_state.get('lang', 'CN') == 'CN'
            lang_map = {
                "title": "🔍 AI FINGERPRINT SCANNING" if not is_cn else "🔍 AI 指纹扫描决策",
                "waiting": "Waiting for shuffling..." if not is_cn else "等待新靴开牌...",
                "action_label": "Best Action" if not is_cn else "最优决策",
                "edge_label": "Edge Advantage" if not is_cn else "优势概率",
                "insufficient": "DEPTH INSUFFICIENT" if not is_cn else "序列深度不足",
                "miss": "FINGERPRINT MISS" if not is_cn else "未匹配到有效指纹",
            }

            # 核心逻辑导入
            

            # 2. Redis 连接初始化 (集成环境切换逻辑)
            if 'redis_adapter' not in st.session_state:
                try:
                    use_cloud = st.secrets.get("USE_CLOUD_REDIS", False)
                    target_url = st.secrets["UPSTASH_REDIS_URL"] if use_cloud else st.secrets["LOCAL_REDIS_URL"]
                    st.session_state.redis_adapter = RedisAdapter(target_url)
                    
                    mode_msg = "Online" if use_cloud else "Local"
                    st.toast(f"Connected to {mode_msg} Redis")
                except Exception as e:
                    st.error(f"Redis Connection Error: {e}")

            # 3. 变量初始化 (物理对齐修复，防止 UnboundLocalError)
            clean_seq = st.session_state.get('clean_results', [])
            h_min = st.session_state.get('hist_min', 3)  # 这样它就会实时同步侧边栏的滑动数值  # 采样器门槛
            fp_advice = {"match": False, "status": "WAITING"}
            
            # 🟢 像素对齐修改：引用全局外壳变量
            html = f'<div style="{container_style}">'
            html += f'''<div style="{header_style}">
                        <span>{lang_map["title"]}</span><span style="font-size: 0.6rem; color: #555; background: rgba(0,0,0,0.2); padding: 2px 6px; border-radius: 4px;">V8-PRO</span>
                      </div>'''

            
               # --- 4. 状态逻辑处理 (V8 极致物理对齐版) ---
            # 初始化变量，防止 UnboundLocalError
            state_hash = None 
            fp_advice = {"match": False, "status": "WAITING", "fp_id": ""}

            if clean_seq:
                # 🚀 A. 一站式整理 (整理工厂)
                # 内部已包含：物理隔离、归口处理、生存统计(>=LEN)、H_MIN过滤
                components = get_fp_components(clean_seq, h_min=h_min)
                c_side, c_len, hB_f, hP_f, _ = components # 结构化解包

                # 🚀 B. 约束检查
                # 只有当历史区在 H_MIN 以上确实存在数据时才继续
                if not hB_f and not hP_f:
                    fp_advice.update({
                        "status": lang_map["insufficient"],
                        "fp_id": "SCOPE_BELOW_THRESHOLD"
                    })
                else:
                    # 🚀 C. 计算 (直接使用 * 解包 5 要素，物理对齐)
                    state_hash = generate_fp_hash(*components)
                    
                    # 🚀 D. 执行 Redis 查询
                    decision = st.session_state.redis_adapter.get_state_decision(state_hash)

                    if decision:
                        fp_advice.update({
                            "match": True,
                            "action": decision["action"],
                            "edge": decision["edge"],
                            "ev_cut": decision["ev_cut"],
                            "ev_cont": decision["ev_cont"],
                            "fp_id": state_hash
                        })
                        
                        # 🎈 特效触发器
                        if st.session_state.get("last_balloon_hash") != state_hash:
                            st.balloons()
                            if decision["edge"] > 0.01: st.snow()
                            st.session_state.last_balloon_hash = state_hash
                    else:
                        fp_advice.update({
                            "status": lang_map["miss"], 
                            "fp_id": state_hash
                        })

                # --- 调试打印 (清晰简练) ---
                print("\n" + "⚡" * 25)
                print(f"🔍 [V8-DEBUG] H_MIN: {h_min} | CUR: {c_side}{c_len}")
                print(f"📊 B_f: {hB_f}")
                print(f"📊 P_f: {hP_f}")
                print(f"🔑 HASH: {state_hash}")
                print(f"🏁 STATUS: {fp_advice['status']}")
                print("⚡" * 25 + "\n")
                
                # --- 5. HTML 内容填充逻辑 ---
            if not fp_advice.get('match') and fp_advice.get('status') == 'WAITING':
                # 🟢 像素对齐微调：居中内边距
                html += f'<div style="color:#666; text-align:center; padding-top: 50px;">{lang_map["waiting"]}</div>'
            
            elif fp_advice.get('match'):
                fid = fp_advice["fp_id"]
                act = fp_advice["action"]
                edge_pct = f'{fp_advice["edge"]:+.2%}'
                e_cut_pct = f'{fp_advice["ev_cut"]*100:+.2f}%'
                e_cont_pct = f'{fp_advice["ev_cont"]*100:+.2f}%'

                html += f'''
                <div>
                    <div style="font-family: monospace; font-size: 0.65rem; color: #1E90FF; background: rgba(0,0,0,0.3); padding: 5px 10px; border-radius: 4px; margin-bottom: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{fid}">
                        Fingerprint: {fid}
                    </div>
                    <div style="text-align: center; margin-bottom: 15px;">
                        <div style="font-size: 0.7rem; color: #888; text-transform: uppercase;">{lang_map["action_label"]}</div>
                        <div style="font-size: 2.2rem; font-weight: 800; color: #00FFAA; text-shadow: 0 0 10px rgba(0,255,170,0.4);">{act}</div>
                    </div>
                    <div style="display: flex; gap: 10px; margin-bottom: 12px;">
                        <div style="flex: 1; background: rgba(255,255,255,0.05); padding: 8px; border-radius: 8px; text-align: center; border: 1px solid #444;">
                            <div style="font-size: 0.6rem; color: #aaa;">EV (CUT)</div>
                            <div style="font-size: 1.0rem; font-weight: bold; color: #fff;">{e_cut_pct}</div>
                        </div>
                        <div style="flex: 1; background: rgba(255,255,255,0.05); padding: 8px; border-radius: 8px; text-align: center; border: 1px solid #444;">
                            <div style="font-size: 0.6rem; color: #aaa;">EV (CONT)</div>
                            <div style="font-size: 1.0rem; font-weight: bold; color: #fff;">{e_cont_pct}</div>
                        </div>
                    </div>
                    <div style="text-align: center; background: rgba(0,255,170,0.1); padding: 5px; border-radius: 20px; border: 1px solid #00FFAA33;">
                        <span style="font-size: 0.8rem; color: #00FFAA; font-weight: bold;">{lang_map["edge_label"]}: {edge_pct}</span>
                    </div>
                </div>
                '''
            else:
                # 🟢 像素对齐微调：居中内边距
                html += f'''
                <div style="margin-top: 45px; text-align:center;">
                    <div style="color:#FF4444; font-size: 0.9rem; margin-bottom: 8px; font-weight:bold;">⚠️ {fp_advice["status"]}</div>
                    <div style="font-family: monospace; font-size: 0.6rem; color: #555; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 0 20px;" title="{fp_advice.get("fp_id","")}">
                        ID: {fp_advice.get("fp_id","")}
                    </div>
                </div>
                '''

            html += '</div>'
            
            # 6. 渲染到界面
            st.markdown(html, unsafe_allow_html=True)


