import streamlit as st

def get_big_road_matrix(results):
    """
    V3 核心坐标算法：计算大路矩阵
    """
    if not results: return {}, 0
    matrix = {}
    max_x, curr_x, curr_y = 0, 0, 0
    last_main_winner = None
    initial_ties = 0
    
    for r in results:
        # --- 和局逻辑 ---
        if r == 'T':
            if last_main_winner is None: 
                initial_ties += 1
            else:
                if (curr_x, curr_y) in matrix: 
                    matrix[(curr_x, curr_y)]['ties'] += 1
            continue
            
        # --- 换列与拐弯逻辑 ---
        if last_main_winner is None:
            matrix[(0, 0)] = {'type': r, 'ties': initial_ties}
            last_main_winner, curr_x, curr_y = r, 0, 0
        elif r == last_main_winner:
            nx, ny = curr_x, curr_y + 1
            # 遇到底部（第6行）或该位置已有数据（长龙拐弯）
            if ny >= 6 or (nx, ny) in matrix: 
                nx, ny = curr_x + 1, curr_y
            matrix[(nx, ny)] = {'type': r, 'ties': 0}
            curr_x, curr_y = nx, ny
        else:
            # 换手：寻找最左侧空列的第一行
            sx = 0
            while (sx, 0) in matrix: 
                sx += 1
            curr_x, curr_y, last_main_winner = sx, 0, r
            matrix[(curr_x, curr_y)] = {'type': r, 'ties': 0}
        
        max_x = max(max_x, curr_x)
    return matrix, max_x

def render_big_road(results):
    """
    V3 样式渲染器：注入 HTML/CSS 和 自动滚动脚本
    """
    # 语言处理
    lang = st.session_state.get('lang', 'CN')
    no_data_msg = (
        "💡 暂无数据，发牌后将在此生成大路图。" 
        if lang == 'CN' else 
        "💡 No data available. Big Road will be generated after dealing."
    )
    
    matrix, max_x = get_big_road_matrix(results)
    
    if not matrix:
        st.info(no_data_msg)
        return

    # 设定显示列数，保证美观并支持横向滚动
    display_cols = max(24, max_x + 2)
    
    # --- V3 经典网格 CSS ---
    grid_style = (
        f"display: grid; "
        f"grid-template-columns: repeat({display_cols}, 32px); "
        f"grid-template-rows: repeat(6, 32px); "
        f"background-color: #fff; "
        f"background-image: "
        f"linear-gradient(#e0e0e0 1px, transparent 1px), "
        f"linear-gradient(90deg, #e0e0e0 1px, transparent 1px); "
        f"background-size: 32px 32px; "
        f"width: {display_cols * 32}px; "
        f"height: 192px;"
    )

    # 构造 HTML
    html = [
        f'<div id="road-view" style="width:100%; overflow-x:auto; background:#f8f9fa; '
        f'padding:10px; border:1px solid #ccc; border-radius:5px; white-space:nowrap;">'
        f'<div style="{grid_style}">'
    ]
    
    for (x, y), item in matrix.items():
        # V3 配色
        color = "#FF4500" if item['type'] == 'B' else "#1E90FF"
        char = item['type']
        
        # 和局标识（绿色圆圈数字）
        tie_tag = (
            f'<div style="position:absolute; top:-4px; right:-4px; background:#32CD32; '
            f'color:white; border-radius:50%; width:15px; height:15px; font-size:9px; '
            f'line-height:15px; text-align:center; border:1px solid white; z-index:10;">'
            f'{item["ties"]}</div>' 
            if item['ties'] > 0 else ""
        )
        
        # 单元格渲染：空心圆环 + 字母
        cell = (
            f'<div style="grid-column:{x+1}; grid-row:{y+1}; position:relative; '
            f'width:32px; height:32px; display:flex; align-items:center; justify-content:center;">'
            f'<div style="width:26px; height:26px; border:3px solid {color}; '
            f'border-radius:50%; display:flex; align-items:center; justify-content:center; background:white;">'
            f'<b style="color:{color}; font-size:13px;">{char}</b></div>{tie_tag}</div>'
        )
        html.append(cell)
        
    html.append('</div></div>')
    
    # 注入 JavaScript：确保发牌后路纸始终滚动到最右端最新一手
    html.append(
        '<script>'
        'var c = document.getElementById("road-view");'
        'if(c) { '
        '    c.scrollLeft = c.scrollWidth; '
        '    setTimeout(function() { c.scrollLeft = c.scrollWidth; }, 100); '
        '}'
        '</script>'
    )
    
    st.markdown("".join(html), unsafe_allow_html=True)
