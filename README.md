# BAC_PRO (Baccarat Professional Analysis Engine)

这是一个基于 Python 开发的百家乐概率模拟与实时分析系统，支持 10 亿手（1e9）级别的模拟数据处理。

## 核心功能
* **模拟计算**：通过 `pipeline` 模块进行大规模数据采样。
* **实时策略**：`app` 模块提供基于 `premax_state_ev` 表的最优动作建议。
* **视觉识别**：内置 `vision_scanner` 用于牌局状态自动输入。

## 快速开始

### 1. 安装依赖
确保已安装 Python 3.8+，然后在项目根目录执行：
```bash
pip install -r requirements.txt
```

### 2. 数据库配置
项目依赖 MySQL 存储模拟结果。请运行以下脚本初始化核心表结构：
```bash
# 建议先根据你的本地环境修改脚本中的 DB_PASSWORD
python3 app/tools/insert_streak_raw.py 
```
*(注：由于你删除了旧的初始化脚本，建议未来将核心表 `premax_state_ev` 的建表语句也放入此处。)*

## 目录指南
* `app/`: UI 界面与核心逻辑
* `core/`: 数据库适配器与视觉扫描核心
* `dealer/`: 发牌逻辑模拟
* `drawing/`: 期望值（EV）曲线绘图工具

