> 系列：智能问数
> 简历基线：[`../../my_resume.md`](../../my_resume.md)
> 总览：[`01-总览与业务背景.md`](./01-总览与业务背景.md)
> 深度研究：[`../深度研究/01-通用问答.md`](../深度研究/01-通用问答.md)

> 上一篇：[01-总览与业务背景](./01-总览与业务背景.md) · 下一篇：[03-查询记忆复用](./03-查询记忆复用.md)

---

# SchemaMapper LLM 语义映射（58% → 81%）

## 1. 背景：为什么做，怎么发现的问题

**原先为什么主要靠规则**：语义层已经建好——指标 / 维度 / 别名会灌进 HanLP 词典，SchemaMapper 常态走 `STRICT → MODERATE` 的 Keyword 精确命中。「净利润」「扣非净利润」这类已注册的内地标准名，规则层直接命中，**根本不进 Embedding**。`EmbeddingMapper` 只在整轮解析仍空、降级到 `LOOSE` 时才打开，属于兜底路径，平时用得很少。

**什么问题把兜底路径暴露出来**：实习在广东智能院，问数用户常混用内地口径与港澳 / 港股报表口径，再叠加错别字、繁体字、生僻缩写。语义层与词典按内地命名建设，对中港异名覆盖不足（对照如：董事袍金 ↔ 董事薪酬，期内溢利 ↔ 净利润）。这些问法在 STRICT/MODERATE 上 **规则 0 hit**，整轮无候选后被迫降级 LOOSE——Embedding 这条原先很少打到的路径，开始被真实流量打到。

**Embedding 上出了什么错**：以「期内溢利」为例——词典无此别名 → 进入 `EmbeddingMapper` → 向量按内地近义召回「净利润 / 利润总额 / 营业利润 / 扣非净利润 / 息税前利润…」→ 纯相似度把近邻利润指标排到前面。下游照错字段生成 SQL：**语法对、执行不报错、结果看似合理但语义错**——这是 Chat-BI 最危险的失败模式。

**因此做什么**：不是推翻「规则优先」，而是给 `EmbeddingMapper` 加 **LLM 重排 / 精选**（选择题选 ID），专门治理 LOOSE 路径上「召回对了近义簇、但排错 / 选错」的问题。

**怎么发现的**：端到端有五个环节（多轮改写、SchemaMapper、S2SQL 生成、语义校正、物理 SQL 翻译）。定位到 SchemaMapper 分三步：

1. **用户反馈 + ELK 日志看链路**——研究员反馈查「期内溢利」等问句结果对不上；按 `traceId` 串联发现 STRICT/MODERATE 无候选，LOOSE 才出现 Embedding 候选；正确映射（如净利润）在 Top-K 但非 rank1，利润近邻抢前。
2. **分层验证确认瓶颈位置**——把 SchemaMapper 输出的错误候选手动换成正确字段，后续 Parser/Corrector/Translator 生成的 SQL 就对了。后续管道是确定性的，**SchemaMapper 错了全链必错**。
3. **小样本量化归因**——从 ELK 导出最近一周约 1000 次查询，失败 query 里随机抽约 50 条人工拆链路，约 60%（约 30 条）错在 SchemaMapper，25% 是 SQL 生成错误，15% 是值链接失败。

**量化瓶颈**：端到端准确率 T0 只有 45%，其中约 60% 的错误归因到 SchemaMapper——**优化 SchemaMapper（尤其是 LOOSE / Embedding 路径）是提升端到端准确率的最高 ROI 路径**。SchemaMapper 层 Exact Match（EM）基线只有 58%。

**错误的具体表现**（50 条里反复出现、且会进 LOOSE 的）：
- **中港异名 / 未注册别名**：「期内溢利」「董事袍金」等 → 规则 miss → Embedding 近义簇
- **错别字 / 繁体**：exact match 断裂 → 同上降级
- **进 Embedding 后近义选错**：利润簇（净利 / 总额 / 营业 / 扣非 / EBIT）打架，向量排错
- **召回遗漏**：说法与内地命名差太远，Top-K 里根本没有正确项

---

## 2. 方案选型：考虑了哪些方案，如何权衡

**选型前提**：规则主路径（STRICT/MODERATE + 语义层词典）不动。问题出在 LOOSE 降级后——Embedding 已召回近义簇，但排错 / 选错。因此比的是「召回之后怎么精选」，不是要不要规则、也不是端到端让 LLM 写 SQL。

**逐步淘汰**：

| 顺序 | 方案 | 做法 | 淘汰 / 入选理由 |
|------|------|------|----------------|
| ① 淘汰 | 继续增强语义层、堆别名（含中港词汇对照） | 把「期内溢利」「董事袍金」等写进 alias / 词典 | **治标不治本**：说法组合近乎无限（错别字、繁体、生僻缩写、地域异名），维护成本随用户增长；别名解决「已知说法」，解决不了「未见说法」 |
| ② 淘汰 | LLM pairwise 两两比较重排 | 每次比两个候选，再聚合成序 | **延迟不可接受**：即使用较省的比较排序，也要约 \(K \log K\) 量级的多次 LLM 调用；\(K=10\sim20\) 时易到秒级，主链路吃不消。全量两两更是 \(O(K^2)\) |
| ③ 淘汰 | Cross-encoder 专用 reranker | 对 (query, column_text) 打分后再截断 | **标注 + 部署成本高**：要 (query, 正确字段) 训练数据，还要训/服一额外模型；实习周期与当时基础设施不划算 |
| ✅ 入选 | **LLM listwise 精选 ID** | 召回合并后的候选一次进 prompt，返回**相关** ID 列表（不定长） | **一次调用**、零训练、能读 COMMENT/description 做中港与近义消歧；**选择题选 ID，不填空生成字段名** |

**金句**：别名盖已知、pairwise 太慢、cross-encoder 太重 → **LLM 做选择题，不做填空题**（listwise / `detectWithLLM`）。

**入选后要分清的两个「数量」（别混成同一个 K）**

| | 含义 | 代码里实际怎样 |
|--|------|----------------|
| **进 prompt 的候选池** | Embedding 合并后塞给 listwise 的条数 | 每段默认召回 **5** 条（`embedding.number`），4–5 个词就可能是 **20–25** 条，再按 id 去重；**当前实现进 LLM 前不再做全局 Top-K 截断**，整包 `retrievedInfo` 进 prompt |
| **LLM 输出** | 精选后留下的字段 | **不是固定 Top-K 排序**。Prompt 要求「只返回与问句高度相关的 ID 列表」，长度随问句变化（可能 1 个，也可能多个）；代码用返回的 ID 过滤 `results`，并打 `llmMatched`，**没有**再配置一个输出侧的 k |

因此：listwise 在这里是 **filter / 精选**（相关则留），不是「对 20 条重排后取 top5」。文档若写「送进 LLM 的 K=5」，容易和「每段召回 5」或「输出只要 5 个」搞混——**输出侧没有固定的 k**。

**和「候选太多 → position bias」的关系**：池子到 20+ 时，listwise 确实更容易首尾偏置、中间漏看。工程上更干净的做法是进 prompt 前再截一刀（例如全局相似度 Top-10/Top-5）；**现仓库尚未做这一刀**，控量主要靠「每段 top5 + id 去重」。选型时仍应意识到：池子过大是 listwise 的风险，不是「输出 K=5」能单独解决的。

**和现有代码的关系**：不改「规则优先 → LOOSE 才开 Embedding」的主链路；只在 `EmbeddingMapper` 召回之后加精选。切入点是 `EmbeddingMatchStrategy.detectByBatch`，新增 `detectWithLLM`（listwise + 要求 JSON ID 列表；structured output / 解析兜底属工程配套，不是第四套方案）。

**落地后的三层形态**：
1. **STRICT/MODERATE 规则匹配**（HanLP + 词典）——命中就走，失败才降级
2. **LOOSE Embedding 召回**——多段近义粗召回（每段约 top5，合并去重）
3. **LLM listwise 精选** ⭐——对合并后的候选池做相关 ID 过滤（输出不定长）

**何时整段 Mapping 跳过**：请求已带 `selectedParseInfo` / mapInfo 非空 → 直接进 PARSING，不跑 Mapper。

---

## 3. 行动计划：怎么一步步写出来的

按真实开发时序，分两步落地。

### 第一步：前置优化——召回链路并行化

**为什么先做这步**：后面的 LLM listwise 会多一次调用（约 1–3 秒）。Embedding 本身又会因「多段查询」多次打向量库；若这些检索仍是串行 for 循环，再叠 LLM，Mapping 延迟容易顶满。所以先把**同一次 Embedding 内的多段向量召回**并行化，给 LLM 腾预算。

**并行边界**：SPI 上 `EmbeddingMapper → KeywordMapper → …` **仍是顺序执行**。并行只发生在 `EmbeddingMatchStrategy` 内部的多次 `retrieveQuery`，不是六个 Mapper 一起跑。

#### 1）召回流水线（先弄清「在并行什么活」）

**① 切段**——一条问句变成多个查询片段，两种切法：

- **基础路径（字符滑窗）**：`word.size=3`、`word.step=2`。例：「期内溢利同比增长」→ `期内溢` / `溢利同` / `同比增` / `增长`…
- **LLM 路径（HanLP 分词）**：按词切开再过滤。例：「比亚迪期内溢利」→ 可能得到 `比亚迪`、`期内`、`溢利`…

**② 每段召回多少**：`retrieveQuery(..., embedding.number)`，默认 **每段最多 5 条**相似 schema 命中（指标/维度等）。例：`溢利` → 净利润、利润总额、营业利润、扣非净利润、息税前利润…（至多 5 个）。

**③ 召回之后**：

| 步骤 | 行为 | 默认配置 |
|------|------|----------|
| 阈值 | 相似度低于 0.9 的丢掉 | `threshold=0.9`；**LLM 路径跳过**，交给 listwise |
| 批内截断 | 拍平后按 similarity 降序，`limit(round.number × 本批片段数)` | `round.number=10`；片段少时常常裁不到 |
| 合并去重 | 各并行任务结果按 **id** 去重 | `EmbeddingResult.equals` 按 id |
| 分流 | 基础路径：结果进 `mapInfo`；LLM 路径：合并后的集合整包进 prompt，**再 1 次 listwise**（输出不定长 ID，标 `llmMatched`） | 进 LLM 前**无**全局 Top-K 截断；控量主要靠每段 top5 + 去重 |

补充：`detect()` 在 `useLLM=true` 时会 **先后跑两路并 addAll**（滑窗保底 ∪ HanLP+LLM），不是 if-else 二选一；缘由见 §4 坑 4。

#### 2）并行化怎么改的

- **改前**：`for` 循环按片段（组）依次 `retrieveQuery`，耗时 ≈ 各次之和。
- **改了什么 / 关键类**：
  - `EmbeddingMatchStrategy.detectByBatch`：多段检索改为任务列表 + 线程池
  - `BaseMatchStrategy.executeTasks`：用 `mapExecutor` 异步执行并 `allOf` 汇总
  - `detectByQueryTextsSub`：单批内的召回、阈值、截断
  - `BatchMatchStrategy`：滑窗切段入口；`SingleMatchStrategy` 的多步检测也复用同一套 `executeTasks`
  - `ThreadPoolConfig#mapExecutor`：Mapping 专用池
- **改后**：每次召回打成任务丢进 `mapExecutor`，并行打向量库，再走上面的合并与后处理。池子常驻 **8** 线程、配置上 max=16，但队列无界，实际很少扩到 16，**有效并发≈8**；空闲 180s 回收；拒绝策略 CallerRuns（无界队列下几乎用不上）；线程名 `supersonic-map-pool-*`。

#### 3）效果

同一次 Embedding 里多次向量检索的墙钟时间从约 \(\sum t_i\) 降到约 \(\max t_i\)（受有效并发≈8 限制），为后面那 **1 次** listwise 留出延迟余量。


### 第二步：主合入——LLM filter 五件套一次性落地

**本节只讲「怎么把 listwise 接到线上」**：召回怎么切段/合并、STRICT→LOOSE 何时开 Embedding，见 §2 与第一步；这里不重复。

**设计思路**：功能开关 + 默认关闭。yaml 默认 `false`，评测环境先验证，业务侧再手动打开（与第三步「评测期硬编码强开」区分）。

#### 1）一次落地的五件套

| # | 件 | 作用 |
|---|-----|------|
| 1 | 配置开关 `EMBEDDING_MAPPER_USE_LLM`（`s2.mapper.embedding.use-llm-enhance`，默认 false） | 是否走 LLM 精选 |
| 2 | Prompt 模板 `LLM_FILTER_PROMPT` | 吃 `userText` + `retrievedInfo`，要求返回相关 ID 的 JSON 数组 |
| 3 | `detectWithLLM` / `detectByBatch(..., useLlm=true)` | 召回合并后发起 **1 次** listwise，按返回 ID 过滤 |
| 4 | `EmbeddingResult.llmMatched` / `SchemaElementMatch.isLlmMatched()` | 标记 LLM 选中项，传给下游 |
| 5 | `MapFilter` 白名单 | `llmMatched=true` 的候选 **跳过短词过滤**，避免规则误杀精选结果 |

切入点仍在已有 Embedding 链路上：`EmbeddingMatchStrategy.detectByBatch`，不改 SPI 顺序。

#### 2）一次调用的入参 / 出参（举例）

Prompt 变量：

- `userText`：原始问句  
- `retrievedInfo`：LLM 路径上**各片段召回并集**的 `EmbeddingResult` JSON（`JSONObject.toJSONString(results)`；构建过程见第一步）

问句「比亚迪期内溢利」时，HanLP 多段召回合并后的入参示意（条数已缩短；`detectWord` 标明来自哪一段）：

```text
比亚迪 → （维值多半不在 meta 向量，常空/噪声；实体靠 KeywordMapper）
期内   → 报告期、会计期间…
溢利   → 净利润、扣非净利润、利润总额…
         ↓ id 去重
    retrievedInfo 整包进 prompt
```

```json
[
  { "id": "105", "name": "净利润",     "similarity": 0.91, "detectWord": "溢利", "llmMatched": false,
    "metadata": { "type": "METRIC", "bizName": "net_profit", "dataSetId": "1_" } },
  { "id": "106", "name": "扣非净利润", "similarity": 0.88, "detectWord": "溢利", "llmMatched": false,
    "metadata": { "type": "METRIC", "bizName": "net_profit_excluding", "dataSetId": "1_" } },
  { "id": "107", "name": "利润总额",   "similarity": 0.86, "detectWord": "溢利", "llmMatched": false,
    "metadata": { "type": "METRIC", "bizName": "total_profit", "dataSetId": "1_" } },
  { "id": "301", "name": "报告期",     "similarity": 0.83, "detectWord": "期内", "llmMatched": false,
    "metadata": { "type": "DIMENSION", "bizName": "report_period", "dataSetId": "1_" } },
  { "id": "302", "name": "会计期间",   "similarity": 0.80, "detectWord": "期内", "llmMatched": false,
    "metadata": { "type": "DIMENSION", "bizName": "accounting_period", "dataSetId": "1_" } }
]
```

出参（不定长 ID 列表，要求纯 JSON、不要 markdown 代码块）：

```json
["105", "301"]
```

→ `filter(id ∈ 列表)`，命中项 `llmMatched=true`。空响应则清空本路 `results`；格式烂了走 §4 坑 3 的解析兜底 / retry。

#### 3）合入后写回哪里

精选后的 `EmbeddingResult` 经 `EmbeddingMapper.doMap` 写成 `SchemaElementMatch`（带上 `llmMatched`）进入 `SchemaMapInfo`；末尾 `MapFilter.filter` 做 dataSet/短词等规则，其中短词规则对 LLM 命中项放行。下游 Parser 只吃映射后的 schema，不吃全库表。

---

## 4. 迭代优化：遇到什么问题，怎么克服

LLM filter 不是"加上就涨点"，评测驱动的 prompt 迭代是主要工作。每周 2-3 次迭代，每次改 prompt 或加规则后，5 分钟跑完全量 200 条 Schema 评测 + 输出混淆矩阵，看混淆矩阵定位问题——是召回阶段漏了（embedding 词典不够）还是消歧阶段选错了（prompt 需要调）。针对性修 → 再跑评测 → 看数字提升。如果掉了回滚——**评测集是迭代的护栏**。

### 坑 1：LLM 忽略 COMMENT，只看字段名（最大 bad case 来源）

- **现象**：用户问"扣非利润"，候选 rank 1 是"净利润"（COMMENT='合并口径净利润'），rank 2 是"扣非净利润"（COMMENT='扣除非经常性损益后的净利润'）。LLM 选了 rank 1——只看字段名字面相似度，没看 COMMENT
- **业界对照**：LangChain GitHub Issue #5158 同样观察——"Column names do not describe perfectly well what they contain"
- **修复（评测发现驱动的增强设计）**：在 prompt 里加显式引导——"优先对比每个候选的 name + description/COMMENT + dataType + 所属表，不要只看字段名做字面匹配"
- **效果**：这类 case 准确率从 ~40% 提升到 ~75%

### 坑 2：LLM 过度自信，理由是事后合理化

- **现象**：早期 prompt 让模型「先写理由再选 ID」。选错时仍能写出一段「看似合理」的推理（如「扣非利润最接近净利润」）——理由是事后合理化，还会干扰选对
- **业界对照**：FinVerBench（arXiv 2506）结论同向——**LLM 给的「理由」不能当正确性证据**
- **修复（评测直接对比）**：不让输出理由，**只输出选项 ID 数组**（如 `["105","301"]`）。下游 Corrector/Translator 也只吃 ID，不读自然语言解释
- **效果**：比「带 reasoning」约好 **5pp**

### 坑 3：JSON 格式不稳定

- **现象**：原版 prompt 要求 JSON 输出，但实际约 5-15% 的输出会带 markdown fence（```json）、寒暄（'Sure, here are...'）、或 Python 集合格式（`{'id1'}` 而非 JSON `["id1"]`）
- **业界对照**：业界实测纯 prompt 要求 JSON 只能拿到 80-95% 稳定性；Google Cloud 六大失败模式之一就是"Messy Output"
- **修复**：① 开启 LLM 的 `json_format=true`（structured output）；② 加 callback 后处理用 regex 提取 `[...]` 段做兜底；③ parse 失败时 retry-with-error-feedback（把错误信息塞回 prompt 重试 1 次）
- **效果**：格式失败率从 ~12% 降到 <2%

### 坑 4：`detect` 编排——先 if-else 二选一，再改回两路并集

- **第一版想法**：开 LLM 就用 if-else——`useLLM ? detectWithLLM() : super.detect()`，以为「有精选就不必再跑旧滑窗召回」，结构也更干净。
- **现象**：评测上部分 case **召回变差**。滑窗 n-gram 能打中的片段，HanLP 切词未必有；listwise 又会再收窄。二选一只留路径 B 时，等于拆掉原有 Embedding 保底——LLM 空响应 / 过滤过狠 / 切段不一致时，整路 Embedding 直接变瘦。
- **改回（现状）**：始终跑路径 A（滑窗 + `useLlm=false`），`useLLM` 时再 **`addAll` 路径 B**（HanLP + listwise），最后按 id `distinct`。
  - A：宽召回保底，`llmMatched=false`
  - B：近义消歧精选，`llmMatched=true`
  - B 失败返回 empty 时，A 仍在——增强挂件，不是替换主干
- **代价（面试可主动说）**：同一问句可能打两遍向量库；A 路未过 LLM 的候选也会进 `mapInfo`，池子偏宽。更「纯」的做法是并集召回后 **统一 listwise 一次**，或接受 if-else 并补齐切段——当时优先保召回、少动原链路。
- **和附录的关系**：附录阶段二画的「A ∪ B」是 **迭代后的定稿**；if-else 是中间踩坑方案。

### 调整后的 prompt（最终版本要点）

```
#Role: You are a data analyst experienced in financial data semantics.
#Task: 从向量召回的候选字段中，选出与用户 query 最匹配的字段。

#候选字段（已按 embedding 相似度排序）：
#C1: name=净利润, COMMENT=合并口径净利润（税后）, dataType=REAL, 表=利润表
#C2: name=扣非净利润, COMMENT=扣除非经常性损益后的净利润, dataType=REAL, 表=利润表
#C3: name=利润总额, COMMENT=税前利润总额, dataType=REAL, 表=利润表
...

#Rules:
1. **优先对比每个候选的 COMMENT 和 dataType，不要只看字段名做字面匹配**
2. 逐个评估每个候选的 COMMENT 与用户 query 的语义匹配度
3. 若有 2 个以上候选语义高度接近无法区分，返回全部（不要强行二选一）
4. 输出 JSON 数组，只含 ID，如: ["#C2"]
```

关键变化：① 显式强调 COMMENT 优先；② 候选编号 + 逐个评估；③ 不确定返回多个；④ 只输出 ID、不写理由（见坑 2）。

---

## 5. 成果展示：怎么衡量，效果如何

### 5.1 怎么评：分层口径 + Gold

**同一批 200 条 query，两套 gold——Schema 分和端到端分不能混谈。**

| 层次 | Headline | 测什么 | 方法 |
|------|----------|--------|------|
| **Schema 映射** | **58% → 81%** | query → 语义元素 ID **集合是否全对** | 召回率/精确率 + **样本级集合全等 EM** |
| **端到端** | **45% → 72% → 87%** | NL → SQL → 执行结果是否对 | 执行准确率 + 五维语义评分 |

全等 EM：选出的集合与 gold **完全一致**才记 1（多选、漏选都算 0），严于「覆盖即可」的论文口径，不宜横比。Schema 分只说明映射；端到端还叠 SQL 等错误。

Gold 来自端到端标注里的 `gold_elements`，抽出后只评 Mapper、不跑 SQL（线上约 50 条只够定方向，不是评测集来源）。例「比亚迪期内溢利」：METRIC 净利润 `(105)`、ENTITY 比亚迪 `(201)`（Keyword 命中也计入）、可选 DIMENSION 报告期 `(301)`。

### 5.2 对照结果：无 LLM 精选 vs 有 LLM 精选

**比的不是「整条解析开不开大模型」**，而是 Embedding 召回之后要不要再做 listwise ID 精选。规则、语义层、200 题和 gold 两边相同；只改是否走 `detectWithLLM`。

| | **T0：无 LLM 过滤** | **T1：有 LLM 过滤** |
|--|---------------------|---------------------|
| 规则 + Embedding 召回 | 有 | 有 |
| listwise 精选 ID | **关**（纯相似度 + 阈值） | **开** |
| Schema 全等 EM | **58%** | **81%** |
| 同期端到端（记忆库未上） | **45%** | **72%** |

附指标：召回率 ~70%→~90%，精确率 ~65%→~88%。Headline 用**全等 EM**（多选也算错）。T0 纯向量 + 阈值常见两种败法，都会直接 EM=0：

1. **搞错**——近义簇排错（如「期内溢利」选成利润总额）  
2. **多出来**——阈值内塞进噪声维/近邻指标，gold 都在也因多余 ID 不得分  

T1 listwise 主要解决**语义相近**（近义簇消歧、砍冗余），全等 EM 又偏准确率（多一个无关 ID 就 0），所以精确率与 EM 一起抬。召回不够时先调向量召回的 top-k（`embedding.number`），再交给 listwise；端到端 45%→72% 是 mapping 变干净的下游红利（72%→87% 才是记忆库）。

剩余 **19%** 还可继续修（按严重程度）：

1. **COMMENT 建设与质量仍不足**（约 10%）——历史字段缺注释、口径写得含糊时，listwise 只能靠字段名猜；继续推注释补全与口径规范  
2. **跨主题域歧义 / 缺业务背景**（约 5%）——如 "PE" 金融市盈率 vs 行为实验量表；单靠候选 COMMENT 不够，需主题域/业务上下文  
3. **候选池变大后 listwise 注意力涣散**（约 4%）——片段/候选数上去后，中间项易被忽略；进 prompt 前再截 Top-K、或分段精选后再合并

### 5.3 单条评测输出示例（bad case）

```json
{
  "query_id": 78,
  "query_text": "比亚迪期内溢利",
  "schema_mapper_output": {
    "candidates": [
      {"id": "105", "name": "净利润", "detectWord": "溢利", "similarity": 0.91, "comment": "合并口径净利润"},
      {"id": "106", "name": "扣非净利润", "detectWord": "溢利", "similarity": 0.88, "comment": "扣除非经常性损益后的净利润"},
      {"id": "107", "name": "利润总额", "detectWord": "溢利", "similarity": 0.86, "comment": "税前利润总额"},
      {"id": "301", "name": "报告期", "detectWord": "期内", "similarity": 0.83, "comment": "报告期/会计期间"}
    ],
    "llm_selected": ["107", "301"]
  },
  "gold_elements": [105, 201],
  "selected_elements": [107, 301],
  "metrics": { "recall": 0.0, "precision": 0.0, "exact_match": false },
  "error_type": "错选",
  "error_detail": "gold 要净利润+比亚迪；模型选了利润总额+报告期（近义选错；实体应由 Keyword 贡献）"
}
```

错误类型：**召回遗漏**（gold 不在池）/ **错选**（在池里选错）/ **多选**（多带无关 → 全等 EM=0）/ **格式失败**（见 §4 坑 3）。混淆矩阵按类型 + 易混元素对统计，驱动 prompt 迭代。

---

## 附录：核心代码标本

先看清**整条调用链**（面试口述按这个顺序），再看分阶段代码：

```text
EmbeddingMapper.accept? ──否──▶ 不跑 Embedding
        │是（LOOSE / LLM_OR_RULE）
        ▼
EmbeddingMapper.doMap
        │
        ▼
BaseMapper.getMatches(ctx, EmbeddingMatchStrategy)
        │  ① HanLP 切 terms（再按 dataSet 过滤）
        │  ② matchStrategy.match(ctx, terms, dataSetIds)
        │        └─ BaseMatchStrategy.match
        │              └─ detect(...)          ★ 编排入口（阶段二）
        │  ③ 从 Map<MatchText, List> 取第一份非空 List 返回
        ▼
doMap：EmbeddingResult → SchemaElementMatch（带 llmMatched）→ mapInfo
        ▼
BaseMapper.map 末尾 MapFilter.filter（短词对 llmMatched 放行）
```

`detect` 内部的编排（先召回、再精选；**为何是并集不是 if-else → 见 §4 坑 4**）：

```text
EmbeddingMatchStrategy.detect
  ├─【路径 A】super.detect = BatchMatchStrategy.detect
  │     滑窗切段 → detectByBatch(segments, useLlm=false)
  │       └─ 只做向量召回（有阈值），不做 listwise
  │
  └─【路径 B】useLLM 时 detectWithLLM
        HanLP 切词 → detectByBatch(segments, useLlm=true)
          └─ 先同样并行向量召回（跳过阈值）
          └─ 再 1 次 listwise：retrievedInfo → 返回 ID → 过滤并 llmMatched=true

  最后：A ∪ B，按 id distinct（迭代后定稿；中间曾试过 if-else 二选一只留 B）
```

共用引擎是 `detectByBatch`（阶段三）：**向量召回始终发生；`useLlm` 只决定召回后要不要 listwise**。

---

### 阶段一：从 doMap 接到 Strategy —— 桥接层

> 来源：`EmbeddingMapper` + `BaseMapper.getMatches` + `BaseMatchStrategy.match`  
> 作用：证明 `doMap` **不会直接**调 `detectByBatch`，而是经 getMatches → match → **detect**

```java
// ----- EmbeddingMapper -----
@Override
public boolean accept(ChatQueryContext chatQueryContext) {
    boolean loose = MapModeEnum.LOOSE.equals(/* mapMode */);
    boolean llmOrRule = /* text2SQLType */ == Text2SQLType.LLM_OR_RULE;
    return loose || llmOrRule; // 不满足则整段 Embedding 不跑
}

public void doMap(ChatQueryContext chatQueryContext) {
    EmbeddingMatchStrategy matchStrategy = /* Spring 取 Bean */;

    // 唯一入口：把「怎么召回」交给 Strategy；自己只负责写回 mapInfo
    List<EmbeddingResult> matchResults = getMatches(chatQueryContext, matchStrategy);

    HanlpHelper.transLetterOriginal(matchResults); // 略
    for (EmbeddingResult matchResult : matchResults) {
        /* 读 metadata → 查 SchemaElement → 组装 SchemaElementMatch
           → setLlmMatched → addToSchemaMap（按 dataSetId 入桶） */
    }
}

// ----- BaseMapper.getMatches：doMap → detect 的桥 -----
public <T> List<T> getMatches(ChatQueryContext ctx, MatchStrategy matchStrategy) {
    List<S2Term> terms = HanlpHelper.getTerms(/* queryText */, /* model↔dataSet */);
    terms = HanlpHelper.getTerms(terms, /* 请求 dataSetIds 再滤 */);

    // 这里进入 EmbeddingMatchStrategy 所在继承链的 match()
    Map<MatchText, List<T>> matchResult =
            matchStrategy.match(ctx, terms, /* dataSetIds */);

    // 约定：取第一份非空 List 作为本次 matches
    return /* matchResult 中第一个非空 value，否则 empty */;
}

// ----- BaseMatchStrategy.match：再薄薄包一层，真正干活的是 detect -----
public Map<MatchText, List<T>> match(ChatQueryContext ctx, List<S2Term> terms, Set<Long> dataSetIds) {
    List<T> detects = detect(ctx, terms, dataSetIds); // ★ 多态到 EmbeddingMatchStrategy.detect
    Map<MatchText, List<T>> result = new HashMap<>();
    result.put(/* MatchText 包一下原句 */, detects);
    return result;
}
```

---

### 阶段二：编排中枢 —— EmbeddingMatchStrategy.detect（先召回，再 LLM）

> 来源：`EmbeddingMatchStrategy.detect` / `detectWithLLM` + 父类 `BatchMatchStrategy.detect`  
> 作用：看清「两路召回怎么排、LLM 挂在哪一路」——**这是串联阶段一与阶段三的枢纽**

```java
// ----- EmbeddingMatchStrategy.detect：getMatches/match 最终落到这里 -----
@Override
public List<EmbeddingResult> detect(ChatQueryContext ctx, List<S2Term> terms, Set<Long> dataSetIds) {
    // ========== 路径 A：只向量召回（无 LLM）==========
    // super.detect → BatchMatchStrategy.detect：
    //   按 word.size/step 滑窗切段 → detectByBatch(segments, useLlm=false)  【阶段三】
    List<EmbeddingResult> baseResults = super.detect(ctx, terms, dataSetIds);

    // ========== 路径 B：再召回一轮 + listwise 精选（与 A 并集，非 if-else；见 §4 坑 4）==========
    boolean useLLM = true; // 评测期硬开；产品应读 EMBEDDING_MAPPER_USE_LLM
    if (useLLM) {
        List<EmbeddingResult> llmResults = detectWithLLM(ctx, dataSetIds);
        if (!CollectionUtils.isEmpty(llmResults)) {
            baseResults.addAll(llmResults); // 增强叠加，不是替换路径 A
        }
    }
    return baseResults.stream().distinct().collect(Collectors.toList()); // equals 按 id
}

// 路径 B 入口：换一套切段方式，并打开 useLlm
private List<EmbeddingResult> detectWithLLM(ChatQueryContext ctx, Set<Long> dataSetIds) {
    String queryText = /* 用户原句 */;
    if (StringUtils.isBlank(queryText)) { return Collections.emptyList(); }

    // 与路径 A 的滑窗不同：HanLP 分词 + 词性过滤 → segments
    Set<String> detectSegments = extractValidSegments(queryText);
    if (CollectionUtils.isEmpty(detectSegments)) { return Collections.emptyList(); }

    // 同一个 detectByBatch；useLlm=true ⇒ 召回后多跑 listwise【阶段三】
    return detectByBatch(ctx, dataSetIds, detectSegments, true);
}

// ----- 父类 BatchMatchStrategy.detect：路径 A 的切段方式 -----
@Override // 在 BatchMatchStrategy 中
public List<EmbeddingResult> detect(...) {
    Set<String> detectSegments = new HashSet<>();
    // 滑窗：size=3, step=2，例「期内溢利」→ 期内溢 / 溢利 …
    for (/* start += step */) {
        detectSegments.add(/* substring(start, start+size) */);
    }
    // 无第四参时走重载：detectByBatch(..., useLlm=false)
    return detectByBatch(ctx, dataSetIds, detectSegments);
}
```

---

### 阶段三：共用引擎 —— detectByBatch（向量召回 → 可选 listwise）

> 来源：`EmbeddingMatchStrategy.detectByBatch` / `detectByQueryTextsSub`  
> 作用：路径 A/B **共用**；差别只在 `useLlm` 与传入的 `detectSegments`  
> 对应正文：第一步并行化；第二步入参/出参

```java
public List<EmbeddingResult> detectByBatch(..., Set<String> detectSegments, boolean useLlm) {
    // —— ① 向量召回（A/B 都走）——
    List<List<String>> batches = Lists.partition(/* 非空片段 */, /* embedding.batch */);
    List<Supplier<List<EmbeddingResult>>> tasks = new ArrayList<>();
    for (List<String> oneBatch : batches) {
        // 每个任务内部：detectByQueryTextsSub（每段 top5、阈值、批内截断）
        tasks.add(createTask(/* ctx, dataSetIds, oneBatch, useLlm */));
    }
    Set<EmbeddingResult> results = executeTasks(tasks); // mapExecutor 并行 + 按 id 合并

    // —— ② 仅 useLlm=true（路径 B）时：对合并结果做 1 次 listwise ——
    if (useLlm) {
        Map<String, Object> variable = new HashMap<>();
        variable.put("userText", /* 原句 */);
        variable.put("retrievedInfo", JSONObject.toJSONString(results)); // 多片段并集

        Prompt prompt = PromptTemplate.from(LLM_FILTER_PROMPT).apply(variable);
        String response = ModelProvider.getChatModel(/* 配置 */)
                .generate(/* prompt 文本 */); // 一次调用

        if (StringUtils.isBlank(response)) {
            results.clear();
        } else {
            List<String> ids = JSONObject.parseArray(response, String.class); // 如 ["105","301"]
            results = results.stream()
                    .filter(r -> ids.contains(r.getId()))
                    .collect(Collectors.toSet());
            results.forEach(r -> r.setLlmMatched(true));
        }
    }
    // useLlm=false（路径 A）：到此结束，带着阈值过滤后的召回结果返回
    return new ArrayList<>(results);
}

// 单个并行任务里真正打向量库
private List<EmbeddingResult> detectByQueryTextsSub(..., List<String> queryTextsSub, boolean useLlm) {
    int embeddingNumber = /* 默认 5：每段召回条数 */;
    double threshold = /* 默认 0.9 */;
    int roundNumber = /* 默认 10：批内截断系数 */;

    RetrieveQuery retrieveQuery = RetrieveQuery.builder() /* .queryTextsList(本批) */ .build();
    List<RetrieveQueryResult> retrieved = metaEmbeddingService.retrieveQuery(
            retrieveQuery, embeddingNumber, /* model↔dataSet */, detectDataSetIds);

    List<EmbeddingResult> collect = retrieved.stream().peek(result -> {
        if (!useLlm) { /* similarity < threshold 等则丢；LLM 路径跳过阈值 */ }
    }).flatMap(/* → EmbeddingResult，detectWord=该段查询词 */).collect(Collectors.toList());

    return collect.stream()
            .sorted(/* similarity 降序 */)
            .limit(roundNumber * queryTextsSub.size())
            .collect(Collectors.toList());
}
```

---

### 附：LLM_FILTER_PROMPT 模板常量

> 来源：`EmbeddingMatchStrategy.LLM_FILTER_PROMPT`  
> 对应正文：§4 坑 1（忽略 COMMENT）、坑 3（JSON 不稳）
> 面试要点：原版只塞整体 JSON、未强调 COMMENT——后续评测驱动才加强引导

```java
private static final String LLM_FILTER_PROMPT =
        """
                #Role: 你是擅长指标/维度语义的数据分析师
                #Task: 根据用户问句，从向量召回的候选里选出用户真正关心的项
                #Rules:
                1. 依据问句 + retrievedInfo，准确判断相关指标/维度
                2. 不要原样返回全部召回，只留高度相关的
                3. 排除与意图无关的项
                4. 输出 JSON 数组，且只能是 retrievedInfo 里已有的 id，如 ['id1','id2']
                5. 直接返回 JSON，不要 markdown 代码块
                #User Query: {{userText}}
                #Retrieved Metrics/Dimensions: {{retrievedInfo}}
                #Output:""";
```

### 附：数据结构 —— EmbeddingResult

> 来源：`EmbeddingResult`  
> 对应正文：第二步「llmMatched」  
> 面试要点：`equals/hashCode` 按 id（合并去重用）；`llmMatched` 供 MapFilter 白名单

```java
@Data
public class EmbeddingResult extends MapResult {
    private String id;                          // schema 元素 id
    private Map<String, String> metadata;       // type / dataSetId / bizName …
    private boolean llmMatched;                 // 是否被 listwise 选中

    @Override public boolean equals(Object o) { /* 只比 id */ }
    @Override public int hashCode() { /* 只基于 id */ }
    @Override public String getMapKey() { /* name + "_" + id */ }
}
```

### 阶段四：规则后置 —— MapFilter 白名单

> 来源：`MapFilter`  
> 对应正文：第二步五件套第 5 项  
> 面试要点：短词过滤对 `llmMatched` 放行，避免误杀 LLM 精选

```java
public static void filter(ChatQueryContext chatQueryContext) {
    filterByDataSetId(chatQueryContext);           // 按 Agent/DataSet 可见范围裁剪
    filterByDetectWordLenLessThanOne(chatQueryContext); // 短词过滤（见下，含 LLM 白名单）
    twoCharactersMustEqual(chatQueryContext);      // 两字词需更严匹配等
    // 按请求的 QueryDataType（TAG/METRIC/DIMENSION）再滤一层
    switch (/* queryDataType */) { /* ... */ }
    filterByRules(chatQueryContext);               // 其它规则（exact 优先等）
}

public static void filterByDetectWordLenLessThanOne(ChatQueryContext chatQueryContext) {
    // 遍历 mapInfo 里各 dataSet 的 SchemaElementMatch 列表
    for (/* 每个 dataSet 的 match 列表 value */) {
        value.removeIf(m ->
                StringUtils.length(m.getDetectWord()) <= 1   // detectWord 过短
                && !m.isLlmMatched());                      // 但 LLM 选中的不删
    }
}
```
