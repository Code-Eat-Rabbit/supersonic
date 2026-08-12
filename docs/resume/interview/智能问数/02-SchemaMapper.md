> 系列：智能问数
> 简历基线：[`../../my_resume.md`](../../my_resume.md)
> 总览：[`01-总览与业务背景.md`](./01-总览与业务背景.md)
> 深度研究：[`../深度研究/01-通用问答.md`](../深度研究/01-通用问答.md)

> 上一篇：[01-总览与业务背景](./01-总览与业务背景.md) · 下一篇：[03-查询记忆复用](./03-查询记忆复用.md)

---

# SchemaMapper LLM 语义映射（58% → 81%）

## 1. 背景：为什么做，怎么发现的问题

**痛点**：研究员用业务术语提问，但数据库里字段是英文缩写（如 `net_profit`、`net_profit_excluding`）。原来的系统靠向量相似度匹配，遇到语义相近的字段就会混淆——"查扣非净利润返回了净利润的值，差了好几个亿"。这是 Chat-BI 最危险的失败模式：**SQL 语法对、执行不报错、结果看似合理但语义错**。

**怎么发现的**：端到端查询有五个环节（多轮改写、SchemaMapper、S2SQL 生成、语义校正、物理 SQL 翻译）。定位到 SchemaMapper 分三步：

1. **用户反馈 + ELK 日志看链路**——研究员反馈"查比亚迪扣非净利润，返回的是净利润的值"；在 Kibana Discover 里按 `traceId` 串联看完整链路，发现正确字段 `net_profit_excluding` 在 Top-10 但排第 3，错误字段 `net_profit` 排第 1——**embedding 把语义相近的字段排到了前面**。
2. **分层验证确认瓶颈位置**——把 SchemaMapper 输出的错误候选手动替换成正确字段，后续 Parser/Corrector/Translator 生成的 SQL 就对了。后续管道是确定性的，**SchemaMapper 错了全链必错**。
3. **小样本量化归因**——从 ELK 导出最近一周约 1000 次查询，失败 query 里随机抽约 50 条人工拆链路，约 60%（约 30 条）错在 SchemaMapper，25% 是 SQL 生成错误，15% 是值链接失败。

**量化瓶颈**：端到端准确率 T0 只有 45%，其中约 60% 的错误归因到 SchemaMapper——**优化 SchemaMapper 是提升端到端准确率的最高 ROI 路径**。SchemaMapper 层 Exact Match（EM）基线只有 58%。

**错误的具体表现**（50 条里反复出现）：
- **选错近义字段**："净利润"→"利润总额"、"扣非利润"→"净利润"
- **营收口径混淆**："营收"→"营业总收入"而非"营业收入"
- **一字之差**："市盈率"→"市净率"
- **召回遗漏**：ROE（衍生指标，不在物理表字段名里）、"扣非利润"（用户简称 vs 库里全称差太远）

---

## 2. 方案选型：考虑了哪些方案，如何权衡

**候选方案对比**：

| 方案 | 做法 | 不足 |
|------|------|------|
| 端到端 LLM 生成 SQL | 把 200+ 张表全塞给 LLM，让它直接出 SQL | 200+ 表规模下准确率只有 10-31%（业界实测）；黑盒不可解释；token 爆炸 |
| 纯 Embedding 召回 | 向量 topK + 阈值过滤 | 分不清"净利润"和"扣非净利润"——语义相近但业务含义不同 |
| 规则过滤（HanLP 词典） | STRICT/MODERATE 模式靠分词词典 | 对"扣非利润"这种简称/别名覆盖不够；衍生指标（ROE）完全无能为力 |
| **三层漏斗 + LLM 消歧**（选的） | 规则失败 → 向量粗召回 → LLM 做选择题精选 ID | 多一次 LLM 调用（成本+延迟）；但准确率可控、可解释 |

**选型理由**：

1. **可解释性**——分层设计能看到每一步在做什么（召回对不对、过滤对不对、消歧对不对）；端到端 LLM 是黑盒
2. **准确率上限**——分层设计利用确定性引擎（规则 + Calcite）兜底，LLM 只做"选择题"不做"填空题"，准确率可控
3. **金句：LLM 做选择题，不做填空题**

**和现有代码的关系**：在 SuperSonic 已有的 `EmbeddingMapper` 召回链路上加 LLM filter，不改主链路结构。切入点是 `EmbeddingMatchStrategy.detectByBatch`，新增 `detectWithLLM` 路径。

**三层漏斗设计**：
1. **STRICT/MODERATE 规则匹配**（HanLP 分词 + 词典）——成功就直接走，失败才降级
2. **LOOSE Embedding 召回**——向量 topK + 阈值 0.9，失败模式的兜底
3. **LLM 消歧精选** ⭐——对 Embedding 召回的候选做 ID 精选（选择题，不是填空生成字段名）

**何时整段 Mapping 跳过**：请求已带 `selectedParseInfo` / mapInfo 非空 → 直接进 PARSING 阶段，不跑 Mapper。

---

## 3. 行动计划：怎么一步步写出来的

按真实开发时序，分四步落地。

### 第一步：前置优化——召回链路并行化

**为什么先做这步**：LLM filter 会引入一次额外的 LLM 调用（约 1-3 秒），如果召回链路本身是串行的，叠加后主链路延迟会爆。先做并行化，为后续 LLM 调用腾性能预算。

**改了什么**：
- `BaseMatchStrategy.executeTasks` 把多个 Mapper 的召回任务改成并行提交
- 引入 `BatchMatchStrategy` 雏形 + `ThreadPoolConfig` 配置专用线程池
- `EmbeddingMatchStrategy` 从单条串行改成批量并行召回

**关键类名**：`BaseMatchStrategy.executeTasks`、`SingleMatchStrategy`、`ThreadPoolConfig`

**效果**：召回阶段耗时从约 X 秒降到约 X/N 秒（N 个 Mapper 并行），为后续 LLM 调用留出性能预算。

### 第二步：主合入——LLM filter 五件套一次性落地

**设计思路**：典型的"功能开关 + 默认关闭 + 一切就绪"上线策略。开关默认关闭，先在评测环境验证，再业务侧手动打开。

**五件套同时引入**：

1. **配置开关** `EMBEDDING_MAPPER_USE_LLM`（yaml `s2.mapper.embedding.use-llm-enhance`，默认 false）——业务侧需要时手动打开
2. **Prompt 模板** `LLM_FILTER_PROMPT`——让 LLM 从 `retrievedInfo`（EmbeddingResult JSON）里选最匹配的字段 ID
3. **主链路方法** `EmbeddingMatchStrategy.detectWithLLM` / `detectByBatch(..., useLlm=true)`——召回候选不为空且开关打开时，走 LLM 精选路径
4. **数据字段** `EmbeddingResult.llmMatched` + `SchemaElementMatch.isLlmMatched()`——标记哪些候选是 LLM 选的
5. **MapFilter 白名单**——LLM 命中的候选跳过短词过滤（避免短词规则误杀 LLM 精选结果）

**LLM 入参**（标本实际接线）：
```
retrievedInfo = EmbeddingResult JSON（id/name/similarity/detectWord
              + DataItem 系 metadata：bizName/type/modelId…）
```

**LLM 出参**：JSON ID 列表，如 `["101", "105"]` → 对应候选标记 `llmMatched=true`

**调用链路**：
```
NL2SQLParser.parse
  ├─ 先 STRICT / MODERATE + 规则向（Keyword / HanLP…）  ← EmbeddingMapper 通常不跑
  └─ 无结果再 LOOSE / LLM_OR_RULE
        └─ ChatWorkflowEngine.performMapping  （mapInfo 空才跑）
              └─ SchemaMapper 链（spring.factories）
                    EmbeddingMapper → KeywordMapper → QueryFilterMapper → …
```

| 步骤 | 类·方法 | 要点 |
|------|---------|------|
| Embedding 召回 | `EmbeddingMapper.doMap` → `EmbeddingMatchStrategy.detect` | 仅 `LOOSE` 或 `Text2SQLType.LLM_OR_RULE` 时 `accept` |
| 滑窗 / 批向量 | `BatchMatchStrategy` + `MetaEmbeddingService.retrieveQuery` | 片段 topK≈`embedding.number`（默认 5）；阈值默认 0.9（LLM 路径会跳过阈值） |
| LLM 精选 | `detectWithLLM` / `detectByBatch(..., useLlm=true)` | 输出 JSON ID 列表 → `llmMatched=true` |
| 规则后置 | `BaseMapper.map` 末尾 `MapFilter.filter` | dataSet 裁剪、短词、QueryDataType、exact match 优先；LLM 命中项跳过短词过滤 |

**输出结构**：
```
SchemaMapInfo
  dataSetId → [ SchemaElementMatch {
      element: SchemaElement { id, name, bizName, type, description, … },
      similarity, detectWord, word, llmMatched
  }, … ]
```

下游 Parser（`OnePassSCSqlGenStrategy`）吃的是**映射后的 schema 文本**，不是原始 200 张表。

### 第三步：评测期强制开启 + 对比测量

**为什么单独成步**：产品代码默认 `useLLM=false`，但评测需要对比"开 vs 不开"的效果差异。评测期临时把 `EmbeddingMatchStrategy` 里的 `useLLM` 硬编码改成 `true`（Force enable for measurement），加 token 估算日志，跑完 200 条全量评测后回滚。

**这是评测脚手架，不是产品代码**——面试时要讲清"产品代码默认关闭，业务侧手动打开"和"评测期临时硬开"的区分。

### 第四步：上线后兜底——NPE 修复

**问题**：上线后发现 `detectByBatch` 在候选为空的边界场景下抛 NPE。

**修复**：加空值兜底（约 8 行代码），在 `detectByBatch` 入口判断候选列表非空。

**关键类名**：`EmbeddingMatchStrategy.detectByBatch` NPE 兜底

---

## 4. 迭代优化：遇到什么问题，怎么克服

LLM filter 不是"加上就涨点"，评测驱动的 prompt 迭代是主要工作。每周 2-3 次迭代，每次改 prompt 或加规则后，5 分钟跑完全量 200 条 Schema 评测 + 输出混淆矩阵，看混淆矩阵定位问题——是召回阶段漏了（embedding 词典不够）还是消歧阶段选错了（prompt 需要调）。针对性修 → 再跑评测 → 看数字提升。如果掉了回滚——**评测集是迭代的护栏**。

### 坑 1：LLM 忽略 COMMENT，只看字段名（最大 bad case 来源）

- **现象**：用户问"扣非利润"，候选 rank 1 是"净利润"（COMMENT='合并口径净利润'），rank 2 是"扣非净利润"（COMMENT='扣除非经常性损益后的净利润'）。LLM 选了 rank 1——只看字段名字面相似度，没看 COMMENT
- **业界对照**：LangChain GitHub Issue #5158 同样观察——"Column names do not describe perfectly well what they contain"
- **修复（评测发现驱动的增强设计）**：在 prompt 里加显式引导——"优先对比每个候选的 name + description/COMMENT + dataType + 所属表，不要只看字段名做字面匹配"
- **效果**：这类 case 准确率从 ~40% 提升到 ~75%

### 坑 2：LLM 过度自信，理由是事后合理化

- **现象**：LLM 选了错误字段后还给了一段"看似合理的推理"——如"扣非利润最接近净利润的概念"
- **业界对照**：FinVerBench 论文（arXiv 2506）发现 GPT-4.1 在财务校验任务上 95.3% 假阳率——它把 41 个正确的报表全部判错，每一个都给了"看似合理的计算理由"。论文结论：**LLM 给的"理由"不能作为正确性的证据**
- **修复**：不在运行时依赖 LLM 的理由做正确性判断。转而用**执行结果反向校验**——跑 SQL 后检查数值是否符合 FinVerBench 四类约束（Arithmetic / Cross-Statement / YoY / Magnitude），不齐就触发兜底
- **评测 vs 运行的区分**：评测/调试时 prompt 保留 reasoning 字段用于人工分析 bad case；实际运行时 reasoning 不参与下游决策——Corrector/Translator 只用 LLM 选出的字段 ID 列表

### 坑 3：候选太多时 LLM 注意力首尾偏置

- **现象**：Top-10 候选拼进 prompt 时，中间 rank 4-7 的候选容易被 LLM 忽略——它倾向于选 rank 1 或 rank 10 附近的
- **业界对照**：学术界 RSL-SQL（arXiv 2411.00073，Spider leaderboard SOTA）建议 Top-K=5 而非 10
- **修复**：把 Top-10 限制为 Top-5，给每个候选定稳定编号（#C1, #C2...），prompt 里要求 LLM "逐个评估每个候选的 COMMENT 与 query 的匹配度"
- **效果**：候选数从 10 降到 5 后，中间候选被忽略的问题基本消除

### 坑 4：JSON 格式不稳定

- **现象**：原版 prompt 要求 JSON 输出，但实际约 5-15% 的输出会带 markdown fence（```json）、寒暄（'Sure, here are...'）、或 Python 集合格式（`{'id1'}` 而非 JSON `["id1"]`）
- **业界对照**：业界实测纯 prompt 要求 JSON 只能拿到 80-95% 稳定性；Google Cloud 六大失败模式之一就是"Messy Output"
- **修复**：① 开启 LLM 的 `json_format=true`（structured output）；② 加 callback 后处理用 regex 提取 `[...]` 段做兜底；③ parse 失败时 retry-with-error-feedback（把错误信息塞回 prompt 重试 1 次）
- **效果**：格式失败率从 ~12% 降到 <2%

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

关键变化：① 显式强调 COMMENT 优先；② 候选编号 + 逐个评估；③ 不确定返回多个；④ 限制 Top-5。

### 剩余 19% 的错误归因（按严重程度）

1. **注释缺失导致 LLM 盲猜**（约 8%，最大瓶颈）——约 25% 的历史遗留字段没有中文注释，正在推注释补全
2. **低频实体值不在词典里**（约 4%）——HanLP 词典每天从数据库导 top 10 万高频值，小众公司名排在 10 万以外
3. **LLM 过度自信 + 格式不稳定**（约 3%）——已在坑 2/坑 4 处理
4. **跨主题域歧义**（约 2%）——"PE"在金融是市盈率，在行为实验域可能是心理量表维度
5. **隐式时间/多指标歧义**（约 2%）——"去年"是自然年还是财年

---

## 5. 成果展示：怎么衡量，效果如何

### 评测口径

**⚠️ 前置澄清：同一批 200 条 query，两套 gold，测的层次不同**

| 指标 | 测什么 | 评测集 | 用什么方法测 |
|------|-------|-------|-----------|
| SchemaMapper 映射准确率 **58%→81%** | **字段映射**（query → 多个语义元素 ID 是否全对）| **200 条 SchemaMapper 专属测评集**（从端到端集一一对应衍生）| Recall + Precision + **Exact Match（EM）** |
| 端到端查询准确率 **45%→72%→87%** | **完整链路**（NL → SQL → 执行结果是否对）| **200 条自建端到端测评集**（先于 Schema 优化就有）| 执行准确率 + 五维度语义评分 |

两套评测集是**一一对应**的——同一批 200 条 query。端到端 gold 看整条链路；SchemaMapper gold 只是其中的字段映射那一层。数字不能混谈，但 query 不是两套无关的题。

**SchemaMapper 200 条专属测评集怎么来的**：不是从线上失败 case 现抽的——线上那 50 条只够定方向。专属集是从已有的端到端测评集倒推出来的：每条端到端标注里本来就包含正确的语义元素集合（`gold_elements`：METRIC / DIMENSION / ENTITY…），SchemaMapper 专属测评集 = 抽出这 200 条的 `gold_elements` 层，只评字段映射，不跑 SQL。

### 58%→81% 具体怎么测的

一条 query 如"比亚迪去年的营收和净利润"的 Schema gold 是一个字段集合：
- METRIC: 营业收入 (id=101)
- METRIC: 净利润 (id=105)
- ENTITY: 比亚迪 (id=201, value=002594)
- DIMENSION: 报告期 (id=301, value=2025)

SchemaMapper 也输出一个选中字段集合。评测用信息检索的三件套：

| 指标 | 公式 | 含义 | 58%→81% 用的 |
|------|------|------|-------------|
| **Recall（召回率）** | gold 中被选中的数 / gold 总数 | "该选的都选了吗" | T0 ~70% → T1 ~90% |
| **Precision（准确率）** | 选中的字段里对的数 / 选中总数 | "选的有多少是对的" | T0 ~65% → T1 ~88% |
| **Exact Match（EM）** | 选中集合 == gold 集合 → 1 分，否则 0 分 | "**全对了吗**" | **58% → 81%** ⭐ |

58%→81% 测的是 **EM（精确匹配率）**——200 条里选中字段集合和 gold 集合完全一致的比例。最严格：多选一个、漏选一个都算 0 分。

### LLM 消歧显著解决的问题（+23pp 主要来自这三类）

1. **语义相近但业务含义不同的消歧** ⭐ 最大贡献（约 +12pp）——"净利润"vs"利润总额"vs"营业利润"，这类 case 从 ~30% 提升到 ~85%
2. **同义词/别名识别**（约 +6pp）——"营收"="营业收入"
3. **衍生指标识别**（约 +5pp）——ROE 在语义层 measures 定义后 LLM 能选出来

### 业界对标

FinStat2SQL（arXiv 2506.23273）在金融报表 Text2SQL 里也用"向量召回 + LLM 二次判断"的两阶段消歧处理"Net Income (IFRS) vs Profit After Tax (VAS)"的术语差异——和我们的方案是同一个套路。

### 评测输出 JSON 示例（错误 case——LLM 忽略 COMMENT + 漏选维度）

```json
{
  "query_id": 78,
  "query_text": "比亚迪的扣非利润",
  "schema_mapper_output": {
    "candidates": [
      {"rank": 1, "id": 105, "name": "净利润", "bizName": "net_profit", "comment": "本期合并口径净利润", "similarity": 0.91},
      {"rank": 2, "id": 106, "name": "扣非净利润", "bizName": "net_profit_excluding", "comment": "扣除非经常性损益后的净利润", "similarity": 0.88},
      {"rank": 3, "id": 107, "name": "利润总额", "bizName": "total_profit", "comment": "税前利润总额", "similarity": 0.85}
    ],
    "llm_selected": [105],
    "llm_reasoning": "'扣非利润'最接近'净利润'"
  },
  "gold_elements": [106, 201],
  "selected_elements": [105],
  "metrics": {
    "recall": 0.0,
    "precision": 0.0,
    "exact_match": false
  },
  "difficulty": "hard",
  "error_type": "选错（gold 包含 id=106 扣非净利润，但 LLM 选了 id=105 净利润）",
  "error_detail": "正确字段'扣非净利润'（rank 2，COMMENT='扣除非经常性损益后的净利润'）在候选里，但 LLM 只看字段名选了'净利润'（rank 1）——COMMENT 未被充分利用。同时 gold 里的 ENTITY'比亚迪'(id=201) 也没被选中"
}
```

每条评测输出包含：候选排序列表、LLM 选中的字段集合、gold 字段集合、三指标、错误类型（`error_type` 分三类：**召回遗漏** / **选错** / **格式失败**）。混淆矩阵按这三类 + 元素对统计。
