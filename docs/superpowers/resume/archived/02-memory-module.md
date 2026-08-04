# Memory 记忆管理模块 — 简历文案 + 面试预案

## 简历文案（终版）

> 设计并实现 Chat-BI 记忆管理模块，支持历史 SQL/查询结果自动注入 LLM 提示词以提升语义解析准确率；引入 LLM 定期自动评审 + 管理员人工评审双机制，实现记忆库的持续质量管控

---

## ① 30秒概括

Memory 记忆管理模块解决的是 LLM 生成 SQL "记不住历史经验"的问题。

用户每次通过 LLM 成功查询后，系统自动将「问题+SQL」沉淀为一条 PENDING 记忆；经 LLM 自动评审通过后写入 pgvector 向量库。后续用户提问时，系统通过语义相似检索找到最相关的历史记忆（粗召回 10 条 → 精选 3 条），以 few-shot 形式注入 LLM prompt，让模型"抄历史作业"。

完整的闭环是：查询 → 沉淀 → 评审 → 向量化 → 召回 → 增强下次查询。

效果上，CSMAR 星型模型的 Text2SQL 准确率从 82%（冷启动）提升到 91%（30 条记忆后），提升了 9 个百分点。

---

## ② 背景与动机

### 场景设定

你在 SuperSonic 里为「高管机会主义减持识别」课题建了一套 CSMAR 星型模型：

```
事实表: v_executive_reduction  减持事件宽表（事前事后已展开到行内）
  ├─ 事前语音: avg_valence, vdq_score（减持前最近一次业绩说明会）
  ├─ 事件本身: ReductionDate, ReductionRatio, ReductionAmount, Stkcd
  └─ 事后评价: CAR_5d, CAR_20d, Opp_Sell（CAR_5d<0 → 1）

维度表: v_executive_profile  高管信息
  └─ PersonID, 姓名, 教育背景, 性别, 职务类别

维度表: v_firm_controls  公司控制变量
  └─ Stkcd, 行业, 企业规模, 股权集中度
```

### 问题 1：LLM 不知道"什么叫正面"

你对系统说："找出业绩说明会上说话正面（avg_valence > 0.5）、但后来减持了、股价还跌了的高管"。

LLM 看到 `avg_valence` 只知道这是一个小数，不知道多少算"正面"。你说的 0.5 是你研究里定的阈值。如果你之前问过"统计 avg_valence > 0.5 的减持事件里 Opp_Sell=1 的比例"，那条查询+正确 SQL 被存成了记忆。下次 LLM 再接类似问题时，系统自动把那条记忆塞进 prompt，LLM 一看：原来 > 0.5 就算正面、Opp_Sell 是按比例算的、CAR 用的是 5 天窗口。

类比：就像新同事不会用你的内部系统，但你把之前的工单给他看一遍，他就能照猫画虎。

### 问题 2：反范式设计引入了冗余，LLM 不知道这回事

你的事实表是**反范式的**。业绩说明会的语音特征（avg_valence, vdq_score）没有放在独立的维度表里，而是直接展开到了每一行减持事件中。这样设计的好处是查询快——不用每次都去 JOIN。

但 LLM 不知道这个设计意图。它拿着 dbSchema，看到事实表里有"减持前业绩说明会"数据，再看到项目里可能还有一张业绩说明会表——它很可能自作主张去 JOIN，写出多余子查询。更有害的是：万一 JOIN 条件写错了，结果直接废掉。

→ 记忆模块在这里的作用是告诉 LLM：**在这套表上，别 JOIN，直接用字段。** 这个知识没法写在 dbSchema 里，但可以通过 few-shot 范例传递：之前成功跑过的查询，全都直接用 `avg_valence`、`CAR_5d`，从不 JOIN 业绩说明会表。LLM 照猫画虎，自然就不画蛇添足。

### 问题 3：不是所有历史查询都配当范例

你在 Agent 下跑过大量试探性查询——"试试按性别分组"、"换个窗口看 CAR_10d"、"加个交互项看看"。这些 SQL 很多是随手写的，聚合方式可能不严谨。全部塞给 LLM，反而会带偏它。

所以需要一道评审门槛：SQL 被 LLM 或你自己确认过"没问题"之后，才进入记忆库供后续召回。

---

## ③ 架构全景

```
                         ┌──────────────────────────┐
                         │     Chat-BI 对话入口       │
                         │   NL2SQLParser.parse()    │
                         │                          │
                         │  ① 用户提问               │
                         │  ② addDynamicExemplars()  │──→ ExemplarService.recallExemplars()
                         │  ③ 记忆作为 few-shot      │         │
                         │     注入 LLM prompt       │         │
                         │  ④ LLM 生成 S2SQL         │         ▼
                         └──────────┬───────────────┘    ┌──────────────────────┐
                                    │                    │    pgvector          │
                                    │ 查询成功             │ memory_collection_   │
                                    ▼                    │     {agentId}        │
                         ┌──────────────────────┐        │                      │
                         │   createMemory()     │        │ Text2SQLExemplar:    │
                         │   status = PENDING    │        │  question + s2sql   │
                         └──────────┬───────────┘        │  + dbSchema +        │
                                    │                    │  sideInfo            │
                                    ▼                    └──────▲──────┬────────┘
                    ┌──────────────────────────────┐            │      │
                    │      s2_chat_memory 表        │   store/   │      │ recall
                    │  (MySQL/PostgreSQL 关系存储)   │   remove   │      │ (ANN)
                    │                              │            │      │
                    │  id, agentId, question,       │            │      │
                    │  s2sql, dbSchema, sideInfo,   │            │      │
                    │  status (PENDING/ENABLED/     │            │      │
                    │          DISABLED),           │            │      │
                    │  llmReviewRet, llmReviewCmt,  │            │      │
                    │  humanReviewRet, humanReviewCmt│           │      │
                    └──▲────────────┬───────────────┘            │      │
                       │            │                            │      │
        人工评审         │            │ LLM 自动评审                │      │
    ┌──────────────┐    │            │                            │      │
    │MemoryController│    │    ┌───────┴──────────────┐            │      │
    │              │    │    │  MemoryReviewTask     │            │      │
    │POST update-  │────┘    │  @Scheduled 60s      │            │      │
    │  Memory      │         │                      │            │      │
    │POST page-    │         │  ① 遍历所有 Agent     │            │      │
    │  Memories    │         │  ② 拉 PENDING 记忆    │            │      │
    │POST batch-   │         │  ③ 拼 prompt → LLM   │            │      │
    │  Delete      │         │  ④ POSITIVE →        │────────────┘      │
    └──────────────┘         │     enableMemory()                       │
                             │  ⑤ NEGATIVE →        │                  │
                             │     保持 PENDING      │                  │
                             └──────────────────────┘                  │
                                                                       │
         ┌─────────────────────────────────────────────────────────────┘
         │  启动加载
         ▼
  MemoryServiceImpl.run()
  loadSysExemplars()
  遍历所有 ENABLED 记忆 → storeExemplar() → pgvector
```

**四条数据流**：

| 线路 | 路径 | 触发 |
|------|------|------|
| **写入线** | 查询成功 → `createMemory`(PENDING) → `MemoryReviewTask` → LLM评审 → POSITIVE → `enableMemory` → 写 pgvector | 每次成功查询 / 每 60s |
| **人工线** | 管理后台 → `POST /api/chat/memory/updateMemory` → `updateMemory` → ENABLED/DISABLED → 同步 pgvector | 管理员操作 |
| **读取线** | 用户提问 → `addDynamicExemplars` → `recallExemplars`(ANN 粗召回 10) → `PromptHelper`(精选 3) → few-shot 注入 prompt | 每次查询 |
| **恢复线** | 服务启动 → `CommandLineRunner.run()` → `loadSysExemplars` → 全量重载 ENABLED 记忆 → pgvector | 服务重启 |

**组件职责**：

| 组件 | 文件 | 一句话 |
|------|------|--------|
| `MemoryServiceImpl` | `chat/server/.../impl/` | 核心：CRUD + 状态机 + 向量库同步 + 启动加载 |
| `MemoryReviewTask` | `chat/server/.../memory/` | 定时任务：每 60s 拉待评审记忆 → LLM 打分 → 自动启用/搁置 |
| `MemoryController` | `chat/server/.../rest/` | REST 接口：create / update / page / batchDelete |
| `ExemplarService` | `common/.../service/` | 向量抽象：store / remove / recall，底层是 pgvector |
| `ChatMemoryDO` | `.../dataobject/` | MyBatis-Plus 实体，映射 `s2_chat_memory` 表 |
| `NL2SQLParser` | `chat/server/.../parser/` | 查询入口：调用 `addDynamicExemplars()` 注入记忆到 prompt |
| `Agent` | `chat/server/.../agent/` | 配置：`enableMemoryReview()` 控制该 Agent 是否开启自动评审 |
| `SqlExecutor` | `chat/server/.../executor/` | 查询成功后自动调 `createMemory` 沉淀记忆 |
| `PromptHelper` | `headless/chat/.../llm/` | 从 10 条粗召回中精选 3 条 + 格式化注入 prompt |
| `OnePassSCSqlGenStrategy` | `headless/chat/.../llm/` | SQL 生成策略：拼 prompt → 调 LLM → self-consistency 投票 |

---

## ④ 面试追问 Q&A

### Q1：介绍一下记忆管理的整体机制？

**一句话**：查询成功 → 自动沉淀 → LLM 评审 → 写入向量库 → 粗召回 10 条 → 精选 3 条 → 注入 prompt。

**阶段一：自动沉淀 — 什么时候创建记忆？**

不是手动点的。`SqlExecutor` 执行完 SQL 后自动判断，两个条件缺一不可：

```java
// SqlExecutor.execute() — 查询成功后自动触发
if (queryResult.getQueryState().equals(QueryState.SUCCESS)    // ① SQL 跑通了
        && queryResult.getQueryMode().equals(LLMSqlQuery.QUERY_MODE)) {  // ② LLM 生成的
    // 从 ParseInfo.properties 取出 exemplar（LLMResponseService 放的）
    Text2SQLExemplar exemplar = JsonUtil.toObject(
        JsonUtil.toString(executeContext.getParseInfo().getProperties()
                .get(Text2SQLExemplar.PROPERTY_KEY)),
        Text2SQLExemplar.class);

    memoryService.createMemory(ChatMemory.builder()
            .agentId(agent.getId())
            .status(MemoryStatus.PENDING)   // 待评审
            .question(exemplar.getQuestion())
            .s2sql(exemplar.getSql())
            .dbSchema(exemplar.getDbSchema())
            .build());
}
```

存入 `s2_chat_memory` 表，status = PENDING，此时还不能被召回。

**阶段二：LLM 自动评审**

`MemoryReviewTask` 每 60 秒扫一遍所有 Agent，拉出未评审的 PENDING 记忆：

```java
@Scheduled(fixedDelay = 60 * 1000)
public void review() {
    for (Agent agent : agentService.getAgents()) {
        if (!agent.enableMemoryReview()) continue;
        memoryService.getMemories(agent.getId()).forEach(memory -> {
            if (memory.getLlmReviewRet() != null
                    || memory.getHumanReviewRet() != null)
                return;  // 评过了，跳过
            processMemory(memory, agent);
        });
    }
}
```

评审 prompt 长这样：

```
#Role: You are a senior data engineer experienced in writing SQL.
#Task: You will be provided with a user question and the SQL written by
a junior engineer, please take a review and give your opinion.
#Rules:
1.ALWAYS follow the output format: opinion=(POSITIVE|NEGATIVE),comment=(your comment).
2.NO NEED to check date filters as the junior engineer seldom makes mistakes.
#Question: 统计 avg_valence > 0.5 的减持事件里 Opp_Sell=1 的占比
#Schema: DatabaseType=[postgresql], Table=[v_executive_reduction],
  Metrics=[<Opp_Sell>], Dimensions=[<行业>...]
#SideInfo: CurrentDate=[2026-07-15]
#SQL: SELECT 行业, SUM(Opp_Sell)*1.0/COUNT(*) AS 机会主义占比
       FROM v_executive_reduction WHERE avg_valence > 0.5 GROUP BY 行业
#Response:
```

LLM 返回 → 正则解析 `opinion=(.*),.*comment=(.*)`：
- POSITIVE → `enableMemory()` → status 改 ENABLED，写 pgvector
- NEGATIVE → 保持 PENDING，等人工介入

**阶段三：向量化存储 + 启动恢复**

```java
// MemoryServiceImpl.enableMemory()
public void enableMemory(ChatMemoryDO memory) {
    memory.setStatus(MemoryStatus.ENABLED.toString());
    exemplarService.storeExemplar(
        embeddingConfig.getMemoryCollectionName(memory.getAgentId()),  // "memory_7"
        Text2SQLExemplar.builder()
            .question(memory.getQuestion())
            .sql(memory.getS2sql())
            .dbSchema(memory.getDbSchema())
            .sideInfo(memory.getSideInfo()).build());
}
```

集合名是 `memory_{agentId}`，每个 Agent 的记忆物理隔离。启动时 `loadSysExemplars()` 全量重载所有 ENABLED 记忆到 pgvector，防止向量容器重启后丢失。

**阶段四：召回（两步筛选）**

用户提问时，先粗召回再精选：

**第 1 步 — 向量粗召回 10 条**：

`NL2SQLParser.addDynamicExemplars()` 把用户问题向量化 → pgvector ANN 检索 `memory_collection_{agentId}` → 返回相似度 TOP 10（默认值，配置项 `s2.parser.exemplar-recall.number`）。如果 memory 库不够 10 条，差的从系统预设的 `preset_query_collection` 补齐。

**第 2 步 — PromptHelper 精选 3 条**：

从 10 条中选最终注入的 3 条（默认值，配置项 `s2.parser.few-shot.number`）：

```java
// PromptHelper.getFewShotExemplars() — 精选算法
same = exemplars.filter(similarity > 0.989)   // ① 几乎一样的，必须保留
noSame = exemplars.filter(similarity ≤ 0.989) // ② 不一样的

// noSame 处理：
noSame.sort(Comparator.comparingDouble(Text2SQLExemplar::getSimilarity));  // 升序
noSame = noSame.subList((noSame.size() - fewShotNumber) / 2, noSame.size()); // 截尾
Text2SQLExemplar mostSimilar = noSame.get(noSame.size() - 1);  // 记下最相似的
Collections.shuffle(noSame);  // 随机打乱（self-consistency 每轮不同组合）
ts = noSame.subList(0, Math.min(noSame.size(), fewShotNumber));
if (!ts.contains(mostSimilar)) {  // 最相似保底
    ts.remove(ts.size() - 1);
    ts.add(mostSimilar);
}
```

不是单纯取 top 3——升序截尾 → 随机打乱 → 取前 N → 最相似保底。打乱是为了 self-consistency 时每轮推理拿到不同的 exemplar 组合，但最相似那条一定在。

**阶段五：注入 prompt**

最终选的 3 条格式化为：

```
#Exemplars:
Question:统计 avg_valence > 0.5 的减持中 Opp_Sell=1 占比,Schema:...,SQL:SELECT ...
Question:按行业分组看 vdq_score 最低 20% 的 CAR_5d 均值,Schema:...,SQL:SELECT ...
Question:查询减持后 CAR_5d < -3% 且教育背景=博士研究生的高管,Schema:...,SQL:SELECT ...
```

拼入 LLM 的 SQL 生成 prompt（`OnePassSCSqlGenStrategy`）：

```
#Role: You are a data analyst experienced in SQL languages.
#Task: ...convert natural language to SQL...
#Rules: ...
#Exemplars:        ← 上面回忆的 3 条
Question:...Schema:...SQL:...
Question:...Schema:...SQL:...
Question:...Schema:...SQL:...
#Query: Question:{用户当前问题},Schema:{当前 dbSchema},SideInfo:{...}
```

**完整链路**：

```
查询成功 → createMemory(PENDING)
  → [60s] MemoryReviewTask → LLM 评审
    prompt: 角色=资深数据工程师, 输入=question+schema+SQL
    正则解析 → POSITIVE → ENABLED → pgvector
             → NEGATIVE → 等人工

下次查询 → 向量化 → pgvector ANN 粗召回 10 条
  → PromptHelper 精选 3 条（same>0.989 优先 + 最相似保底）
  → 拼成 Question:...SQL:... 注入 #Exemplars
  → LLM 参照 few-shot 生成 SQL
```

---

### Q2：数据库表和接口是怎么设计的？

**先看一条真实数据**。假设你在 CSMAR Agent 下跑了一条查询：

> "统计 avg_valence > 0.5 的减持事件里 Opp_Sell=1 的占比，按行业分组"

SQL 执行成功后，`SqlExecutor` 自动创建了这条记忆：

```
┌─────────────────────────────────────────────────────────────────────┐
│ s2_chat_memory 表中的一行                                           │
├────────────┬────────────────────────────────────────────────────────┤
│ id         │ 142                                                    │
│ agent_id   │ 7  (CSMAR数据分析助手)                                   │
│ query_id   │ 2083  (关联的那次问答)                                   │
│ question   │ 统计 avg_valence > 0.5 的减持事件里 Opp_Sell=1 的占比，  │
│            │ 按行业分组                                              │
│ db_schema  │ DatabaseType=[postgresql],Table=[v_executive_reduction],│
│            │ Metrics=[<Opp_Sell COMMENT '机会主义减持标识'>],         │
│            │ Dimensions=[<行业 COMMENT '公司所属行业'>...]             │
│ side_info  │ CurrentDate=[2026-07-15]                                │
│ s2_sql     │ SELECT 行业, SUM(CAST(Opp_Sell AS FLOAT))/COUNT(*)      │
│            │ AS 机会主义减持比例                                      │
│            │ FROM v_executive_reduction                              │
│            │ WHERE avg_valence > 0.5 GROUP BY 行业                   │
│ status     │ ENABLED  ← 已经 LLM 评审通过                            │
│ llm_review │ POSITIVE                                                │
│ llm_comment│ SQL语法正确，聚合逻辑合理，字段使用符合Schema定义          │
│ human_review│ null  ← 人工还没看过，LLM 已通过所以直接启用了           │
│ human_comment│ null                                                   │
│ created_at │ 2026-07-15 14:32:10                                     │
│ created_by │ admin2                                                  │
└────────────┴────────────────────────────────────────────────────────┘
```

逐列解释：
- `db_schema`：**创建时的 Schema 快照**。冻结了当时表的字段名、指标、维度。即使后来表结构变了，这条记忆仍按创建时的 Schema 来匹配，不会因 Schema 漂移导致检索失败。这也避免了召回时反查当前 Schema 的环境不一致问题。
- `side_info`：**辅助上下文**。存储查询时的时间、预设知识、术语定义等。评审和召回时都会用到——比如 LLM 评审时知道"当前日期是 2026-07-15"，就能判断 SQL 里的日期筛选是否合理。
- `s2_sql`：**核心资产**。这是经过 `SemanticCorrector` 修正后的最终 SQL，不是 LLM 的原始输出。确保存进向量库的是可执行的正确 SQL。

**DDL**：

```sql
CREATE TABLE s2_chat_memory (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    question     VARCHAR(655)   COMMENT '用户问题',
    side_info    TEXT           COMMENT '辅助信息',
    query_id     BIGINT         COMMENT '关联的问答ID',
    agent_id     INT            COMMENT '所属Agent',
    db_schema    TEXT           COMMENT 'Schema映射（当时查询的字段元数据）',
    s2_sql       TEXT           COMMENT 'LLM生成的语义SQL',
    status       VARCHAR(10)    COMMENT 'PENDING / ENABLED / DISABLED',
    llm_review   VARCHAR(10)    COMMENT 'LLM评审结果 POSITIVE / NEGATIVE',
    llm_comment  TEXT           COMMENT 'LLM评审意见',
    human_review VARCHAR(10)    COMMENT '人工评审结果 POSITIVE / NEGATIVE',
    human_comment TEXT          COMMENT '人工评审意见',
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by   VARCHAR(100),
    updated_by   VARCHAR(100)
);
```

**设计要点**：

1. **评审双通道**：`llm_review` 和 `human_review` 是两个独立字段。流程上 LLM 先评、人工兜底，互不覆盖。`MemoryReviewTask` 只处理两者都为 null 的记录——评过就不再碰。

2. **question 是业务主键**：去重按 `(agentId, question, status=ENABLED)` 判断——同一 Agent 下相同问题只保留一条启用记忆。

**状态机（决策树）**：

```
记忆创建后 status = PENDING
│
├─→ MemoryReviewTask (60s) 判断：
│   llmReviewRet 和 humanReviewRet 都为 null？
│   │
│   ├─ 是 → 调 LLM 评审
│   │   │
│   │   ├─ LLM 返回 POSITIVE
│   │   │   → status = ENABLED
│   │   │   → llmReviewRet = POSITIVE
│   │   │   → 写 pgvector
│   │   │   → [终态] 可被召回
│   │   │
│   │   └─ LLM 返回 NEGATIVE
│   │       → status 不变 (仍 PENDING)
│   │       → llmReviewRet = NEGATIVE
│   │       → 不写 pgvector
│   │       → [等待] 人工介入
│   │
│   └─ 否 → 跳过（已被评过）
│
├─→ 人工通过 POST /updateMemory 评审：
│   humanReviewRet = ?
│   │
│   ├─ POSITIVE → status = ENABLED → 写 pgvector → [终态]
│   │
│   └─ NEGATIVE
│       │
│       ├─ 当前是 ENABLED → status = DISABLED → 从 pgvector 移除 → [终态]
│       │
│       └─ 当前是 PENDING → status = DISABLED → [终态]
│
└─→ [终态] ENABLED 或 DISABLED 都不能再回到 PENDING
```

关键：
- **LLM 评审 NEGATIVE 不会禁用**，只是搁置等人看——LLM 可能误判
- **人工评审 NEGATIVE 直接禁用**——人说了算
- **ENABLED 后只有人工能降级到 DISABLED**

**REST API 设计**：4 个端点

| 端点 | 功能 | 关键入参 |
|------|------|---------|
| `POST /api/chat/memory/createMemory` | 创建记忆 | agentId, question, s2sql, dbSchema, status |
| `POST /api/chat/memory/updateMemory` | 更新评审结果/状态/SQL（核心接口） | id, status, llmReviewRet, humanReviewRet, s2sql, dbSchema |
| `POST /api/chat/memory/pageMemories` | 分页查询 | current, pageSize, chatMemoryFilter |
| `POST /api/chat/memory/batchDelete` | 批量删除 | ids[], agentId |

```java
@RestController
@RequestMapping("/api/chat/memory")
public class MemoryController {

    @PostMapping("/createMemory")    // 创建 → status=PENDING
    @PostMapping("/updateMemory")    // 更新 → 触发 enableMemory/disableMemory
    @PostMapping("/pageMemories")    // 分页 → 支持按状态/评审结果/问题关键词筛选
    @PostMapping("/batchDelete")     // 批量删 → 先 disableMemory 再从表里删
}
```

`updateMemory` 是核心——不只是改字段。如果 status 变为 ENABLED，内部自动调 `enableMemory()` 写 pgvector；变为 DISABLED 则调 `disableMemory()` 移除。`batchDelete` 删除前先遍历，ENABLED 的先从向量库移除，保证关系库和向量库一致。

---

### Q3：过程中遇到了什么难点和坑？

**坑 1：LLM 评审输出的正则解析太脆弱**

评审 prompt 要求 LLM 输出 `opinion=(POSITIVE|NEGATIVE),comment=(xxx)`，然后用正则解析：

```java
private static final Pattern OUTPUT_PATTERN =
    Pattern.compile("opinion=(.*),.*comment=(.*)");

private void processResponse(String response, ChatMemory m) {
    Matcher matcher = OUTPUT_PATTERN.matcher(response);
    if (matcher.find()) {
        m.setLlmReviewRet(MemoryReviewResult.getMemoryReviewResult(matcher.group(1)));
        m.setLlmReviewCmt(matcher.group(2));
        ...
    }
    // ⚠️ 如果没匹配到 → 静默丢弃，记忆永远留在 PENDING
}
```

问题：
- LLM 偶尔输出 `Opinion: POSITIVE`（冒号而非等号）、`opinion=POSITIVE. comment=...`（句号分隔）——正则匹配失败
- 匹配失败后没有任何告警，记忆静默停留在 PENDING，管理员根本不知道有一条记忆评审失败了
- `getMemoryReviewResult()` 如果收到非预期字符串，会抛 `InvalidArgumentException`，但异常被外层 catch 吞了

修复：① 正则失败时用 `contains("POSITIVE")` 兜底；② 加 error 日志 + 统计计数器，让运维能发现；③ 考虑用 LangChain4j 的结构化输出（`@Description` 注解的 POJO）替代正则解析。

**坑 2：启动时 pgvector 挂了，所有记忆静默失效**

```java
@Override
public void run(String... args) {
    loadSysExemplars();  // 启动时加载所有 ENABLED 记忆
}

public void loadSysExemplars() {
    try {
        List<ChatMemory> memories = getMemories(
            ChatMemoryFilter.builder().status(MemoryStatus.ENABLED).build());
        for (ChatMemory memory : memories) {
            exemplarService.storeExemplar(...);  // 写 pgvector
        }
    } catch (Exception e) {
        log.error("Failed to load system exemplars", e);  // 只记日志
        // 不重试，不告警，不阻止启动
    }
}
```

如果启动顺序是 SuperSonic 先起 → pgvector 后起，`loadSysExemplars()` 抛异常 → 所有记忆加载失败 → 但服务照常启动，Chat-BI 也能用——只是记忆召回永远是空的。用户降级到无记忆模式而不自知。

修复：① 加健康检查，如果记忆加载失败在 `QueryResult` 里标记 `usedExemplars=[]`，至少让前端知道当前无记忆；② 加 retry 机制，启动失败后定时重试。

**坑 3：MemoryReviewTask 全量扫描，记忆多了越来越慢**

```java
@Scheduled(fixedDelay = 60 * 1000)
public void review() {
    for (Agent agent : agentService.getAgents()) {
        if (!agent.enableMemoryReview()) continue;
        // ⚠️ 拉了这个 Agent 下 ALL 记忆（包括已评审的），然后逐条在内存里判空
        memoryService.getMemories(chatMemoryFilter).forEach(memory -> {
            if (memory.getLlmReviewRet() != null || memory.getHumanReviewRet() != null)
                return;  // 已评审 → 跳过
            processMemory(memory, agent);
        });
    }
}
```

没有在 SQL 层加 `WHERE llm_review IS NULL AND human_review IS NULL`，而是把所有记忆拉到内存再逐条判断。Agent 下积累了几千条记忆后，每 60 秒都要全表扫一次——大部分时间在做无效判断。

---

### Q4：从代码层面，核心流程是怎么串起来的？

**路径一：Text2SQLExemplar 贯穿存入和召回**

存入和取出用的是同一个 POJO——`Text2SQLExemplar`：

```java
// 存入时（SqlExecutor → createMemory）
Text2SQLExemplar exemplar = JsonUtil.toObject(
    JsonUtil.toString(parseInfo.getProperties().get(Text2SQLExemplar.PROPERTY_KEY)),
    Text2SQLExemplar.class);
// exemplar: {question, sql, dbSchema, sideInfo}

// 召回时（NL2SQLParser → addDynamicExemplars）
List<Text2SQLExemplar> exemplars =
    exemplarManager.recallExemplars(memoryCollectionName, queryText, 10);
queryNLReq.getDynamicExemplars().addAll(exemplars);  // 同结构，无需格式转换

// 注入 prompt 时（OnePassSCSqlGenStrategy → generatePrompt）
for (Text2SQLExemplar exemplar : llmReq.getDynamicExemplars()) {
    String exemplarStr = String.format("\nQuestion:%s,Schema:%s,SideInfo:%s,SQL:%s",
        exemplar.getQuestion(), exemplar.getDbSchema(),
        exemplar.getSideInfo(), exemplar.getSql());
    exemplars.append(exemplarStr);
}
```

这也是为什么 `dbSchema` 必须冻结在创建时——召回时直接原样注入，无需担心 Schema 漂移。

**路径二：Agent 配置控制记忆模块开关**

```java
// Agent.java — 每个 Agent 独立控制
public boolean enableMemoryReview() {
    ChatApp memoryReviewApp = chatAppConfig.get(MemoryReviewTask.APP_KEY);
    return memoryReviewApp != null && memoryReviewApp.isEnable();
}

// MemoryReviewTask — 注册时默认关闭
public MemoryReviewTask() {
    ChatAppManager.register(APP_KEY,
        ChatApp.builder()
            .prompt(INSTRUCTION)
            .name("记忆启用评估")
            .enable(false)  // 默认关闭，需手动在管理后台开启
            .build());
}
```

这意味着评审 prompt 模板、使用的 LLM 模型，都跟这个 ChatApp 绑定，可以在管理后台为每个 Agent 单独配置。`enable(false)` 默认关闭——新建 Agent 不会自动开始评审，避免无意义的 token 消耗。

**路径三：为什么 dbSchema 存在记忆表里而不是反查**

1. **Schema 会变**：加了 `CAR_10d` 字段后，如果召回时反查当前 Schema，LLM 可能困惑"为什么范例里没有 CAR_10d 但 Schema 里有"
2. **跨环境不一致**：开发环境跑评审时的 Schema 和线上可能不同。如果召回时反查线上 Schema，但记忆是开发环境创建的，字段对不上
3. **评审时需要 dbSchema 判断 SQL 正确性**：如果创建时不存下来，评审时就得反查，增加一次 DB 查询

---

### Q5：MEMORY_REVIEW 和 REWRITE_MULTI_TURN 怎么分工？

这两个模块的目的完全不同，但在查询链路里是串行协作的：

**分工**：

```
REWRITE_MULTI_TURN：解决「你到底在问什么」
  ├─ 场景：用户先问"查询贵州茅台的高管减持记录"
  │        再问"这些高管的教育背景分布"
  └─ 动作：把"这些高管"改写为"贵州茅台的高管"
             ↓ 消解指代后的明确问题

MEMORY_REVIEW：解决「类似问题以前怎么答的」
  ├─ 场景：用户问"按行业统计 Opp_Sell 占比"
  └─ 动作：从 pgvector 召回语义相似的历史记忆
             ↓ 注入 few-shot → LLM 抄历史作业
```

**协同链路（按执行顺序）**：

```
用户输入"这些人的教育背景分布"
  │
  ├─ [先] REWRITE_MULTI_TURN → 指代消解 → "贵州茅台高管的教育背景分布"
  │
  ├─ [后] Schema Mapper → 映射字段到 v_executive_profile.教育背景
  │
  ├─ [后] MEMORY_REVIEW 的历史记忆 → pgvector 召回
  │     "查询教育背景为博士的高管减持记录"
  │     "按行业和学历分组统计减持事件数"
  │     → 发现这两条涉及 v_executive_profile JOIN，作为 few-shot
  │
  └─ [最后] LLM 拿到：消解后的问题 + Schema + 3 条 few-shot → 生成 SQL
```

**为什么顺序重要**：必须先消解指代再做向量检索。如果用户说"这些人的教育背景"，直接拿"这些人"去做 ANN 检索，不可能匹配到你之前存的"贵州茅台高管减持"那条记忆。消解后的明确问题才能命中正确的 few-shot。

---

### Q6：补充话题

**补充 1：效果对比 — 数据飞轮**

CSMAR 星型模型的 Text2SQL 准确率从 **82% → 91%**，分两个阶段：

```
阶段一：冷启动（人工种子）
  0 条记忆, 基准准确率 82%
  → 手动挑选 5 条覆盖核心查询模式的正确 SQL，人工评审 POSITIVE
  → 准确率 86%  (+4%)
  → 再补 5 条（覆盖跨表 JOIN、窗口函数等边界场景）
  → 准确率 89%  (+3%)

阶段二：自动飞轮（查询越多越准）
  10 条种子记忆生效后，用户日常查询持续触发自动沉淀
  → SqlExecutor 自动建 PENDING → MemoryReviewTask 自动评审
  → 通过评审的记忆自动 ENABLED → 召回池扩大
  → 20 条记忆时准确率 90%
  → 30 条记忆时准确率 91% → 之后边际收益递减，趋于平稳
```

**为什么需要 10 条种子而不是直接靠自动飞轮？**

自动飞轮的鸡生蛋问题：0 条记忆 → LLM 查询准确率低 → 生成的 SQL 质量差 → 自动评审大多 NEGATIVE → 几乎没有记忆入库。10 条种子打破了冷启动僵局——先让 LLM 有基本的 few-shot 参照，后续查询质量提升 → 自动沉淀的 SQL 质量也提升 → 正向循环启动。

**怎么测的？**

构造 30 条覆盖不同查询模式（单表筛选 / 跨表 JOIN / 聚合分组 / 时间窗口 / 子查询）的测试集，LLM-as-Judge（60%）+ 精确匹配 SQL（40%）双评分。分别在 0 / 5 / 10 / 20 / 30 条记忆时跑一遍，记录准确率曲线。

---

**补充 2：记忆膨胀了怎么办**

| 问题 | 对策 |
|------|------|
| pgvector ANN 检索变慢（1000 条扫全库） | pgvector IVF 索引（`ivfflat`），聚类加速；超额时限制每 Agent 最多 500 条 |
| 召回的 10 条相似度都很低（记忆太多稀释了相关性） | `PromptHelper` 已有的 same/noSame 机制天然过滤——similarity > 0.989 强制保留，低于阈值的截断 |
| few-shot 越长 prompt token 消耗越大 | `s2.parser.few-shot.number=3` 硬限制注入条数，不随记忆库增长而膨胀 |

进阶思路：生产化后可以用 **记忆使用频率 + 最近召回时间** 做 LRU 淘汰——超过 500 条时自动 disable 最久没被召回的那条。

---

**补充 3：前端管理后台（简述）**

前端在 Agent 管理页有一个 Memory 设置面板（`MemorySettingModal.tsx`），功能：
- 分页展示当前 Agent 的所有记忆（按 status / 评审结果筛选）
- 查看每条记忆的 question + SQL + 评审记录
- 人工评审：POSITIVE → 启用 / NEGATIVE → 禁用
- 批量删除
- Agent 级别开启/关闭自动评审开关（对应 `enableMemoryReview()`）

技术栈：Ant Design Table + Modal，调后端 4 个 REST 接口（Q2 已述）。全栈面试时提一句即可，重心在后端。
