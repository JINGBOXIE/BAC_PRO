# core/db_adapter.py 
import pandas as pd
import pymysql
import os
import json
import hashlib
from core.snapshot_engine import build_state_key
import redis

class RedisAdapter:
    def __init__(self, redis_url):
        self.client = redis.from_url(redis_url, decode_responses=True)

    def get_state_decision(self, state_hash):
        """
        获取脱水后的决策数据
        返回格式: dict {action, edge, ev_cut, ev_cont}
        """
        raw_val = self.client.get(f"fp:v8:{state_hash}")
        if not raw_val:
            return None
        
        # 解析脱水字符串
        parts = raw_val.split('|')
        return {
            "action": parts[0],
            "edge": float(parts[1]),
            "ev_cut": float(parts[2]),
            "ev_cont": float(parts[3])
        }
    
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

# core/db_adapter.py

def get_fingerprint_advice(cur_side, cur_len, hist_B, hist_P, hist_min=3):
    # 1. 生成指纹 (确保与 state_sampler.py 的逻辑对齐)
    state_hash = generate_fp_hash(cur_side, cur_len, hist_B, hist_P, hist_min)
    
    try:
        # 使用 st.secrets 中的配置连接
        conn = mysql.connector.connect(**st.secrets["mysql"])
        cursor = conn.cursor(dictionary=True)
        
        # 2. 执行查询，获取 2026 重新系统学习金融经济所需的量化指标
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
            return {
                "match": True,
                "fp_id": state_hash,
                "action": row['best_action'],
                "edge": row['edge'],
                "ev_info": {
                    "斩 (Cut)": row['ev_cut'],
                    "跟 (Cont)": row['ev_continue']
                },
                "prob": {
                    "P_Cut": row['p_cut'],
                    "P_Cont": row['p_continue']
                }
            }
    except Exception as e:
        print(f"[TEST-ONLY] DB Error: {e}")
    
    return {"match": False, "fp_id": state_hash}


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