# SchemaMapper LLM Filter 测评 — 面试文档设计

> NL → 语义元素映射测评 · SchemaMapper LLM filter 模式 · 4 维度 × 2 题追问预案

---

## 设计概述

- **目标**：将 `docs/superpowers/resume/01-evaluation-discussion-agenda.md` 重写为面试话术参考
- **范围**：SchemaMapper LLM filter 模式——NL 到语义元素（指标/维度/实体/过滤条件）映射质量
- **场景**：沪深 300 三张财务报表
- **叙事**：52% → 82% → 91%，语义模型完备性三阶段治理
- **管线**：SchemaMapper（6 mapper 串行，LLM filter 为焦点）→ Parser → Corrector → Translator

## 文档结构

```
├── 30 秒概括
├── 测评定位（为什么是 SchemaMapper）
├── 关键数据
├── LLM Filter 提示词设计
│   ├── 提示词原版
│   ├── Bad case：过度过滤 / 实体混淆 / 上下文盲区
│   └── 迭代三版 + 金融场景 few-shot
├── 测评集构建
│   ├── 为什么三张报表
│   ├── 题目设计：四类 × 25 = 100 题
│   ├── gold 格式：SchemaMapper 输出结构
│   ├── 语义标注流程（四步 + 措辞包装）
│   └── 评分机制
│       ├── 精确匹配（40%）：element ID 集合 Jaccard
│       └── LLM-as-Judge（60%）：映射语义正确性
├── Baseline 与改进路线
│   ├── Phase 0：裸语义模型 + 默认提示词 → 52% baseline
│   ├── Phase 1：LLM filter 提示词迭代（先做，变量隔离）
│   │   └── 默认 → 硬编码 → few-shot，+13 分 → 65%
│   ├── Phase 2：双维度多聚合注册 + 维度补全（后做，保持 V3 prompt）
│   │   └── 候选池完备化，+17 分 → 82%
│   └── Phase 3：Memory 增强
│       └── 历史映射 boost，+9 分 → 91%
├── 各阶段四类题目准确率分布表
├── 顽固 9% 归因（论文支撑）
├── 追问预案 × 8
├── 方法论沉淀
└── 产出物清单
```

## 关键设计决策

### 1. 测评对象：SchemaMapper LLM filter 模式

```
NL → HanLP 分词 → BGE embedding 召回候选
  → LLM filter（← 测评聚焦点）→ 最终映射结果
  → Parser（拿映射生成 SQL，不纠错）→ Corrector → Translator
```

Mapper 的输出是 Parser 的输入。Mapper 映射错误则全链错误。端到端测评无法区分"Mapper 错了"和"Parser 错了"——聚焦 Mapper 能精确归因。

### 2. LLM Filter 提示词设计与迭代

SchemaMapper 的 LLM filter 位于 `EmbeddingMatchStrategy.detectByBatch()`。BGE embedding 召回候选元素后，将候选列表 + NL 问题送入 LLM 做语义过滤，输出 JSON 数组 `['id1', 'id2']`，只保留 LLM 认为相关的元素。

**提示词原版（SuperSonic 默认）：**

```
#Role: You are a professional data analyst specializing in metrics and dimensions.
#Task: Given a user query and a list of retrieved metrics/dimensions through vector recall,
please analyze which metrics/dimensions the user is most likely interested in.
#Rules:
1. Based on user query and retrieved info, accurately determine metrics/dimensions
   user truly cares about.
2. Do not return all retrieved info, only select those highly relevant to user query.
3. Maintain high quality output, exclude metrics/dimensions irrelevant to user intent.
4. Output must be in JSON array format, only include IDs, e.g.: ['id1', 'id2']
5. Return JSON content directly without markdown formatting
#Input Example:
#User Query: {{userText}}
#Retrieved Metrics/Dimensions: {{retrievedInfo}}
#Output:
```

**Bad case 三类型 + 迭代过程：**

第一版直接用默认提示词跑 20 题，发现三类 bad case：

(a) **过度过滤**（6/20 题）：LLM 把维度字段当噪音滤掉了。
    例："各行业平均净利润"→LLM 只返回了"净利润"的 ID，把"行业分类"维度过滤掉了——因为 prompt 里强调"only select those highly relevant"，LLM 过度解读为"只保留指标"。

(b) **实体混淆**（4/20 题）：LLM 分不清相似实体。
    例："平安"→embedding 召回"中国平安(601318)"和"平安银行(000001)"都是候选。LLM 无法判断用户说的是哪个，有时两个都保留（冗余），有时只保留一个（可能错）。

(c) **上下文盲区**（3/20 题）：LLM 不理解聚合维度。
    例："近五年平均净利润"→LLM 只保留了"净利润_avg"但丢弃了"报告期"维度。用户要的是跨年度 AVG，维度字段不是冗余——没有"报告期"维度就无法区分不同年份。

第二版在 prompt 末尾追加了一句：

```
#Additional Rule:
- Always retain ALL dimension and entity fields from the retrieved list,
  even if they seem indirectly related. Only filter metrics.
```

过度过滤基本消除（从 6/20 降到 1/20），但带来新问题——CL 跨表题目中 LLM 保留了太多无关表里的维度，增加了下游 Parser 的噪音。

第三版放弃硬编码规则，改为 financial few-shot：

```
#Few-shot Example 1:
User Query: "2023年贵州茅台净利润"
Retrieved: [{"id":"1","name":"净利润","type":"METRIC"},
            {"id":"2","name":"报告期","type":"DIMENSION"},
            {"id":"3","name":"贵州茅台","type":"ENTITY"},
            {"id":"4","name":"毛利","type":"METRIC"}]
Output: ["1","2","3"]  // 保留净利润+报告期+实体，过滤毛利

#Few-shot Example 2:
User Query: "各行业平均资产负债率"
Retrieved: [{"id":"1","name":"资产负债率","type":"METRIC"},
            {"id":"2","name":"行业分类","type":"DIMENSION"},
            {"id":"3","name":"总资产","type":"METRIC"}]
Output: ["1","2"]  // 保留指标+行业维度，过滤总资产（冗余）
```

Few-shot 版本在 100 题上表现稳定。面试时的总结：

"LLM filter 的提示词不是一版就好的。第一版过度过滤把维度全丢了，第二版反向补救带来噪音，第三版用两个金融场景 few-shot 教会模型区分什么该留什么该丢——才稳定下来。这个过程本身也说明，SchemaMapper 的 LLM filter 对提示词设计很敏感——同样的 embedding 召回结果，提示词好坏能让准确率差 15 个点以上。"

### 3. Gold 格式：SchemaMapper 输出结构

非 SQL。Gold 是 SchemaMapper 应输出的语义元素 ID 列表：

```json
{
  "question": "2023年贵州茅台净利润是多少？",
  "datasetId": 1,
  "gold_matches": [
    {"elementId": 101, "type": "METRIC", "name": "净利润"},
    {"elementId": 5, "type": "DIMENSION", "name": "报告期"},
    {"elementId": 3, "type": "DIMENSION", "name": "股票简称"},
    {"elementId": 10, "type": "VALUE", "name": "2023-12-31"},
    {"elementId": 15, "type": "ENTITY", "name": "贵州茅台"}
  ]
}
```

SchemaMapper 输出通过 `/api/semantic/query/chat/map` 获取，返回 `MapResp`（含 `SchemaMapInfo`，按 datasetId 分组的 `List<SchemaElementMatch>`）。每个 `SchemaElementMatch` 含 `element.id`、`element.name`、`element.type`、`similarity`、`llmMatched`。

### 3. 评分机制

**精确匹配（40%）**：pred 和 gold 的 element ID 集合做 Jaccard 相似度（交集 / 并集）。

```
exact_score = |pred_ids ∩ gold_ids| / |pred_ids ∪ gold_ids| × 100
```

**LLM-as-Judge（60%）**：评估映射的语义正确性（非 SQL 正确性）。5 维度 × 20 分：

- 语义模型选择：是否路由到正确 dataset
- 指标映射：NL 指标词 → 正确的 field ID
- 过滤条件映射：时间/实体/阈值条件元素正确
- 聚合语义匹配：SUM/AVG/MAX 类型是否符合 NL 意图
- 业务语义一致性：映射结果能否回答用户原问题

提示词迭代三阶段：15 条 Few-shot → 偏差分析（Judge 脑补语义偏高、对等价写法扣分过重）→ 瘦身到 5 条精选 case → Kappa（人机 0.87 / 机机 0.83）。

**追问：为什么不做下钻测评？**

"我只负责 SchemaMapper 的端到端映射测评。Parser/Corrector 的单元测评由各模块负责人做。端到端聚焦协同质量，单元聚焦模块内部——分工有意义。"

### 4. Baseline 与改进路线（变量隔离）

所有改进分步进行，每步保持其他变量不变，确保每步的贡献可独立量化：

**Phase 0 — Baseline（52%）**：裸语义模型（每字段单 SUM、维度仅股票简称/代码）+ 默认 LLM filter 提示词 → 100 题综合准确率 52%。

**Phase 1 — 提示词迭代（52% → 65%，+13 分，先做）**：
保持裸语义模型不变，只迭代 LLM filter 提示词。V1 默认 → V2 硬编码规则 → V3 金融 few-shot。三版迭代后准确率从 52% 提升到 65%（+13 分）。变量隔离——语义模型没变，提升全部来自提示词改进。

**Phase 2 — 语义治理（65% → 82%，+17 分，后做）**：
保持 V3 few-shot 提示词不变，改进语义模型——双维度多聚合注册 + 维度补全。准确率从 65% 提升到 82%（+17 分）。变量隔离——提示词没变，提升全部来自候选池完备化。

**Phase 3 — Memory 增强（82% → 91%，+9 分）**：
保持 V3 提示词 + 完整语义模型不变，引入 memory 机制。历史成功映射做 boost 加权插入候选列表前列 → 82% → 91%（+9 分）。

**为什么先做提示词后做语义治理？**

"提示词迭代是零成本快速验证——改几行文本就能看到 13 分的提升，不需要重建语义模型、不需要改数据库。确认了 LLM filter 本身能产生价值之后，再投入时间做语义治理——此时多聚合注册和维度补全的 ROI 才被证明。如果反过来先做治理再调提示词，你不知道治理的 30 分里有多少是提示词没调好的锅。"

面试追问：

Q: "为什么 Phase 1（提示词）和 Phase 2（治理）的贡献不是简单相加？"
A: "因为它们是乘性关系而非加性关系。好的提示词 + 烂的候选池 = 巧妇难为无米之炊（65%）。好的候选池 + 好的提示词 = 米和厨师都好（82%）。单独测试时，提示词在烂候选池上能提 13 分——但如果直接在烂提示词上做治理，治理的效果会被提示词拖累，看不到真实的 17 分贡献。所以必须变量隔离。"


### 5. 各阶段四类题目准确率分布

| 题目类型 | Phase 0 (baseline) | Phase 1 (+提示词) | Phase 2 (+治理) | Phase 3 (+memory) |
|---------|--------------------|--------------------|------------------|--------------------|
| AS 单表指标 | ~60% | ~72% | ~90% | ~95% |
| CL 跨表关联 | ~45% | ~54% | ~78% | ~88% |
| YoY 同比   | ~35% | ~42% | ~75% | ~88% |
| MG 数量级  | ~68% | ~75% | ~85% | ~93% |

提示词迭代（P0→P1）对各类型的提升幅度不同——AS 受益最大（+12），因为 AS 的候选简单、提示词好坏是关键区分因素；YoY 受益最小（+7），因为 YoY 的候选池本身缺时间维度，提示词再好也没东西可选。

语义治理（P1→P2）补上了候选池的短板——YoY 暴涨 33 分（时间维度 + 聚合区分同时到位），CL 涨 24 分（维度补全+跨表字段可选），AS 涨 18 分（聚合可选）。

Memory（P2→P3）在 AS 上最有效（+5，同义词复用），在 CL 上中等（+10 但其中字段歧义不变），YoY 上部分有效（+13，隐含上下文改善但未根除）。

### 6. 双维度多聚合注册

同一字段按横向（跨公司）和纵向（跨年度）注册 SUM/AVG/MAX 变体，各有不同 alias。LLM filter 靠 alias 做语义区分。

### 6. 顽固 9% 归因

论文支撑：ODIN (2025)、ISESL-SQL (2023)、CLARITY (2026)、Error Detection (2023)。

| 归因 | 占比 | 表现 |
|------|------|------|
| 跨表同名字段歧义 | ~3.5% | 6-8 个"利润"候选 embedding 0.75-0.85 |
| 同义词映射失败 | ~2.5% | 俗称/术语/业务概念三类 |
| 隐含上下文缺失 | ~1.5% | 最新期 vs 累计 vs 三年平均 |
| Over-confident mapping | ~1.5% | 高置信度错映射 |

### 7. 性能数据

| 指标 | 数值 |
|------|------|
| SchemaMapper LLM filter 延迟 | ~1,500ms（BGE ~200ms + LLM ~1,300ms） |
| Token | ~1,200/query |
| 测试用例 | 1 题（实现阶段实测后替换） |

## 待实现

1. 修改 `01-evaluation-discussion-agenda.md` 按本文档重写
2. 实测 SchemaMapper LLM filter 延迟 + token（1 题，调 `/api/semantic/query/chat/map`）
3. 用实测值替换估算值

## 引用论文

ODIN (2505.19302) · ISESL-SQL (2208.03903) · Error Detection (2305.13683) · CLARITY (2604.22313) · FinStat2SQL (2506.23273) · NL2SQL-BUGs (2503.11984)
