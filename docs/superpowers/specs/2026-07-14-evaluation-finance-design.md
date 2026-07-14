# SuperSonic 金融数据测评方案设计（evaluation-finance）

> 状态: 设计已批准 | 日期: 2026-07-14
> 参考: FinVerBench (Panda, 2026) 的四类错误分类法 + CSMAR 数据描述规范

## 1. 目标

构建基于沪深 300 A 股财务数据的 SuperSonic Text2SQL 测评集，覆盖 4 类场景 × 4 级难度共 100 题，在 qwen3.7-plus 和 deepseek-v4-pro 两个模型上运行测评，重点回答：

1. 两个模型在金融 NL→SQL 场景下的准确率对比
2. 语义层衍生指标对准确率的影响（有 vs 无衍生指标的差值）
3. SuperSonic 语义层在金融场景下的瓶颈点

## 2. 数据管线

### 2.1 数据获取

```python
# akShare 数据源
沪深300成分股列表  → ak.index_stock_cons()
资产负债表          → ak.stock_balance_sheet_by_report_em()
利润表              → ak.stock_profit_sheet_by_report_em()
现金流量表          → ak.stock_cash_flow_sheet_by_report_em()
```

### 2.2 数据范围

- 成分股: 沪深 300
- 报告期: 最近 5 期年报（如 2021/2022/2023/2024/2025）
- 存储: SQLite（`evaluation-finance/data/csi300.db`）
- 校验: stock_code 连续性校验，缺失的跳过；字段存在性校验

### 2.3 表结构

**balance_sheet（资产负债表）**:
stock_code, stock_name, report_date, total_assets, total_liabilities, total_equity, current_assets, current_liabilities, non_current_assets, non_current_liabilities, ...

**income_stmt（利润表）**:
stock_code, stock_name, report_date, revenue, operating_cost, selling_expense, admin_expense, rd_expense, operating_profit, net_profit, ...

**cash_flow（现金流量表）**:
stock_code, stock_name, report_date, operating_cf, investing_cf, financing_cf, net_cf, ...

> 注：具体字段以 akShare 实际返回为准。拉取后择优选取 15-20 个核心字段。

## 3. 语义层设计

### 3.1 注释规范（参考 CSMAR DES 文件格式）

```yaml
# 维度
- name: 中文名称（如"证券简称"）
  bizName: 英文字段名（如"stock_name"）
  description: 详细说明（如"以沪、深证券交易所公布的证券简称为准"）

# 指标
- name: 中文名称（如"净利润"）
  bizName: 英文字段名（如"net_profit"）
  description: 含义 + 单位（如"利润表中归属于母公司股东的净利润，单位：元"）

# 衍生指标
- name: 中文名称（如"净资产收益率"）
  bizName: 英文字段名（如"ROE"）
  description: 含义 + 计算公式（如"净资产收益率，计算公式为：净利润/净资产×100%"）
```

### 3.2 语义模型层级

```
Domain: 沪深300财务数据 (bizName: csi300)

Model 1: 资产负债表 (bizName: balance_sheet)
  ├── dimensions: stock_code(股票代码), stock_name(公司简称), report_date(报告期)
  ├── measures: total_assets(总资产), total_liabilities(总负债), current_assets(流动资产),
  │             current_liabilities(流动负债), ...
  └── 所有字段带完整中文注释

Model 2: 利润表 (bizName: income_stmt)
  ├── dimensions: stock_code, stock_name, report_date
  ├── measures: revenue(营业总收入), operating_cost(营业成本), net_profit(净利润), ...
  └── 同上

Model 3: 现金流量表 (bizName: cash_flow)
  ├── dimensions: stock_code, stock_name, report_date
  ├── measures: operating_cf(经营现金流), investing_cf(投资现金流), financing_cf(筹资现金流), net_cf(净现金流)
  └── 同上

Model Relations:
  balance_sheet ↔ income_stmt ON (stock_code + report_date)
  balance_sheet ↔ cash_flow    ON (stock_code + report_date)

Dataset: 沪深300财务全景 (bizName: csi300_finance)
  └── 聚合 3 个 Model，引用全部维度+指标

Agents (×2):
  CSI300 Qwen3.7+   — chatModelId → qwen3.7-plus
  CSI300 DeepSeekV4 — chatModelId → deepseek-v4-pro
  共享同一 Dataset
```

### 3.3 衍生指标（方案 3：建 6 个核心的）

| 衍生指标 | 公式 | 涉及报表 |
|---------|------|---------|
| ROE（净资产收益率） | net_profit / total_equity | IS + BS |
| ROA（总资产收益率） | net_profit / total_assets | IS + BS |
| 资产负债率 | total_liabilities / total_assets | BS |
| 流动比率 | current_assets / current_liabilities | BS |
| 毛利率 | (revenue - operating_cost) / revenue | IS |
| 经营现金流比 | operating_cf / net_profit | CF + IS |

## 4. 测试集设计

### 4.1 题目分类体系（FinVerBench 映射）

| 类型 | 全称 | 测什么 | FinVerBench 对应 |
|------|------|--------|-----------------|
| AS | 算术校验 | 聚合/表达式计算 | Arithmetic Errors |
| CL | 跨表关联 | 报表间勾稽关系 | Cross-Statement Linkage |
| YoY | 同比分析 | 时间序列比较 | Year-over-Year |
| MG | 量级敏感 | 数值范围/排序 | Magnitude Perturbations |

### 4.2 100 题分配

| 类型 | easy | medium | hard | extra | 小计 |
|------|------|--------|------|-------|------|
| AS 算术 | 6 | 7 | 7 | 5 | 25 |
| CL 跨表 | 4 | 8 | 8 | 5 | 25 |
| YoY 同比 | 5 | 7 | 8 | 5 | 25 |
| MG 量级 | 5 | 8 | 7 | 5 | 25 |
| **合计** | **20** | **30** | **30** | **20** | **100** |

难度定义：
- easy: 单表 + 单聚合/单过滤
- medium: 单表多条件 / 两表 JOIN + 聚合
- hard: 三表 JOIN / 窗口函数 / HAVING / 衍生指标
- extra: 嵌套子查询 / 多期自关联 / 复合比率

衍生指标穿插策略：每类题目中，约一半 gold SQL 用到语义层已有衍生指标，另一半要求 LLM 自己拼表达式，用于对比分析。

### 4.3 Gold 标注格式

```
query_text: 自然语言问题
gold_sql: 参考 SQL（SQLite 语法）
difficulty: easy/medium/hard/extra
category: AS/CL/YoY/MG
has_derived_in_gold: true/false
tables_needed: [balance_sheet, income_stmt, cash_flow]
notes: 考点说明
```

### 4.4 生成流程

1. 拉完数据建好 schema 后，写出完整的 schema 说明 + 4 类题目模板 + 5 条示例
2. 喂给 deepseek-v4-pro，先出 5 题验证格式
3. 确认格式 → 要求批量生成 100 题
4. 人工审核所有 gold SQL
5. 入库为 `evaluation-finance/data/gold.txt`

## 5. 目录结构

```
evaluation-finance/
├── data/
│   ├── csi300.db              # SQLite 数据库
│   └── gold.txt               # 100 条 gold SQL
├── scripts/
│   ├── fetch_data.py          # akShare 数据拉取 + 入库
│   ├── build_semantic.py      # 构建 Domain/Model/Dataset/Agent
│   ├── generate_questions.py  # 调用 deepseek-v4-pro 生成题目 + gold
│   ├── run_eval.py            # 100 题 × 2 模型跑批
│   ├── calc_accuracy.py       # 执行准确率 + 衍生指标对比
│   └── report.py              # 生成汇总报告
├── output/                    # 跑批结果
└── README.md
```

## 6. 评分方法

采用 Execution Accuracy，逻辑如下：

1. 将 pred SQL 和 gold SQL 分别在 SQLite 上执行
2. 对比时只比较 gold SQL 要求的列（pred 多余的列忽略）
3. 按列名匹配 → 每列的值排序后比对 → 两边的 map 完全相等判正确
4. 列顺序、行顺序不影响；但少列、多行、值不匹配判错
5. 浮点数精确比较（不设容差，统一精度由 gold SQL 中显式控制）

## 7. 测评指标

| 指标层 | 指标 | 说明 |
|--------|------|------|
| 可用率 | ok / parse_fail / timeout / exception 分布 | 按模型分 |
| 准确率 | Execution Accuracy × 难度 × 类型 × 模型 | 带 Wilson 95% CI |
| 衍生对比 | 有衍生指标 vs 无衍生指标的准确率差值 | 核心卖点量化 |
| 延迟 | avg / p50 / p95 | 按模型分 |
| 错误分析 | 翻车题型 Top N | 定性分析 |

## 8. 风险与缓解

| 风险 | 缓解 |
|------|------|
| akShare 限流/字段变动 | 固定 snapshot + 字段存在性校验 |
| deepseek-v4-pro 生成的 gold SQL 有逻辑错误 | 每题人工审核 + 执行验真 |
| 沪深 300 成分股 5 期内有退市/更名 | 拉取时校验 stock_code 连续性，缺失跳过 |
| 100 题跑双模型超时 | 1.5s 速率限制间隔；分成 2 批并行 |
| 浮点数精度不一致 | gold SQL 中显式 CAST/ROUND 控制精度 |
| SuperSonic 版本 drift | 记录 git commit hash |

## 9. 排期

| Phase | 内容 | 预估 |
|-------|------|------|
| 1 | 数据拉取 + 语义层构建 | 半天 |
| 2 | 5 题生成 + 格式验证 | 1h（人在回路） |
| 3 | 100 题批量生成 + 审核 | 半天（人在回路） |
| 4 | 跑批 + 出报告 | 2h（自动化） |

## 10. 可复现性 Checklist

- [ ] git commit hash 记录
- [ ] Python venv 锁定
- [ ] akShare 数据 snapshot 日期
- [ ] SuperSonic 配置快照
- [ ] DashScope 模型版本记录
- [ ] 所有环境变量显式设置，无隐式依赖
