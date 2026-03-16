import pandas as pd
import pymysql
import os

def get_ev_data(side, length):
    """
    核心适配器：优先尝试从本地 MySQL 读取，
    如果失败（比如在 GitHub 环境中），则尝试读取本地 CSV 备份。
    """
    try:
        # 1. 尝试连接本地数据库
        conn = pymysql.connect(
            host="localhost",
            user="root",
            password="your_password", 
            database="BAC_PRO"
        )
        query = f"SELECT * FROM premax_state_ev WHERE cur_side='{side}' AND cur_len={length}"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        # 2. 如果数据库连不上，寻找项目目录下的备份文件
        backup_path = "data/premax_backup.csv"
        if os.path.exists(backup_path):
            df_all = pd.read_csv(backup_path)
            return df_all[(df_all['cur_side'] == side) & (df_all['cur_len'] == length)]
        else:
            return None