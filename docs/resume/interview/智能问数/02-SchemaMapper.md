> 系列：智能问数
> 简历基线：[`../../my_resume.md`](../../my_resume.md)
> 总览：[`01-总览与业务背景.md`](./01-总览与业务背景.md)
> 深度研究：[`../深度研究/01-通用问答.md`](../深度研究/01-通用问答.md)

> 上一篇：[01-总览与业务背景](./01-总览与业务背景.md) · 下一篇：[03-查询记忆复用](./03-查询记忆复用.md)
> 题纲：[`../面试题纲.md`](../面试题纲.md) § 2.1
> 标本：`headless/chat/.../mapper/` + `chat/.../NL2SQLParser`

---

# SchemaMapper LLM 语义映射（58% → 81%）

## 0. 本章地图 + 诚实边界

### 0.1 地图

| 节 | 内容 | 题纲 |
|----|------|------|
| **§0** | 调用点、数据结构、与纯 embedding 差异、诚实边界 | 宽问 / SuperSonic 对照 |
| **§1.1–1.2** | 痛点、三层漏斗、归因 | 功能实现 |
| **§1.3** | EM 58%→81%、评测集 | 指标 |
| **§1.4** | Prompt / bad case（含「期望增强」vs 标本） | Prompt 深挖 |
| **§1.5–1.6** | 诚实边界 + 题纲索引 | — |

### 0.2 诚实边界总表（先读再背后文）

| 说法 | 可讲 | 不可讲 / 需纠正 |
|------|------|----------------|
| **链路** | Mapping 阶段：Embedding 召回 + MapFilter +（本仓库）LLM filter 精选 ID | 「端到端一次 LLM 直接出 SQL 就是 SchemaMapper」 |
| **三层漏斗** | 规则 STRICT/MODERATE（HanLP）→ 失败再 LOOSE Embedding；LLM 路径在 EmbeddingMatchStrategy | 把 STRICT/MODERATE 说成「规则过滤数据类型」——那是 `MapFilter` + `QueryDataType`，不是 MapMode 全称 |
| **LLM 入参（本仓库标本）** | `retrievedInfo` = `EmbeddingResult` JSON（id/name/similarity/detectWord + DataItem 系 metadata：bizName/type/modelId…） | 声称**当前标本代码**已把 COMMENT/dataType/表名四维拼进 prompt——**尚未接线** |
| **「四维 COMMENT」叙事** | 可作为**评测发现驱动的增强设计 / 业务侧期望**（§1.4）；面试要说清：痛点真实，增强若未合入标本就标「设计/业务环境」 | 指着本仓库 `LLM_FILTER_PROMPT` 说已经是 C1+COMMENT 模板 |
| **开关** | yaml 有 `s2.mapper.embedding.use-llm-enhance`；**代码里 `useLLM=true` 写死**（Force enable for measurement），未读该 Parameter | 「靠配置一键开关，我没改代码」 |
| **Embedding 文本** | meta 向量库默认 `meta_collection`；segment 文本主要是字段 **name** | 「向量里已经存了完整 COMMENT」 |
| **默认模型（OSS）** | Parameter 默认常写 `bge-small-zh` / IN_MEMORY；业务叙述可用 BGE-M3——**对齐部署配置再说** | 未对配置就说死模型名 |
| **跳过 Mapping** | 请求已带 `selectedParseInfo` / mapInfo 非空 → 直接 PARSING | 每次 query 都必跑全量 Mapper |

### 0.3 调用点（背类名）

```
NL2SQLParser.parse
  ├─ 先 STRICT / MODERATE + 规则向（Keyword / HanLP…）  ← EmbeddingMapper 通常不跑
  └─ 无结果再 LOOSE / LLM_OR_RULE
        └─ ChatWorkflowEngine.performMapping  （mapInfo 空才跑）
              └─ SchemaMapper 链（spring.factories）
                    EmbeddingMapper → KeywordMapper → QueryFilterMapper → …
```

| 步骤 | 类 · 方法 | 要点 |
|------|-----------|------|
| Embedding 召回 | `EmbeddingMapper.doMap` → `EmbeddingMatchStrategy.detect` | 仅 `LOOSE` 或 `Text2SQLType.LLM_OR_RULE` 时 `accept` |
| 滑窗 / 批向量 | `BatchMatchStrategy` + `MetaEmbeddingService.retrieveQuery` | 片段 topK≈`embedding.number`（默认 5）；阈值默认 0.9（**LLM 路径会跳过阈值**） |
| LLM 精选 | `EmbeddingMatchStrategy.detectWithLLM` / `detectByBatch(..., useLlm=true)` | 输出 JSON ID 列表 → `llmMatched=true` |
| 规则后置 | `BaseMapper.map` 末尾 `MapFilter.filter` | dataSet 裁剪、短词、QueryDataType、exact match 优先 |
| 结果结构 | `SchemaMapInfo` → `List<SchemaElementMatch>` | 含 `SchemaElement` + similarity + detectWord + llmMatched |

**何时整段 Mapping 跳过**：`S2ChatLayerService.parse` 若上下文已有 elementMatches → 从 `PARSING` 起步；`performMapping` 见 mapInfo 非空直接 return。

### 0.4 输出长什么样

```
SchemaMapInfo
  dataSetId → [ SchemaElementMatch {
      element: SchemaElement { id, name, bizName, type, description, … },
      similarity, detectWord, word, llmMatched
  }, … ]
```

下游 Parser（`OnePassSCSqlGenStrategy`）吃的是**映射后的 schema 文本**，不是原始 200 张表。

### 0.5 相对「纯 Embedding」差在哪（对照题纲）

| | 纯 Embedding（规则失败后的基线） | + LLM filter（本仓库测量路径） |
|--|-------------------------------|--------------------------------|
| 召回 | 向量 topK + 阈值 0.9 | 仍先召回；LLM 路径可忽略阈值再精选 |
| 消歧 | 只靠相似度排序 + MapFilter | LLM 按 query 从候选里**做选择题出 ID** |
| 可解释 | 看 similarity 列表 | 可看 `llmMatched`；reasoning 若只在评测脚本则勿称线上必有 |
| SuperSonic 上游 | 有 EmbeddingMapper；LLM enhance 可配 | 本仓库强制 `useLLM=true` 便于对比测量 |

**面试时怎么说（诚实版）**：

> 「Mapping 在 STRICT/MODERATE 规则打不满时走 Embedding；我们打开（并测量）LLM 对召回结果做 ID 精选，EM 从 58% 到 81%。评测里最大 bad case 是近义字段——理想情况要把 COMMENT/类型/表名显式喂给模型；**当前开源标本里 LLM 主要看 EmbeddingResult JSON，四维拼装是我们评测结论驱动的增强项，面试按是否已合入生产如实说。**」

---

## 1.1 30 秒概括

> "研究员说'查一下净利润'，系统需要知道'净利润'对应数据库里哪个字段。原来的系统靠向量匹配找最相似的字段，但分不清'净利润'和'扣非净利润'——语义相近但业务含义完全不同。我引入了 LLM 做消歧，让它像人一样根据上下文选对字段。映射准确率从 58% 提升到 81%。"

## 1.2 功能实现类问题

**Q：为什么需要这个功能？用户痛点是什么？**

> "最大的痛点是'查不准'——研究员用业务术语提问，但数据库里字段是英文缩写（如 `net_profit`、`net_profit_excluding`）。原来的系统靠向量相似度匹配，遇到语义相近的字段就会混淆。研究员拿到的数据可能是错的——比如查'扣非净利润'结果返回了'净利润'，差了好几个亿。这是 Chat-BI 系统最危险的失败模式：**SQL 语法对、执行不报错、结果看似合理但语义错**。"

**Q：怎么解决的？产品思路是什么？**

> "三层漏斗设计：
> 1. **向量粗召回**——先用 embedding 找 Top-10 候选字段（快但粗）
> 2. **规则过滤**——去掉数据类型不匹配的（比如用户要数值，去掉文本类型）
> 3. **LLM 消歧精选** ⭐——对 Embedding 召回的候选做 **ID 精选**（选择题，不是填空生成字段名）
>
> **洞察（评测结论）**：近义字段只靠 name/相似度不够；**若把 COMMENT/类型/表名显式进 prompt，消歧更稳**。本仓库标本实际入参见 **§0.2**；§1.4 的「四维模板」按增强设计讲，勿与标本未接线部分打架。
>
> 金句：**LLM 做选择题，不做填空题**。"

**Q：为什么不直接用最强的 LLM 端到端生成 SQL？**

> "两个原因：
> 1. **可解释性**——分层设计能看到每一步在做什么（召回对不对、过滤对不对、消歧对不对）；端到端 LLM 是黑盒
> 2. **准确率上限**——业界实测端到端 LLM 生成 SQL 在 200+ 表规模下准确率只有 10-31%；分层设计利用确定性引擎（规则+Calcite）兜底，LLM 只做'选择题'不做'填空题'，准确率可控"

**Q：你是怎么排查定位到瓶颈在 SchemaMapper，而不是 SQL 生成或执行环节的？**

> "端到端查询有多轮改写、SchemaMapper、S2SQL 生成、语义校正、物理 SQL 翻译五个环节。定位到 SchemaMapper 分三步：
>
> **第一步：用户反馈 + ELK 日志看链路**
> - 研究员反馈'查比亚迪扣非净利润，返回的是净利润的值'
> - 在 Kibana Discover 里按 `traceId` 串联看完整链路：改写后的 query → SchemaMapper 候选列表 → LLM 生成的 S2SQL → 最终物理 SQL
> - 发现 SchemaMapper 召回的候选里，正确字段（`net_profit_excluding`）在 Top-10 但排第 3，错误字段（`net_profit`）排第 1——**embedding 把语义相近的字段排到了前面**
>
> **第二步：分层验证确认瓶颈位置**
> - 把 SchemaMapper 输出的错误候选**手动替换成正确字段**，后续 Parser/Corrector/Translator 生成的 SQL 就对了
> - 这证明后续管道是确定性的——**不纠正映射错误**。SchemaMapper 错了全链必错
>
> **第三步：小样本量化归因（定方向，不建大评测集）**
> - 从 ELK 导出**最近一周约 1000 次查询**（日均 ~150 × 7 天）
> - 在失败 query 里**随机抽约 50 条**人工拆链路看——样本量不大，目标是**定方向**而不是做统计显著性
> - 约 **60%（约 30 条）错在 SchemaMapper**，约 25% 是 SQL 生成错误（时间条件/聚合函数），约 15% 是值链接失败（公司名没匹配到代码）
> - SchemaMapper 错误的**具体表现**（50 条里反复出现的几类）：
>   - **选错近义字段**：'净利润'被映射成'利润总额' / '扣非利润'被映射成'净利润'——embedding 把语义近的字段排到前面，规则过滤分不清
>   - **营收口径混淆**：'营收'被映射成'营业总收入'而不是'营业收入'——总营收含其他业务收入，业务含义不同
>   - **一字之差**：'市盈率'被映射成'市净率'——字面极近、业务完全不同
>   - **召回遗漏**：'ROE'没进候选——ROE 是衍生指标（净利润/净资产），不在物理表字段名里；'扣非利润'没进候选——用户简称 vs 库里全称差太远
> - 结论：**优化 SchemaMapper 是提升端到端准确率的最高 ROI 路径**
>
> **评测集怎么来的**（和上面 50 条归因是两件事）：
> - 端到端自建测评集**在 SchemaMapper 优化之前就已经有了**（T0 的 45% 就是用它测的）
> - SchemaMapper 专属测评集是从这套端到端测评集**一一对应倒推**出来的——同一批 200 条 query，Schema gold 只是端到端 gold 里的字段映射部分（详见 § 1.3 / § 2）"

## 1.3 指标类问题

**⚠️ 前置澄清：同一批 200 条 query，两套 gold，测的层次不同**

| 指标 | 测什么 | 评测集 | 用什么方法测 |
|------|-------|-------|-----------|
| SchemaMapper 映射准确率 **58%→81%** | **字段映射**（query → 多个语义元素 ID 是否全对）| **200 条 SchemaMapper 专属测评集**（从端到端集一一对应衍生）| Recall + Precision + **Exact Match（EM）** |
| 端到端查询准确率 **45%→72%→87%** | **完整链路**（NL → SQL → 执行结果是否对）| **200 条自建端到端测评集**（先于 Schema 优化就有，详见 § 2）| 执行准确率 + 五维度语义评分 |

> "两套评测集是**一一对应**的——同一批 200 条 query。端到端 gold 看整条链路；SchemaMapper gold 只是其中的**字段映射那一层**。数字不能混谈，但 query 不是两套无关的题。"

**Q：SchemaMapper 的 200 条专属测评集怎么来的？**

> "不是从线上失败 case 现抽的——线上那 50 条只够**定方向**。专属集是从**已有的端到端测评集倒推**出来的：
>
> 1. 端到端测评集在 SchemaMapper 优化前就已经建好（T0 的 45% 用它测）——人工 + 多大模型交叉验证标注的完整过程详见 § 2
> 2. 每条端到端标注里本来就包含正确的语义元素集合（`gold_elements`：METRIC / DIMENSION / ENTITY…）
> 3. SchemaMapper 专属测评集 = **抽出这 200 条的 `gold_elements` 层**，只评字段映射，不跑 SQL
>
> 所以：**200 = 200，一一对应**；SchemaMapper 测评是端到端测评的**单步显微镜**——端到端错了，可以下钻看是不是映射层错了。"

**Q：58%→81% 具体怎么测的？**

> "一条 query 如'比亚迪去年的营收和净利润'的 Schema gold 不是单个字段，而是**一个字段集合**（就是端到端标注里的 `gold_elements`）：
> - METRIC: 营业收入 (id=101)
> - METRIC: 净利润 (id=105)
> - ENTITY: 比亚迪 (id=201, value=002594)
> - DIMENSION: 报告期 (id=301, value=2025)
>
> SchemaMapper 也输出一个**选中字段集合**。评测用信息检索的三件套：
>
> | 指标 | 公式 | 含义 | 58%→81% 用的 |
> |------|------|------|-------------|
> | **Recall（召回率）** | gold 中被选中的数 / gold 总数 | '该选的都选了吗' | T0 ~70% → T1 ~90% |
> | **Precision（准确率）** | 选中的字段里对的数 / 选中总数 | '选的有多少是对的' | T0 ~65% → T1 ~88% |
> | **Exact Match（EM，精确匹配率）** | 选中集合 == gold 集合 → 1 分，否则 0 分 | '**全对了吗**' | **58% → 81%** ⭐ |
>
> 58%→81% 测的是 **EM（精确匹配率）**——200 条里选中字段集合和 gold 集合完全一致的比例。这是最严格的指标：多选一个、漏选一个都算 0 分。
>
> **为什么要同时看三个指标**：
> - Recall 低 → **召回阶段漏了**（embedding 词典不够，该选的字段没进候选）
> - Precision 低 → **选了不该选的**（LLM 消歧过度召回）
> - EM 低 → **整体集合不对**（任何一个错了或漏了就算不对）
>
> 混淆矩阵按 **元素对**统计——比如'净利润'被误选为'扣非净利润'多少次、'营收'被误选为'营业总收入'多少次。
>
> **关键**：58%→81% 是 SchemaMapper 层的 EM——不执行 SQL，只看字段映射集合。跟端到端评测（要执行 SQL 比对结果集）是完全不同的评测方法，但用的是同一批 query。"

**测评模型输出 JSON 示例（正确 case）：**

```json
{
  "query_id": 42,
  "query_text": "比亚迪去年的营收和净利润",
  "schema_mapper_output": {
    "candidates": [
      {"rank": 1, "id": 101, "name": "营业收入", "bizName": "revenue", "comment": "本期营业总收入", "similarity": 0.92},
      {"rank": 2, "id": 105, "name": "净利润", "bizName": "net_profit", "comment": "本期合并口径净利润", "similarity": 0.89},
      {"rank": 3, "id": 108, "name": "营业总收入", "bizName": "total_revenue", "comment": "含其他业务收入", "similarity": 0.85}
    ],
    "llm_selected": [101, 105],
    "llm_reasoning": "用户问'营收和净利润'——'营收'对应'营业收入'（rank 1），'净利润'对应'净利润'（rank 2）"
  },
  "gold_elements": [101, 105, 201, 301],
  "selected_elements": [101, 105, 201, 301],
  "metrics": {
    "recall": 1.0,
    "precision": 1.0,
    "exact_match": true
  },
  "difficulty": "medium",
  "error_type": null
}
```

**测评模型输出 JSON 示例（错误 case——LLM 忽略了 COMMENT + 漏选维度）：**

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

> "每条评测输出包含：候选排序列表（rank + id + name + bizName + comment + similarity）、LLM 选中的字段集合、gold answer 字段集合、**三指标**（recall / precision / exact_match）、错误类型。`error_type` 分为三类：**召回遗漏**（gold 字段没进候选池）、**选错**（进了候选池但 LLM 选了别的）、**格式失败**（LLM 输出解析不了）。混淆矩阵按这三类 + 元素对统计。"

**Q：测 SchemaMapper 时遇到了什么困难？**

> "三个困难：
> 1. **gold 不唯一**——有些 query 正确映射不唯一（如'PE'可以是 TTM 也可以是 Forward）。规则在端到端标注阶段就定了（'默认选 TTM，标为 ambiguous'），Schema 层直接继承
> 2. **召回和排序要分开看**——要区分'召回阶段漏了'（embedding 词典不够）和'召回到了但选错'（需要 LLM 消歧）。所以同时看 Top-K 命中率和 EM
> 3. **单步准 ≠ 端到端准**——Schema EM 到了 81%，端到端还可能在 SQL 生成/时间条件上翻车；反过来端到端偶尔也对（简单 query），但映射集合并不 EM——所以两套指标都要看"

**Q：怎么迭代的？迭代节奏是什么？**

> "**每周 2-3 次迭代**。每次改 prompt 或加规则后，5 分钟跑完全量 200 条 Schema 评测 + 输出混淆矩阵。看混淆矩阵定位问题——是召回阶段漏了（embedding 词典不够）还是消歧阶段选错了（prompt 需要调）。针对性修 → 再跑评测 → 看数字提升。如果掉了回滚——**评测集是迭代的护栏**。端到端准确率的变化用同一批 200 条的完整链路评测跟踪（详见 § 2）。"

## 1.4 Prompt 调优与 bad case

> **先对齐 §0.2**：下面「修复后的四维 / C1 模板」是**评测 bad case 驱动的增强设计**。本仓库 `EmbeddingMatchStrategy.LLM_FILTER_PROMPT` 仍是上游模板，`retrievedInfo` 为 EmbeddingResult JSON。面试讲「我们发现要喂 COMMENT」= 真；讲「标本里已经改成四维模板」= 假，除非你确认生产 fork 已合入。

**初始 prompt（SuperSonic 原版 / 本仓库标本仍接近此版）：**

> SuperSonic 的 `EmbeddingMatchStrategy.java` 里的 `LLM_FILTER_PROMPT`：
> ```
> #Role: You are a professional data analyst specializing in metrics and dimensions.
> #Task: Given a user query and a list of retrieved metrics/dimensions through vector recall,
> please analyze which metrics/dimensions the user is most likely interested in.
> #Rules:
> 1. Based on user query and retrieved info, accurately determine metrics/dimensions user truly cares about.
> 2. Do not return all retrieved info, only select those highly relevant to user query.
> 3. Maintain high quality output, exclude metrics/dimensions irrelevant to user intent.
> 4. Output must be in JSON array format, only include IDs from retrieved info, e.g.: ['id1', 'id2']
> 5. Return JSON content directly without markdown formatting
> ```

> "**原版的问题**：只让 LLM 看 `retrievedInfo`（整体 JSON），没有显式引导它关注 COMMENT/中文注释。Reddit r/LangChain 社区的共识是：**'hallucinated columns 问题 rarely about retrieval, it's that the LLM only sees column names but not what they mean'**——LLM 会退化为字面匹配。"

**踩过的 4 个坑（按时间顺序）和修复：**

**坑 1：LLM 忽略 COMMENT，只看字段名（最大 bad case 来源）**

> - **现象**：用户问'扣非利润'，候选 rank 1 是'净利润'（COMMENT='合并口径净利润'），rank 2 是'扣非净利润'（COMMENT='扣除非经常性损益后的净利润'）。LLM 选了 rank 1——**只看字段名字面相似度，没看 COMMENT 里的'扣除非经常性损益'**
> - **业界对照**：LangChain GitHub Issue #5158 提出同样的观察——'Column names do not describe perfectly well what they contain. If the SQL agent can consider the table and column comments, it will help.'
> - **修复**：在 prompt 里加显式引导——'**优先对比每个候选的 name + description/COMMENT + dataType + 所属表，不要只看字段名做字面匹配**'
> - **效果**：这类 case 准确率从 ~40% 提升到 ~75%

**坑 2：过度自信——LLM 给的理由是事后合理化，不能作为正确性的证据**

> - **现象**：LLM 选了错误字段后还给了一段'看似合理的推理'——如'扣非利润最接近净利润的概念，因为扣非是一种净利润的衍生'。但实际选错了
> - **业界对照**：FinVerBench 论文（arXiv 2506）发现 GPT-4.1 在财务校验任务上 **95.3% 假阳率**——它把 41 个正确的报表全部判错，每一个都给了'看似合理的计算理由'。论文结论：**LLM 给的'理由'不能作为正确性的证据**
> - **评测 vs 运行的区分**（保持上下文一致的关键）：
>   - **评测/调试时**：prompt 里要求 LLM 输出 reasoning 字段——**保留**，用于人工分析 bad case（理解 LLM 为什么选错，是忽略 COMMENT 还是字面匹配）。JSON 格式里的 `llm_reasoning` 就是这个用途
>   - **实际运行时**：reasoning **不参与下游决策**——Corrector/Translator 看不到 LLM 的理由，只用 LLM 选出的字段 ID 列表。理由只是给人看的辅助信息，不是系统的判断依据
> - **修复**：不在运行时依赖 LLM 的理由做正确性判断。转而用**执行结果反向校验**——跑 SQL 后检查数值是否符合 FinVerBench 四类约束（Arithmetic / Cross-Statement / YoY / Magnitude），不齐就触发兜底
> - **效果**：评测时靠 reasoning 定位 bad case，运行时靠确定性校验做闭环——**不依赖 LLM 自评**

**坑 3：候选太多时 LLM 注意力首尾偏置**

> - **现象**：Top-10 候选拼进 prompt 时，中间 rank 4-7 的候选容易被 LLM 忽略——它倾向于选 rank 1 或 rank 10 附近的
> - **业界对照**：学术界 RSL-SQL（arXiv 2411.00073，Spider leaderboard SOTA）建议 Top-K=5 而非 10
> - **修复**：把 Top-10 限制为 Top-5，给每个候选定稳定编号（#C1, #C2...），prompt 里要求 LLM '逐个评估每个候选的 COMMENT 与 query 的匹配度'
> - **效果**：候选数从 10 降到 5 后，中间候选被忽略的问题基本消除

**坑 4：JSON 格式不稳定**

> - **现象**：原版 prompt 要求 JSON 输出，但实际约 5-15% 的输出会带 markdown fence（```json）、寒暄（'Sure, here are...'）、或 Python 集合格式（`{'id1'}` 而非 JSON `["id1"]`）
> - **业界对照**：业界实测纯 prompt 要求 JSON 只能拿到 80-95% 稳定性；Google Cloud 六大失败模式之一就是'Messy Output'
> - **修复**：① 开启 LLM 的 `json_format=true`（structured output）；② 加 callback 后处理用 regex 提取 `[...]` 段做兜底；③ parse 失败时 retry-with-error-feedback（把错误信息塞回 prompt 重试 1 次）
> - **效果**：格式失败率从 ~12% 降到 <2%

**调整后的 prompt（最终版本要点）：**

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

> "关键变化：① 显式强调 COMMENT 优先；② 候选编号 + 逐个评估；③ 不确定返回多个；④ 限制 Top-5。"

## 1.5 诚实边界

**LLM 消歧显著解决的问题（58%→81% 的 +23pp 主要来自这几类）：**

> 1. **语义相近但业务含义不同的消歧** ⭐ 最大贡献（约 +12pp）
>    - 之前 embedding 把'净利润'、'利润总额'、'营业利润'排到相似度前 3，规则过滤分不清
>    - LLM 看到 COMMENT 里的'税前利润总额' vs '税后合并口径净利润'后能正确区分
>    - 这类 case 从 ~30% 准确率提升到 ~85%
>    - **业界对标**：FinStat2SQL（arXiv 2506.23273）在金融报表 Text2SQL 里也用'向量召回 + LLM 二次判断'的两阶段消歧处理'Net Income (IFRS) vs Profit After Tax (VAS)'的术语差异——和我们的方案是同一个套路
>
> 2. **同义词 / 别名识别**（约 +6pp）
>    - 用户说'营收'，数据库里叫'营业收入'——在语义层注册别名后召回到了，LLM 理解'营收'='营业收入'选对了
>
> 3. **衍生指标识别**（约 +5pp）
>    - 用户说'ROE'，ROE 是衍生指标（净利润/净资产）不在物理表里——在语义层 measures 定义后 LLM 能选出来

**剩余 19% 的错误 case 归因分析（按严重程度排序）：**

> 1. **注释缺失导致 LLM 盲猜**（约 8%，最大瓶颈）
>    - 约 25% 的历史遗留字段没有中文注释（如 `fin_exp_intan` 只有英文名）
>    - LLM 只能靠字段名 + 数据类型猜——'fin_exp_intan'是'无形资产摊销'还是'金融支出'？猜不对
>    - **业界对标**：Reddit r/LangChain 共识——'column names do not describe perfectly well what they contain'；WrenAI 的方案是强制在 MDL 里定义每个字段的 description，我们部分字段缺失 description
>    - **改进**：正在推注释补全，优先补高频字段
>
> 2. **低频实体值不在词典里**（约 4%）
>    - HanLP 词典每天从数据库导 top 10 万高频值，但有些小众公司名/行业名排在 10 万以外
>    - **改进**：白名单机制 + 降低词典阈值
>
> 3. **LLM 过度自信 + 格式不稳定**（约 3%）
>    - FinVerBench 论文实测 GPT-4.1 在财务校验上 95.3% 假阳率——LLM 会给出'看似合理的理由'但其实选错了
>    - EMNLP 2025 论文（arXiv 2411.16742）证实直接让 LLM 给置信度**系统性偏高**，建议用 token-level 置信度做 rescaling
>    - **我们的应对**：不在 prompt 里让 LLM 自评置信度，改用执行结果反向校验
>
> 4. **跨主题域歧义**（约 2%）
>    - 'PE'在金融是市盈率，但在行为实验域可能是心理量表维度缩写
>    - **改进**：多轮改写补全主题域上下文
>
> 5. **隐式时间 / 多指标歧义**（约 2%）
>    - '去年'是自然年还是财年？'利润'是净利润、利润总额还是归母净利润？
>    - **改进**：返回多个候选让用户选

**评测集本身的短板：**
> - 200 条（与端到端同一批）不能完全覆盖线上长尾场景。业界如 Spider 2.0 有几千条
> - 目前只测了金融经济数据，行为实验数据还没进评测集
>
> **改进路线**：补注释 + 与端到端集同步扩到 500 条 + 引入 FinVerBench 四类约束做执行结果反向校验 + 行为实验数据进评测。"

---

## 1.6 题纲索引（§2.1）+ 回看清单

| 题号焦点 | 锚点 | 口径 |
|----------|------|------|
| 宽问：58%→81% 做了什么 | §0.3、§1.1 | Embedding + MapFilter + LLM ID 精选；主指标 EM |
| 为什么分层 / 为何不端到端 LLM | §1.2 | 可解释 + 选择题 vs 填空 |
| 如何定位瓶颈在 Mapping | §1.2 三步归因 | ELK + 换正确字段复跑 + 50 条定向 |
| 评测集 / EM·P·R | §1.3 | 200 条与端到端一一对应的 gold_elements |
| Prompt / bad case | §1.4 + **§0.2** | 先对齐标本再讲增强 |
| vs SuperSonic 纯 embedding | **§0.5** | 多 LLM filter；四维是否合入要诚实 |
| 多轮改写影响 | 链到 `01` H25 / 改写节 | 改写丢实体 → Mapping 必伤 |

### 回看清单

- [ ] 能画出 STRICT/MODERATE → LOOSE Embedding → LLM filter 的顺序
- [ ] 能说出跳过 Mapping 的条件（已有 selectedParse）
- [ ] 能区分：召回遗漏 vs 排序靠前错 vs LLM 选错
- [ ] 对「COMMENT 四维」能按 §0.2 划清标本 vs 增强，不穿帮
- [ ] EM 58→81 与端到端 45→72 不混谈

---
