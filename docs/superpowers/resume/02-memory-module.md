# Agent 记忆管理系统

## 简历文案

> 设计 Agent 记忆管理系统：成功执行的 LLM 生成 SQL 自动存入 Memory 向量库，作为 Few-shot 样本注入后续 NL2SQL 的 prompt 中；引入 LLM 定期自动评审 + 人工审核双机制，实现记忆库的持续质量管控

---

## 设计决策

### 为什么需要 PENDING 状态？

Memory 不能写入即生效，因为：

1. **SQL schema 可能过期**：表结构变更后（字段删除、类型修改），旧 SQL 虽然曾经成功执行，但现在已经失效。直接注入 prompt 会误导 LLM 生成错误的 SQL。

2. **LLM 生成的 SQL 可能有语义错误**：成功执行 ≠ 语义正确。`SELECT * FROM orders WHERE amount > 100` 执行成功，但可能用户真正想查的是 `amount > 1000`。SQL 语法正确但业务语义错误，需要审核。

3. **恶意或低质量输入可能污染 prompt**：如果用户输入了恶意 SQL 注入或低质量的自然语言（如大量重复词），这些不应该进入 Memory。

因此设计 `PENDING → 审核 → ENABLED/DISABLED` 的三态状态机。

### 为什么双审核机制？

- **LLM 自动审核**：覆盖 80% 的常规 case，自动化降本
- **人工审核兜底**：LLM 可能误判（POSITIVE 判成 NEGATIVE 或被低质量 SQL 欺骗），人工审核作为最终安全网

---

## 核心文件

| 文件 | 职责 |
|------|------|
| `SqlExecutor.java` (L43-58) | 成功执行后创建 PENDING Memory |
| `MemoryReviewTask.java` (134行) | @Scheduled 定时 LLM 审核 |
| `NL2SQLParser.java` (L265-270) | embedding 召回 Memory 注入 prompt |
| `MemoryController.java` | 人工审核 API |

---

## 面试 Q&A

### Q1: Memory 的完整生命周期是什么样的？

```
用户提问 → NL2SQLParser 生成 SQL → SqlExecutor 执行
    │
    ├─ 条件: queryState == SUCCESS && queryMode == LLM_S2SQL
    │
    └─ MemoryService.createMemory()
        ├─ status = PENDING         ← 初始状态，不可被检索
        ├─ question = "Q3各渠道销售额"
        ├─ s2sql = "SELECT channel, SUM(amount) FROM sales..."
        ├─ dbSchema = "{...}"
        └─ sideInfo = "{...}"
            │
            ▼
    MemoryReviewTask @Scheduled(60s)
    │
    ├─ LLM 审核
    │   ├─ POSITIVE → status = ENABLED → 写入向量库 → 可被 embedding 检索
    │   └─ NEGATIVE → 维持 PENDING → 等待人工审核
    │
    └─ 人工审核
        ├─ enableMemory  → status = ENABLED
        └─ disableMemory → status = DISABLED
            │
            ▼
    ENABLED 状态的 Memory 在后续查询中生效:
    NL2SQLParser 调用 exemplarManager.recallExemplars(memoryCollectionName)
    → 召回 Top-N 相似 Memory → 作为 Few-shot 注入 LLM prompt
```

### Q2: Memory 如何注入 NL2SQL 的 prompt？

在 `NL2SQLParser` 中：

```java
// NL2SQLParser.java L265-270
String memoryCollectionName = 
    embeddingConfig.getMemoryCollectionName(agentId);
    // "agent_memory_{agentId}"

List<Text2SQLExemplar> exemplars = 
    exemplarManager.recallExemplars(memoryCollectionName, queryText, 10);

// 将召回的 examplars 作为 Few-shot 拼接到 LLM prompt 中
// prompt = 系统提示词 + exemplars + 用户问题
```

注入方式：把 `Text2SQLExemplar` 列表中的 `(question, s2sql)` 对格式化为 Few-shot 示例，嵌入 prompt。LLM 看到历史成功案例后，生成 SQL 时更容易匹配正确的字段和语法。

### Q3: MemoryReviewTask 的审核逻辑是怎样的？

```java
@Scheduled(fixedDelay = 60 * 1000)  // 每 60 秒执行一次
public void review() {
    List<Agent> agentList = agentService.getAgents();
    for (Agent agent : agentList) {
        if (!agent.enableMemoryReview()) continue;  // 检查 Agent 是否开启
        
        memoryService.getMemories(chatMemoryFilter).forEach(memory -> {
            // 只处理未被审核过的 Memory
            if (m.getLlmReviewRet() != null || m.getHumanReviewRet() != null) {
                return;  // 已审核 → 跳过
            }
            processMemory(memory, agent);
        });
    }
}
```

审核 prompt：

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

LLM 返回格式：`opinion=POSITIVE,comment=SQL correctly maps the question to the schema`。

正则解析：
```java
Pattern OUTPUT_PATTERN = Pattern.compile("opinion=(.*),.*comment=(.*)");
Matcher matcher = OUTPUT_PATTERN.matcher(response);
if (matcher.find()) {
    MemoryReviewResult result = MemoryReviewResult.getMemoryReviewResult(matcher.group(1));
    String comment = matcher.group(2);
    
    if (MemoryReviewResult.POSITIVE.equals(result)) {
        memory.setStatus(MemoryStatus.ENABLED);  // 直接启用
    }
    // NEGATIVE → 维持 PENDING
    memoryService.updateMemory(updateReq, User.getDefaultUser());
}
```

### Q4: 人工审核的 API 接口是什么？

```java
// MemoryController
POST /api/chat/memory/enableMemory  → status = ENABLED
POST /api/chat/memory/disableMemory → status = DISABLED
```

管理员在前端看到待审核的 Memory 列表，可以手动决策。

### Q5: 为什么要区分 LLM 生成 SQL 和规则生成 SQL？

只收集 LLM 生成的 SQL（`queryMode == LLMSqlQuery.QUERY_MODE`），不收集规则引擎生成的。

原因：
- 规则生成的 SQL 是 100% 确定性的——同样的输入永远生成相同的 SQL，不需要作为"经验"学习
- LLM 生成的 SQL 具有语义泛化价值——"Q3各渠道销售额"的成功案例可以帮助生成"Q2各地区订单量"
- 避免规则 SQL 稀释 embedding 相似度——大量规则 SQL 在向量库中可能淹没具有泛化价值的 LLM SQL

### Q6: 如果 Memory 的 dbSchema 过期了怎么办？

`MemoryReviewTask` 审核时会用 LLM 检查 SQL 与 schema 的匹配性。如果 schema 中的字段已不存在（字段删除）、类型变更，LLM 会判 `NEGATIVE`。

此外，注入 NL2SQLParser prompt 时只注入 `question + s2sql`，不注入旧的 `dbSchema`——当前查询使用当前 schema，所以旧 schema 不会直接污染新 prompt。

但如果旧 SQL 中的字段名本身还存在（只是业务含义变了），确实可能产生误导。这是当前设计的一个已知局限，通过定期人工清理 DISABLED 状态 Memory 来缓解。

### Q7: 相似问题推荐和 Memory 有什么关系？

两者共用了同一套底层数据（Memory 向量库），但用途不同：

| 维度 | 相似问题推荐 | Memory Few-shot |
|------|-----------|---------------|
| 检索内容 | 只取 `question` 文本 | 取完整的 `(question, s2sql, schema)` |
| 检索时机 | Parse 阶段（异步） | NL2SQLParser 生成 SQL 时 |
| 检索数量 | Top-5 | Top-10 |
| 用途 | 展示给用户，用户点击 → 发起新查询 | 注入 LLM prompt，提升 SQL 生成准确率 |
| 对用户可见 | 是 | 否 |
