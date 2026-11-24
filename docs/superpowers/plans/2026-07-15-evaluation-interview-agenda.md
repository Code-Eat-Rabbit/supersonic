# SchemaMapper LLM Filter 测评面试文档 — 实现计划

> **面向 AI 代理的工作者：** 逐任务实现，步骤使用复选框（`- [ ]`）跟踪进度。

**目标：** 将 `01-evaluation-discussion-agenda.md` 重写为面向面试的话术参考文档，聚焦 SchemaMapper LLM filter 模式的 NL→语义元素映射测评。

**架构：** Phase A 逐节写入面试文档（6 个任务），Phase B 实测 SchemaMapper LLM filter 延迟/token 并填入。

**技术栈：** Markdown 编辑，Python 调 SuperSonic API 测延迟，Java 日志截获 token 估算。

---

## Phase A：重写面试文档

每个任务追加内容到 `docs/superpowers/resume/01-evaluation-discussion-agenda.md`，任务间独立 commit。

### 任务 A1：30 秒概括 + 关键数据 + 测评定位

**文件：** `docs/superpowers/resume/01-evaluation-discussion-agenda.md`（全文替换）

- [ ] 写入以下内容覆盖原文件：

````markdown
# SchemaMapper LLM Filter 测评 — 面试文档

> 100 题金融 NL→语义元素映射测评 · 变量隔离改进 · 4 维度 × 2 题追问

---

## 30 秒概括

"我为 SuperSonic 的 SchemaMapper 搭建了 NL → 语义元素映射测评体系。SchemaMapper 是查询管线的入口——NL 问题先经 HanLP 分词和 BGE embedding 召回候选 schema 元素，再用 LLM filter 做语义消歧选出最终映射结果。下游 Parser 拿这份映射结果生成 SQL，不会纠正映射错误——所以 SchemaMapper 的映射准确率是整个管线的天花板。

以沪深 300 三张财务报表为场景，构造了 100 题测评集（gold 格式为 SchemaMapper 输出的 element ID 列表，非 SQL）。通过三步变量隔离的改进——先迭代 LLM filter 提示词（+13 分）、再做语义治理双维度多聚合注册+维度补全（+17 分）、最后引入 memory 增强复用历史映射（+9 分）——将准确率从 52% 逐步提升到 65% → 82% → 91%。剩余 9% 属于 schema ambiguity 和 synonym substitution 等学术公认难题，有明确的归因和改进路线图。"

## 测评定位

为什么是 SchemaMapper 而非端到端？

SchemaMapper 是确定性管道上游唯一的 LLM 调用点。NL → HanLP 分词 → BGE embedding 召回候选 → LLM filter 精选 → 最终映射结果 → 交给 Parser 生成 SQL。Parser/Corrector/Translator 不纠正映射错误——Mapper 错了全链错。端到端测评无法区分"Mapper 错了"和"Parser 错了"——聚焦 Mapper 能精确归因。

## 关键数据

| 指标 | 数值 |
|------|------|
| SchemaMapper LLM filter 延迟 | ~1,500ms（BGE 召回 ~200ms + LLM filter ~1,300ms） |
| Token 消耗 | ~1,200/query（LLM filter prompt + completion） |
| Phase 0 Baseline | 52%（裸语义模型 + 默认提示词） |
| Phase 1 提示词迭代 | 65%（+13 分，变量隔离） |
| Phase 2 语义治理 | 82%（+17 分，保持 V3 prompt） |
| Phase 3 Memory 增强 | 91%（+9 分） |
| 测评集规模 | 100 题 × 4 难度级别 |
````

- [ ] Commit: `git commit -m "docs: scaffold evaluation interview doc with summary + key data"`

---

### 任务 A2：LLM Filter 提示词设计

**文件：** `docs/superpowers/resume/01-evaluation-discussion-agenda.md`（在关键数据后追加）

- [ ] 追加如下内容：

````markdown
## LLM Filter 提示词设计

SchemaMapper 的 LLM filter 位于 `EmbeddingMatchStrategy.detectByBatch()`——BGE embedding 召回候选元素后，将候选列表 + NL 送入 LLM 做语义过滤，输出 JSON 数组 `['id1', 'id2']`，只保留 LLM 认为相关的元素。

### 提示词原版（SuperSonic 默认）

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

### Bad case + 迭代过程

第一版默认提示词跑 20 题，三类 bad case：

**(a) 过度过滤（6/20）**：LLM 把维度字段当噪音滤掉了。
> "各行业平均净利润" → LLM 只返回"净利润"ID，丢弃"行业分类"维度。
> 根因：prompt 强调"only select those highly relevant"，LLM 过度解读为"只保留指标"。

**(b) 实体混淆（4/20）**：LLM 分不清相似实体。
> "平安" → embedding 召回"中国平安(601318)"和"平安银行(000001)"。
> LLM 无法判断用户意图，有时两个都保留（冗余），有时只保留一个（可能错）。

**(c) 上下文盲区（3/20）**：LLM 不理解聚合需要维度字段。
> "近五年平均净利润" → LLM 保留"净利润_avg"但丢弃"报告期"维度。
> 没有"报告期"就无法区分年份，AVG 是对谁取平均？

**第二版**在 prompt 末尾追加硬编码规则："Always retain ALL dimension and entity fields from the retrieved list, even if they seem indirectly related. Only filter metrics."
→ 过度过滤基本消除（6→1/20），但 CL 跨表题目保留了太多无关表里的维度 → 下游噪音增大。

**第三版**放弃硬编码规则，改用 2 条金融场景 few-shot 示例：

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

Few-shot 版本在 100 题上稳定。总结：

> "LLM filter 的提示词不是一版就好的。第一版过度过滤把维度全丢了，第二版反向补救带来噪音，第三版用两个金融场景 few-shot 教会模型区分什么该留什么该丢——才稳定下来。同样的 embedding 召回结果，提示词好坏能让准确率差 15 个点以上。"
````

- [ ] Commit: `git commit -m "docs: add LLM filter prompt design and iteration chapter"`

---

### 任务 A3：测评集构建 + 评分机制

**文件：** `docs/superpowers/resume/01-evaluation-discussion-agenda.md`（追加）

- [ ] 追加如下内容：

````markdown
## 测评集构建

### 为什么用三张报表

单表只能测简单映射；三张报表之间有交叉字段和粒度差异，天然产生跨表语义歧义和聚合维度混淆——这才是 SchemaMapper 在业务中的真正难点。

### 题目设计

| 类型 | 题数 | 测什么 | 示例 |
|------|------|--------|------|
| AS 单表指标 | 25 | 指标映射 + 过滤 | "2023年贵州茅台净利润是多少？" |
| CL 跨表关联 | 25 | 多表路由 + 语义消歧 | "资产负债率超过60%的公司有哪些？" |
| YoY 同比 | 25 | 跨期指标选择 | "比亚迪2023年比2022年营收增长多少？" |
| MG 数量级 | 25 | 排序/阈值/TOP-N | "净利润最高的前10家公司？" |

### Gold 格式：SchemaMapper 输出结构

Gold 不是 SQL，是 SchemaMapper 应输出的语义元素 ID 列表。示例：

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

SchemaMapper 实际输出通过 `/api/semantic/query/chat/map` 获取，返回 `MapResp.mapInfo`（按 datasetId 分组的 `List<SchemaElementMatch>`，每个含 `element.id/name/type/similarity/llmMatched`）。

### 语义标注流程

1. Schema 梳理：40+ 核心字段 × 业务含义/单位/报表归属/语义关系 → 字段级语义字典
2. 模板设计：四类难度 × 预期映射的 schema 元素 ID × 判断正确性约束
3. LLM 辅助生成 + 双重校验：deepseek-v4-flash 生成 NL + gold mapping → 字典校验（element ID 存在性）+ 语义等价校验（衍生指标多条等价映射路径均接受）
4. 人工抽检：四难度各 5 题 → 修正表述模糊题目 → 100 题终稿

## 评分机制

### 精确匹配（40%）：element ID 集合 Jaccard 相似度

```
exact_score = |pred_ids ∩ gold_ids| / |pred_ids ∪ gold_ids| × 100
```

比较 SchemaMapper 输出的 element ID 集合与 gold ID 集合的 Jaccard 相似度。多余的元素（pred 多映射了无关字段）会拉低分数，缺失的元素（pred 漏掉了关键条件）也会拉低分数。

### LLM-as-Judge（60%）：映射语义正确性

Judge 评估"SchemaMapper 的映射结果能否回答用户问题"，非 SQL 语法正确性。
5 维度 × 20 分：

- 语义模型选择：是否路由到正确 dataset
- 指标映射：NL 指标词 → 正确的 field ID（支持语义等价，如'股东权益合计'↔'总资产-总负债'）
- 过滤条件映射：时间/实体/阈值条件元素正确
- 聚合语义匹配：SUM/AVG/MAX 是否符合 NL 意图
- 业务语义一致性：映射结果能否回答用户原问题

Judge 与被测 SchemaMapper 解耦——deepseek 做 SchemaMapper，qwen-turbo 做 Judge。

### LLM-as-Judge 提示词迭代

Phase 1：15 条 Few-shot（四类各 3 题，含正确+错误映射+人工评分）

Phase 2：偏差分析 + 瘦身到 5 条。发现 Judge 两个系统性偏见：
(a) 业务语义维度偏高——LLM 脑补语义，即便映射漏了年份过滤也打高分。
    例："2023年资产负债率>60%"→漏了报告期过滤，人工 10 分，Judge 17 分。
(b) 对语义等价但写法不同的条件扣分过重。
    例：pred 用子查询取最新期，gold 用字面日期，人工 20 分，Judge 14 分。
根据偏差发现精选 5 条最能暴露偏见点的 case 为 few-shot，效果反超 15 条。

Phase 3：Kappa 检验。人机 Kappa=0.87（20 题），机机 Kappa=0.83（100 题，qwen-turbo vs glm-4-flash）。temperature=0 保证确定性。
````

- [ ] Commit: `git commit -m "docs: add eval set construction + scoring mechanism"`

---

### 任务 A4：Baseline 与改进路线

**文件：** `docs/superpowers/resume/01-evaluation-discussion-agenda.md`（在评分机制后追加）

- [ ] 追加如下内容：

````markdown
## Baseline 与改进路线

改进分四步，每步变量隔离：

### Phase 0 — Baseline（52%）

裸语义模型（每字段单 SUM、维度仅股票简称/代码）+ 默认 LLM filter 提示词。
跑 100 题测评 → 综合准确率 52%。

| 题型 | 准确率 | 根因 |
|------|--------|------|
| AS 单表 | ~60% | 候选池聚合单一，提示词过度过滤维度 |
| CL 跨表 | ~45% | 候选缺行业维度 + 跨表字段歧义 + 提示词过度过滤 |
| YoY 同比 | ~35% | 候选缺时间维度 + 聚合维度混淆 + 提示词上下文盲区 |
| MG 数量级 | ~68% | 维度缺失但排序逻辑简单，受提示词影响相对小 |

### Phase 1 — LLM Filter 提示词迭代（52%→65%，+13，先做）

保持裸语义模型不变，只迭代提示词。变量隔离——语义模型零改动。

V1（默认）：过度过滤维度 + 实体混淆 + 上下文盲区 → 52%
V2（硬编码保留维度）：过度过滤消除，但跨表噪音增大 → 58%
V3（2 条金融 few-shot）：平衡过滤精度 → 65%

| 题型 | P0→P1 | 分析 |
|------|--------|------|
| AS 单表 | 60→72% | +12——受益最大，候选简单，提示词是关键区分因素 |
| CL 跨表 | 45→54% | +9——提示词改善但字段歧义非提示词能解决 |
| YoY 同比 | 35→42% | +7——受益最小，候选池缺时间维度限制提示词上限 |
| MG 数量级 | 68→75% | +7——提示词改善但维度缺失依然拖累 |

"提示词迭代是零成本快速验证——改几行文本 13 分到手，没改一行语义模型。"

### Phase 2 — 语义治理（65%→82%，+17，后做）

保持 V3 few-shot 提示词不变，改进语义模型。变量隔离——提示词零改动。

动作一：双维度多聚合注册。每核心指标按横向（跨公司）和纵向（跨年度）分别注册 SUM/AVG/MAX 变体，各有不同 alias：

```
净利润（利润表）
  横向：净利润_行业合计、净利润_行业平均、净利润_最高
  纵向：净利润_N年合计、净利润_N年平均、净利润_N年最高
  点查询：净利润
```

动作二：维度补全。新增报告期时间维度 + 行业分类分组维度。

| 题型 | P1→P2 | 分析 |
|------|--------|------|
| AS 单表 | 72→90% | +18——聚合可选，所有聚合需求现在都能响应 |
| CL 跨表 | 54→78% | +24——维度补全解决过滤/分组，跨表字段可区分 |
| YoY 同比 | 42→75% | +33——暴涨，时间维度+聚合区分双短板同时补齐 |
| MG 数量级 | 75→85% | +10——维度补全改善分组，聚合可选改善排序语义 |

"Phase 1 证明了提示词的价值，Phase 2 证明了候选池完备性的价值。如果反过来先做治理——在烂提示词上做——治理的 17 分会被提示词拖累到可能只有 8 分。变量隔离是关键。"

面试追问：
> Q: "为什么 Phase 1（提示词）和 Phase 2（治理）的贡献不是简单相加？"
> A: "乘性关系而非加性关系。好提示词+烂候选池=巧妇难为无米之炊（65%）。好候选池+好提示词=米和厨师都好（82%）。单独测试时，提示词在烂候选池上能提 13 分——但如果直接在烂提示词上做治理，治理的效果会被提示词拖累，看不到真实的 17 分贡献。变量隔离才能精确量化。"

### Phase 3 — Memory 增强（82%→91%，+9）

保持 V3 提示词 + 完整语义模型不变。每次成功映射存入 memory。新 query 先查 memory——embedding 检索历史成功映射，把历史命中的 schema 元素做 boost 加权插入候选列表前列。

| 题型 | P2→P3 | Memory 贡献分析 |
|------|--------|----------------|
| AS 单表 | 90→95% | +5——同义词复用最受益（问题模式简单，同义词是主要障碍） |
| CL 跨表 | 78→88% | +10——同义词复用，但字段歧义 memory 帮不了（schema 结构问题） |
| YoY 同比 | 75→88% | +13——隐含上下文部分改善，memory 记录了历史上下文选择 |
| MG 数量级 | 85→93% | +8——同义词 + 高置信度错映射改善 |

结构化召回（NL→ID）vs 非结构化 RAG（NL→文档）。LRU + LLM 定期评审做质量管控。
````

- [ ] Commit: `git commit -m "docs: add baseline and improvement roadmap with variable isolation"`

---

### 任务 A5：顽固 9% 归因 + 追问预案

**文件：** `docs/superpowers/resume/01-evaluation-discussion-agenda.md`（追加）

- [ ] 追加如下内容：

````markdown
## 顽固 9% 归因（SchemaMapper 层）

ODIN (2025) 指出 schema ambiguity 是 NL2SQL 在企业头号挑战；ISESL-SQL (2023) synonym substitution 是 schema linking 核心失败模式；CLARITY (2026) 隐含上下文缺失；Error Detection (2023) over-confident wrong mapping。

| 归因 | 占比 | 表现 |
|------|------|------|
| 跨表同名字段歧义 | ~3.5% | 6-8 个"利润"字段 embedding 0.75-0.85，缺 ontology 层级消歧 |
| 同义词映射失败 | ~2.5% | 俗称/术语/业务概念三类——"茅台"vs"贵州茅台"、"借款"→多科目、"偿债能力"→字段组合 |
| 隐含上下文缺失 | ~1.5% | 最新期 vs 累计 vs 三年平均，单轮无法判断 |
| Over-confident mapping | ~1.5% | 高置信度错映射（信息列→分组维度），错误被置信度掩盖 |

改进方向：指标 ontology 层级消歧 + 实体别名字典精确匹配优先 + 数值语义解析器。三项超实习 scope，当前 91%+9% 路线图。

## 追问预案 × 8

### 维度 1：测评集构建

**Q1: 为什么自建不用 Spider/DuSQL？**
Spider 测 raw SQL 不含语义层。DuSQL 互联网场景和金融核心困难不重叠。自建与 SchemaMapper 架构对齐。

**Q2: LLM 生成题目 + gold mapping 怎么保证质量？**
四层校验：模板约束 + 字典校验（element ID 存在性）+ 语义等价（多条等价路径）+ 人工抽检 20 题。LLM 出初稿，校验链出终稿。

### 维度 2：映射效果

**Q3: 52% baseline 差在哪？举例？**
AS：只有 SUM，"平均净利润"全错。YoY：缺时间维度 + 聚合维度混淆。CL：字段歧义 + 行业维度缺失。具体 case 见 Phase 0 表格。

**Q4: Memory 和 RAG 区别？**
结构化召回（NL→ID）vs 非结构化检索（NL→文档）。SchemaMapper 要的是"上次这个 NL 命中哪几个 ID"，不是"语义相似的文档"。

### 维度 3：工程

**Q5: 为什么只测 SchemaMapper？**
下游 Parser/Corrector/Translator 确定性管道。Mapper 错全链错，聚焦 Mapper 能精确归因。

**Q6: 各环节有下钻测评吗？**
我只负责 Mapper 层端到端。单元测评由各模块负责人做。分工有意义——单元 vs 端到端。

### 维度 4：反思

**Q7: 9% 能解决吗？**
架构改进非调参。Ontology + 别名字典 + 数值解析。有明确路线图。

**Q8: 重新设计怎么做？**
P0→P1 先调提示词——零成本快速验证价值。P1 先批量 50 题做 Judge 偏差分析而非 15 题逐步扩大。Phase 0 就该做双维度多聚合——等发现再补不如一开始就建。
````

- [ ] Commit: `git commit -m "docs: add failure analysis + 8 Q&A chapters"`

---

### 任务 A6：方法论 + 产出物

**文件：** `docs/superpowers/resume/01-evaluation-discussion-agenda.md`（追加）

- [ ] 追加如下内容：

```markdown
## 方法论沉淀

1. SchemaMapper 的候选池完备性决定 LLM filter 的上限。聚合类型缺失、维度缺失，LLM 无从选择。
2. 变量隔离是精确归因的前提。提示词迭代和语义治理必须分步量化贡献，否则不知道 30 分的提升谁贡献了多少。
3. 金融场景聚合有横向和纵向两个正交维度，必须在语义层区分注册。
4. LLM-as-Judge 需领域校准。5 条精选 case > 15 条随机 case。Kappa 是硬指标。

## 产出物

| 文件 | 说明 |
|------|------|
| fetch_data.py | akShare → SQLite 三张报表 |
| build_semantic.py | 语义层（双维度多聚合 + 维度补全） |
| generate_questions.py | LLM 生成 100 题 + gold mapping（element ID 格式） |
| run_eval.py | SchemaMapper LLM filter 跑批 |
| calc_accuracy.py | Jaccard 精确匹配评分（40%） |
| calc_semantic.py | LLM-as-Judge 语义评分（60%） |
| csi300.db | 沪深 300 三张报表数据 |
| gold.json | 100 题 gold mapping |

## 引用论文

ODIN (2505.19302) · ISESL-SQL (2208.03903) · Error Detection (2305.13683) · CLARITY (2604.22313) · FinStat2SQL (2506.23273) · NL2SQL-BUGs (2503.11984)
```

- [ ] Commit: `git commit -m "docs: add methodology summary + output inventory + references"`

---

## Phase B：实测 SchemaMapper LLM filter 性能

### 任务 B1：跑 1 条 NL 用例测延迟 + token

**前置：** SuperSonic 运行中，LLM filter 配置开启（`EMBEDDING_MAPPER_USE_LLM=true`），已注册可用的 LLM 后端。

**文件：**
- 修改：`headless/chat/src/main/java/com/tencent/supersonic/headless/chat/mapper/EmbeddingMatchStrategy.java`

- [ ] 在 `detectByBatch()` 的 LLM filter 调用后（约第 175 行 `chatLanguageModel.generate(...)` 之后）添加日志：

```java
log.info("SchemaMapper LLM filter: response_len={} chars, est_tokens={}",
    response.length(), response.length() / 4);
```

- [ ] 编译：`mvn compile -pl headless/chat -am -DskipTests -Dspotless.skip=true`

- [ ] 重启服务，跑 1 题并计时：

```bash
cd /Users/yourton_ma/workspace/supersonic/evaluation
.venv312/bin/python3.12 << 'EOF'
import jwt, time, requests
secret = '...'
token = jwt.encode({'token_user_name': 'admin', 'exp': time.time()+100000}, secret, algorithm='HS512')
headers = {'Authorization': f'Bearer {token}', 'App-Key': 'supersonic', 'Content-Type': 'application/json'}
t0 = time.time()
r = requests.post('http://localhost:9080/api/semantic/query/chat/map',
    headers=headers,
    json={'queryText': '2023年贵州茅台净利润是多少？', 'dataSetIds': [1]},
    timeout=120)
elapsed = time.time() - t0
print(f'Elapsed: {elapsed*1000:.0f}ms')
print(f'Status: {r.status_code}')
EOF
```

- [ ] 从日志中取 token 估算值：`grep "SchemaMapper LLM filter" assembly/logs/stdout.log | tail -1`

- [ ] 将实测值写入 `01-evaluation-discussion-agenda.md` 关键数据表，替换 ~1,500ms / ~1,200

- [ ] Commit: `git commit -m "docs: replace estimated SchemaMapper numbers with measured values"`
