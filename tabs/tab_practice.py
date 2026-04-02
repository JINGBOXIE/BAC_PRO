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

def render_practice_tab(lang):
    """
    100% 还原原始测试版本的练习模块
        """
    # tabs/tab_practice.py

    # 1. 安全获取开关状态
    use_cloud = st.secrets.get("USE_CLOUD_REDIS", False)

    # 2. 优化 URL 获取逻辑，使用 .get() 避免 KeyError
    if use_cloud:
        redis_url = st.secrets.get("UPSTASH_REDIS_URL")
        if not redis_url:
            st.error("❌ 已开启云端模式，但未找到 UPSTASH_REDIS_URL 配置")
            st.stop()
    else:
        # 本地模式提供备选默认值
        redis_url = st.secrets.get("LOCAL_REDIS_URL", "redis://localhost:6379/0")

    # 3. 检查并初始化适配器 (确保逻辑连贯)
    if 'redis_adapter' not in st.session_state:
        try:
            from core.db_adapter import RedisAdapter
            st.session_state.redis_adapter = RedisAdapter(redis_url)
            st.toast(f"✅ 已连接至 {'Upstash' if use_cloud else 'Local'} Redis")
        except Exception as e:
            st.error(f"Redis Connection Error: {e}")
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
            # 1. 语言配置
            is_cn = st.session_state.get('lang', 'CN') == 'CN'
            lang_map = {
                "title": "🔍 AI FINGERPRINT SCAN" if not is_cn else "🔍 AI 指纹扫描决策",
                "waiting": "Waiting for sequence..." if not is_cn else "等待序列输入...",
                "action_label": "Best Action" if not is_cn else "最优决策",
                "edge_label": "Edge Advantage" if not is_cn else "优势概率",
                "insufficient": "DEPTH INSUFFICIENT" if not is_cn else "序列深度不足",
                "miss": "DATA MISS (1.4M+)" if not is_cn else "未匹配到历史指纹",
            }

            from core.snapshot_engine import get_fp_components
            from core.db_adapter import RedisAdapter, generate_fp_hash 

            # 2. Redis 连接初始化 (集成环境切换逻辑)
            if 'redis_adapter' not in st.session_state:
                try:
                    # 自动根据开关选择 URL
                    use_cloud = st.secrets.get("USE_CLOUD_REDIS", False)
                    target_url = st.secrets["UPSTASH_REDIS_URL"] if use_cloud else st.secrets["LOCAL_REDIS_URL"]
                    
                    # 初始化适配器
                    st.session_state.redis_adapter = RedisAdapter(target_url)
                    
                    # 提示当前连接模式
                    mode_msg = "Online" if use_cloud else "Local"
                    st.toast(f"Connected to {mode_msg} Redis")
                except Exception as e:
                    st.error(f"Redis Connection Error: {e}")

            # 3. 状态逻辑处理
            clean_seq = st.session_state.get('clean_results', [])
            h_min = 3 
            fp_advice = {"match": False, "status": "WAITING"}

            
            # tabs/tab_practice.py

            if clean_seq:
                c_side, c_len, hB_raw, hP_raw = get_fp_components(clean_seq)
                hB_f = {k: v for k, v in hB_raw.items() if int(k) >= h_min}
                hP_f = {k: v for k, v in hP_raw.items() if int(k) >= h_min}

                if hB_f or hP_f:
                    state_hash = generate_fp_hash(c_side, c_len, hB_f, hP_f, h_min)
                    
                    # --- 🔴 关键调试代码开始 ---
                    # 这行会把线上生成的完整 Key 直接显示在 UI 上，方便你复制对比
                    st.info(f"DEBUG - 实时生成的 Key: `fp:v8:{state_hash}`")
                    # --- 🔴 关键调试代码结束 ---

                    decision = st.session_state.redis_adapter.get_state_decision(state_hash)
                    
                    
                    if decision:
                        fp_advice = {
                            "match": True,
                            "action": decision["action"],
                            "edge": decision["edge"],
                            "ev_cut": decision["ev_cut"],
                            "ev_cont": decision["ev_cont"],
                            "fp_id": state_hash
                        }
                    else:
                        fp_advice = {"match": False, "status": lang_map["miss"], "fp_id": state_hash}
                else:
                    fp_advice = {"match": False, "status": lang_map["insufficient"]}

            # 4. 构建 HTML 字符串 (关键修复：避免嵌套 f-string)
            # 外层容器
            html = '<div style="padding: 18px; border: 2px solid #1E90FF; border-radius: 15px; background-color: rgba(10, 20, 30, 0.6); box-shadow: 0 4px 15px rgba(0,0,0,0.3); min-height: 220px;">'
            
            # 头部
            html += f'<div style="font-weight: bold; color: #1E90FF; font-size: 0.9rem; letter-spacing: 1px; margin-bottom: 12px; border-bottom: 1px solid #1E90FF44; padding-bottom: 8px; display: flex; justify-content: space-between;">'
            html += f'<span>{lang_map["title"]}</span><span style="font-size: 0.6rem; color: #555; background: rgba(0,0,0,0.2); padding: 2px 6px; border-radius: 4px;">V8-KV</span></div>'

            # 内容区判断
            if not fp_advice.get('match') and fp_advice.get('status') == 'WAITING':
                html += f'<div style="color:#666; text-align:center; padding: 40px;">{lang_map["waiting"]}</div>'
            
            elif fp_advice.get('match'):
                fid = fp_advice["fp_id"]
                act = fp_advice["action"]
                edge = fp_advice["edge"]
                e_cut_pct = f'{fp_advice["ev_cut"]*100:+.2f}%'
                e_cont_pct = f'{fp_advice["ev_cont"]*100:+.2f}%'
                edge_pct = f'{edge:+.2%}'

                html += f'''
                <div>
                    <div style="font-family: monospace; font-size: 0.65rem; color: #1E90FF; background: rgba(0,0,0,0.3); padding: 5px; border-radius: 4px; word-break: break-all; margin-bottom: 15px;">Fingerprint: {fid}</div>
                    <div style="text-align: center; margin-bottom: 20px;">
                        <div style="font-size: 0.7rem; color: #888; text-transform: uppercase;">{lang_map["action_label"]}</div>
                        <div style="font-size: 2.2rem; font-weight: 800; color: #00FFAA; text-shadow: 0 0 10px rgba(0,255,170,0.4);">{act}</div>
                    </div>
                    <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                        <div style="flex: 1; background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #444;">
                            <div style="font-size: 0.6rem; color: #aaa;">EV (CUT)</div>
                            <div style="font-size: 1.1rem; font-weight: bold; color: #fff;">{e_cut_pct}</div>
                        </div>
                        <div style="flex: 1; background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #444;">
                            <div style="font-size: 0.6rem; color: #aaa;">EV (CONT)</div>
                            <div style="font-size: 1.1rem; font-weight: bold; color: #fff;">{e_cont_pct}</div>
                        </div>
                    </div>
                    <div style="text-align: center; background: rgba(0,255,170,0.1); padding: 5px; border-radius: 20px; border: 1px solid #00FFAA33;">
                        <span style="font-size: 0.8rem; color: #00FFAA; font-weight: bold;">{lang_map["edge_label"]}: {edge_pct}</span>
                    </div>
                </div>
                '''
            else:
                html += f'<div style="color:#FF4444; margin-top: 40px; text-align:center; font-size: 0.9rem;">⚠️ {fp_advice["status"]}</div>'

            html += '</div>'

            # 5. 渲染
            st.markdown(html, unsafe_allow_html=True)
