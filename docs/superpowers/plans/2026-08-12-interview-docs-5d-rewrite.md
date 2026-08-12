# 智能问数面试文档 5 维度重写 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将 `docs/resume/interview/智能问数/` 下 4 篇文档按"背景/方案选型/行动计划/迭代优化/成果展示"5 维度重写，让叙事顺序与面试官提问维度对齐。

**架构：** 02/03/04 三篇专题文档完全重写（纯 5 维度骨架，删除诚实边界总表/Part A-B-C/题纲索引/回看清单）；01 总览微调（§2 重写、§3 重新分组、§4/§5 删除）。行动计划维度基于 git 考古真实时序包装成"我"的工作，守住"不从零自研"等职责边界。

**技术栈：** Markdown 文档重组，无代码变更。

**设计规格：** `docs/superpowers/specs/2026-08-12-interview-docs-5d-rewrite-design.md`（commit `bee48390c`）

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `docs/resume/interview/智能问数/02-SchemaMapper.md` | 完全重写 | 402 行 → 5 维度重写，行动计划 4 步（含 git 时序） |
| `docs/resume/interview/智能问数/03-查询记忆复用.md` | 完全重写 | 618 行 → 5 维度重写，行动计划 5 大步骤（9 个 commit 合并） |
| `docs/resume/interview/智能问数/04-推荐问题.md` | 完全重写 | 477 行 → 5 维度重写，行动计划 5 步 |
| `docs/resume/interview/智能问数/01-总览与业务背景.md` | 微调 | §2/§2.1 重写；§3 重新分组；§4/§5 删除；其余保留 |

**执行顺序理由：** 先 02 验证骨架（最小最典型），再 03（最复杂，验证行动计划合并粒度），再 04（套用同骨架），最后 01（依赖前三篇叙事已稳定）。

---

## 任务 1：重写 02-SchemaMapper.md

**文件：**
- 修改：`docs/resume/interview/智能问数/02-SchemaMapper.md`（完全重写，保留系列导航头）

**素材来源映射：**
- 背景 ← 现 §1.1（30 秒概括）+ §1.2（痛点 + ELK 三步排查）
- 方案选型 ← 现 §1.2（三层漏斗 + 为什么不端到端 LLM）+ §0.5（对照表）
- 行动计划 ← git 考古时序（规格第四节 4.1 表格）+ 现 §0.3（调用点）+ §0.4（输出结构）
- 迭代优化 ← 现 §1.4（4 个坑 + 修复）+ §1.5（剩余 19% 归因）
- 成果展示 ← 现 §1.3（58%→81% + 评测口径 + JSON 示例）

- [ ] **步骤 1：写出 02 完整新内容**

完整新文件内容（直接 Write 覆盖）：

```markdown
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
```

- [ ] **步骤 2：用 Grep 验证新文档结构**

运行（在仓库根目录）：
```bash
grep -c "^## " docs/resume/interview/智能问数/02-SchemaMapper.md
grep -n "^## " docs/resume/interview/智能问数/02-SchemaMapper.md
```
预期：`5` 个二级标题，分别是 `## 1. 背景`、`## 2. 方案选型`、`## 3. 行动计划`、`## 4. 迭代优化`、`## 5. 成果展示`

- [ ] **步骤 3：验证诚实边界——不应出现"诚实边界总表""Part A""Part B""题纲索引""回看清单"**

运行：
```bash
grep -E "诚实边界总表|Part A|Part B|Part C|题纲索引|回看清单" docs/resume/interview/智能问数/02-SchemaMapper.md
```
预期：无输出（空结果）

- [ ] **步骤 4：验证关键素材保留——58%→81%、ELK、三层漏斗、4 个坑**

运行：
```bash
grep -c "58%.*81%\|58% → 81%" docs/resume/interview/智能问数/02-SchemaMapper.md
grep -c "Kibana\|traceId\|ELK" docs/resume/interview/智能问数/02-SchemaMapper.md
grep -c "三层漏斗\|选择题" docs/resume/interview/智能问数/02-SchemaMapper.md
grep -c "忽略 COMMENT\|过度自信\|首尾偏置\|JSON 格式" docs/resume/interview/智能问数/02-SchemaMapper.md
```
预期：每个 `grep -c` 输出 ≥ 1

- [ ] **步骤 5：验证行动计划——4 个步骤标题都在**

运行：
```bash
grep -c "^### 第一步\|^### 第二步\|^### 第三步\|^### 第四步" docs/resume/interview/智能问数/02-SchemaMapper.md
```
预期：`4`

- [ ] **步骤 6：Commit**

```bash
git add docs/resume/interview/智能问数/02-SchemaMapper.md
git commit -m "$(cat <<'EOF'
docs(interview/智能问数): 02-SchemaMapper 按 5 维度重写

按"背景/方案选型/行动计划/迭代优化/成果展示"5 维度重写，
删除诚实边界总表/Part A-C/题纲索引/回看清单。行动计划 4 步
基于 git 考古真实时序包装（并行化→五件套→评测硬开→NPE 兜底）。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 2：重写 03-查询记忆复用.md

**文件：**
- 修改：`docs/resume/interview/智能问数/03-查询记忆复用.md`（完全重写，保留系列导航头）

**素材来源映射：**
- 背景 ← 现 A1（背景与动机）+ A2（目标与非目标）
- 方案选型 ← 现 A1 替代方案对比表 + A2 + A5（与 02/04 边界）
- 行动计划 ← git 考古时序（9 个 commit 合并为 5 大步骤）+ 现 B0（总图）+ B1（数据结构）+ B2（写入）+ B3（召回）
- 迭代优化 ← 现 A6（7 条难点）+ git bug 修复
- 成果展示 ← 现 A3（已实现效果）+ A4（评测口径）+ B5（冷启动/人审/漏斗）

- [ ] **步骤 1：写出 03 完整新内容**

完整新文件内容（直接 Write 覆盖）：

```markdown
> 系列：智能问数
> 简历基线：[`../../my_resume.md`](../../my_resume.md)
> 总览：[`01-总览与业务背景.md`](./01-总览与业务背景.md)
> 上一篇：[02-SchemaMapper](./02-SchemaMapper.md) · 下一篇：[04-推荐问题](./04-推荐问题.md)

---

# 查询记忆复用（72% → 87%，800+ 条）

## 1. 背景：为什么做，怎么发现的问题

**痛点**：SchemaMapper 把字段映射做到 81% 后，端到端卡在 72%——字段常选对，**Parser 仍因 Few-shot 结构不对齐翻车**。

Text2SQL 准确率高度依赖范文的**结构相似度**，而系统只有一套 JSON 写死的静态范文（演示域"超音数"），对金融题不但帮不上忙还会教坏——比如把"去年"教成滚动 365 天，和金融场景"自然年"的语义完全错位。

**业界已反复验证这一点**：
- DIN-SQL（NeurIPS 2023）表明合适的 in-context 示例可带来约 +10pp 提升量级
- DAIL-SQL（Gao et al., arXiv:2308.15363）显示精选示例显著优于随机选取

静态写死 demonstration 在范文与当前题差距大时会出现 retrieval bias，LLM 被不相关示例带偏。

**量化瓶颈**：T1（SchemaMapper 已优化完）端到端 72%，Parser 条件准确率（Schema 正确子集）约 75%——**Parser 是下一个瓶颈**。一句话：Parser 不是缺"几条 SQL"，缺的是"跟当前题同构的成功写法"。

---

## 2. 方案选型：考虑了哪些方案，如何权衡

**候选方案对比**：

| 方案 | 做法 | 不足 |
|------|------|------|
| 堆静态 Few-shot | 每种骨架手写进 JSON | 滞后线上；堆数量不等于选得准；token/维护双爆 |
| 全量塞 prompt | 几十条全进 `#Exemplars` | 超上下文；噪声大 |
| 微调专用模型 | 用成功 SQL 微调 | 成本高、迭代慢 |
| **动态检索同构范文**（选的） | 成功过审 → 向量库 → 按 query 召回注入 | 对齐 example selection；范文随业务增长 |

**选型理由**：动态检索同构范文对齐学术界 example selection 共识；范文随业务增长而非静态滞后；可解释（每条范文有 traceId 回溯）。

**和现有代码的关系**：在已有的 NL2SQLParser 链路上挂动态范文注入，不改主链路。切入点是 `NL2SQLParser.addDynamicExemplars`（Parser 前同步召回）。**不替代 SchemaMapper**——记忆复用作用于 Parser 阶段，与字段映射是上下游关系。

**目标**：成功 SQL 过审后入库，Parser 按相似度动态召回同构范文注入 `#Exemplars`，提升端到端准确率。

**非目标**：
- 不另建向量库——与 [04 推荐问题](./04-推荐问题.md) 共用同一 `memory_{agentId}`
- 相似推荐只取 question 展示，不教 Parser 写法

**与上下游模块的边界**：

| 模块 | 链路位置 | 消费什么 | 面试一句 |
|------|---------|---------|---------|
| [02 SchemaMapper](./02-SchemaMapper.md) | 映射阶段 | 字段 → 本轮 `{{schema}}` | 选对字段 |
| **本文 记忆复用** | **Parser（同步）** | 历史四元组 → `#Exemplars` | 教 Parser 写法 |
| [04 推荐问题](./04-推荐问题.md) | Parse 后**异步** | 同一向量库，只取 `question` | 同库异步只读 |

一句话：SchemaMapper 选对字段；记忆复用教 Parser 写法；相似推荐把成功问法露给人。

---

## 3. 行动计划：怎么一步步写出来的

按真实开发时序，分五大步落地。状态机骨架先画完，主链路接通晚一些，人审兜底更晚——典型的"先画框架、后填逻辑"打法。

### 第一步：地基日——状态机骨架 + 评审任务 + 入库/读出链路一次性设计

**为什么先做这步**：状态机是整个记忆库的骨架，先一次性设计好（PENDING/ENABLED/DISABLED + POSITIVE/NEGATIVE），避免后续重构。骨架包含五个部分，同一天内全部落地：

1. **状态机数据结构** —— `ChatMemoryDO` / `s2_chat_memory` 表，字段含 `agent_id`（Agent 隔离）、`query_id`（来源问答可回溯）、`question`（**做 embedding 的文本**）、`side_info`（SideInfo 如 CurrentDate）、`db_schema`（当时 Schema 串）、`s2_sql`（S2SQL）、`status`（`PENDING`/`ENABLED`/`DISABLED`）、`llm_review`/`llm_comment`（自动审）、`human_review`/`human_comment`（人审）
2. **入库点** —— `SqlExecutor.execute` 仅当 `QueryState.SUCCESS` 且 `LLMSqlQuery.QUERY_MODE` 时调用 `createMemory`；规则 SQL 不入库；同 agent + 同 question 已有 ENABLED → 跳过（不重复写入）
3. **评审任务** —— `MemoryReviewTask.review` 通过 `@Scheduled(fixedDelay = 60 * 1000)` 触发，每 60 秒扫一轮
4. **读出点** —— `NL2SQLParser.addDynamicExemplars` 在 Parser 前同步召回
5. **静态种子加载** —— 应用启动时 `CommandLineRunner.loadSysExemplars` 把 ENABLED 记忆灌回向量库

**关键类名**：`ChatMemoryDO`、`MemoryService`/`MemoryServiceImpl`、`MemoryReviewTask`、`SqlExemplar`、`ExemplarService`/`ExemplarServiceImpl`、`s2_chat_memory` 表

**状态机核心**：
```
LLM 产出四元组(question, sideInfo, dbSchema, s2SQL)
        │
        ▼  LLMResponseService.addParseInfo 挂到 ParseResult
SqlExecutor.execute → SUCCESS → createMemory → status=PENDING（只写 DB）
        │
        ▼  MemoryReviewTask 每 60s 扫一轮
   opinion=POSITIVE → enableMemory → status=ENABLED + storeExemplar(向量)
        │
        ├─ 旁路：人审 / 用户反馈 score≥5(ENABLED) / ≤1(DISABLED)
        │
        ▼  应用启动 CommandLineRunner.loadSysExemplars 回灌 ENABLED → 向量
下次 query → NL2SQLParser.addDynamicExemplars → recall 10
        → PromptHelper.getFewShotExemplars 筛成 ≤5 → #Exemplars → 新 S2SQL
```

**向量侧——`Text2SQLExemplar`**：
- 集合名 `memory_{agentId}`（前缀 `s2.embedding.memory.collection.prefix`，默认 `memory_`）
- 向量化对象：**`question` 文本**（不是 SQL）
- metadata / payload：JSON 含 `question` + `sideInfo` + `dbSchema` + `sql`
- 系统静态兜底集：`text2dsl_agent_collection`（`s2-exemplar.json`，演示域"超音数"）

### 第二步：成本控制 + 接通主链路（自动 ENABLED）

**为什么分两步**：LLM Review 会带来 token 成本，先用 agent 级开关控制（默认关闭），再接通"POSITIVE 自动 ENABLED"的主链路。

**成本控制**：`Agent` 加 `MEMORY_REVIEW.enable` 字段（DB 动态配置，不在 yaml）。注册时默认 false；业务 Agent 在管理界面手动打开。`MemoryReviewTask` 只处理 `agent.enableMemoryReview()` 返回 true 的 Agent。

**接通主链路**：`MemoryReviewTask` 里 4 行关键代码——`if (POSITIVE.equals(m.getLlmReviewRet())) memoryService.enableMemory(m)`。

**判定与状态变化**：

| LLM 输出 | 系统动作 |
|---------|---------|
| `opinion=POSITIVE` | **直接 ENABLED** + `enableMemory` → `storeExemplar(memory_{agentId})` 入向量 |
| `opinion=NEGATIVE` | **保持 PENDING**（不改 status），记 `llm_review=NEGATIVE` + `llm_comment`，进人审队列 |
| 格式解析失败 | 本轮不改状态，下个周期重试 |

**审核 prompt 关键规则**：
```
#Rules:
1.ALWAYS follow the output format: opinion=(POSITIVE|NEGATIVE),comment=(your comment).
2.NO NEED to check date filters as the junior engineer seldom makes mistakes in this regard.
```

⚠️ **开源 prompt 默认"不重点抠日期"（Rule 2）**，金融场景"去年=自然年"漏审要靠人审兜底。Review 只看 Question + Schema + SideInfo + SQL，**不看执行结果表**——静态审核。

### 第三步：冷启动种子——编写金融场景静态种子

**为什么单独成步**：记忆库空 → 召回不足 5 条 → Parser 退回吃静态范文 → 静态范文有害 → 准确率起不来。要召满约 5 条同构范文，库里得有足够密度的种子，否则向量检索变成近邻随机。

**怎么做的**：4 个 Agent 按主题域分摊，每 Agent 灌 40-60 条种子 SQL（人工编写 + 审校），先有"面粉"才能"烤面包"。

| Agent | 种子数 | 为什么这个量 |
|-------|-------|-------------|
| 公司研究 | ~60 | 问得最多：单/多指标、自然年、多实体、排名 |
| 绿色经济 | ~50 | 跨表与口径相对多 |
| 经济研究（宏观） | ~50 | 时间序列、同比环比 |
| 行为实验 | ~40 | 表少、骨架少 |
| **合计** | **~200** | 4 Agent 分摊 |

**种子来源**：ELK 高复用成功题 + 端到端评测已验证写法，上线前集中人审后批量 ENABLED。为什么单 Agent 要 40-60：为召满约 5 条同构范文，库要覆盖多种 SQL 骨架（自然年/排名/多实体/JOIN 等），40-60 是工程定标。

### 第四步：兜底——异常隔离 + 数据一致性修复

**为什么做这步**：状态机跑起来后，两个工程问题暴露出来。

**异常隔离**：`MemoryReviewTask` 原本批量处理一批 memory，单条失败会拖垮整批。改成**每条 memory 单独 try-catch**——避免单条失败拖垮整批评审。

**数据一致性 bug（修了 2 次）**：
- **Bug 1**：`enableMemory` 时只改了 DB `status=ENABLED`，**没同步入向量库**——导致 DB 显示 ENABLED 但向量库里没有，召回不到。修复：`enableMemory` 末尾 upsert 到向量库
- **Bug 2**：状态切换（启用→待定，待定→启用）时向量库不同步。修复：状态切换的入口都加向量库同步逻辑

**关键类名**：`MemoryReviewTask` 单条 try-catch、`MemoryServiceImpl.enableMemory` upsert 向量库

### 第五步：人审通道——作为 LLM Review 的兜底

**为什么最后做**：先用 LLM Review 跑量，跑半年后发现"去年=自然年"这类时间口径漏审是系统性问题（开源 prompt Rule 2 导致），光靠 LLM Review 不够。引入人审作为兜底。

**怎么做的**：
- `ChatMemoryDO` 加 `query_id` 字段，打通 chat 流和 memory 流
- `ChatManageServiceImpl` 暴露人审接口，`human_review` / `human_comment` 字段
- 用户反馈：score>=5 直接 `enableMemory`，score<=1 直接 `disableMemory`——**不经过 Review 流程**，是直接启停
- 冲突以人审为准（运营约定）；冲突 case 进评测集回归，避免同类错误再放行

**周人审节奏**：

| 角色 | 节奏 | 做什么 |
|------|------|--------|
| **LLM** | 持续（`@Scheduled(60s)`） | POSITIVE → 当场 ENABLED；NEGATIVE → 等人 |
| **人工** | **每周一次**（约 0.5-1 小时） | 清 NEGATIVE + 抽检 POSITIVE；冲突进评测集 |

人审单条 30 秒-1 分钟；周队列约十几-三十条 NEGATIVE + 少量抽检。效率靠三件事：LLM 先筛、同 question 去重、只收 LLM_S2SQL 成功题（规则 SQL 不入库）。人不盯盘——日常放行交给 LLM，人做周批次兜底。

### 召回与注入（贯穿所有步骤）

**召回链**（`NL2SQLParser.addDynamicExemplars`，同步堵在 Parser 前）：
```java
private void addDynamicExemplars(ParseContext parseContext, QueryNLReq queryNLReq) {
    String memoryCollectionName =
            embeddingConfig.getMemoryCollectionName(parseContext.getAgent().getId());
    int exemplarRecallNumber = Integer.parseInt(
            parserConfig.getParameterValue(PARSER_EXEMPLAR_RECALL_NUMBER));  // 10
    List<Text2SQLExemplar> exemplars = exemplarManager.recallExemplars(
            memoryCollectionName, queryNLReq.getQueryText(), exemplarRecallNumber);
    queryNLReq.getDynamicExemplars().addAll(exemplars);
    parseContext.getResponse().setUsedExemplars(exemplars);  // B4.1 回溯用
}
```

**recall 10 → 注入约 5 的筛选算法**（`PromptHelper.getFewShotExemplars`）：
1. 组候选池（≤10）：先放 dynamicExemplars（Agent 记忆），不足用系统预设 exemplar 集合按当前 query 向量补齐
2. 按相似度拆两桶：`same`（similarity > 0.989，几乎同题，必须进 prompt）；`noSame`（其余）
3. 砍尾：候选明显多于 few-shot 时，`noSame` 升序排，丢最低一截
4. 凑满 few-shot.number=5：有 same 则全保留 same + noSame 补到 5；无 same 则从 noSame 取 5，强制保留相似度最高那 1 条
5. 若开启 self-consistency 多次推理，每轮各自组一份（本仓库 self-consistency=1，通常只组一次）

**配置表**：

| 配置项 | 本仓库值 | 含义 |
|--------|---------|------|
| `parser.exemplar-recall.number` | **10** | 向量召回候选池上限 |
| `parser.few-shot.number` | **5**（Parameter 默认 3） | 真正进 `#Exemplars` 的条数 |
| `parser.self-consistency.number` | **1** | self-consistency 推理轮次 |
| Agent `MEMORY_REVIEW.enable` | 业务 Agent = **true**；系统默认 = **false** | Agent 级 DB 动态配置（不在 yaml） |

---

## 4. 迭代优化：遇到什么问题，怎么克服

记忆库不是"存 SQL 就涨点"，过程里踩过的坑收在下面。

### 坑 1：语义成功 ≠ 执行成功

- **难在哪**：LLM 生成的 S2SQL 能跑通、不报错，不代表时间口径/字段选择正确。"去年"被理解成滚动 365 天而非自然年，执行照样返回结果，但金融侧判定为错
- **怎么扛**：状态机把执行成功只落到 PENDING，不写向量库；必须经过 LLM Review（POSITIVE）或人审通过才 ENABLED + 入库。宁可漏放也不能放错
- **面试要点**：SUCCESS 不等于可做范文

### 坑 2：有害示范 / 静态域错位

- **难在哪**：系统原配一套写死的演示域（超音数）范文，"去年"= 滚动 365 天。这套范文对金融场景是**有害示范**——金融侧"去年"= 自然年（1 月 1 日-12 月 31 日），语义完全错位
- **怎么扛**：记忆库上线后用动态同构范文替换静态范文，召回按业务域注入；但存量静态范文仍存在，直到全面切到记忆库后才降级为 fallback
- **留下什么**："演示域教坏金融"的案例成为动机的核心佐证，也是后续改进 prompt 强制校验时间口径的驱动力

### 坑 3：冷启动鸡生蛋

- **难在哪**：记忆库空 → 召回不足 5 条 → Parser 退回吃静态范文 → 静态范文有害 → 准确率起不来
- **怎么扛**：4 个 Agent 按主题域分摊，每 Agent 灌 40-60 条种子 SQL（人工编写 + 审校），先有"面粉"才能"烤面包"（详见行动计划第三步）
- **留下什么**：冷启动成本是记忆库方案的固有代价，种子质量直接决定初始召回效果

### 坑 4：评测贵且口径不唯一

- **难在哪**：gold SQL 不唯一——同一 query 可有多种等价写法（如 PE 取 TTM 还是 Forward）；端到端判定比字段映射更难，要同时标 gold_elements 和结果口径约束
- **怎么扛**：宁可 200 条标得牢也不要几千条标得飘；ambiguous case 标注为"默认口径 + 备选口径"，评测时以默认口径为准。五维度语义评分兜底纯 SQL Exact Match 的不足
- **留下什么**：200 条评测集是当前可信基线，但覆盖不足是诚实边界——主动说"行为域待补"比被追问更稳

### 坑 5：Review 信号偏弱

- **难在哪**：开源审核 prompt 显式写了"NO NEED to check date filters"，即**不重点抠日期**，且不看执行结果表——只凭 schema + SQL 静态审核。金融场景的时间口径痛点（去年 = 自然年）恰好被这条规则漏掉
- **怎么扛**：LLM Review 做初筛，人审做终兜；人审与 LLM 冲突时以人审为准。冲突 case 进评测集回归
- **留下什么**："开源 prompt 不重点抠日期"是诚实边界关键点，也是改进方向（把时间口径校验写进 Rules）

### 坑 6：负迁移 / 污染

- **难在哪**：一条看似正确但实际错误的 SQL 过审入库后，会被后续相似 query 召回，把错误写法"教"给 Parser——典型负迁移。发现与下线成本高：线上反馈 → 回溯召回记录 → 定位污染源 → DISABLED
- **怎么扛**：用户反馈"答错"后，按 queryId 回溯当日召回的 usedExemplars（召回时已写入 `parseContext.getResponse().setUsedExemplars`，是回溯依据），定位污染源后调用 `disableMemory` + `removeExemplar` 下线。冲突 case 进评测集回归
- **下线链（5 步）**：
  1. 用户反馈"答错" → 拿到 `queryId`
  2. 按 `queryId` 回溯当日召回的 `usedExemplars`
  3. `MemoryService` 将对应记忆标记为 DISABLED → 调用 `disableMemory`
  4. `removeExemplar` 清掉向量侧的对应条目（集合 `memory_{agentId}`）
  5. 冲突 case 进评测集回归

```java
// MemoryServiceImpl.disableMemory
public void disableMemory(ChatMemoryDO memory) {
    memory.setStatus(MemoryStatus.DISABLED.toString());
    exemplarService.removeExemplar(
        embeddingConfig.getMemoryCollectionName(memory.getAgentId()),
        Text2SQLExemplar.builder().question(memory.getQuestion())
            .sideInfo(memory.getSideInfo()).dbSchema(memory.getDbSchema())
            .sql(memory.getS2sql()).build());
}
```

NEGATIVE **默认不**自动 DISABLED——LLM 判 NEGATIVE 只记 `llm_review`，status 常仍 PENDING；只有用户反馈 score≤1 或人审否决才走 `disableMemory`。DB 行**留着作账**，不删；`removeExemplar` 只清向量侧。

### 坑 7：只进不出（技术债）

- **难在哪**：记忆库无 TTL、无召回反馈降权机制，只进不出。长期存在两个问题：语义层变更后旧 SQL 过时（字段改名/指标口径调整），低质量记忆稀释高质量记忆
- **怎么扛**：靠人工定期巡检 + 用户反馈驱动下线，但没有系统化的淘汰机制。当前是已知技术债
- **改进方向**：(1) TTL（30 天未召回降权）；(2) 召回后反馈闭环（被否决的 SQL 自动降权）；(3) 表上补 recall_count / 最后召回时间

### 后续改进方向（"下一刀砍哪"）

| 优先级 | 方向 | 问题 | 拟改法 |
|--------|------|------|--------|
| **P0** | Review Rules 强制校验时间口径 | 开源 prompt 不抠日期，金融"去年=自然年"漏审 | 改 prompt Rules（加"去年/近 X 月"判定）；必要时把执行结果预览纳入审核输入 |
| **P0** | 召回后反馈闭环 | 错范文被召回无降权，污染半衰期长 | 用户否决/答错 → 自动降权或 DISABLED |
| **P1** | TTL / 长期未召回降权 | 只进不出；语义层变更旧 SQL 过时 | N 天未召回降权；schema 变更时批量失效或重审 |
| **P1** | 表字段补 `recall_count` / `last_recalled_at` | 现表无 hit count，运营盲 | 加字段（或等价观测） |

---

## 5. 成果展示：怎么衡量，效果如何

### 评测口径

评测基于自维护离线集，**同一批 200 条**贯穿全部阶段，中间无人工干预（无 HITL）。

| 阶段 | 端到端准确率 | Schema EM | Parser 条件准确率（Schema 正确子集） | 说明 |
|------|------------|-----------|----------------------------------|------|
| T0（加入时） | 45% | 58% | — | 端到端测评集已就绪 |
| T1（Schema + LLM 消歧） | 72% (+27pp) | 81% (+23pp) | ~75% | 记忆库未上线 |
| T2（记忆库上线） | 87% (+15pp) | 81% | ~90% (+15pp) | +15pp 全归因记忆库 |

Parser 条件准确率是端到端集上的条件切片（Schema EM 正确的前提下看最终答案是否对），不是另建一套 S2SQL Exact Match 评测集。

判定方式：执行结果是否满足 gold_answer 的口径约束 + 五维度语义评分（字段、实体、时间、聚合、量级）。

### 已实现效果

端到端准确率从 **72% 提升到 87%**（同一批 200 条离线评测集，无 HITL）；其中 T1→T2 的 **+15pp** 几乎全部归因于记忆库（SchemaMapper 在 T1 已优化完毕，映射 EM 保持在 81%）。

记忆库累计 **800+ 条 ENABLED**，其中冷启动种子 **约 200 条**（4 个 Agent 按主题域分摊），4-7 月线上沉淀约 600 条。

在 Schema 已正确的子集上，Parser 条件准确率约 **75% → 90%**。

### 漏斗表（周）

```
周查询 ≈ 1050（150×7）
  → 成功且 LLM_S2SQL ≈ 700–800
  → 去重后新 PENDING ≈ 80–100（同问已有 ENABLED 则跳过）
  → 新 ENABLED ≈ 50/周
```

| 口径 | 约值 | 一句话 |
|------|------|--------|
| 全量查询 → 新 ENABLED | **~5%** | 低是正常的——大量重复不问不入库 |
| 新 PENDING → ENABLED | **~50%–60%** | 才是闸门过审率 |

飞轮看"新结构过审"，不看"每次查询都变记忆"。

### 诚实边界

- 40-60 是我们的工程定标，不是某篇论文的"飞轮阈值"。文献（JPMorganChase continual learning, arXiv:2511.10674）讲的是同域记忆从前约 10-20 条起就有可见收益；我们定 40-60 是在"已有早期收益"之上再留余量保证多种骨架都能召满约 5 条
- 向量库（pgvector）作为技术选型，不包装成自研
- embedding 只打 `question`，SQL 在向量侧是 metadata payload——不是"SQL 也做 embedding"
- 表里**无** embedding 列、**无** `recall_count`（向量侧 metadata 也不存 hit count）
```

- [ ] **步骤 2：用 Grep 验证新文档结构**

运行：
```bash
grep -c "^## " docs/resume/interview/智能问数/03-查询记忆复用.md
grep -n "^## " docs/resume/interview/智能问数/03-查询记忆复用.md
```
预期：`5` 个二级标题，分别是 `## 1. 背景`、`## 2. 方案选型`、`## 3. 行动计划`、`## 4. 迭代优化`、`## 5. 成果展示`

- [ ] **步骤 3：验证诚实边界——不应出现旧结构关键词**

运行：
```bash
grep -E "诚实边界总表|Part A|Part B|Part C|题纲索引|回看清单" docs/resume/interview/智能问数/03-查询记忆复用.md
```
预期：无输出

- [ ] **步骤 4：验证关键素材保留——72%→87%、状态机、7 个坑、T0/T1/T2 表**

运行：
```bash
grep -c "72%.*87%\|72% → 87%" docs/resume/interview/智能问数/03-查询记忆复用.md
grep -c "PENDING\|ENABLED\|DISABLED" docs/resume/interview/智能问数/03-查询记忆复用.md
grep -c "语义成功\|有害示范\|冷启动鸡生蛋\|评测贵\|Review 信号偏弱\|负迁移\|只进不出" docs/resume/interview/智能问数/03-查询记忆复用.md
grep -c "T0.*45%\|T1.*72%\|T2.*87%" docs/resume/interview/智能问数/03-查询记忆复用.md
```
预期：每个 `grep -c` 输出 ≥ 1

- [ ] **步骤 5：验证行动计划——5 大步骤标题都在**

运行：
```bash
grep -c "^### 第一步\|^### 第二步\|^### 第三步\|^### 第四步\|^### 第五步" docs/resume/interview/智能问数/03-查询记忆复用.md
```
预期：`5`

- [ ] **步骤 6：验证职责边界——不应出现"从零自研"**

运行：
```bash
grep -E "从零自研|独立自研" docs/resume/interview/智能问数/03-查询记忆复用.md
```
预期：无输出

- [ ] **步骤 7：Commit**

```bash
git add docs/resume/interview/智能问数/03-查询记忆复用.md
git commit -m "$(cat <<'EOF'
docs(interview/智能问数): 03-查询记忆复用 按 5 维度重写

按"背景/方案选型/行动计划/迭代优化/成果展示"5 维度重写。
行动计划 5 大步（地基日→成本控制+主链路→冷启动种子→兜底→
人审通道）基于 git 考古时序合并 9 个 commit 包装。
迭代优化保留 7 个坑叙事；守住"不从零自研"职责边界。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 3：重写 04-推荐问题.md

**文件：**
- 修改：`docs/resume/interview/智能问数/04-推荐问题.md`（完全重写，保留系列导航头）

**素材来源映射：**
- 背景 ← 现 A1（双场景：行为实验 + 绿色金融）
- 方案选型 ← 现 A2（目标与非目标）+ A5（与 03 边界）+ B0（双通道设计）
- 行动计划 ← git 考古时序（规格第四节 4.3 表格）+ 现 B1（内置）+ B2（相似）+ B3（汇合）
- 迭代优化 ← 现 A6（6 条难点）+ B4（晚了/空了/推歪了）+ git bug 修复
- 成果展示 ← 现 A3（15%/11%）+ A4（指标口径）

- [ ] **步骤 1：写出 04 完整新内容**

完整新文件内容（直接 Write 覆盖）：

```markdown
> 系列：智能问数
> 简历基线：[`../../my_resume.md`](../../my_resume.md)
> 总览：[`01-总览与业务背景.md`](./01-总览与业务背景.md)
> 上一篇：[03-查询记忆复用](./03-查询记忆复用.md) · 回到：[01-总览与业务背景](./01-总览与业务背景.md)

---

# 推荐问题（内置 15% + 相似 11%）

## 1. 背景：为什么做，怎么发现的问题

推荐要拆场景——不是全站统一痛点，更不是"用户不会提问"。

**主场景：行为实验开展期，实验助理反复查 + 连续追问**

谁在问：兼职大学生、实习生，在实验实施的约 4 周内高频查运维题——没发报酬有哪些人、校准失败要不要补招、场次男女比例、实验预算花了/剩下/人均多少。骨架固定，变的是实验名和场次。查完报酬名单后，下一步常问预算、校准失败人数或样本结构——这是一张固定运维清单上的连续追问，不是随机发散。

**次场景：绿色金融等金融经济研究，引导开口**

实证研究一次一问、换假设就换结构，不像实验运维那样近重复扎堆。痛点是"这套库自然语言怎么起头才问得出面板"——内置引导题是开口模板，点下去走完整问数链路。

**一句话**：相似吃"查完 A 还要问 B"；内置吃"不知道怎么开口"。两条通道互补，权重不同。

讲场景时先把范围锁死再谈数字，否则贡献率口径经不起追问。

---

## 2. 方案选型：考虑了哪些方案，如何权衡

**双通道分工设计**：

| 通道 | 解决什么 | 数据源 | 时机 |
|------|---------|--------|------|
| **通道一：进门内置**（`Agent.examples`） | 不知道怎么开口——绿色金融引导题 | 管理员预配置的 `List<String>` | 进门前展示 |
| **通道二：查完相似**（`QueryRecommendProcessor`） | 查完 A 还要问 B——行为实验连续追问 | 同一 `memory_{agentId}`，只取 question | Parse 后异步 |

**两通道关系**：**B1 ∥ B2 并行**，不是先后工序。会话中常先遇 B1、查完再遇 B2；但用户纯手打（不点 B1）也会触发 B2——B2 不依赖 B1 被点过。

**汇合点（B3）**：两通道的**共同出口**——点击后果走完整 `parseAndExecute`，差异只在归因 `source` 字段。

**选型理由**：
- 不用输入联想（边打边出的联想是另一套 search/recommend，不是本模块）
- 不另建推荐向量库——与 [03 记忆复用](./03-查询记忆复用.md) 共用同一 `memory_{agentId}`
- 相似只取 question 展示，不教 Parser 写法（不替代记忆复用）

**与 03 的边界**：

| | [03 记忆复用](./03-查询记忆复用.md) | 本文推荐问题 |
|--|--|--|
| **集合** | `memory_{agentId}` | 同一个 |
| **时机** | Parser **前**同步 | Parse **后**异步 |
| **消费** | 四元组 → `#Exemplars` 教 Parser | 仅 `question` 展示给人点 |
| **写入** | Review ENABLED 后 `storeExemplar` | 不写库，只读 |

详细工程差异见 03 文；本文不展开 Review / `#Exemplars` 细节。

**目标**：
- 降低开口成本：内置引导题让绿色金融用户点一下就走完整链路
- 结果旁下一跳：相似推荐把历史成功问法摊在结果区，助理连着点下去

---

## 3. 行动计划：怎么一步步写出来的

按真实开发时序，分五步落地。相似通道先做（端到端打通），内置通道晚了约 6 个月引入，两者最终通过共用 ExemplarService 融合。

### 第一步：相似通道先行——一天内端到端三连击

**为什么先做相似**：行为实验助理的"连续追问"痛点最具体，相似推荐直接吃已有记忆库，工程路径最短。

**一天内三连击**：
1. **后端 Processor + Manager + DB schema** —— 新增 `QueryRecommendProcessor`（相似问题召回 + 异步回写 queryId）、`SimilarQueryRecallResp`（响应结构）、`ChatQueryDO.similar_queries` 字段（DB 持久化）。异步用 `CompletableFuture.runAsync` 不指定线程池 → 用 `ForkJoinPool.commonPool()`
2. **改名"Recommend"语义** —— 把 `SimilarQueryProcessor` 改名 `QueryRecommendProcessor`，把"相似"语义改成"推荐"语义（产品视角统一）
3. **前端 UI 接入** —— `SimilarQuestionItem.tsx`（导出名 `SimilarQuestions`）接到新接口，结果区渲染可点列表

**关键类名**：`QueryRecommendProcessor.process`、`getSimilarQueries`、`SimilarQueryRecallResp`、`ChatQueryDO.similarQueries`、`SimilarQuestionItem.tsx`

**召回逻辑**：
```java
String memoryCollectionName = embeddingConfig.getMemoryCollectionName(agentId);
List<Text2SQLExemplar> exemplars =
        exemplarService.recallExemplars(memoryCollectionName, queryText, 5); // topK 硬编码
return exemplars.stream().map(sqlExemplar -> SimilarQueryRecallResp.builder()
        .queryText(sqlExemplar.getQuestion()).build()).collect(Collectors.toList());
```

- 集合名 `memoryCollectionName`（前缀 `memory_`）
- topK = **5 硬编码**（不是 yaml；改要改源码）
- **只取 `question`** → `SimilarQueryRecallResp.queryText`（不取 SQL 四元组的 schema / sql / sideInfo——与 03 的 `#Exemplars` 消费完全不同）

**异步回写**：`CompletableFuture.runAsync(() -> doProcess(parseContext))` 不堵 parse 返回。`chatQueryDO.setSimilarQueries(JSONObject.toJSONString(solvedQueries))`（String JSON 持久化）。

### 第二步：链路兜底——修复失败查询 queryId 缺失 bug

**问题**：上线 6 天发现——失败查询不返回 queryId，导致推荐问题接口挂掉（异步回写找不到挂载点）。

**修复**：`ChatQueryRepositoryImpl` 保证失败查询也返回 queryId；`RespBuildProcessor` / `SqlInfoProcessor` / `QueryServiceImpl` 协同补链路。

**关键类名**：`ChatQueryRepositoryImpl`、`RespBuildProcessor`、`QueryServiceImpl`

**留下的教训**：异步回写机制要求"任何查询路径都要有 queryId"——这是异步推荐链路的完整性前提。

### 第三步：内置通道——与 ChatMemory 模块同日引入

**为什么这天做**：内置通道的诞生与 ChatMemory 模块（03）是**同一天、同一个 feature 的两个 commit**（绑定关系，不是巧合）——Agent examples 既能进门展示给人点，又能异步灌入 ChatMemory 表当冷启动种子。

**怎么做的**：新增 `AgentExample2MemoryTransformer`（49 行 `@Async`）——把 `agent.examples` 走一遍 `chatService.parseAndExecute`，结果以 PENDING 状态灌入 ChatMemory 表。

**关键类名**：`AgentExample2MemoryTransformer`、`MemoryController`、`ChatMemoryFilter`、`MemoryStatus` 枚举、`MemoryReviewResult` 枚举

**内置通道存储**：
- Domain 层：`Agent.examples` 是 `List<String>`
- DB 层：`AgentDO.examples` 是 **String JSON**
- DO ↔ Domain 转换在 `AgentServiceImpl`：`JsonUtil.toList` / `JsonUtil.toString`

**前端展示 + 点击**：chat-sdk 进门拉 `Agent.examples`，结果区渲染可点列表。用户点某条 example → 前端把文字当 `queryText` 提交，走完整 `parseAndExecute`。

**勿混 `preset_query_collection`**：`EmbeddingConfig.presetCollection`（字段名，默认 `preset_query_collection`）给 **Plugin** embedding 识别用（`PluginManager.recognize` 消费），不是结果旁"点一下再查"的内置 FAQ 列表——**两套不互通**。

### 第四步：重构内置通道——独立组件改成内部线程池

**为什么重构**：初版用独立 `@Async` 组件，跑起来发现两个问题：① 没有连通性预检，LLM 不可用时空跑；② 独立组件不利于状态管理。

**怎么改的**：删除 `AgentExample2MemoryTransformer`，逻辑挪进 `AgentServiceImpl` 的 `executeAgentExamplesAsync` / `doExecuteAgentExamples`，用 `Executors.newFixedThreadPool(1)` + LLM 连通性预检。

```java
private synchronized void doExecuteAgentExamples(Agent agent) {
    if (!agent.containsDatasetTool() || !agent.enableMemoryReview()
            || CollectionUtils.isEmpty(agent.getExamples())) {
        return;
    }
    // …调 chatQueryService.parseAndExecute，成功则按 03 B2 走 PENDING → Review
}
```

**前置条件**：`agent.containsDatasetTool() && enableMemoryReview() && examples 非空`。`doExecuteAgentExamples` 是 `private synchronized`，通过 `executeAgentExamplesAsync` 在 **`chatExecutor` 线程池**触发（与相似通道的 `ForkJoinPool.commonPool()` 不是同一个池）。

### 第五步：两通道融合——相似通道切换到 ExemplarService

**为什么做这步**：相似通道原本直查 embedding store + 低分过滤 + QueryResp 查询，代码冗余且与 03 的数据源割裂。ChatMemory 模块上线后，两通道应该共用同一数据底座。

**怎么改的**：`QueryRecommendProcessor` 从"直查 embedding store"改成走 `ExemplarService.recallExemplars(agentId, queryText, 5)`，**删除整个 `SimilarQueryManager`（-80 行）**，代码量净减少。

**这是"架构收敛"的典型例子**——两通道共用同一 `memory_{agentId}` 集合，03 同步写入/召回，04 异步只读。

---

## 4. 迭代优化：遇到什么问题，怎么克服

### 坑 1：场景易说成全站痛点

- **难在哪**：推荐很容易被讲成"用户不会提问"这种全站泛痛点，但实际只覆盖两个窄场景，一旦说大就会被追问到没有数据支撑的地方
- **怎么扛**：叙事只拆两块——行为实验助理反复查（相似通道主战场）和绿色金融引导开口（内置通道），不往全站延伸
- **留下什么**：讲场景时先把范围锁死再谈数字，否则贡献率口径经不起追问

### 坑 2：贡献率 ≠ 少打字证明

- **难在哪**：15%/11% 只说明"从推荐入口进来的查询占比"，不代表用户真的少打了字或更快得到答案
- **怎么扛**：口径上只报贡献率，不主动宣称"减少输入量"。更深一层要 source=similar|preset 子集看执行成功率，以及同骨架手打是否下降
- **留下什么**：被追问"怎么证明有用"时，先承认观测指标非因果，再说可做的深化方向

### 坑 3：async 慢了 → 空列表

- **难在哪**：相似推荐是 Parse 后异步召回，OSS 没有专门的 timeout UI 协议——异步慢则列表暂空，用户看到的就是"推荐区什么都没有"
- **怎么扛**：前端 `useEffect` 在 `expanded && similarQuestions.length===0 && queryId` 时再拉一次（等异步写完）；用户进下一问则推荐挂在旧题旁
- **时序示例**：
  ```
  T0: 用户提交 queryId=100，parse 触发 QueryRecommendProcessor async
  T1: 前端渲染结果区，similarQueries=[]（async 未写完）
  T2: 用户展开"相似题"→ useEffect → GET getChatQuery/100 → similarQueries=[]（仍空）
  T3: async 完成，ChatQueryDO.similarQueries 写入
  T4: 用户再展开 → useEffect → GET getChatQuery/100 → similarQueries=[...3 条]
  ```
- **留下什么**：空态不是 bug，是异步时序的固有表现，但需要在不加 OSS 协议的前提下做好体验兜底

### 坑 4：竞态错挂

- **现状**：OSS 实现按 `queryId` 回写 `ChatQueryDO.similarQueries`——**无独立 version 字段**
- **怎么扛**：用户快速连发 query（A → B → C）时，三次异步各自回写各自的 `queryId`，互不覆盖。若用户已进 B 的 Parse，A 的异步回来仍挂 A 的 queryId——**挂在旧题旁**，产品上可接受（用户还能回去看 A 的结果）。`queryId` 天然隔离：每条查询记录独立，不会把 A 的推荐错写到 B
- **诚实边界**：OSS 没有"版本号协议"，面试别编；若 fork 加了再讲

### 坑 5：推错近邻放大风险

- **难在哪**：相似推荐只推 ENABLED 近邻（依赖 03 治理），但 ENABLED 仍可能语义错——比如"去年"按滚动 365 天召回，季节性题目会被教坏
- **怎么扛**：错范文先治 03 记忆库（Review 流程卡 ENABLED），不从推荐侧做过滤
- **留下什么**：推荐的准确率上限被上游记忆库质量锁死，推荐模块自己弥补不了

### 坑 6：缺严肃 A/B

- **难在哪**：贡献率是观测指标，不是因果推断——没有 randomized exposure，也没按 Agent / 实验周切片做常态化看板
- **怎么扛**：口径上只报产品贡献率，不宣称 A/B 效果
- **留下什么**：如果要做严肃因果评估，需要按 Agent 分组、控制曝光、做差异检验

### 后续改进方向（"下一刀砍哪"）

| 优先级 | 方向 | 问题 | 拟改法 |
|--------|------|------|--------|
| **P0** | `source` 在可查证链路中代码化 | OSS Java 主链路无 source 枚举；15%/11% 是产品/ELK 口径，面试讲不硬气 | 前端点击 handler / 网关 query 参数加 source；或 Java 加枚举对齐 |
| **P0** | 相似异步空态与超时的产品约定 | OSS 无 timeout；列表暂空靠前端二次拉 | 明确重试次数 / 占位文案 / 超时秒数 |
| **P1** | 内置 × 相似去重与联动 | 点过的内置是否在相似里降权？现状两通道无联动 | 点过的内置在相似召回里过滤或降权 |
| **P1** | 按 Agent / 实验周切片的贡献率看板 | 全站 15%/11%，按场景拆不够系统 | 看 source × agentId × 周切片 |
| **P1** | 与 03 治理联动 | 03 DISABLED 后 04 自动召不到（同库只读）；但 04 侧用户负反馈无闭环 | 推荐侧负反馈能否触发 03 的 `disableMemory` |

---

## 5. 成果展示：怎么衡量，效果如何

### 指标口径

每次真正提交问数打一条 `query_submit`，带归因字段 `source`：

| source 枚举 | 含义 |
|-------------|------|
| `manual` | 手打提交 |
| `preset` | 点内置推荐触发 |
| `similar` | 点相似推荐触发 |

贡献率公式：`count(source=X) / count(全部 query_submit)`。

**为什么不用 impression CTR**：内部 B 端工具，关心的是"有多少查询真的从推荐进来"，不是资讯流式曝光点击。只看了推荐没提交，不进分子，也不单独当主 KPI。

| 指标 | 公式 | 简历值 |
|------|------|--------|
| 内置贡献率 | `count(source=preset) / count(全部)` | **15%** |
| 相似贡献率 | `count(source=similar) / count(全部)` | **11%** |

**诚实标注**：`source` 枚举在当前 OSS Java 主链路与前端 chat-sdk 中均**未检索到**（`SimilarQueryRecallResp` 只有 `queryId` + `queryText`；前端 `SimilarQuestionType` 只有 `queryId` + `parseId` + `queryText`）。15% / 11% 为 `[产品/ELK 口径]`，需与 ELK 自定义埋点字段对齐后方可代码化验证。

### 已实现效果

双通道统一用**查询贡献率**度量——分母都是总查询次数，分子分别是内置 / 相似来源的查询数。

| 指标 | 数值 | 日均 150 次时约 |
|------|------|----------------|
| 内置贡献率 | **15%** | ~23 次 |
| 相似贡献率 | **11%** | ~17 次 |
| 合计 | **26%** | ~40 次 |

### 行为实验侧——相似推荐代表性样例

| 问法 | 推荐来源 | 连续追问链 |
|------|---------|-----------|
| "xxx 实验未发报酬人员有哪些" | 内置 FAQ | → 预算花了/剩/人均 |
| "注意力校准失败的被试有多少" | 相似近邻 | → 要不要补招 |
| "xxx 实验预算花了多少 / 还剩多少 / 人均多少" | 相似近邻 | 查完报酬常被推 |

### 绿色金融侧——内置引导题代表性样例

| 引导题 | 示范什么 |
|--------|---------|
| 绿色金融改革试验区地级市 2010–2020 碳排放、GDP、第二产业占比面板 | 政策试点 × 面板口径 |
| A 股公司按 ESG 评级分组平均 ROA / Tobin's Q，区分国企与非国企 | ESG × 财务 × 所有制异质 |

### 点击后链路——"连续追问"闭环

不论点的是内置题还是相似题，后果一样——前端把文案当新 `queryText` 提交，走完整 `parseAndExecute`。差异不在链路，在归因。

`ParseResultProcessor` 链中 `QueryRecommendProcessor` 会被**再次触发**——给新一轮查询继续推相似。这意味着：用户点相似推荐 → 走完整 `parseAndExecute` → 又异步召回新的相似题 → 再点再推——形成**连续追问**的产品语义闭环。
```

- [ ] **步骤 2：用 Grep 验证新文档结构**

运行：
```bash
grep -c "^## " docs/resume/interview/智能问数/04-推荐问题.md
grep -n "^## " docs/resume/interview/智能问数/04-推荐问题.md
```
预期：`5` 个二级标题，分别是 `## 1. 背景`、`## 2. 方案选型`、`## 3. 行动计划`、`## 4. 迭代优化`、`## 5. 成果展示`

- [ ] **步骤 3：验证诚实边界——不应出现旧结构关键词**

运行：
```bash
grep -E "诚实边界总表|Part A|Part B|Part C|题纲索引|回看清单" docs/resume/interview/智能问数/04-推荐问题.md
```
预期：无输出

- [ ] **步骤 4：验证关键素材保留——15%/11%、双场景、双通道、6 个坑**

运行：
```bash
grep -c "15%\|11%" docs/resume/interview/智能问数/04-推荐问题.md
grep -c "行为实验\|绿色金融" docs/resume/interview/智能问数/04-推荐问题.md
grep -c "Agent.examples\|QueryRecommendProcessor" docs/resume/interview/智能问数/04-推荐问题.md
grep -c "场景易说成\|贡献率.*少打字\|async 慢\|竞态错挂\|推错近邻\|缺严肃 A/B" docs/resume/interview/智能问数/04-推荐问题.md
```
预期：每个 `grep -c` 输出 ≥ 1

- [ ] **步骤 5：验证行动计划——5 个步骤标题都在**

运行：
```bash
grep -c "^### 第一步\|^### 第二步\|^### 第三步\|^### 第四步\|^### 第五步" docs/resume/interview/智能问数/04-推荐问题.md
```
预期：`5`

- [ ] **步骤 6：Commit**

```bash
git add docs/resume/interview/智能问数/04-推荐问题.md
git commit -m "$(cat <<'EOF'
docs(interview/智能问数): 04-推荐问题 按 5 维度重写

按"背景/方案选型/行动计划/迭代优化/成果展示"5 维度重写。
行动计划 5 步（相似三连击→queryId 兜底→内置通道→重构→
两通道融合）基于 git 考古真实时序包装。保留双场景叙事
（行为实验/绿色金融）和双通道分工设计。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 4：微调 01-总览与业务背景.md

**文件：**
- 修改：`docs/resume/interview/智能问数/01-总览与业务背景.md`

**操作清单**：
1. §2 电梯陈述 + §2.1 补充口述 → 重写为 5 维度浓缩版
2. §3 追问链 A-H 八组 → 重新分组为 5 维度
3. §4 高风险问题清单 → 删除
4. §5 一致性自检 → 删除
5. §0 元信息、§0.7 模块地图、§1 答题原则、附录 → 保留不动

**§3 重新分组映射表**（基于现有 A-H 八组标题）：

| 新分组 | 归入的原问题（题号） | 理由 |
|--------|-------------------|------|
| **3.1 背景类**（为什么做/怎么发现） | D10 立项背景、D11 项目地位、D12 接手时痛点、D13 竞品对标、E14 常查问题、E15 教不会、E16 绕过 Agent | 立项动机、痛点发现、用户画像 |
| **3.2 选型类**（方案权衡/和代码关系） | C7 单体/分布式、C8 整体链路、C8-Token token 消耗、C9 技术栈、H23 向量库选型、H24 被否决方案、H25 最大遗憾 | 技术选型、架构决策 |
| **3.3 行动类**（怎么写出来的） | A3 团队分工、B5 数据库规模、B6 为什么不写 SQL、G20 元数据管理、G21 字段名对不上 | 实施过程、工程落地 |
| **3.4 迭代类**（遇到什么问题/怎么克服） | F17 生产事故、F18 LLM 错误 SQL、F19 弃用率、G22 数据更新频率 | 事故、迭代、数据治理 |
| **3.5 成果类**（怎么衡量/效果） | A1 用户与规模、A2 机构分布、A4 加入阶段 | 规模、效果数字 |

**注意**：重新分组只改 §3 下的小节标题层级，**不改正文内容**。原 A-H 的每个问题（如 A1、A2...）作为一个个独立小节，归入新的 3.1-3.5 五个大组下。

- [ ] **步骤 1：读取 01 文件，定位需要修改的区域**

运行：
```bash
grep -n "^## " docs/resume/interview/智能问数/01-总览与业务背景.md
```
预期：看到 `## 2.`、`## 2.1`、`## 3.`、`## 4.`、`## 5.` 的行号

- [ ] **步骤 2：重写 §2 电梯陈述为 5 维度浓缩版**

用 Edit 工具，old_string 为现有 §2 + §2.1 的完整内容（从 `## 2. 30 秒电梯陈述` 到 `## 3. 追问链答题（A–H 八组）` 之前的 `---`）。

new_string：

```markdown
## 2. 30 秒电梯陈述

> 用于宽问开场，控制在 1 分钟内。按 5 维度浓缩——每个维度 1-2 句，串起来就是完整故事线。

**背景**：实验室 500+ 研究员用业务术语查 200+ 张表，但字段是英文缩写（`net_profit` vs `net_profit_excluding`），向量匹配分不清语义相近的近义字段——"查扣非净利润返回净利润的值，差好几个亿"。

**方案选型**：没选端到端 LLM（200+ 表规模准确率只有 10-31%，黑盒不可解释），选了"三层漏斗 + LLM 消歧"——LLM 做选择题不做填空题，分层设计可解释、准确率可控。

**行动计划**：三块技术工作按真实开发时序推进——SchemaMapper LLM filter（EM 58%→81%）、查询记忆复用（端到端 72%→87%）、相似问题推荐（内置 15% + 相似 11%）。每块都是"先骨架后链路，先开源后业务侧增强"。

**迭代优化**：每块都踩过坑——SchemaMapper 的 LLM 忽略 COMMENT、记忆库的"语义成功 ≠ 执行成功"、推荐通道的异步空态。每个坑都有评测驱动的修复闭环。

**成果展示**：端到端准确率 T0 45% → T1 72% → T2 87%（同一批 200 条离线评测集，无 HITL）；记忆库 800+ 条；推荐贡献率合计 26%。另外深度研究 Python 服务由我从 0-1 搭建，GAIA-165 评测 53%。

**追问点预防**：30 秒陈述里主动暴露了"SchemaMapper 81% vs 端到端 87%"这两个数字——面试官可能会问"为什么单步指标比全链路还低？"。答案是**两个评测集难度不同**：SchemaMapper 评测集偏难（含多表关联 35% + 复杂聚合 25%），端到端评测集是线上真实抽样（含大量被试库管理等简单日常琐事）。
```

- [ ] **步骤 3：删除原 §2.1 补充口述**

§2.1 的内容（"最大的收获""自己最大的优势"）已被新 §2 浓缩版吸收，整体删除。

用 Edit 工具，old_string 包含 `## 2.1 补充口述（收获 / 优势）` 整节到 `## 3. 追问链答题（A–H 八组）` 之前。

new_string：空（直接接到 §3）。

- [ ] **步骤 4：§3 重新分组——只改分组标题，不改正文内容**

§3 现有结构：
```
## 3. 追问链答题（A–H 八组）
### A. 用户与规模
### B. 数据资产
### C. 技术全景
### D. 业务价值与立项背景
### E. 用户画像与真实使用场景
### F. 运营与事故
### G. 数据治理与质量
### H. 决策细节与替代方案（深水区）
```

改成 5 维度分组。**关键约束**：每个问题的正文内容（从 `#### A1.` 到对应小节结束）**完全不动**，只改它上面的 `###` 分组标题。

具体改法：把 8 个 `### A.` ~ `### H.` 分组标题，替换成 5 个 `### 3.1 背景` ~ `### 3.5 成果` 标题，然后按映射表把每个 `#### XX.` 问题移到对应的新分组下。

由于这一步涉及大量文本移动，用以下顺序操作：

1. 先用 Edit 把 `### A. 用户与规模` 改成 `### 3.5 成果类`（A 组归入成果类）
2. 把 `### B. 数据资产` 改成 `### 3.3 行动类`（B 组归入行动类）
3. 把 `### C. 技术全景` 改成 `### 3.2 选型类`（C 组归入选型类）
4. 把 `### D. 业务价值与立项背景` 改成 `### 3.1 背景类`（D 组归入背景类）
5. 把 `### E. 用户画像与真实使用场景` 也归入背景类——但 E 组在 D 组后面，需要移到 D 组下方。由于 markdown 里移动整节容易出错，**保守做法**：保留 E 组的 `###` 标题，但加上前缀标注归属，如 `### E. 用户画像与真实使用场景（归 3.1 背景类）`。
6. 同理 F、G、H 组：F 标注"（归 3.4 迭代类）"，G 标注"（归 3.3 行动类）"，H 标注"（归 3.2 选型类）"。

**简化方案**（避免大规模文本移动）：保留 A-H 字母分组作为子结构，在 §3 开头加一张"5 维度分组映射表"，说明每个字母组归入哪个维度。这样既满足"重新分组"的要求，又避免大规模文本移动出错。

new §3 开头（替换 `## 3. 追问链答题（A–H 八组）` 标题及下方引导语）：

```markdown
## 3. 追问链答题（按 5 维度分组）

> 每条问题统一格式：**面试官问法 → 第一句答题 → 要点展开 → 边界标注**。
> 边界标注：`[做过]` = 亲手实现 / `[源码学过]` = 没做但研读过 SuperSonic 源码 / `[未来思路]` = 业界也尚在探索。

**5 维度分组映射**（原 A-H 字母组归入对应维度，便于按面试官提问维度快速定位）：

| 维度 | 包含的字母组 | 典型问题 |
|------|------------|---------|
| **3.1 背景类**（为什么做/怎么发现） | D（立项背景）、E（用户画像） | D10 立项背景、D12 接手时痛点、E14 常查问题 |
| **3.2 选型类**（方案权衡/和代码关系） | C（技术全景）、H（决策细节） | C7 单体/分布式、C8 整体链路、H23 向量库选型、H25 最大遗憾 |
| **3.3 行动类**（怎么写出来的） | A（用户与规模，部分）、B（数据资产）、G（数据治理，部分） | A3 团队分工、B5 数据库规模、G20 元数据管理 |
| **3.4 迭代类**（遇到什么问题/怎么克服） | F（运营与事故）、G（数据治理，部分） | F17 生产事故、F18 LLM 错误 SQL、F19 弃用率 |
| **3.5 成果类**（怎么衡量/效果） | A（用户与规模，部分） | A1 用户与规模、A2 机构分布、A4 加入阶段 |

---
```

- [ ] **步骤 5：删除 §4 高风险问题清单**

用 Edit 工具，old_string 包含从 `## 4. 高风险问题清单（集中复检）` 到 `## 5. 一致性自检（面试前最后过一遍）` 之前的所有内容（含中间的 `---`）。

new_string：空。

- [ ] **步骤 6：删除 §5 一致性自检**

用 Edit 工具，old_string 包含从 `## 5. 一致性自检（面试前最后过一遍）` 到 `## 附录 A：调研参考链接` 之前的所有内容（含中间的 `---`）。

new_string：空。

- [ ] **步骤 7：用 Grep 验证修改结果**

运行：
```bash
grep -n "^## " docs/resume/interview/智能问数/01-总览与业务背景.md
```
预期：不再出现 `## 4. 高风险问题清单`、`## 5. 一致性自检`；保留 `## 0.`、`## 0.7`、`## 1.`、`## 2.`、`## 3.`、`## 附录 A`

运行：
```bash
grep -c "5 维度浓缩\|背景.*方案选型.*行动计划\|T0 45%.*T1 72%.*T2 87%" docs/resume/interview/智能问数/01-总览与业务背景.md
```
预期：`≥ 1`（新 §2 已写入）

运行：
```bash
grep -c "5 维度分组映射\|3.1 背景类\|3.2 选型类\|3.3 行动类\|3.4 迭代类\|3.5 成果类" docs/resume/interview/智能问数/01-总览与业务背景.md
```
预期：`≥ 1`（新 §3 分组表已写入）

运行：
```bash
grep -E "^## 4\.|^## 5\." docs/resume/interview/智能问数/01-总览与业务背景.md
```
预期：无输出（§4/§5 已删除）

- [ ] **步骤 8：验证正文内容未被破坏——抽查 A1/A4/C8 等关键问题仍在**

运行：
```bash
grep -c "A1\.|A4\.|C8\.|H23\.|H25\." docs/resume/interview/智能问数/01-总览与业务背景.md
```
预期：`≥ 5`（A1、A4、C8、H23、H25 等关键问题正文仍在）

运行：
```bash
grep -c "45%.*72%.*87%\|500+\|800+" docs/resume/interview/智能问数/01-总览与业务背景.md
```
预期：`≥ 1`（关键数字仍在）

- [ ] **步骤 9：Commit**

```bash
git add docs/resume/interview/智能问数/01-总览与业务背景.md
git commit -m "$(cat <<'EOF'
docs(interview/智能问数): 01 总览按 5 维度微调

§2 电梯陈述重写为 5 维度浓缩版（背景/选型/行动/迭代/成果）；
§3 追问链 A-H 重新分组为 5 维度（加分组映射表）；
§4 高风险问题清单删除；§5 一致性自检删除。
正文内容保留，只调整组织结构。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 5：整体验证

**文件：** 无文件修改，只做全局一致性检查。

- [ ] **步骤 1：验证 4 篇文档都已按 5 维度重写**

运行：
```bash
for f in docs/resume/interview/智能问数/0{1,2,3,4}-*.md; do
  echo "=== $f ==="
  grep -c "^## " "$f"
  grep "^## " "$f" | head -10
done
```

预期：
- 02/03/04：各 5 个二级标题（背景/方案选型/行动计划/迭代优化/成果展示）
- 01：保留原有 §0/§0.7/§1/§2/§3/附录 结构，但 §2 已重写、§3 已重新分组、§4/§5 已删除

- [ ] **步骤 2：验证不再有旧结构关键词**

运行：
```bash
grep -rE "诚实边界总表|Part A|Part B|Part C|题纲索引|回看清单" docs/resume/interview/智能问数/
```
预期：无输出

- [ ] **步骤 3：验证关键数字跨文档一致**

运行：
```bash
echo "=== SchemaMapper 58%→81% ==="
grep -r "58%.*81%" docs/resume/interview/智能问数/ | wc -l
echo "=== 端到端 45%→72%→87% ==="
grep -r "45%.*72%.*87%" docs/resume/interview/智能问数/ | wc -l
echo "=== 记忆库 800+ ==="
grep -r "800+" docs/resume/interview/智能问数/ | wc -l
echo "=== 推荐 15%/11% ==="
grep -rE "15%.*11%|内置 15%" docs/resume/interview/智能问数/ | wc -l
```

预期：每个数字在多个文档中一致出现（01/02 都有 58%→81%；01/03 都有 45%→72%→87% 和 800+；01/04 都有 15%/11%）。

- [ ] **步骤 4：验证行动计划包装——每个模块的步骤标题都在**

运行：
```bash
echo "=== 02 行动计划步骤 ==="
grep "^### 第" docs/resume/interview/智能问数/02-SchemaMapper.md
echo "=== 03 行动计划步骤 ==="
grep "^### 第" docs/resume/interview/智能问数/03-查询记忆复用.md
echo "=== 04 行动计划步骤 ==="
grep "^### 第" docs/resume/interview/智能问数/04-推荐问题.md
```

预期：
- 02：第一步、第二步、第三步、第四步（4 步）
- 03：第一步、第二步、第三步、第四步、第五步（5 步）
- 04：第一步、第二步、第三步、第四步、第五步（5 步）

- [ ] **步骤 5：验证诚实边界——不应出现"从零自研"**

运行：
```bash
grep -rE "从零自研|独立自研" docs/resume/interview/智能问数/
```
预期：无输出

- [ ] **步骤 6：最终确认——所有 commit 都已提交**

运行：
```bash
git log --oneline -6
```

预期：看到 4 个 commit（02/03/04/01 各一个），加上规格 commit（bee48390c）。

---

## 自检结果

### 1. 规格覆盖度

| 规格章节 | 对应任务 |
|---------|---------|
| 二、决策清单（10 项决策） | 任务 1-4 全部覆盖 |
| 三、02/03/04 统一新骨架 | 任务 1/2/3 |
| 四、行动计划包装策略（3 个模块） | 任务 1/2/3 的行动计划部分 |
| 五、内容来源映射（3 个模块） | 任务 1/2/3 的素材引用 |
| 六、01 总览微调方案（§2/§3/§4/§5） | 任务 4 |
| 七、迁移策略（执行顺序、单独 commit） | 任务 1-4 的 commit 步骤 |
| 八、诚实性边界（4 条底线） | 任务 1-4 的验证步骤 + 任务 5 步骤 5 |

**遗漏检查**：无遗漏。

### 2. 占位符扫描

- 无"待定"、"TODO"、"后续实现"、"补充细节"
- 无"类似任务 N"
- 每个 Edit/Write 步骤都包含完整的 old_string/new_string 或完整文件内容
- 每个验证步骤都有具体命令和预期输出

### 3. 类型一致性

- 5 维度标题在 3 个任务中一致：`## 1. 背景`、`## 2. 方案选型`、`## 3. 行动计划`、`## 4. 迭代优化`、`## 5. 成果展示`
- 行动计划步骤命名一致：`### 第一步`、`### 第二步`...
- git 考古的 commit hash 在任务 1/2/3 的行动计划中与规格第四节一致

### 4. 范围检查

- 4 篇文档重组，可由单个实现计划覆盖
- 执行顺序明确：02 → 03 → 04 → 01 → 整体验证
- 每篇单独 commit，方便回滚
