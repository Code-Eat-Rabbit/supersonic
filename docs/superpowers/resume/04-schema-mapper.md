# 语义层建模引擎（SchemaMapper LLM 增强）

## 简历文案

> 为 SchemaMapper 引入 LLM Filter 机制：在 HanLP 分词 + BGE embedding 粗排召回候选字段后，由 LLM 对候选做语义消歧精选；通过三步变量隔离实验将映射准确率从 52% 提升至 91%，剩余 9% 顽固 case 完成归因分析并制定改进路线

---

## 架构全景

```
用户 NL: "2023年贵州茅台净利润"
    │
    ▼
SchemaMapper（SPI 链，按 spring.factories 注册顺序执行）
    │
    ├─ EmbeddingMapper → BGE embedding 粗排召回 Top-N 候选元素
    ├─ KeywordMapper  → HanLP 分词 + 字典精确匹配
    ├─ TermDescMapper → 术语描述匹配
    ├─ QueryFilterMapper → 过滤条件映射
    ├─ PartitionTimeMapper → 时间分区映射
    └─ AllFieldMapper → 全字段兜底
    │
    ▼
候选元素列表（可能包含无关项）
    │
    ▼
LLM Filter（EmbeddingMatchStrategy.detectByBatch）
    ├─ Prompt: 候选列表 + NL → LLM 语义消歧
    └─ 输出: ['id1', 'id2', 'id3']（只保留相关元素）
    │
    ▼
最终映射: { metrics: [净利润], dimensions: [报告期, 股票简称], values: [2023, 贵州茅台] }
    │
    ▼
交给 Parser → Corrector → Translator → SQL
```

### 为什么只测 SchemaMapper 而非端到端？

SchemaMapper 是查询管线中上游唯一的 LLM 调用点。下游 Parser/Corrector/Translator 是确定性管道——不纠正映射错误。**Mapper 错了全链错**。端到端测评无法区分"Mapper 错了"和"Parser 错了"——聚焦 Mapper 能精确归因。

---

## 三步变量隔离：52% → 65% → 82% → 91%

核心方法论：**每次只改一个变量**，确保能精确量化每个改进动作的贡献。

### Phase 1 — LLM Filter 提示词迭代（52%→65%，+13 分）

**变量隔离**：语义模型零改动，只改 prompt。

```
V1（默认）: 过度过滤维度 + 实体混淆 + 上下文盲区 → 52%
V2（硬编码保留维度）: 过度过滤消除，但跨表噪音增大 → 58%
V3（2 条金融 few-shot）: 平衡过滤精度 → 65%
```

典型 Bad Case：
- **(a) 过度过滤**："各行业平均净利润" → LLM 只保留"净利润"ID，丢弃"行业分类"维度。根因：prompt 强调"only select highly relevant"，LLM 过度解读。
- **(b) 实体混淆**："平安" → embedding 召回"中国平安"和"平安银行"。LLM 无法判断意图。
- **(c) 上下文盲区**："近五年平均净利润" → 保留"净利润_avg"但丢弃"报告期"维度——没有报告期就无法区分年份。

> "提示词迭代是零成本快速验证——改几行文本 13 分到手，没改一行语义模型。"

### Phase 2 — 语义治理（65%→82%，+17 分）

**变量隔离**：保持 V3 few-shot 提示词不变，只改语义模型。

动作一：**双维度多聚合注册**。每核心指标按横向（跨公司）和纵向（跨年度）分别注册 SUM/AVG/MAX 变体，各有不同 alias：

```
净利润（利润表）
  横向：净利润_行业合计、净利润_行业平均、净利润_最高
  纵向：净利润_N年合计、净利润_N年平均、净利润_N年最高
  点查询：净利润
```

动作二：**维度补全**。新增报告期时间维度 + 行业分类分组维度。

| 题型 | P1→P2 | 分析 |
|------|--------|------|
| YoY 同比 | 42%→75% | **+33**——暴涨。时间维度+聚合区分双短板同时补齐 |
| CL 跨表 | 54%→78% | +24——维度补全解决过滤/分组，跨表字段可区分 |
| AS 单表 | 72%→90% | +18——聚合可选，所有聚合需求现在都能响应 |

> "Phase 1 证明了提示词的价值，Phase 2 证明了候选池完备性的价值。如果反过来先做治理——在烂提示词上做——治理的 17 分可能只有 8 分。**变量隔离是关键。**"

### Phase 3 — Memory 增强（82%→91%，+9 分）

**变量隔离**：保持 V3 提示词 + 完整语义模型不变。

每次成功映射存入 memory。新 query 先查 memory——embedding 检索历史成功映射，把历史命中的 schema 元素做 boost 加权插入候选列表前列。

| 题型 | P2→P3 | Memory 贡献分析 |
|------|--------|----------------|
| YoY 同比 | 75%→88% | +13——Memory 记录了历史上下文选择 |
| CL 跨表 | 78%→88% | +10——同义词复用 |
| AS 单表 | 90%→95% | +5——同义词复用最受益 |

### 为什么 Phase 1 和 Phase 2 的贡献不是简单相加？

**乘性关系而非加性关系**。好提示词+烂候选池=巧妇难为无米之炊（65%）。好候选池+好提示词=米和厨师都好（82%）。单独测试时，提示词在烂候选池上能提 13 分——但如果直接在烂提示词上做治理，治理的效果会被提示词拖累，看不到真实的 17 分贡献。变量隔离才能精确量化。

---

## 顽固 9% 归因

| 归因 | 占比 | 表现 |
|------|------|------|
| 跨表同名字段歧义 | ~3.5% | 6-8 个"利润"字段 embedding 0.75-0.85，缺 ontology 层级消歧 |
| 同义词映射失败 | ~2.5% | "茅台"vs"贵州茅台"、"借款"→多科目、"偿债能力"→字段组合 |
| 隐含上下文缺失 | ~1.5% | 最新期 vs 累计 vs 三年平均，单轮无法判断 |
| Over-confident mapping | ~1.5% | 高置信度错映射（信息列→分组维度），错误被置信度掩盖 |

改进方向：指标 ontology 层级消歧 + 实体别名字典精确匹配优先 + 数值语义解析器。

---

## 评分机制

- **精确匹配（40%）**：element ID 集合 Jaccard 相似度
- **LLM-as-Judge（60%）**：五维度语义评估（模型选择/指标映射/过滤条件/聚合语义/业务一致性）
- Judge 与被测 SchemaMapper 解耦（deepseek 做 Mapper，qwen-turbo 做 Judge）
- 人机 Kappa=0.87，机机 Kappa=0.83

---

## 面试 Q&A

### Q1: 为什么 SchemaMapper 需要 LLM？只用 embedding 不够吗？

Embedding 只能做 surface-level 语义匹配。三个典型问题：

1. **同义词**："营收" vs "销售额" embedding 距离可能很大，但业务语义相同
2. **多义词**："苹果" 在水果电商 vs 数码电商中映射不同字段，embedding 无法区分
3. **上下文依赖**："各行业平均净利润"——embedding 能召回"净利润""行业分类"，但无法判断两者需要同时保留

LLM 能理解上下文，做精准消歧。但全用 LLM 成本高+延迟大——所以用 **embedding 粗排 + LLM 精选** 的两阶段方案。

### Q2: 为什么强调变量隔离？

因为改进动作之间存在交互效应。如果不隔离变量：
- 同时改提示词和语义模型 → 52%→82%，+30 分——但不知道提示词贡献了多少、治理贡献了多少
- 精确归因后才能制定正确的改进策略——"提示词和价值一样重要，不能只做一头"

方法：**每次只改一个变量**——Phase 1 只改 prompt、Phase 2 只改语义模型、Phase 3 只加 memory。

### Q3: SchemaMapper 的完整映射链路是什么？

```java
// spring.factories 注册的 Mapper SPI 链（按顺序执行）:
com.tencent.supersonic.headless.chat.mapper.SchemaMapper=\
    EmbeddingMapper, KeywordMapper, QueryFilterMapper,
    PartitionTimeMapper, TermDescMapper, AllFieldMapper

// 每个 Mapper 负责一类映射:
EmbeddingMapper  → embedding 粗排召回候选
KeywordMapper   → HanLP 分词 + 字典精确匹配
TermDescMapper  → 术语描述匹配
// ...
// 最后 AllFieldMapper 做全字段兜底
```

映射完成后，候选列表进入 LLM Filter（`EmbeddingMatchStrategy.detectByBatch()`）做语义消歧。

### Q4: 9% 顽固 case 的归因怎么做？

从文献中找已经公认的难题分类，然后检查自己的 9 个失败 case 分别属于哪一类：

- ODIN (2025): schema ambiguity 是 NL2SQL 企业头号挑战
- ISESL-SQL (2023): synonym substitution 是 schema linking 核心失败模式
- CLARITY (2026): 隐含上下文缺失

不是盲目猜测，而是基于学术界已有共识的分类体系做归因。

### Q5: SchemaMapper 错了会导致什么后果？

Parser/Corrector/Translator 是确定性管道，不纠正映射错误。如果 SchemaMapper 把"净利润"映射成了"毛利"的 ID，整条链都会在错误的基础上生成 SQL——SQL 语法正确但语义错误。这就是为什么 SchemaMapper 的准确率是整个管线的天花板。

### Q6: 为什么自建测评集而不用 Spider/DuSQL？

- Spider 测 raw SQL 不含语义层（指标/维度/实体的抽象）
- DuSQL 是互联网场景（商品搜索/推荐），和金融场景的核心困难不重叠
- 自建与 SchemaMapper 的架构对齐（gold 格式是 element ID 列表而非 SQL）
