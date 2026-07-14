# SuperSonic 全面测评方案设计

> 状态: 待审查 (v3 — R2 修正) | 日期: 2026-07-14
> 参考: FinVerBench (Panda, 2026) 的财务报表数据结构与受控对比思想

## 1. 目标

为面试准备一份可量化、可复现的 SuperSonic Text2SQL 性能报告，回答三个核心面试问题：
1. 哪个 LLM 模型在 SuperSonic 上表现最好？（模型选型）
2. Agent / Dataset 的最佳规模是多少？（工程最佳实践）
3. SuperSonic 语义层的衍生建模到底值多少钱？（核心卖点量化）

## 2. SuperSonic 语义模型层级（基础共识）

本文后续所有设计的术语均基于以下代码核查结果：

```
Domain 主题域  (可嵌套)
├── Model 模型  (有 domainId, 无 dataSetId)
│   └── ModelDetail 内联定义:
│       ├── identifiers (主键/外键)
│       ├── dimensions  (维度, 创建时拆入 s2_dimension 表)
│       ├── measures    (原始物理字段+聚合, 创建时拆入 s2_metric 表)
│       └── fields      (物理列)
│
├── Dataset 数据集 (有 domainId, 无 modelId)
│   └── dataSetModelConfigs: 按 Model 分组引用已存在的维度/指标 ID
│
└── Agent (dataSetIds: Set<Long>)
    └── 只绑定 Dataset, 用户提问时 LLM 看到所绑 Dataset 的 schema
```

**四个关键关系**:
- Model 与 Dataset 是**平级兄弟**，都挂在 Domain 下，互不引用
- 维度/指标**归属 Model**（有 modelId），Dataset 只引用
- 一个 Model 可被多个 Dataset 引用（Dataset 是"逻辑视图"）
- Dataset 可聚合多个 Model，系统用 Model 关系自动处理 JOIN

**两类指标（治理实验的关键变量）**:
- 基础指标: `净利润 = SUM(net_profit)` ← 对应物理字段
- 衍生指标: `净利率 = 净利润 / 营业收入` ← 表达式，不对应物理字段

## 3. 测评框架

```
优先级: 子实验 B B(threshold) > D'(衍生指标) > A(Model数) > 维度一(模型对比) > C(分治策略)

┌──────────┬──────────────────────┬─────────────────────┬──────────────────┐
│ 维度      │ 规模最佳实践 ★        │ 模型对比 (baseline)  │ 衍生指标价值 ★     │
│ 叙事      │ "Agent/Dataset 上限"  │ "模型选型"           │ "语义层值多少钱"   │
│ 数据源    │ akShare A股           │ DuSQL (内置)         │ akShare A股        │
│ 优先      │ 子实验 B 最高ROI      │ baseline             │ 子实验 D'最高ROI   │
└──────────┴──────────────────────┴─────────────────────┴──────────────────┘
```

## 4. 维度一：模型对比（优先级: baseline）

### 4.1 模型选择

三个模型统一走 DashScope compatible-mode API (`https://dashscope.aliyuncs.com/compatible-mode/v1`)：

| 模型 | DashScope name | reasoning 特征 |
|------|---------------|----------------|
| Qwen3.7-Plus | `qwen3.7-plus` | 无 |
| DeepSeek V4 Flash | `deepseek-v4-flash` | reasoning_content 总是存在 |
| GLM-5.2 | `glm-5.2` | 重度 reasoning |

**重要限定**: 本对比是**端到端服务能力对比**，包含 reasoning 开销。

### 4.2 配置

```yaml
provider: OPEN_AI
baseUrl: https://dashscope.aliyuncs.com/compatible-mode/v1
temperature: 0.0
timeOut: 60
apiKey: ${DASHSCOPE_API_KEY}  # 运行时注入，AES/ECB 加密后写入 DB
```

### 4.3 语义模型与 Agent

- DuSQL 语义模型 (Domain/Model/Dataset) **只创建一次**，三模型共享同一套
- 创建 **3 个独立 Agent**，各自绑定 DuSQL 同一个 Dataset，仅 `chatAppConfig.chatModelId` 不同
- `build_models.py` 现有幂等逻辑保证重复运行不创建重复实体

### 4.4 评估数据集

SuperSonic 内置 DuSQL 评测集：100 条 NL→SQL 查询，4 张表，4 级难度。

### 4.5 指标（分层 + 多次运行）

| 指标 | 说明 |
|------|------|
| status 分布 | ok / parse_fail / timeout / exception |
| 端到端可用率 | count(status=ok) / total |
| 纯模型准确率 | 仅在 status=ok 子集上计算 Execution Accuracy |
| Execution Accuracy | 3 次 mean±std，按难度 + ALL |
| 延迟 | avg/min/max/p95 (ms), 3 次 |
| Token | prompt/completion/reasoning(分列), 通过 traceId 关联服务端日志获取 (M8) |
| Wilson 95% CI | 所有准确率附 n |

## 5. Agent / Dataset 规模最佳实践

### 5.1 SuperSonic 的分治机制（代码核查）

**机制 1: Dataset 路由 (winner-takes-all)**

`HeuristicDataSetResolver.java:27-37` — Agent 即使关联 N 个 Dataset，映射阶段只选**相似度最高**的一个进入 LLM。选择优先级：① dataset 总相似度 → ② metric 相似度 → ③ 总和 → ④ metric 使用次数。

**机制 2: Schema 字段过滤**

`LLMRequestService.java:34-47` — `PARSER_FIELDS_COUNT_THRESHOLD` 控制给 LLM 喂全量 schema 还是仅命中元素。默认 0（全量）。

**无硬限制**: Agent.dataSetIds 数量、Dataset 内 Model 数、Dataset 聚合指标数 — 三者均无 MAX 校验。实际瓶颈是 **prompt token 上限**和**映射检索质量**。

### 5.2 四个正交子实验

#### 子实验 A — Dataset 内 Model 数量

- **变量**: 一个 Dataset 的 `dataSetModelConfigs` 含 1 / 5 / 10 / 20 个 Model
- **固定**: 同一 Agent, 单一 Dataset, 全量 schema (threshold=0), 同一份 gold 查询集
- **观察**: 准确率拐点、prompt token 增长、LLM 延迟、context window 是否撞顶
- **假设**: 准确率随 schema 膨胀下降，数据量增长对 LLM 延迟的影响**主要通过 schema 膨胀间接传导**（PromptHelper 把全部 metrics/dimensions 拼入 prompt，prompt token 随 Model 数量近似线性增长）；额外记录 prompt token 作为 schema 膨胀代理变量与延迟做相关性分析

#### 子实验 B — `PARSER_FIELDS_COUNT_THRESHOLD` 调参 ★（最高 ROI）

- **变量**: threshold ∈ {0(全量), 5, 10, 20}
- **固定**: 大 Dataset (20 个 Model), 同一份 gold 查询集
- **观察**: threshold 对准确率、延迟、token 的影响 — 找甜点区
- **叙事价值**: SuperSonic 文档未讲清的调参点，实测数据很有说服力
- **⚠️ 前置验证**: 实施前先实测 `threshold=0` 的真实分支行为

#### 子实验 C — Agent 跨 Dataset 分治策略

- **变量**:
  - 方案 1: 1 个大 Agent 关联 10 个 Dataset（靠 winner-takes-all）
  - 方案 2: 10 个小 Agent 各关联 1 个 Dataset（手工分治）
  - 方案 3: 3 个中 Agent 各关联 3-4 个 Dataset（按业务域分组）
- **观察**: 路由准确率、端到端准确率、运维复杂度
- **目标**: 给出"何时自动路由 / 何时必须手工拆分"的判据

#### 子实验 D' — 衍生指标的价值 ★（最干净治理实验）

利用基础指标 vs 衍生指标的区别，做**真正的单变量**治理实验：

- **变量**: Dataset 是否包含衍生指标
  - 对照组: 只引用基础指标 (`净利润 = SUM(net_profit)`)
  - 实验组: 额外引用衍生指标 (`净利率 = 净利润 / 营业收入`)
- **固定**: 同一物理 Model, 同一份 gold 查询集
- **测试集**: 含"比率/衍生"语义的查询（如"各公司净利率排名"）
  - 对照组: LLM 需要自己拼表达式
  - 实验组: 直接用衍生指标
- **叙事价值**: 直接量化"语义层衍生建模值多少钱"，SuperSonic 区别于纯 Text2SQL 的核心卖点

### 5.3 数据源（akShare A 股）

```
1. 资产负债表: ak.stock_balance_sheet_by_report_em()
2. 利润表: ak.stock_profit_sheet_by_report_em()
3. 现金流量表: ak.stock_cash_flow_sheet_by_report_em()
4. 股本结构: ak.stock_individual_info_em()
```

**表设计**: 按公司分表（每公司 3 张表），制造 schema 膨胀场景，测试 SuperSonic 在多表场景下的表现。

### 5.4 Gold 标注方案

- **Gold 四元组**: `(NL 问题, 目标 Dataset ID, 目标结果集, 参考 SQL)`
- 准确率评判**主用结果集比对**（`eval_exec_match`）
- 参考 SQL 用完整治理写法（最易读）
- 规模: 30-50 条人工标注，1 人编写 + 1 人交叉验证
- `目标 Dataset ID` — 子实验 C 必需（评判路由是否选对）

### 5.5 指标体系

| 指标层 | 指标 | 适用子实验 |
|--------|------|-----------|
| 路由层 | Dataset 选择正确率 (winner==gold) | A / C |
| 路由层 | 纯映射端点 `/api/semantic/query/chat/map` 命中元素分布 | 全部 |
| Prompt 层 | prompt_tokens（通过 traceId 关联服务端日志） | A / B |
| 准确率层 | Execution Accuracy（结果集比对） | 全部 |
| 延迟层 | 映射延迟 / LLM 延迟 / 端到端延迟 | 全部 |
| 容量层 | context window 命中率 / 截断率 | A |

> **M5 修正**: 映射成功率改用 `/api/semantic/query/chat/map` 端点（纯 SchemaMapper 链，不跑 LLM）。删掉"200 OK 比例"指标 — SuperSonic 全局异常处理器把所有异常包成 HTTP 200，此指标无信息量。

> **M8 修正**: token 使用追踪 — SuperSonic 服务端无 `tokenUsage` 暴露。方案: 在 LLM 调用点把 `response.tokenUsage()` 写入 traceId 关联日志，benchmark 脚本通过 traceId 拉日志解析。降级方案: 维度二/三弱化 token 指标，只报延迟。

### 5.6 映射延迟拆分（B6 修正）

`use-llm-enhance` 在 `s2-config.yaml` 中默认 `true`（不是 false）。这意味着每次 embedding 检索会额外调一次 LLM 做二次过滤。延迟需拆三段：

- 纯 embedding 检索延迟 (`use-llm-enhance=false` 时测)
- LLM 二次过滤延迟 (`use-llm-enhance=true` 时的增量)
- NL2SQL 生成延迟

各实验组需显式声明 `use-llm-enhance` 取值。Level 0/1 对照组需明确设为 `false`。

### 5.7 实施优先级

1. **子实验 B** (threshold 调参) — 最高 ROI，叙事最强，代码改动最小
2. **子实验 D'** (衍生指标) — 最干净单变量实验，量化语义层价值
3. **子实验 A** (Model 数) — 验证容量拐点
4. **维度一** (模型对比) — baseline
5. **子实验 C** (分治策略) — 时间允许再做

## 6. 项目产出

| 产出 | 路径 |
|------|------|
| 测评报告 | `evaluation/output/<timestamp>/benchmark_report.json` |
| 模型对比 | `evaluation/output/<timestamp>/model_comparison.md` |
| 规模最佳实践 | `evaluation/output/<timestamp>/scale_best_practices.md` |
| 一键脚本 | `evaluation/benchmark.sh` |

## 7. 已知风险与缓解

| 风险 | 缓解 |
|------|------|
| 泄露的 API key | 在 DashScope 控制台手动 revoke；规格用 `${DASHSCOPE_API_KEY}` 占位符 |
| deepseek/glm reasoning 吃掉 token 预算 | max_tokens=4096 + timeout=60s |
| akShare 限流 + 字段变动 | rate limit + 固定 snapshot 日期 + 字段存在性校验 |
| SuperSonic 版本 drift | 记录 git commit hash |
| 模型静默升级 (DashScope) | 记录 `response.model` 版本字段 |
| schema 膨胀导致 prompt 超 context window | Dataset 拆分 / schema 裁剪 (子实验 B) / 换大窗口模型 |
| per-model 创建耗时被 HTTP round-trip 主导 | 拆 per-model 分布(P50/P95) + 总计 |
| `PARSER_FIELDS_COUNT_THRESHOLD=0` 行为未验证 | 实施前先实测确认分支逻辑 |

## 8. 可复现性 Checklist

- [ ] git commit hash 记录
- [ ] Python venv 锁定: `pip freeze > evaluation/requirements-freeze.txt`
- [ ] DashScope 模型版本记录
- [ ] SuperSonic 配置快照
- [ ] akShare 数据 snapshot 日期
- [ ] 所有环境变量通过 shell script 显式设置，无隐式依赖
