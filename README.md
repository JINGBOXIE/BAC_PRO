# 🃏 BACC-INTELLI: 全域决策矩阵工程文档

## 📌 项目概述
BACC-INTELLI 是一款集成“实战模拟”、“资金管理”与“AI 势能分析”的高级百家乐分析系统。系统通过 Rank Bias (点数偏移) 与 Snapshot Bias (图形势能) 双引擎驱动，提供科学的决策支持。

## 📂 目录结构说明

### 🛰️ 调度层 (Action Layer)
* **`streamlit_app.py`**: 系统指挥中心。处理 UI 交互、文件上传（拍照识别接口）、以及各模块间的调度。

### 🎴 发牌物理层 (Dealer Layer)
* **`dealer/baccarat_dealer.py`**: **[逻辑已锁定]** 负责 8 叠牌的洗牌、发牌规则（含补牌逻辑）及结果生成。

### 📦 公开功能模块 (Modules)
* **`road_renderer.py`**: 负责大路图渲染，包含长龙下拐与 HTML/JS 自动对焦逻辑。
* **`stats_manager.py`**: 负责实时 Rank 计数（0-9 剩余张数）及基础统计。
* **`bankroll_engine.py`**: 负责本金追踪、流水记录及胜负自动结算。

### 🛡️ 核心机密层 (Protected Core)
> **注意：此目录下的 `.py` 文件在发布前必须编译为 `.pyd` 混淆文件。**
* **`core/snapshot_proxy.py`**: 外部接口代理，屏蔽内部核心算法。
* **`core/engine_source.py`**: **核心资产**。包含图形特征哈希化算法及 Snapshot 匹配逻辑。
* **`core/data_vault/`**: 加密仓库。
    * `snapshot_bias.bin`: 经 AES-256 加密的图形 EV 预计算字典。

---

## 🔐 安全协议 (Security Protocol)
1. **资产隔离**: 严禁在 `streamlit_app.py` 中直接编写图形识别逻辑。
2. **内存加密**: `snapshot_bias.bin` 仅在运行时解密至内存字典，禁止生成任何中间明文文件。
3. **哈希查询**: 所有图形状态必须转换为 `StateID` (Hash) 后再进行字典检索，确保数据不可逆向。

## 🚀 未来扩展计划
- [ ] **Vision Module**: 接入 OpenCV，实现路纸照片自动识别。
- [ ] **Bias Engine v2**: 接入海量预计算的 Snapshot EV 表。
- [ ] **Bankroll Chart**: 实时生成资金曲线图。
