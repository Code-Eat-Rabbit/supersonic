# SuperSonic 全面测评方案设计

> 状态: 待审查 (v2 — 已根据 review 修正) | 日期: 2026-07-14
> 参考: FinVerBench (Panda, 2026) 的财务报表数据结构与受控对比思想

## 1. 目标

为面试准备一份可量化、可复现的 SuperSonic Text2SQL 性能报告，覆盖两个核心维度 + 一个可选维度。

## 2. 测评框架（优先级排序）

```
优先级: 维度三(治理对比) > 维度一(模型对比) > 维度二(数据量,可选)

┌──────────┬─────────────────────┬─────────────────┬──────────────────┐
│ 维度      │ 3. 治理方案对比 ★    │ 1. 模型对比      │ 2. 数据量测试     │
│ 优先级    │ 高 (SuperSonic独有)  │ 中 (baseline)   │ 低 (可选)         │
├──────────┼─────────────────────┼─────────────────┼──────────────────┤
│ 变量      │ 三级数据治理         │ 3个LLM模型       │ 数据集规模        │
│ 固定      │ akShare财务数据      │ DuSQL 100条      │ 单模型+Level 2   │
│ 数据源    │ akShare A股          │ 内置DuSQL        │ akShare A股       │
├──────────┼─────────────────────┼─────────────────┼──────────────────┤
│ 核心指标  │ 映射率/SQL准确率/gold│ 准确率/延迟/token │ 元数据层+查询层    │
│ 叙事价值  │ "为什么语义层有价值"  │ "模型选型依据"    │ "系统容量天花板"  │
└──────────┴─────────────────────┴─────────────────┴──────────────────┘
```

### Gold 标注方案（维度二/三共用）

维度二/三使用 akShare 新数据集，无现成 gold SQL。标注方案：
- 规模: 30-50 条人工标注的 (NL问题, gold SQL, gold结果集) 三元组
- 流程: 1 人编写 + 1 人交叉验证，记录 disagreement
- 降级方案: 若标注人力不足，降级为"人工评判查询结果正确性"（适合治理对比，重点不是 SQL 文本精确匹配而是"答对没"）
- 存储: `evaluation/data/akshare/gold_queries.json` + `evaluation/data/akshare/*.db`

## 3. 维度一：模型对比（优先级: 中）

### 3.1 模型选择

三个模型统一走 DashScope compatible-mode API (`https://dashscope.aliyuncs.com/compatible-mode/v1`)：

| 模型 | DashScope name | provider | reasoning | 备注 |
|------|---------------|----------|-----------|------|
| Qwen3.7-Plus | `qwen3.7-plus` | OPEN_AI | 无 | 通义原生 |
| DeepSeek V4 Flash | `deepseek-v4-flash` | OPEN_AI | reasoning_content 总是存在 | content 有值，token 开销大 |
| GLM-5.2 | `glm-5.2` | OPEN_AI | 重度 reasoning | content 有值但需大 token 预算 |

**重要限定**: 本对比是**端到端服务能力对比**，包含 reasoning 开销，而非纯模型推理能力对比。DeepSeek/GLM 的额外 reasoning 成本是其固有特征的一部分。

### 3.2 配置参数

```yaml
provider: OPEN_AI
baseUrl: https://dashscope.aliyuncs.com/compatible-mode/v1
temperature: 0.0
timeOut: 60
apiKey: ${DASHSCOPE_API_KEY}  # 运行时注入，AES/ECB 加密后写入 DB
```

### 3.3 Agent 方案：3 个独立 Agent（非热切换）

**不采用热切换 `chatModelId` 方案**（缓存污染风险、并发污染风险）。

改为创建 3 个独立 Agent，各自绑定一个模型：
- `agent_qwen` → chatModelId = qwen3.7-plus 的 model ID
- `agent_deepseek` → chatModelId = deepseek-v4-flash 的 model ID
- `agent_glm` → chatModelId = glm-5.2 的 model ID

串行执行：Agent A 跑完 100 条 → Agent B 跑 100 条 → Agent C 跑 100 条。避免状态污染，代价仅多 2 个 Agent 数据库记录。

### 3.4 评估数据集

使用 SuperSonic 内置 DuSQL 评测集：
- 100 条中文自然语言 → SQL 查询
- 4 张表：company, brand, company_brand_revenue, company_revenue
- 4 级难度：easy / medium / hard / extra

### 3.5 指标（修正：分层准确率 + 多次运行）

**每条查询跑 3 次**，报告准确率的 mean ± std。

**分层准确率**: 为每条查询记录 `status` 字段：

| status | 含义 | 计入"纯模型准确率"？ |
|--------|------|-------------------|
| ok | 正常返回可执行 SQL | ✅ |
| parse_fail | 解析失败，返回 default SQL | ❌ |
| timeout | 超时无响应 | ❌ |
| exception | 异常（NPE/500等） | ❌ |

最终报告：
- **端到端可用率**: `count(status==ok) / total`
- **纯模型准确率**: 仅在 `status==ok` 子集上计算 Execution Accuracy
- **综合准确率**: 所有查询（含失败）的准确率

| 指标类别 | 具体指标 | 汇总方式 |
|---------|---------|---------|
| 可用率 | status 分布 (ok/parse_fail/timeout/exception) | 按模型 |
| 准确率 | Execution Accuracy (纯模型 + 综合，按难度) | 3次 mean±std |
| 准确率 | Exact Match | 3次 mean±std |
| 延迟 | avg / min / max / p95 (ms) | 3次跑的平均 |
| Token | prompt / completion / reasoning(分列) / total | 100条合计 |
| 置信区间 | Wilson 95% CI (每 cell 标注 n) | 所有准确率数字 |

### 3.6 脚本改动

现有文件修改：
- `build_models.py`: 扩展现有 `create_chat_model()` → 循环创建 3 个模型 + 3 个 Agent；每个 Agent 绑定各自 chatModelId
- `build_pred_result.py`: 查询函数增加 `status` 字段记录 + `latency_ms` + `token_usage`；`get_pred_sql()` 失败时标记 status 而非静默 fallback
- `evaluation.py`: 新增 `evaluate_multi_model()` 入口 + 分层准确率计算 + `benchmark_report.json` 输出 + Wilson CI

新增文件：
- `evaluation/benchmark.sh`: 一键启动脚本

## 4. 维度三：数据治理方案对比（优先级: 高）

### 4.1 核心洞察

SuperSonic 与 FinVerBench 的关键区别：SuperSonic 在数据和 SQL 之间有一层语义建模。测试不同治理层级可以量化这层语义建模的价值。

### 4.2 三级治理定义

```
Level 0 — 裸数据
  ├── 列名: akShare 原始英文编码
  ├── 维度类型: 未标注
  ├── Metric: 无定义
  └── 值: 原始编码值

Level 1 — 基础治理
  ├── 列名: 中文别名映射 (DES文件)
  ├── 维度类型: categorical / time / primary
  ├── Metric: SUM/COUNT 基础聚合
  └── 值: 原始编码值

Level 2 — 完整治理 (参考 CSMAR 管线经验)
  ├── 列名: 中文视图 (v_xxx)
  ├── 维度类型: 全标注
  ├── Metric: 全定义
  ├── 值映射: 解码视图
  ├── 值级 Embedding: BGE-small-zh 手动生成
  ├── 单字词补充: 高频分词子词
  └── EmbeddedMapper: use-llm-enhance 启用
```

### 4.3 定性假设（待实测验证）

```
定性假设 (非精确预测):
1. 映射成功率: Level 0 → 1 → 2 单调递增
2. Level 2 在多表 JOIN 查询上显著优于 Level 0/1
3. Level 0 的"可回答查询覆盖比例"极低（列名编码 + 无维度标注）
4. Level 1 → Level 2 的增益主要体现在"值匹配"类查询
5. 治理 ROI: Level 0→1 的边际收益 > Level 1→2（前者解决"能不能答"，后者优化"答得准不准"）
```

### 4.4 测试方法

同一份 akShare 数据，对三个 Level 分别注册独立的 Domain/Dataset/Model/Agent，跑相同 30-50 条 gold 查询集，对比：

| 指标层 | 指标 |
|--------|------|
| 映射层 | `query/search` API 成功率、映射到的实体数量 |
| SQL 层 | Execution Accuracy (vs. gold SQL)、SQL 语法正确率 |
| 结果层 | 查询结果与 gold 结果集比对 |
| 效率层 | 平均延迟、Token 消耗 |

## 5. 维度二：数据量 / 容量测试（优先级: 低，可选）

### 5.1 参考 FinVerBench 的报表结构

对标 FinVerBench 使用三大财务报表的结构，使用 akShare A 股财务数据。

### 5.2 数据源

```
akShare A股财务数据集:
1. 资产负债表: ak.stock_balance_sheet_by_report_em()
2. 利润表: ak.stock_profit_sheet_by_report_em()
3. 现金流量表: ak.stock_cash_flow_sheet_by_report_em()
4. 股本结构: ak.stock_individual_info_em()
```

### 5.3 测试递进

```
第1轮 — 5家公司 × 3报表 = 15张表 → 验证脚本正确性
第2轮 — 20家公司 × 3报表 = 60张表 → 观察性能拐点
第3轮 — 50-100家公司           → 饱和测试 (如果时间允许)
```

### 5.4 指标拆分为两层（修正）

**元数据层**:

| 指标 | 测量方法 | 假设 |
|------|---------|------|
| 建模耗时 | `createModel` API 响应时间 | 随数据量线性增长 |
| Schema 加载时间 | `getModelList` API 延迟 | 与 model 数量相关 |
| 元数据 API 延迟 | domain/dataset/dimension list API | Mark |

**查询层**:

| 指标 | 测量方法 | 假设 |
|------|---------|------|
| 映射成功率 | `query/search` API 200 OK 比例 | Schema 膨胀 → 下降 |
| 映射延迟 | embedding 检索 vs LLM 生成分段计时 | 前者线性，后者稳定 |
| SQL 生成延迟 | Query API P50/P95/P99 | 由 LLM 主导，与数据量几乎无关 |
| 失败临界点 | OOM / NPE / timeout 出现位置 | 取决于缓存/分页策略 |

明确假设: "数据量增长对 LLM 生成延迟无显著影响，对映射成功率有负向影响"。

## 6. 项目产出

| 产出 | 路径 | 用途 |
|------|------|------|
| 测评报告 | `evaluation/output/<timestamp>/benchmark_report.json` | 结构化数据 |
| 模型对比 | `evaluation/output/<timestamp>/model_comparison.md` | 面试展示 |
| 容量分析 | `evaluation/output/<timestamp>/capacity_test.md` | 上限分析 |
| 治理对比 | `evaluation/output/<timestamp>/governance_comparison.md` | ROI 分析 |
| 一键脚本 | `evaluation/benchmark.sh` | 可复现 |

## 7. 已知风险与缓解

| 风险 | 缓解 |
|------|------|
| API key 泄露 | 已在本版规格中使用占位符 `<DASHSCOPE_API_KEY>`；旧 commit 中的真实 key 需在 DashScope 控制台 revoke |
| deepseek-v4-flash / glm-5.2 reasoning 吃掉 token 预算 | max_tokens=4096 + timeout=60s |
| glm-5.2 content 截断 | 同上 |
| akShare 限流 + 字段变动 | rate limit + 固定 snapshot 日期 + 字段存在性校验 |
| H2 内存模式重启丢失数据 | 切换到 Docker PostgreSQL 持久化 |
| 模型静默升级 (DashScope) | 每次跑完记录模型返回的 version 字段 |
| SuperSonic 版本 drift | 记录 git commit hash |
| DashScope QPS 限流 | 串行执行 + sleep(3) 间隔 |
| 多个 Level 的 API 编排脚本复杂度 | 复用 CSMAR 管线脚本模板 |
| 小样本统计效力不足 | 所有准确率附 n 和 Wilson 95% CI |

## 8. 可复现性 Checklist

- [ ] git commit hash 记录: `git rev-parse HEAD`
- [ ] Python venv 锁定: `pip freeze > evaluation/requirements-freeze.txt`
- [ ] DashScope 模型版本: 每条查询记录 `response.model`
- [ ] SuperSonic 配置快照: 保存 `s2_chat_model` 表的模型配置
- [ ] akShare 数据 snapshot 日期: 记录数据拉取日期
- [ ] 所有环境变量通过 shell script 显式设置，无隐式依赖
