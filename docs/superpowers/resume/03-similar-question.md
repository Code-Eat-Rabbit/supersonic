# 相似问题推荐系统

## 简历文案

> 设计基于 embedding 向量检索的相似问题推荐系统：用户提问后异步检索历史成功问答并写入数据库，前端懒加载展示；实现 Agent 级 Memory 隔离与 LLM 自动审核机制

---

## 架构全景

```
用户提问 → Parse 阶段
                │
                ├─ ChatQueryParser 链（同步返回）
                │   └─ NL2SQLParser → SchemaMapper → SemanticParser → S2SQL
                │
                └─ ParseResultProcessor 链（异步）
                    └─ QueryRecommendProcessor.process()
                        └─ CompletableFuture.runAsync() ← 不阻塞 Parse 响应
                            │
                            ├─ getSimilarQueries(queryText, agentId)
                            │   ├─ embeddingConfig.getMemoryCollectionName(agentId)
                            │   │   → "agent_memory_{agentId}"
                            │   │
                            │   └─ exemplarService.recallExemplars(collection, queryText, 5)
                            │       └─ EmbeddingService.retrieveQuery()
                            │           → 向量库 Top-5 相似检索
                            │
                            └─ chatQueryDO.setSimilarQueries(JSON)
                                → 写入 s2_chat_query.similar_queries 字段

前端渲染
    └─ SimilarQuestionItem 组件
        ├─ 初始展开: expanded=true 且 similarQuestions 为空
        │   → GET /api/chat/manage/getChatQuery/{queryId}
        │   → 反序列化 similarQueries JSON → SimilarQueryRecallResp[]
        │
        └─ 用户点击某个推荐问题
            → 作为新的 queryText 重新走 Parse → Execute 流程
```

### 核心文件

| 文件 | 职责 |
|------|------|
| `QueryRecommendProcessor.java` (67行) | Parse 阶段异步 embedding 召回 Top-5 |
| `ExemplarServiceImpl.java` (101行) | 向量库检索 + 系统样例加载 |
| `MemoryReviewTask.java` (134行) | LLM 定时审核 Memory 质量 |
| `ChatQueryRepositoryImpl.java` (L136-137) | similarQueries JSON → QueryResp 反序列化 |
| `SimilarQuestionItem.tsx` (84行) | 前端懒加载 + 展开交互 |

---

## 面试 Q&A

### Q1: 相似问题推荐的完整链路是什么？

以用户提问"第三季度各渠道销售额"为例：

**1. Parse 阶段触发（同步主流程）**

`ChatQueryServiceImpl.parse()` 遍历 `ParseResultProcessor` 链（`spring.factories` 注册顺序）：
```java
// ChatQueryServiceImpl.java L124-128
for (ParseResultProcessor processor : parseResultProcessors) {
    if (processor.accept(parseContext)) {
        processor.process(parseContext);
    }
}
```

`QueryRecommendProcessor.accept()` 始终返回 `true`，所以每次提问都会触发。

**2. 异步 embedding 召回（不阻塞）**

```java
// QueryRecommendProcessor.java L32-33
@Override
public void process(ParseContext parseContext) {
    CompletableFuture.runAsync(() -> doProcess(parseContext));  // 异步
}
```

异步线程中执行 `doProcess()`：
```java
// L37-43
private void doProcess(ParseContext parseContext) {
    Long queryId = parseContext.getResponse().getQueryId();
    List<SimilarQueryRecallResp> solvedQueries = getSimilarQueries(
        parseContext.getRequest().getQueryText(),   // "第三季度各渠道销售额"
        parseContext.getAgent().getId()
    );
    ChatQueryDO chatQueryDO = getChatQuery(queryId);
    chatQueryDO.setSimilarQueries(JSONObject.toJSONString(solvedQueries));
    updateChatQuery(chatQueryDO);
}
```

**3. 向量库检索**

```java
// QueryRecommendProcessor.java L46-53
public List<SimilarQueryRecallResp> getSimilarQueries(String queryText, Integer agentId) {
    ExemplarService exemplarService = ContextUtils.getBean(ExemplarService.class);
    EmbeddingConfig embeddingConfig = ContextUtils.getBean(EmbeddingConfig.class);
    
    String memoryCollectionName = embeddingConfig.getMemoryCollectionName(agentId);
    // "agent_memory_1", "agent_memory_2" ...
    
    List<Text2SQLExemplar> exemplars =
        exemplarService.recallExemplars(memoryCollectionName, queryText, 5);
    
    return exemplars.stream()
        .map(exemplar -> SimilarQueryRecallResp.builder()
            .queryText(exemplar.getQuestion()).build())
        .collect(Collectors.toList());
}
```

`ExemplarServiceImpl.recallExemplars()` 将 query 转为 embedding → 向量库检索 Top-N → 反序列化 `Text2SQLExemplar`。

**4. 数据库持久化**

写入 `s2_chat_query.similar_queries` 字段（JSON 字符串）。`ChatQueryDO` 中没有单独的 similarQueries 字段名——它和其他字段一样通过 `BeanUtils.copyProperties` 赋值。

**5. 前端懒加载**

```typescript
// SimilarQuestionItem.tsx L36-40
useEffect(() => {
    if (expanded && similarQuestions?.length === 0 && queryId) {
        initData();  // 发起 GET /api/chat/manage/getChatQuery/{queryId}
    }
}, [expanded, queryId]);
```

后端反序列化（`ChatQueryRepositoryImpl.convertTo()` L136-137）：
```java
queryResp.setSimilarQueries(
    JSONObject.parseArray(chatQueryDO.getSimilarQueries(), SimilarQueryRecallResp.class)
);
```

**6. 渲染和交互**

展开后渲染最多 5 条问题。用户点击 → 作为新的 `queryText` 重新发起 Parse + Execute。

---

### Q2: 为什么用异步（CompletableFuture）而不是同步？

三个原因：

**1. 用户体验：Parse 阶段不能等**

用户按发送后，前端在等待 Parse 响应——如果 embedding 检索（100-200ms 延迟）阻塞了 Parse 返回，用户会感觉到延迟。

同步 vs 异步的差异：
- 同步：Parse 阶段总延迟 = SchemaMapper + Parser + Corrector + embedding 检索
- 异步：Parse 阶段总延迟 = SchemaMapper + Parser + Corrector（不对 embedding 等待）

**2. 前端有兜底机制**

`SimilarQuestionItem` 在展开时如果 `similarQuestions` 为空会主动发 GET 请求重新拉取。所以即使异步写入还没完成，用户在展开时也能拿到最新数据。

```typescript
// L36-39
if (expanded && similarQuestions?.length === 0 && queryId) {
    initData();  // 懒加载兜底
}
```

**3. 异步失败不影响主流程**

`doProcess()` 中没有 try-catch，如果 embedding 检索失败（向量库不可用、超时等），异常直接被 `CompletableFuture` 吞掉，不影响 Parse 响应。下次用户展开时触发懒加载，仍有机会重试。

---

### Q3: Agent 级别的 Memory 隔离是怎么实现的？

```java
// QueryRecommendProcessor.java L49
String memoryCollectionName = embeddingConfig.getMemoryCollectionName(agentId);
```

`EmbeddingConfig.getMemoryCollectionName()` 内部逻辑：

```java
public String getMemoryCollectionName(Integer agentId) {
    return "agent_memory_" + agentId;
}
```

不同 Agent 的 Memory 存在不同的 LangChain4j embedding collection 中：
- Agent 1 → `agent_memory_1`
- Agent 2 → `agent_memory_2`

这是物理隔离——Agent 2 的向量库中不会有 Agent 1 的 Memory 数据。即使两个 Agent 的问题相似，也只会返回自己历史范围内的推荐。

**为什么需要隔离？**

- 不同 Agent 可能绑定不同的语义模型（数据集不同），Agent 1 的 SQL 对 Agent 2 无意义
- 业务隔离：销售部门的 Agent 不应该推荐财务部门的历史问题

---

### Q4: Memory 的审核机制是怎么设计的？

Memory 不是写入向量库就立即可被检索的。它有一条状态机：

```
PENDING → LLM 审核 → ENABLED  → 可被 embedding 检索
                   → NEGATIVE → 仍为 PENDING，等待人工审核
                                         ↓
                                    人工审核 → ENABLED / DISABLED
```

**LLM 定时审核（MemoryReviewTask）**：

```java
// MemoryReviewTask.java L63
@Scheduled(fixedDelay = 60 * 1000)  // 每 60 秒执行一次
public void review() {
    List<Agent> agentList = agentService.getAgents();
    for (Agent agent : agentList) {
        if (!agent.enableMemoryReview()) continue;  // Agent 需开启此功能
        
        memoryService.getMemories(chatMemoryFilter).forEach(memory -> {
            // 只处理未被审核过的 Memory
            if (Objects.nonNull(m.getLlmReviewRet()) || Objects.nonNull(m.getHumanReviewRet())) {
                return;  // 已审核，跳过
            }
            processMemory(memory, agent);
        });
    }
}
```

审核 prompt 模板：
```
#Role: You are a senior data engineer experienced in writing SQL.
#Task: Your will be provided with a user question and the SQL written by a junior engineer,
please take a review and give your opinion.
#Rules:
1.ALWAYS follow the output format: opinion=(POSITIVE|NEGATIVE),comment=(your comment).
2.NO NEED to check date filters as the junior engineer seldom makes mistakes in this regard.
#Question: {原始问题}
#Schema: {数据库 schema}
#SideInfo: {补充信息}
#SQL: {生成的 S2SQL}
#Response:
```

结果解析：
```java
// L119-132
private void processResponse(String response, ChatMemory m) {
    Matcher matcher = OUTPUT_PATTERN.matcher(response);
    if (matcher.find()) {
        m.setLlmReviewRet(MemoryReviewResult.getMemoryReviewResult(matcher.group(1)));
        m.setLlmReviewCmt(matcher.group(2));
        
        // LLM 审核通过 → 直接启用
        if (MemoryReviewResult.POSITIVE.equals(m.getLlmReviewRet())) {
            m.setStatus(MemoryStatus.ENABLED);
        }
        // NEGATIVE → 维持 PENDING，等待人工审核
        
        memoryService.updateMemory(memoryUpdateReq, User.getDefaultUser());
    }
}
```

**人工审核兜底**：

管理员通过 `MemoryController` 手动 enable/disable：
```
POST /api/chat/memory/enableMemory  → status = ENABLED
POST /api/chat/memory/disableMemory → status = DISABLED
```

**为什么需要双审核？**

- LLM 自动审核覆盖 80% 的 case，降本增效
- 但 LLM 可能误判（POSITIVE 判成 NEGATIVE 或反）
- 人工审核作为最终兜底，确保不会漏掉有价值的 Memory，也不会让错误 SQL 长期污染 prompt

---

### Q5: Memory 数据是怎么进入向量库的？

不是 MemoryReviewTask 写入的。入向量库的时机在两个地方：

**时机 1：SqlExecutor 执行成功后**

```java
// SqlExecutor.java L43-58
if (queryResult.getQueryState().equals(QueryState.SUCCESS)
        && queryResult.getQueryMode().equals(LLMSqlQuery.QUERY_MODE)) {
    
    Text2SQLExemplar exemplar = ...;
    MemoryService memoryService = ContextUtils.getBean(MemoryService.class);
    memoryService.createMemory(ChatMemory.builder()
        .queryId(queryResult.getQueryId())
        .agentId(executeContext.getAgent().getId())
        .status(MemoryStatus.PENDING)    // 初始状态：待审核
        .question(exemplar.getQuestion()) // 原始问题
        .sideInfo(exemplar.getSideInfo()) // 补充信息
        .dbSchema(exemplar.getDbSchema()) // 数据库 schema
        .s2sql(exemplar.getSql())         // 生成的 S2SQL
        .build());
}
```

条件：
- `queryState == SUCCESS`：只有成功执行的 SQL 才记录
- `queryMode == LLMSqlQuery.QUERY_MODE`：只有 LLM 生成的 SQL（规则生成的无关）

**时机 2：MemoryReviewTask 审核通过后**

`MemoryReviewTask` 将 `status` 从 `PENDING` 改为 `ENABLED` 后，`MemoryServiceImpl.updateMemory()` 内部会调用 `embeddingService.addQuery()` 将 Memory 写入向量库。

> 注：具体 enableMemory 的 embedding 写入逻辑在 `MemoryServiceImpl` 中，审核通过后才写入向量库。

---

### Q6: 如果 Memory 数据过期了（比如表结构变了导致 SQL 失效），怎么处理？

两条防线：

**防线 1：LLM 自动审核**

`MemoryReviewTask` 的 prompt 中包含 `dbSchema`（生成 SQL 时的数据库 schema）。LLM 审核时会检查 SQL 是否与 schema 一致——如果 schema 已经更新（字段被删除、类型变更），LLM 会判 `NEGATIVE`。此时 Memory 维持 `PENDING` 状态，不会被启用。

**防线 2：人工审核兜底**

管理员定期检查 `PENDING` 状态的 Memory，手动 `disableMemory`。

**防线 3（隐式）：不注入过期 schema**

注入 NL2SQLParser prompt 时，只注入 `question + s2sql`，不注入旧的 `dbSchema`。当前查询使用当前 schema——所以即使旧 Memory 的 schema 过期，只要 SQL 语法本身还能用，可能不会导致错误。但如果字段名变了，SQL 会执行失败，该 Memory 不会再被 SqlExecutor 重新创建。

---

### Q7: 相似问题推荐和"推荐下钻维度"有什么区别？

| 维度 | 相似问题推荐 | 推荐下钻维度 |
|------|-----------|-----------|
| 触发阶段 | Parse 阶段（QueryRecommendProcessor） | Execute 阶段（DimensionRecommendProcessor） |
| 触发条件 | 每次都触发（异步） | 聚合查询 + 有指标 |
| 数据来源 | 历史 Memory 向量库（embedding） | 语义模型配置（relatedSchemaElements） |
| 推荐内容 | 历史成功问答的问题文本 | 当前查询可用的下钻维度 |
| 用户行为 | 点击 → 发起新查询 | 点击 → 按新维度重新查同一指标 |
| 目的 | "你还可以问什么" | "你可以怎么深入分析当前结果" |
