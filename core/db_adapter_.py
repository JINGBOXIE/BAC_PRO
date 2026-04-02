# core/db_adapter.py 
import pandas as pd
import pymysql
import os
import json
import hashlib
from core.snapshot_engine import build_state_key

def generate_fp_hash(cur_side, cur_len, hist_B, hist_P, hist_min=3):
    """
    [规格文档 1.2 对齐] 
    应用动态 hist_min 截断处理并生成 SHA256 指纹
    """
    # 核心：过滤掉所有长度小于 hist_min 的柱子
    f_B = {k: v for k, v in hist_B.items() if int(k) >= hist_min}
    f_P = {k: v for k, v in hist_P.items() if int(k) >= hist_min}
    
    # 调用 snapshot_engine 里的标准拼接函数
    raw_key = build_state_key(
        cur_side=cur_side,
        cur_len=cur_len,
        hist_B=f_B,
        hist_P=f_P
    )
    
    # 生成 64 位脱敏哈希 ID
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

import mysql.connector # 或者使用 st.connection
import pandas as pd
import streamlit as st

def get_fingerprint_advice(cur_side, cur_len, hist_B, hist_P, hist_min=3):
    # 第一步：根据 4 要素生成哈希，用于匹配数据库的 state_hash 字段
    state_hash = generate_fp_hash(cur_side, cur_len, hist_B, hist_P, hist_min)
    
    # 第二步：执行 SQL 查询 (WHERE state_hash = %s)

    # 2. 从 Streamlit Secrets 或配置获取数据库连接
    # 建议使用 st.connection 提高性能（含内置连接池）
    # 在 get_fingerprint_advice 内部执行查询前
    print(f"DEBUG SQL: SELECT * FROM premax_state_ev WHERE state_hash = '{state_hash}';")


    try:
        conn = mysql.connector.connect(**st.secrets["mysql"])
        cursor = conn.cursor(dictionary=True)
        
        # 3. 执行高频索引查询
        query = """
            SELECT best_action, edge, ev_cut, ev_continue, p_cut, p_continue 
            FROM premax_state_ev 
            WHERE state_hash = %s
        """
        cursor.execute(query, (state_hash,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if row:
            # 命中数据库 ✅
            return {
                "match": True,
                "fp_id": state_hash,
                "fingerprint": state_hash,
                "edge": row['edge'],
                "action": row['best_action'],
                "ev_info": {
                    "cut": row['ev_cut'],
                    "continue": row['ev_continue']
                },
                "prob": {
                    "p_cut": row['p_cut'],
                    "p_cont": row['p_continue']
                },
                "status": "STRATEGY READY"
            }
            
    except Exception as e:
        print(f"❌ Database Access Error: {e}")

    # 4. 未命中：模型未覆盖到的稀有状态 ❌
    return {
        "match": False,
        "fp_id": state_hash,
        "fingerprint": state_hash,
        "edge": 0.0,
        "action": "WAIT",
        "status": "NO HIST DATA"
    }

def query_fp_advice(fp_id):
    """
    模拟从数据库查询指纹建议
    """
    # 这里将来连接你的 MySQL 表 premax_state_ev
    return {
        "match": False,
        "fp_id": fp_id,
        "edge": 0.0,
        "depth": "0.00%"
    }

# 保留你原有的 get_ev_data 用于兼容其他模块
def get_ev_data(side, length):
    # ... 你原来的代码 ...
    pass