# SuperSonic 全面测评方案设计

> 状态: 待审查 | 日期: 2026-07-14 | 基于 FinVerBench (Panda, 2026) 方法论

## 1. 目标

为面试准备一份可量化的 SuperSonic Text2SQL 性能报告，覆盖三个测评维度，产出可复现、可对比的结构化数据。

## 2. 三维测评框架

```
┌─────────────────────────────────────────────────────────────────┐
│                    SuperSonic 测评框架                           │
├──────────┬─────────────────┬─────────────────┬──────────────────┤
│ 维度      │ 1. 模型对比      │ 2. 数据量测试    │ 3. 治理方案对比   │
├──────────┼─────────────────┼─────────────────┼──────────────────┤
│ 变量      │ 3个LLM模型       │ 数据集规模       │ 数据治理层级      │
│ 固定      │ DuSQL 100条      │ 单模型+Level 2  │ akShare财务数据   │
│ 数据源    │ 内置DuSQL        │ akShare A股      │ akShare A股       │
│ 参考      │ --               │ FinVerBench      │ FinVerBench       │
├──────────┼─────────────────┼─────────────────┼──────────────────┤
│ 核心指标  │ 准确率/延迟/token │ 容量上限/拐点    │ 映射率/SQL准确率  │
└──────────┴─────────────────┴─────────────────┴──────────────────┘
```

## 3. 维度一：模型对比

### 3.1 模型选择

三个模型统一走 DashScope compatible-mode API (`https://dashscope.aliyuncs.com/compatible-mode/v1`)：

| 模型 | DashScope name | provider | reasoning | 备注 |
|------|---------------|----------|-----------|------|
| Qwen3.7-Plus | `qwen3.7-plus` | OPEN_AI | 无 | 通义原生，预期最稳定 |
| DeepSeek V4 Flash | `deepseek-v4-flash` | OPEN_AI | 总是有 reasoning_content | content 有值，但 token 开销大 |
| GLM-5.2 | `glm-5.2` | OPEN_AI | 重度 reasoning | content 有值但需大 token 预算 |

### 3.2 配置参数

```yaml
provider: OPEN_AI
baseUrl: https://dashscope.aliyuncs.com/compatible-mode/v1
temperature: 0.0
timeOut: 60
apiKey: sk-5956cac478a5429c94d3dadfaa418245  # AES/ECB 加密后写入 DB
```

### 3.3 评估数据集

使用 SuperSonic 内置 DuSQL 评测集：
- 100 条中文自然语言 → SQL 查询
- 4 张表：company, brand, company_brand_revenue, company_revenue
- 4 级难度：easy / medium / hard / extra

### 3.4 指标

| 指标类别 | 具体指标 | 汇总方式 |
|---------|---------|---------|
| 准确率 | Execution Accuracy (按难度) | 各难度 + ALL |
| 准确率 | Exact Match | 整体 |
| 延迟 | avg / min / max / p95 (ms) | 每条查询计时 |
| Token | prompt_tokens / completion_tokens / total | 100条合计 + avg/q |
| 对比 | 三模型横向对比表 | 一张汇总表 |

### 3.5 脚本改动

现有文件修改：
- `build_models.py`: `create_chat_model()` → `create_chat_models()`，一次注册三个模型；新增 `switch_agent_model()` 
- `build_pred_result.py`: 查询函数记录 `latency_ms` + `token_usage`
- `evaluation.py`: 新增 `evaluate_multi_model()` 入口 + `benchmark_report.json` 输出

新增文件：
- `benchmark.sh`: 一键启动脚本

实现优化：不重启服务，通过切换 Agent 的 `chatModelId` 轮换模型。

### 3.6 输出

- `benchmark_report.json`: 完整结构化数据
- `error_case.json`: 按模型分目录的错误案例
- 终端对比表格：准确率/延迟/token 三维度

## 4. 维度二：数据量 / 容量测试

### 4.1 参考 FinVerBench 的报表结构

FinVerBench 使用三大财务报表 (BS/IS/CFS) 构建 1,985 条测试实例。我们对标使用 akShare A 股财务数据：

### 4.2 数据源

```
akShare A股财务数据集:

1. 资产负债表: ak.stock_balance_sheet_by_report_em()
   字段: 总资产/总负债/股东权益/流动资产/货币资金/应收账款/存货/固定资产等

2. 利润表: ak.stock_profit_sheet_by_report_em()
   字段: 营业收入/营业成本/营业利润/利润总额/净利润等

3. 现金流量表: ak.stock_cash_flow_sheet_by_report_em()
   字段: 经营活动/投资活动/筹资活动现金流净额等

4. 股本结构: ak.stock_individual_info_em() (公司基本信息)
```

### 4.3 测试递进

```
第1轮 — 5家公司 × 3报表 = 15张表
  目标: 验证脚本正确性
  测试: 单表聚合 + 两表JOIN + 三表交叉验证

第2轮 — 20家公司 × 3报表 = 60张表
  目标: 观察性能拐点
  测试: 多表JOIN 查询延迟趋势

第3轮 — 50-100家公司
  目标: 饱和测试，找到上限
  测试: 跨公司对比查询
```

### 4.4 测试指标

| 指标 | 测量方法 |
|------|---------|
| 建模耗时 | `createModel` API 响应时间 |
| 映射成功率 | `query/search` API 200 OK 比例 |
| SQL 生成延迟 | Query API P50/P95/P99 |
| 失败临界点 | OOM / NPE / timeout 出现位置 |

## 5. 维度三：数据治理方案对比

### 5.1 核心洞察

SuperSonic 与 FinVerBench 的关键区别：SuperSonic 在数据和 SQL 之间有一层语义建模。测试不同治理层级可以量化这层语义建模的价值。

### 5.2 三级治理定义

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
  └── 值: 原始编码值 (如教育背景=5)

Level 2 — 完整治理 (参考 CSMAR 管线经验)
  ├── 列名: 中文视图 (v_xxx)
  ├── 维度类型: 全标注
  ├── Metric: 全定义
  ├── 值映射: 解码视图 (5→博士研究生)
  ├── 值级 Embedding: BGE-small-zh 手动生成
  ├── 单字词补充: "独立"/"董事"/"博士"/"减持"
  └── EmbeddedMapper: use-llm-enhance 启用
```

### 5.3 预期表现对比

```
                  Level 0    Level 1    Level 2
映射成功率         < 20%      ~50-70%    > 90%
SQL 准确率         ~0%        ~30-50%    ~60-80%
可查询覆盖比例     极少       单表基础    多表JOIN
```

### 5.4 测试方法

同一份 akShare 数据，对三个 Level 分别注册独立的 Domain/Dataset/Model/Agent，跑相同查询集，对比映射成功率 + SQL 准确率 + 延迟 + Token。

## 6. 项目产出

| 产出 | 用途 |
|------|------|
| `benchmark_report.json` | 结构化测评数据 |
| `model_comparison.md` | 面试用三模型对比分析 |
| `capacity_test.md` | 数据量上限分析 |
| `governance_comparison.md` | 治理方案 ROI 分析 |
| `evaluation/benchmark.sh` | 一键复现脚本 |

## 7. 已知风险与缓解

| 风险 | 缓解 |
|------|------|
| deepseek-v4-flash reasoning 吃掉 token 预算 | 设置 max_tokens=4096 + timeout=60s |
| glm-5.2 content 截断 | 同上，大 token 预算 |
| 100 家公司数据 akShare 限流 | 加 rate limit + 分批拉取 |
| H2 内存模式重启丢失数据 | 切换到 Docker PostgreSQL 持久化 |
| Embedding 生成耗时 | 限制在 Level 2 测试时生成 |
| 多个治理 Level 的 API 编排脚本复杂度 | 复用 CSMAR 管线脚本模板 |
