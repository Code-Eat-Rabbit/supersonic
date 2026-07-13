# 第 1 点：Text2SQL 测评体系 — 讨论议程

## 状态：⏸️ 待定，后续单独讨论

---

## 现有测评体系梳理（讨论基础）

### 测评框架

SuperSonic 内置了一套完整的 Text2SQL 评测框架（`evaluation/`），基于 DuSQL（百度互联网企业数据集）：

- **评测脚本**：`evaluation/evaluation.py` — 支持执行准确率（Execution Accuracy）和逻辑形式准确率（Exact Match）
- **数据集**：`evaluation/data/gold_example_dusql.txt` — 标准答案 SQL，`internet.txt` — 自然语言问题
- **Schema**：4 张表（company / brand / company_revenue / company_brand_revenue），含表间 JOIN 关系
- **难度分级**：easy / medium / hard / extra 四级，按 SQL 子句复杂度（WHERE/GROUP BY/ORDER BY/JOIN/嵌套查询）自动分级
- **评分维度**：
  - 执行准确率：预测 SQL 在 SQLite 上执行结果与标准答案一致
  - 逻辑形式准确率：SQL 结构（SELECT/WHERE/GROUP BY/ORDER BY/HAVING/JOIN 等 10 个维度）的 F1 评分
- **LLM 接入**：`build_models.py` 通过 REST API 创建 Domain/Model/DataSet/Agent，支持替换不同 LLM 后端

### 我们的实际工作

- 搭建完整评测环境（H2 + DeepSeek/DashScope 双模型接入）
- 修复评测脚本中的 LLM 配置链 Bug（Agent → ChatApp → chatModelId）
- 定位 `querySQL` vs `correctedQuerySQL` 字段选择问题（S2SQL 格式 vs 物理 SQL 格式）
- 修复 `build_models.py` 中缺失的 `create_chat_model()` 调用
- 解决 DeepSeek 推理模型（v4-pro）输出在 `reasoning_content` 字段导致 parser 读取为空的兼容性问题

---

## 讨论议题

### 议题 1：简历定位策略

简历中应该强调的是「搭建能力」还是「指标结果」？

- **方案 A（体系搭建）**：强调从零搭建评测管线、多模型并发对比、自动化评分体系 → 适合没有最终评测数据的场景
- **方案 B（指标驱动）**：引用具体准确率数字（如「DeepSeek-v3 在 medium 难度上达到 XX% 执行准确率」）→ 数字更有说服力，但需要真实数据支撑
- **方案 C（混合）**：以体系搭建为主，附带一组代表性指标

### 议题 2：需要确定的具体量化数据

| 指标 | 来源 | 状态 |
|------|------|------|
| 整体执行准确率（all difficulties） | 跑完 evaluation.py 后终端输出 | 需跑一次获取 |
| 各难度分级准确率（easy/medium/hard/extra） | 同上 | 需跑一次获取 |
| 逻辑形式 F1（SELECT/WHERE/GROUP BY...） | 同上 | 需跑一次获取 |
| 模型对比（DeepSeek vs DashScope） | 分别跑两轮评测 | 需跑两次获取 |
| 响应耗时对比 | `parseTimeCost` 字段 | 从日志提取 |

### 议题 3：简历措辞细化方向

一旦确定指标数据，需要讨论：

- 简历中报哪个模型的准确率？（最好的是谁？）
- 是报「执行准确率」还是「逻辑形式准确率」？（执行准确率更直观，逻辑形式 F1 更有技术深度）
- 是否需要拆为两条 bullet？（一条体系搭建 + 一条模型优化/兼容性适配）

### 议题 4：面试追问范围控制

面试官可能追问的深度：

- 「你们的评测标准是什么？」→ DuSQL benchmark，具体指标含义
- 「和 Spider/CoSQL 等公开 benchmark 对比过吗？」→ 需准备回答
- 「CSMAR 自定义数据集的测评怎么做？」→ 我们的 CSMAR 数据导入管线是否也能接入评测
- 「如何保证评测公平性？」→ 同一 Agent 配置、同一测试集、同一 SQLite 环境

---

## 下一步行动

1. 跑一次完整的 evaluation.py（建议用 deepseek-chat，非推理模型避免兼容问题）
2. 记录终端输出的准确率数据
3. 根据数据确定简历方案并更新本文档
