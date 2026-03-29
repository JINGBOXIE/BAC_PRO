# modules/i18n.py

TRANSLATIONS = {
    "CN": {
        "new_shoe": "开启新靴",
        "nav_practice": "🧠 策略训练",
        "nav_ai": "⚡ AI 实战分析",
        "nav_knowledge": "📖 百家乐常识",
        "welcome": "简单与专注",
        "lang_switch": "语言选择 / Language",
        "theoretical": "理论模型 (SBI)",
        "historical": "大数据字典 (DICT)",
        "deal_btn": "🚀 DEAL / 发牌",
        "ai_title": "实时视觉诊断中心",
        "upload_btn": "拍照或上传大路图",
        "start_ai": "开始 AI 智能扫描",
        "diag_report": "大数据诊断报告",
        "neutral": "中性",
        "loading_ai": "AI 正在深度解析大路图...",
        "big_road": "大路演示",
    },
    "EN": {
        "new_shoe": "New Shoe",
        "nav_practice": "🧠 Strategy Drill",
        "nav_ai": "⚡ AI Live Vision",
        "nav_knowledge": "📖 Knowledge Base",
        "welcome": "Simplicity and Focus",
        "lang_switch": "Language",
        "theoretical": "Theoretical (SBI)",
        "historical": "Historical (DICT)",
        "deal_btn": "🚀 DEAL / DRAW",
        "ai_title": "Live Vision Diagnostic",
        "upload_btn": "Capture or Upload Road Map",
        "start_ai": "Start AI Scan",
        "diag_report": "Big Data Report",
        "neutral": "Neutral",
        "loading_ai": "AI is analyzing the roadmap...",
        "big_road": "BIG ROAD", 
    }
}

def t(key, lang="CN"):
    return TRANSLATIONS.get(lang, {}).get(key, key)