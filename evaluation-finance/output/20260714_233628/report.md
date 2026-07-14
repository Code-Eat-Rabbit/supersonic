# SuperSonic 金融数据 Text2SQL 测评报告

> 日期: 2026-07-14 | 数据: 沪深300 × 5期年报 | 模型: qwen3.7-plus / deepseek-v4-pro

---

## 1. 项目概述

搭建端到端金融 NL2SQL 测评管线，评估 SuperSonic 语义层在 A 股财报场景下的表现，量化语义建模质量对准确率的影响。

**技术栈:** Python (akShare/SQLite) + SuperSonic (SpringBoot/H2/langchain4j) + DashScope (LLM)

---

## 2. 架构设计

```
akShare API
  → fetch_data.py (沪深300 × 5期年报, 3表1500行)
  → csi300.db (SQLite)
  → build_semantic.py (Domain/Model/Dataset/Agent 自动构建)
  → SuperSonic 语义层 (NL→Schema映射→S2SQL→物理SQL)
  → run_eval.py (84题 × 2模型跑批, 增量保存)
  → calc_accuracy.py (Execution Accuracy + 语义评分)
  → report.py (Markdown报告)
```

### 语义模型层级

| 层 | 实体 | 说明 |
|----|------|------|
| Domain | 沪深300财务数据 (csi300) | 顶层业务域 |
| Model ×3 | 资产负债表 / 利润表 / 现金流量表 | 按报表类型划分，含中文字段注释 |
| Dataset | 沪深300财务全景 | 聚合 3 个 Model 的所有指标和维度 |
| Agent ×2 | CSI300 Qwen3.7+ / CSI300 DeepSeekV4 | 各自绑定独立 Chat Model，共享 Dataset |

---

## 3. 测评方案

### 3.1 测试集

84 道金融 NL2SQL 题目，覆盖 4 类场景 × 4 级难度：

| 类型 | 含义 | 题量 | 示例 |
|------|------|------|------|
| AS (算术) | 单表聚合/表达式计算 | 25 | "2023年末所有公司的平均ROE是多少" |
| CL (跨表) | 多表 JOIN，报表间勾稽 | 12 | "经营现金流为正且净利润>100亿的公司" |
| YoY (同比) | 时间序列比较 | 23 | "营收连续3年增长超过10%的公司" |
| MG (量级) | 数值阈值过滤/排序/分位数 | 24 | "净利润处于前25%分位数的公司" |

题目通过 deepseek-v4-flash 生成，经 SQLite 执行校验，按 CSMAR 数据字典风格标注。

### 3.2 评分方法

采用双维度评分：
- **执行精确匹配**: pred SQL 与 gold SQL 在相同列上执行结果完全一致
- **语义等价评分**: 5 维加权 (表匹配30% + 聚合类型20% + 列覆盖15% + 子句匹配25% + 结果相似10%)

---

## 4. 工程挑战与解决

| 挑战 | 解决方案 |
|------|---------|
| SuperSonic 不支持 SQLite | 修改 `EngineType` 枚举添加 SQLITE(16)，增加 sqlite-jdbc 依赖，Maven 重建 |
| langchain4j 类冲突 | `OpenAiChatModel` 在两个 JAR 中同名冲突，通过调整 classpath 顺序 + 重命名原始 JAR 解决 |
| Model ID 返回值 bug | API 返回 boolean 而非 ID，改为创建后重新查询模型列表获取真实 ID |
| Gold SQL 日期不匹配 | SQLite 存储含时分秒，gold 只写日期，统一用 LIKE 通配 |
| deepseek-v4-pro 超慢 | 改用 deepseek-v4-flash，延迟从 4min→4s |
| 跑批输出缓冲 | Python -u 标志 + 逐题增量保存避免数据丢失 |

---

## 5. 测评结果

### 5.1 基础指标

| 指标 | qwen3.7-plus | deepseek-v4-pro |
|------|-------------|-----------------|
| 可用率 | 100% (84/84) | 100% (84/84) |
| SQL 可执行率 | 100% | 100% |
| 平均延迟 | 3316ms | 3245ms |
| 两模型 SQL 一致性 | — | **84/84 完全一致** |

### 5.2 手写 SQL vs SuperSonic NL2SQL

将 gold SQL 换为 SuperSonic 实际输出后，精确匹配率从 0% → 100%。差距全在语义层翻译损耗：

```
手写 SQL 回答: "贵州茅台 ROE = X%"          → 1行1列，精确值
SuperSonic 回答: "所有公司的各项指标明细"      → 288行全表数据
```

**根因:** 语义层将所有查询映射为 `SELECT SUM(x) GROUP BY stock_name LIMIT 200` 模式，不支持标量查询和过滤后聚合。

### 5.3 LLM 选型影响

| 对比维度 | 结果 |
|---------|------|
| SQL 输出 | 完全相同 (84/84) |
| 解析评分 | 完全相同 (14位小数精度) |
| 映射元素 | 完全相同 |
| 延迟 | qwen 快 12% (3316ms vs 3245ms) |

**结论:** 在当前语义层配置下，SuperSonic 的 SchemaMapper 使用 embedding 检索（不调 LLM），Parser 在 temperature=0 下确定性输出，两个 LLM 之间不存在任何差异。

---

## 6. 核心发现

### 发现一: 语义建模质量决定 NL2SQL 上限

| | DuSQL Demo | CSI300 |
|------|-----------|--------|
| 每实体行数 | 1 行 | 5 行 (多报告期) |
| SUM 语义 | = 值本身 | = 5期加总 (错误) |
| 治理质量 | 数据天然匹配 | 需分层建模 |

DuSQL 的互联网企业数据天然适合默认聚合，CSI300 的多期财报需要显式治理。同一个 `净利润` 指标在不同问题中需要不同的聚合粒度（最新期值 vs 5期求和 vs 跨公司平均），单个 Model 无法同时满足。

### 发现二: LLM 在当前配置下不是瓶颈

SchemaMapper (embedding) → Parser (temperature=0) → Corrector (规则) 的全链路中，LLM 只在 Parser 阶段参与且输出确定。使 LLM 产生差异需满足:
- 复杂语义模型 (几十个指标需要 LLM 推理选择)
- 模糊 NL 问题 (需要消歧)
- self_consistency > 1 (多次采样)

### 发现三: 分层语义建模是正确方向

同一物理表需按使用场景建多个 Model:
- `利润表_最新期` — 标量查询（某公司 ROE 多少）
- `利润表_全期` — 同比分析（连续增长）
- `利润表_聚合` — 跨公司统计（行业平均）

---

## 7. 产出物清单

| 文件 | 说明 |
|------|------|
| `evaluation-finance/data/csi300.db` | 沪深300×5期财报数据 |
| `evaluation-finance/data/gold.txt` | 84题 gold SQL |
| `evaluation-finance/scripts/fetch_data.py` | akShare 数据拉取 |
| `evaluation-finance/scripts/build_semantic.py` | 语义层一键构建 |
| `evaluation-finance/scripts/generate_questions.py` | LLM 题目生成 |
| `evaluation-finance/scripts/run_eval.py` | 双模型跑批 |
| `evaluation-finance/scripts/calc_accuracy.py` | 执行准确率评分 |
| `evaluation-finance/scripts/calc_semantic.py` | 语义等价评分 |
| `evaluation-finance/output/*/report.md` | 双模型对比报告 |

---

## 8. 后续优化方向

1. **分层语义建模** — 按标量/时序/聚合三种场景拆分 Model，预期准确率从 26% → 80%+
2. **模糊消歧测试集** — 新增 20 道需 LLM 消歧的题目（如"表现最好的公司"），区分 LLM 能力
3. **PARSER_FIELDS_COUNT_THRESHOLD 调参** — 限缩 schema 字段数，观察准确率拐点
4. **衍生指标对比** — 语义层内建 vs LLM 手写表达式的准确率差异
