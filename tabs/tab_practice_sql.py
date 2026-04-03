import streamlit as st
import os
import sys
import pandas as pd
import random

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

def render_practice_tab(lang):
    """
    100% 还原原始测试版本的练习模块
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

    # --- 5. 侧边栏 (重构：投注记录与几率) ---
    # --- 5. 侧边栏 (调整布局顺序) ---
    with st.sidebar:
        #st.markdown(f"### ⚙️ {t('settings')}")
        #st.divider()

        # A. 投注输入区
        sb2, sb1 = st.columns(2)

        label_b = f"{t('🔴')}"
        label_p = f"{t('🔵')}"
        bet_b = sb1.number_input(label_b, min_value=0, step=100, key="bet_input_red")
        bet_p = sb2.number_input(label_p, min_value=0, step=100, key="bet_input_blue")

        # B. 核心发牌与换靴控制
        remaining_cards = len(st.session_state.shoe)
        if remaining_cards <= st.session_state.cut_card_at:
            st.session_state.end_shoe = True

        st.caption(f"Remaining: {remaining_cards} (Cut: {st.session_state.cut_card_at})")
        # 发牌按钮逻辑
        if st.button(t("deal_btn"), width="stretch", type="primary", disabled=st.session_state.end_shoe):
            current_bets = {"B": int(bet_b), "P": int(bet_p), "T": 0}
            total_bet = sum(current_bets.values())
            
            if total_bet <= st.session_state.balance:
                try:
                    # 1. 执行发牌
                    oc = st.session_state.dealer.deal_one_hand(st.session_state.shoe)
                    st.session_state.last_outcome_obj = oc
                    
                    # 2. 更新统计数据 (算牌核心)
                    st.session_state.rank_counts, st.session_state.stats = update_shoe_stats(
                        oc, st.session_state.rank_counts, st.session_state.stats
                    )
                    
                    # 3. 序列记录
                    # A. 原始路单（保留 T，用于大路渲染）
                    if 'results' not in st.session_state:
                        st.session_state.results = []
                    st.session_state.results.append(oc.winner)
                    
                    # B. 核心修改：生成 KEY 专用序列（严格剔除 T）
                    if 'clean_results' not in st.session_state:
                        st.session_state.clean_results = []
                        
                    if oc.winner in ['B', 'P']:
                        st.session_state.clean_results.append(oc.winner)
                    
                    # 4. 财务结算
                    new_bal, net_profit, _ = settle_hand(oc.winner, current_bets, st.session_state.balance)
                    st.session_state.balance = new_bal
                    
                    # 5. 记录投注历史
                    if total_bet > 0:
                        if 'bet_history' not in st.session_state: 
                            st.session_state.bet_history = []
                        st.session_state.bet_history.append({
                            "hand_no": len(st.session_state.results),
                            "winner": oc.winner,
                            "net": net_profit
                        })
                    
                    # 6. 强制刷新界面以更新指纹 KEY
                    st.rerun()
                    
                except IndexError:
                    st.session_state.end_shoe = True
                    st.rerun()
        
        
        # 新牌靴按钮
        if st.button(t("new_shoe"), width="stretch"):
            reset_logic()
            st.rerun()

        # 🚨 搬迁项 1：理论概率 (紧跟在 NEW SHOE 下方)
        sbi_raw = compute_sbi_ev_from_counts(total_decks=8, rank_counts=st.session_state.rank_counts)
        p_prob, b_prob, t_prob = sbi_raw.get('prob_p', 0.4462)*100, sbi_raw.get('prob_b', 0.4586)*100, sbi_raw.get('prob_t', 0.0952)*100
        odds_label = "🎲 理论概率" if st.session_state.lang == "CN" else "🎲 Theo Odds"
        
        st.markdown(
            f"""
            <div style="font-size: 0.82rem; background-color: rgba(255,255,255,0.05); padding: 8px; border-radius: 5px; border-left: 3px solid #00FFAA; margin-top: 10px;">
                <span style="font-weight: bold; color: #00FFAA; margin-right: 5px;">{odds_label}</span>
                <span style="color: #1E90FF;">P: {p_prob:.2f}%</span> | 
                <span style="color: #FF4500;">B: {b_prob:.2f}%</span> | 
                <span style="color: #888;">T: {t_prob:.2f}%</span>
            </div>
            """, 
            unsafe_allow_html=True
        )

        # 🚨 搬迁项 2：投注记录可收缩控件
        with st.expander(f"💰 {t('投注记录') if st.session_state.lang=='CN' else 'Betting History'}", expanded=True):
            st.metric("Total Balance (USD)", f"${st.session_state.balance:,.2f}")
            if st.session_state.get('bet_history'):
                history_html = "".join([
                    f"""<div style='font-size:0.8rem; margin-bottom:8px; border-bottom:1px solid #444; padding-bottom:4px; font-family:monospace;'>
                        <span style='color:#888;'>#{rec['hand_no']}</span> | <b>{rec['winner']}</b> | 
                        <span style='color:{"#00FFAA" if rec['net'] > 0 else "#FF4444" if rec['net'] < 0 else "#888"};'>${rec['net']:+,.2f}</span>
                       </div>"""
                    for rec in reversed(st.session_state.bet_history)
                ])
                st.markdown(f'<div style="height: 300px; overflow-y: auto;">{history_html}</div>', unsafe_allow_html=True)
            else:
                st.caption("本靴暂无投注记录" if st.session_state.lang=="CN" else "No bets this shoe.")

        if st.session_state.end_shoe:
            st.warning("🟥 切牌线已到" if st.session_state.lang == "CN" else "🟥 CUT CARD REACHED")

    # --- 6. 主界面渲染 (保持原样) ---
    #render_casino_table(st.session_state.get('last_outcome_obj'), lang=st.session_state.lang)
    #st.divider()


    # --- 6. 主界面渲染 ---

    # 第一步：渲染牌桌（发牌图片）
    render_casino_table(st.session_state.get('last_outcome_obj'), lang=st.session_state.lang)

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

        # --- 更新后的 THEORETICAL (SBI) 算法核心 ---
        # 调用 sbi_full_model 计算包含 CURVE_DELTA 偏移的结果
        sbi_res = compute_sbi_ev_from_counts(total_decks=8, rank_counts=st.session_state.rank_counts)
        
        # 逻辑对齐：BASE_EV_P(-1.24%) + ΣCURVE_DELTA
        sbi_p = sbi_res.get('ev_p', -0.0124) * 100
        # 逻辑对齐：BASE_EV_B_COMM(-1.06%) + ΣCURVE_DELTA
        sbi_b = sbi_res.get('ev_b_comm', -0.0106) * 100
        # ---------------------------------------

        gold_match = st.session_state.golden_pool.get(current_rk)
        
        # D. 状态逻辑判定
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

        # E. 渲染面板
        st.markdown(f"""<div style="padding: 15px; border: 2px solid #32CD32; border-radius: 12px; background-color: rgba(0,0,0,0.25); min-height: 220px; font-family: sans-serif;">
        <div style="font-weight: bold; color: #32CD32; font-size: 1.1rem; margin-bottom: 5px;">🎯 RANK BIAS DUAL-CORE</div>
        <div style="font-size: 0.8rem; color: #aaa; margin-bottom: 15px; font-family: 'Courier New', monospace; background: rgba(255,255,255,0.07); padding: 6px; border-radius: 5px; border: 1px solid #444;">
            Key: <span style="color: #00FFAA;">{current_rk}</span>
        </div>
        <div style="margin-bottom: 18px; border-left: 4px solid #1E90FF; padding-left: 12px;">
            <div style="font-size: 0.7rem; color: #1E90FF; font-weight: bold; letter-spacing: 1px;">{label_theoretical}</div>
            <div style="font-size: 1.2rem; margin-top: 3px;">
                <span style="color: #ffffff;">P: {sbi_p:+.2f}%</span> | <span style="color: #ffffff;">B: {sbi_b:+.2f}%</span>
            </div>
        </div>
        <div style="border-left: 4px solid {dict_color}; padding-left: 12px;">
            <div style="font-size: 0.7rem; color: {dict_color}; font-weight: bold; letter-spacing: 1px;">{label_historical} - {dict_status}</div>
            <div style="font-size: 1.2rem; margin-top: 3px; {val_style}">
                <span>P: {dict_p:+.2f}%</span> | <span>B: {dict_b:+.2f}%</span>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)
        
    with col_right:
            from core.snapshot_engine import get_fp_components
            from core.db_adapter import get_fingerprint_advice, generate_fp_hash
            from modules.ui_components import render_snapshot_ai

            # 获取当前序列与参数
            clean_seq = st.session_state.get('clean_results', [])
            h_min = st.session_state.get('hist_min', 3)
            
            # --- 0. 声明保底变量，防止 UnboundLocalError ---
            # 默认设置为初始化状态（match=False 触发 UI 的“正在匹配”提示）
            fp_advice = {
                "match": False, 
                "fp_id": "READY", 
                "action": "WAIT", 
                "edge": 0.0, 
                "ev_info": {}
            }
            
            # --- 1. 执行 AI 计算逻辑 ---
            if clean_seq:
                # 1. 提取原始物理要素
                c_side, c_len, hB_raw, hP_raw = get_fp_components(clean_seq)
                
                # 2. 执行脱水过滤
                hB_filtered = {k: v for k, v in hB_raw.items() if int(k) >= h_min}
                hP_filtered = {k: v for k, v in hP_raw.items() if int(k) >= h_min}

                # 🚀 核心修改：双空检查门槛
                if hB_filtered or hP_filtered:
                    # 3. 生成最终 KEY
                    fp_key = generate_fp_hash(c_side, c_len, hB_filtered, hP_filtered, h_min)
                    
                    # 4. 获取数据库查询建议 (此处覆盖初始的 fp_advice)
                    fp_advice = get_fingerprint_advice(
                        cur_side=c_side,
                        cur_len=c_len,
                        hist_B=hB_filtered,
                        hist_P=hP_filtered,
                        hist_min=h_min
                    )

                    # # 5. 打印完整 4 要素调试信息 (保留)
                    print("\n" + "="*40)
                    print(f"✅ [FP MATCHING] Min Filter: {h_min}")
                    print(f"1. Side/Len: {c_side} / {c_len}")
                    print(f"2. History B: {hB_filtered} (Raw: {hB_raw})")
                    print(f"3. History P: {hP_filtered} (Raw: {hP_raw})")
                    print(f"4. Filter Min: {h_min}")
                    print(f"👉 GENERATED KEY: {fp_key}")
                    print("="*40 + "\n")
                else:
                    # 过滤后深度不足
                    fp_advice = {
                        "match": False,
                        "fp_id": "DEPTH INSUFFICIENT", 
                        "status": f"Need streak >= {h_min}",
                        "side": "Neutral"
                    }
                    print(f"ℹ️ [FP SKIP] 历史特征不足 (Min: {h_min})，跳过指纹生成。")
            else:
                # NEW SHOE 后 clean_seq 为空，直接使用初始声明的 fp_advice
                pass

            # --- 2. 同步状态并渲染 ---
            # 更新 Session State 以便其他组件（如日志）同步
            st.session_state.last_fp_advice = fp_advice
            
            # 渲染右侧面板
            render_snapshot_ai(st.session_state.last_fp_advice, lang=st.session_state.get('lang', 'CN'))
