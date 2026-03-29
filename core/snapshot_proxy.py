# core/snapshot_proxy.py
import streamlit as st
try:
    from core.engine_source import extract_pattern_and_analyze
except ImportError:
    def extract_pattern_and_analyze(results):
        return "Core Engine Not Found"

def get_snapshot_bias(results):
    """Snapshot 引擎代理入口"""
    if not results or len(results) < 3:
        return "数据采集记录中，暂无势能分析..."
    
    # 核心算法交由 engine_source 处理
    return extract_pattern_and_analyze(results)