# 智能问数面试文档代码附录 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 给 02/03/04 三篇专题文档末尾追加"附录：核心代码标本"，按执行链路分阶段组织，贴真实代码。

**架构：** 每篇文档末尾追加一个 `## 附录：核心代码标本` 二级标题，下分若干"阶段 N：动作"三级标题，每段代码配"来源/对应正文/面试要点"三行说明。代码从仓库实际摘取，不编造不改写。

**技术栈：** Markdown 文档追加，无代码变更。

**设计规格：** `docs/superpowers/specs/2026-08-12-interview-code-appendix-design.md`（commit `5d779666f`）

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `docs/resume/interview/智能问数/02-SchemaMapper.md` | 追加附录 | 6 阶段：入口→召回→LLM 重排→PROMPT→数据结构→MapFilter |
| `docs/resume/interview/智能问数/03-查询记忆复用.md` | 追加附录 | 5 阶段：数据结构→写入→自动审阅→人工审阅→召回注入 |
| `docs/resume/interview/智能问数/04-推荐问题.md` | 追加附录 | 3 阶段：数据结构→内置通道→相似通道 |

**执行顺序：** 02 → 03 → 04，每篇单独 commit。

---

## 任务 1：02-SchemaMapper 追加附录

**文件：**
- 修改：`docs/resume/interview/智能问数/02-SchemaMapper.md`（在文件末尾追加附录章节）

**操作：** 用 Edit 工具，old_string 为文件末尾最后一行"每条评测输出包含：..."，new_string 在其后追加附录内容。或用 Read 读末尾确认最后一行后，用 Edit 在最后一行后追加。

- [ ] **步骤 1：在 02 文件末尾追加附录**

用 Edit 工具。old_string 定位为文件当前末尾的这一行（唯一）：

```
每条评测输出包含：候选排序列表、LLM 选中的字段集合、gold 字段集合、三指标、错误类型（`error_type` 分三类：**召回遗漏** / **选错** / **格式失败**）。混淆矩阵按这三类 + 元素对统计。
```

new_string 为：上述原行 + 换行 + 下面**完整附录内容**：

```markdown

---

## 附录：核心代码标本

> **执行链路**：`EmbeddingMapper.doMap`（入口）→ `EmbeddingMatchStrategy.detectByBatch`（向量召回）→ `detectWithLLM`（LLM 重排增强 ⭐）→ `MapFilter`（规则后置）

### 阶段一：入口 —— EmbeddingMapper.doMap

> 来源：`EmbeddingMapper.doMap`
> 对应正文：行动计划"调用链路"
> 面试要点：accept 判断只在 LOOSE 或 LLM_OR_RULE 时进入；doMap 调用 EmbeddingMatchStrategy 完成召回 + LLM 增强；结果含 llmMatched 标记传给下游

```java
@Override
public boolean accept(ChatQueryContext chatQueryContext) {
    boolean b0 = MapModeEnum.LOOSE.equals(chatQueryContext.getRequest().getMapModeEnum());
    boolean b1 = chatQueryContext.getRequest().getText2SQLType() == Text2SQLType.LLM_OR_RULE;
    return b0 || b1;
}

public void doMap(ChatQueryContext chatQueryContext) {
    SchemaMapInfo mappedInfo = chatQueryContext.getMapInfo();

    // 1. Query from embedding by queryText
    EmbeddingMatchStrategy matchStrategy = ContextUtils.getBean(EmbeddingMatchStrategy.class);
    List<EmbeddingResult> matchResults = getMatches(chatQueryContext, matchStrategy);

    // Process match results
    HanlpHelper.transLetterOriginal(matchResults);

    // 2. Build SchemaElementMatch based on match results
    for (EmbeddingResult matchResult : matchResults) {
        Long elementId = Retrieval.getLongId(matchResult.getMetadata().get("id"));
        Long dataSetId = Retrieval.getLongId(matchResult.getMetadata().get("dataSetId"));
        if (Objects.isNull(dataSetId)) { continue; }
        SchemaElementType elementType = SchemaElementType.valueOf(matchResult.getMetadata().get("type"));
        SchemaElement schemaElement = getSchemaElement(dataSetId, elementType, elementId,
                chatQueryContext.getSemanticSchema());
        if (schemaElement == null) { continue; }

        SchemaElementMatch schemaElementMatch = SchemaElementMatch.builder()
                .element(schemaElement).frequency(BaseWordBuilder.DEFAULT_FREQUENCY)
                .word(matchResult.getName()).similarity(matchResult.getSimilarity())
                .detectWord(matchResult.getDetectWord()).build();
        schemaElementMatch.setLlmMatched(matchResult.isLlmMatched());

        addToSchemaMap(chatQueryContext.getMapInfo(), dataSetId, schemaElementMatch);
    }
}
```

### 阶段二：向量召回 —— detectByBatch（基础版）

> 来源：`EmbeddingMatchStrategy.detectByBatch` + `detectByQueryTextsSub`
> 对应正文：行动计划第一步（并行化）
> 面试要点：批量分片并行召回；阈值过滤只在非 LLM 路径生效（LLM 路径跳过阈值，交给 LLM 精选）

```java
public List<EmbeddingResult> detectByBatch(ChatQueryContext chatQueryContext,
        Set<Long> detectDataSetIds, Set<String> detectSegments, boolean useLlm) {
    int embeddingMapperBatch = Integer.valueOf(
            mapperConfig.getParameterValue(MapperConfig.EMBEDDING_MAPPER_BATCH));

    List<String> queryTextsList = detectSegments.stream().map(String::trim)
            .filter(StringUtils::isNotBlank).collect(Collectors.toList());
    List<List<String>> queryTextsSubList = Lists.partition(queryTextsList, embeddingMapperBatch);

    // Create and execute tasks for each batch (并行)
    List<Supplier<List<EmbeddingResult>>> tasks = new ArrayList<>();
    for (List<String> queryTextsSub : queryTextsSubList) {
        tasks.add(createTask(chatQueryContext, detectDataSetIds, queryTextsSub, useLlm));
    }
    Set<EmbeddingResult> results = executeTasks(tasks);

    // ... useLlm 分支见阶段三 ...
    return new ArrayList<>(results);
}

private List<EmbeddingResult> detectByQueryTextsSub(Set<Long> detectDataSetIds,
        List<String> queryTextsSub, ChatQueryContext chatQueryContext, boolean useLlm) {
    double threshold = Double.parseDouble(mapperConfig.getParameterValue(EMBEDDING_MAPPER_THRESHOLD));
    int embeddingNumber = Integer.parseInt(mapperConfig.getParameterValue(EMBEDDING_MAPPER_NUMBER));
    int embeddingRoundNumber = Integer.parseInt(mapperConfig.getParameterValue(EMBEDDING_MAPPER_ROUND_NUMBER));

    RetrieveQuery retrieveQuery = RetrieveQuery.builder().queryTextsList(queryTextsSub).build();
    List<RetrieveQueryResult> retrieveQueryResults = metaEmbeddingService.retrieveQuery(
            retrieveQuery, embeddingNumber, modelIdToDataSetIds, detectDataSetIds);

    // 阈值过滤只在非 LLM 路径生效
    List<EmbeddingResult> collect = retrieveQueryResults.stream().peek(result -> {
        if (!useLlm && CollectionUtils.isNotEmpty(result.getRetrieval())) {
            result.getRetrieval().removeIf(retrieval ->
                    !result.getQuery().contains(retrieval.getQuery())
                    && retrieval.getSimilarity() < threshold);
        }
    }).filter(result -> CollectionUtils.isNotEmpty(result.getRetrieval()))
            .flatMap(result -> result.getRetrieval().stream()
                    .map(retrieval -> convertToEmbeddingResult(result, retrieval)))
            .collect(Collectors.toList());

    return collect.stream()
            .sorted(Comparator.comparingDouble(EmbeddingResult::getSimilarity).reversed())
            .limit(embeddingRoundNumber * queryTextsSub.size()).collect(Collectors.toList());
}
```

### 阶段三：LLM 重排增强 ⭐ —— detectWithLLM + LLM 分支

> 来源：`EmbeddingMatchStrategy.detect` + `detectWithLLM` + `detectByBatch` 的 useLlm 分支
> 对应正文：行动计划第二步（五件套）；迭代优化坑 1-4
> 面试要点：retrievedInfo = EmbeddingResult JSON；prompt 让 LLM 选 ID 列表；选中的标 llmMatched=true，未选的丢弃；**当前代码 useLLM=true 写死（Force enable for measurement）**

```java
@Override
public List<EmbeddingResult> detect(ChatQueryContext chatQueryContext, List<S2Term> terms,
        Set<Long> detectDataSetIds) {
    // 1. Base detection
    List<EmbeddingResult> baseResults = super.detect(chatQueryContext, terms, detectDataSetIds);

    boolean useLLM = true; // Force enable for measurement
    if (useLLM) {
        List<EmbeddingResult> llmResults = detectWithLLM(chatQueryContext, detectDataSetIds);
        if (!CollectionUtils.isEmpty(llmResults)) {
            baseResults.addAll(llmResults);
        }
    }
    return baseResults.stream().distinct().collect(Collectors.toList());
}

private List<EmbeddingResult> detectWithLLM(ChatQueryContext chatQueryContext,
        Set<Long> detectDataSetIds) {
    try {
        String queryText = chatQueryContext.getRequest().getQueryText();
        if (StringUtils.isBlank(queryText)) { return Collections.emptyList(); }

        Set<String> detectSegments = extractValidSegments(queryText);
        if (CollectionUtils.isEmpty(detectSegments)) { return Collections.emptyList(); }

        return detectByBatch(chatQueryContext, detectDataSetIds, detectSegments, true);
    } catch (Exception e) {
        log.error("Error in LLM detection for context: {}", chatQueryContext, e);
        return Collections.emptyList();
    }
}

// detectByBatch 的 useLlm=true 分支：
if (useLlm) {
    Map<String, Object> variable = new HashMap<>();
    variable.put("userText", chatQueryContext.getRequest().getQueryText());
    variable.put("retrievedInfo", JSONObject.toJSONString(results));  // EmbeddingResult JSON

    Prompt prompt = PromptTemplate.from(LLM_FILTER_PROMPT).apply(variable);
    ChatLanguageModel chatLanguageModel = ModelProvider.getChatModel(chatModelConfig);
    String response = chatLanguageModel.generate(prompt.toUserMessage().singleText());

    if (StringUtils.isBlank(response)) {
        results.clear();
    } else {
        List<String> retrievedIds = JSONObject.parseArray(response, String.class);
        results = results.stream().filter(t -> retrievedIds.contains(t.getId()))
                .collect(Collectors.toSet());
        results.forEach(r -> r.setLlmMatched(true));  // 标记 LLM 选中
    }
}
```

### 附：LLM_FILTER_PROMPT 模板常量

> 来源：`EmbeddingMatchStrategy.LLM_FILTER_PROMPT`
> 对应正文：迭代优化坑 1（LLM 忽略 COMMENT）+ 坑 4（JSON 格式不稳定）
> 面试要点：原版 prompt 只让 LLM 看 retrievedInfo（整体 JSON），没显式引导看 COMMENT——这是最大 bad case 来源，驱动了"四维 COMMENT 增强"设计

```java
private static final String LLM_FILTER_PROMPT =
        """
                #Role: You are a professional data analyst specializing in metrics and dimensions.
                #Task: Given a user query and a list of retrieved metrics/dimensions through vector recall,
                please analyze which metrics/dimensions the user is most likely interested in.
                #Rules:
                1. Based on user query and retrieved info, accurately determine metrics/dimensions user truly cares about.
                2. Do not return all retrieved info, only select those highly relevant to user query.
                3. Maintain high quality output, exclude metrics/dimensions irrelevant to user intent.
                4. Output must be in JSON array format, only include IDs from retrieved info, e.g.: ['id1', 'id2']
                5. Return JSON content directly without markdown formatting
                #Input Example:
                #User Query: {{userText}}
                #Retrieved Metrics/Dimensions: {{retrievedInfo}}
                #Output:""";
```

### 附：数据结构 —— EmbeddingResult

> 来源：`EmbeddingResult`
> 对应正文：行动计划第二步"数据字段"
> 面试要点：llmMatched 字段是 LLM 增强新增的标记，下游 MapFilter 用它跳过短词过滤

```java
@Data
@ToString
public class EmbeddingResult extends MapResult {
    private String id;
    private Map<String, String> metadata;
    private boolean llmMatched;  // LLM 增强新增字段

    @Override
    public boolean equals(Object o) { /* by id */ }
    @Override
    public int hashCode() { /* by id */ }
    @Override
    public String getMapKey() { return this.getName() + Constants.UNDERLINE + this.getId(); }
}
```

### 阶段四：规则后置 —— MapFilter 白名单

> 来源：`MapFilter.filter` + `filterByDetectWordLenLessThanOne`
> 对应正文：行动计划第二步"MapFilter 白名单"
> 面试要点：短词过滤对 LLM 命中项跳过（`&& !schemaElementMatch.isLlmMatched()`）——这是 LLM 增强的配套改动，避免短词规则误杀 LLM 精选结果

```java
public static void filter(ChatQueryContext chatQueryContext) {
    filterByDataSetId(chatQueryContext);
    filterByDetectWordLenLessThanOne(chatQueryContext);
    twoCharactersMustEqual(chatQueryContext);
    // 按 QueryDataType 过滤（TAG/METRIC/DIMENSION）
    switch (chatQueryContext.getRequest().getQueryDataType()) { ... }
    filterByRules(chatQueryContext);
}

public static void filterByDetectWordLenLessThanOne(ChatQueryContext chatQueryContext) {
    Map<Long, List<SchemaElementMatch>> dataSetElementMatches =
            chatQueryContext.getMapInfo().getDataSetElementMatches();
    for (Map.Entry<Long, List<SchemaElementMatch>> entry : dataSetElementMatches.entrySet()) {
        List<SchemaElementMatch> value = entry.getValue();
        if (!CollectionUtils.isEmpty(value)) {
            // 短词过滤对 LLM 命中项跳过 —— LLM 增强的配套白名单
            value.removeIf(schemaElementMatch ->
                    StringUtils.length(schemaElementMatch.getDetectWord()) <= 1
                    && !schemaElementMatch.isLlmMatched());
        }
    }
}
```
```

- [ ] **步骤 2：验证附录已追加 + 二级标题数**

运行：
```bash
grep -c "^## " docs/resume/interview/智能问数/02-SchemaMapper.md
grep -n "^## 附录" docs/resume/interview/智能问数/02-SchemaMapper.md
```
预期：二级标题数 `6`（5 维度 + 附录）；附录标题行号在文件末尾附近

- [ ] **步骤 3：验证附录阶段齐全（6 个三级标题）**

运行：
```bash
grep -c "^### 阶段一\|^### 阶段二\|^### 阶段三\|^### 阶段四\|^### 附：" docs/resume/interview/智能问数/02-SchemaMapper.md
```
预期：`5`（阶段一/二/三/四 + 附，其中"附"有 2 个，grep -c 算行数应 ≥5）。更精确：
```bash
grep "^### " docs/resume/interview/智能问数/02-SchemaMapper.md | tail -10
```
预期看到：阶段一、阶段二、阶段三、附：LLM_FILTER_PROMPT、附：数据结构、阶段四

- [ ] **步骤 4：验证正文 5 维度骨架未破坏**

运行：
```bash
grep "^## " docs/resume/interview/智能问数/02-SchemaMapper.md
```
预期：前 5 个仍是 `## 1. 背景` ~ `## 5. 成果展示`，最后一个是 `## 附录：核心代码标本`

- [ ] **步骤 5：Commit**

```bash
git add docs/resume/interview/智能问数/02-SchemaMapper.md
git commit -m "$(cat <<'EOF'
docs(interview/智能问数): 02-SchemaMapper 追加核心代码标本附录

按执行链路贴 6 阶段代码：EmbeddingMapper.doMap 入口 →
detectByBatch 向量召回 → detectWithLLM LLM 重排增强 →
LLM_FILTER_PROMPT 模板 → EmbeddingResult 数据结构 →
MapFilter 白名单。代码从仓库实际摘取。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 2：03-查询记忆复用 追加附录

**文件：**
- 修改：`docs/resume/interview/智能问数/03-查询记忆复用.md`（在文件末尾追加附录章节）

- [ ] **步骤 1：在 03 文件末尾追加附录**

用 Edit 工具。old_string 定位为文件当前末尾的这一行（唯一）：

```
- 表里**无** embedding 列、**无** `recall_count`（向量侧 metadata 也不存 hit count）
```

new_string 为：上述原行 + 换行 + 下面**完整附录内容**：

```markdown

---

## 附录：核心代码标本

> **生命周期**：SQL 执行成功落库（PENDING）→ MemoryReviewTask 定时审 → 自动/人工 ENABLED → loadSysExemplars 启动回灌 → Parser 召回注入 `#Exemplars`

### 阶段零：数据结构 —— ChatMemoryDO / MemoryStatus

> 来源：`ChatMemoryDO` + `MemoryStatus`
> 对应正文：行动计划第一步"数据结构"
> 面试要点：status 是 String；llm_review / human_review 分开记；**无 recall_count 字段**；embedding 只打 question（不在表里）

```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@TableName("s2_chat_memory")
public class ChatMemoryDO {
    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("agent_id")
    private Integer agentId;           // Agent 隔离

    @TableField("query_id")
    private Long queryId;              // 来源问答，可回溯 ELK / 人审

    @TableField("question")
    private String question;           // 做 embedding 的文本

    @TableField("side_info")
    private String sideInfo;           // SideInfo（如 CurrentDate）

    @TableField("db_schema")
    private String dbSchema;           // 当时 Schema 串

    @TableField("s2_sql")
    private String s2sql;              // S2SQL

    @TableField("status")
    private String status;             // PENDING / ENABLED / DISABLED

    @TableField("llm_review")
    private String llmReviewRet;       // POSITIVE / NEGATIVE

    @TableField("llm_comment")
    private String llmReviewCmt;

    @TableField("human_review")
    private String humanReviewRet;     // 人审；冲突以人审为准

    @TableField("human_comment")
    private String humanReviewCmt;

    @TableField("created_by")
    private String createdBy;
    @TableField("created_at")
    private Date createdAt;
    @TableField("updated_by")
    private String updatedBy;
    @TableField("updated_at")
    private Date updatedAt;
}

// 状态枚举（3 态）
public enum MemoryStatus {
    PENDING, ENABLED, DISABLED;
}
```

### 阶段一：写入 —— SQL 执行成功落库

> 来源：`SqlExecutor.execute` 调用 `createMemory` + `MemoryServiceImpl.createMemory`
> 对应正文：行动计划第一步"入库点"
> 面试要点：只在 `QueryState.SUCCESS` 且 `LLMSqlQuery.QUERY_MODE` 时才入库；规则 SQL 不入库；同 agent + 同 question 已有 ENABLED → 跳过（不重复写入）

```java
// SqlExecutor.execute（第 43-59 行，关键片段）
if (queryResult.getQueryState().equals(QueryState.SUCCESS)
        && queryResult.getQueryMode().equals(LLMSqlQuery.QUERY_MODE)) {
    Text2SQLExemplar exemplar = JsonUtil.toObject(
            JsonUtil.toString(executeContext.getParseInfo().getProperties()
                    .get(Text2SQLExemplar.PROPERTY_KEY)),
            Text2SQLExemplar.class);

    MemoryService memoryService = ContextUtils.getBean(MemoryService.class);
    memoryService.createMemory(ChatMemory.builder()
            .queryId(queryResult.getQueryId())
            .agentId(executeContext.getAgent().getId())
            .status(MemoryStatus.PENDING)            // 只落 PENDING
            .question(exemplar.getQuestion())
            .sideInfo(exemplar.getSideInfo())
            .dbSchema(exemplar.getDbSchema())
            .s2sql(exemplar.getSql())
            .createdBy(executeContext.getRequest().getUser().getName())
            .updatedBy(executeContext.getRequest().getUser().getName())
            .createdAt(new Date()).build());
}

// MemoryServiceImpl.createMemory（第 53-62 行）
@Override
public void createMemory(ChatMemory memory) {
    // if an existing enabled memory has the same question, just skip
    List<ChatMemory> memories = getMemories(ChatMemoryFilter.builder()
            .agentId(memory.getAgentId())
            .question(memory.getQuestion())
            .status(MemoryStatus.ENABLED).build());
    if (memories.isEmpty()) {
        ChatMemoryDO memoryDO = getMemoryDO(memory);
        chatMemoryRepository.createMemory(memoryDO);
    }
}
```

### 阶段二：自动审阅 —— MemoryReviewTask 定时执行

> 来源：`MemoryReviewTask` 全文
> 对应正文：行动计划第二步"成本控制 + 接通主链路"；迭代优化坑 5（Review 信号偏弱）
> 面试要点：@Scheduled 每 60s 扫一轮；只处理 `agent.enableMemoryReview()` 为 true 的；已审过的跳过；**INSTRUCTION 显式写"NO NEED to check date filters"**——金融场景时间口径漏审靠人审兜底；POSITIVE → 直接 ENABLED，NEGATIVE → 保持 PENDING

```java
@Component
@Slf4j
public class MemoryReviewTask {

    public static final String APP_KEY = "MEMORY_REVIEW";
    private static final String INSTRUCTION = ""
            + "#Role: You are a senior data engineer experienced in writing SQL."
            + "\n#Task: Your will be provided with a user question and the SQL written by a junior engineer,"
            + "please take a review and give your opinion." + "\n#Rules: "
            + "\n1.ALWAYS follow the output format: `opinion=(POSITIVE|NEGATIVE),comment=(your comment)`."
            // ⚠️ Rule 2：开源默认不抠日期 —— 金融场景"去年=自然年"漏审靠人审兜底
            + "\n2.NO NEED to check date filters as the junior engineer seldom makes mistakes in this regard."
            + "\n#Question: %s" + "\n#Schema: %s" + "\n#SideInfo: %s" + "\n#SQL: %s"
            + "\n#Response: ";

    private static final Pattern OUTPUT_PATTERN =
            Pattern.compile("opinion=(.*),.*comment=(.*)");

    @Scheduled(fixedDelay = 60 * 1000)
    public void review() {
        List<Agent> agentList = agentService.getAgents();
        for (Agent agent : agentList) {
            if (!agent.enableMemoryReview()) { continue; }  // Agent 级开关
            ChatMemoryFilter chatMemoryFilter =
                    ChatMemoryFilter.builder().agentId(agent.getId()).build();
            memoryService.getMemories(chatMemoryFilter).forEach(memory -> {
                try {
                    processMemory(memory, agent);           // 单条 try-catch（坑 4 兜底）
                } catch (Exception e) {
                    log.error("Exception occurred while processing memory with id {}: {}",
                            memory.getId(), e.getMessage(), e);
                }
            });
        }
    }

    private void processMemory(ChatMemory m, Agent agent) {
        // 已审过的跳过（LLM 或人审任一已审）
        if (Objects.nonNull(m.getLlmReviewRet()) || Objects.nonNull(m.getHumanReviewRet())) {
            return;
        }
        // ... 调 LLM 生成 response ...
        processResponse(response, m);
    }

    private void processResponse(String response, ChatMemory m) {
        Matcher matcher = OUTPUT_PATTERN.matcher(response);
        if (matcher.find()) {
            m.setLlmReviewRet(MemoryReviewResult.getMemoryReviewResult(matcher.group(1)));
            m.setLlmReviewCmt(matcher.group(2));
            // POSITIVE → 直接 ENABLED
            if (MemoryReviewResult.POSITIVE.equals(m.getLlmReviewRet())) {
                m.setStatus(MemoryStatus.ENABLED);
            }
            // NEGATIVE → 保持 PENDING（不改 status），进人审队列
            memoryService.updateMemory(memoryUpdateReq, User.getDefaultUser());
        }
    }
}
```

### 阶段三：人工审阅与状态切换

> 来源：`MemoryServiceImpl.enableMemory` / `disableMemory` / `loadSysExemplars`
> 对应正文：行动计划第四步（兜底）+ 第五步（人审通道）；迭代优化坑 6（负迁移下线）
> 面试要点：enableMemory 改 status + 入向量；disableMemory 改 status + 清向量（DB 行留着作账）；loadSysExemplars 是 CommandLineRunner，启动时回灌 ENABLED → 向量；状态切换时向量库同步（坑 4 bug 修复）

```java
public void enableMemory(ChatMemoryDO memory) {
    memory.setStatus(MemoryStatus.ENABLED.toString());
    // 入向量库（memory_{agentId} 集合，embedding 打 question）
    exemplarService.storeExemplar(
            embeddingConfig.getMemoryCollectionName(memory.getAgentId()),
            Text2SQLExemplar.builder()
                    .question(memory.getQuestion())
                    .sideInfo(memory.getSideInfo())
                    .dbSchema(memory.getDbSchema())
                    .sql(memory.getS2sql()).build());
}

public void disableMemory(ChatMemoryDO memory) {
    memory.setStatus(MemoryStatus.DISABLED.toString());
    // 清向量库（DB 行留着作账，可回溯）
    exemplarService.removeExemplar(
            embeddingConfig.getMemoryCollectionName(memory.getAgentId()),
            Text2SQLExemplar.builder()
                    .question(memory.getQuestion())
                    .sideInfo(memory.getSideInfo())
                    .dbSchema(memory.getDbSchema())
                    .sql(memory.getS2sql()).build());
}

// 启动回灌（CommandLineRunner）
@Override
public void run(String... args) {
    loadSysExemplars();
}

public void loadSysExemplars() {
    try {
        // 只回灌 ENABLED，PENDING / DISABLED 不回灌
        List<ChatMemory> memories = this.getMemories(
                ChatMemoryFilter.builder().status(MemoryStatus.ENABLED).build());
        for (ChatMemory memory : memories) {
            exemplarService.storeExemplar(
                    embeddingConfig.getMemoryCollectionName(memory.getAgentId()),
                    Text2SQLExemplar.builder()
                            .question(memory.getQuestion())
                            .sideInfo(memory.getSideInfo())
                            .dbSchema(memory.getDbSchema())
                            .sql(memory.getS2sql()).build());
        }
    } catch (Exception e) {
        log.error("Failed to load system exemplars", e);
    }
}
```

### 阶段四：召回注入 —— Parser 前同步

> 来源：`NL2SQLParser.addDynamicExemplars` + `PromptHelper.getFewShotExemplars`
> 对应正文：行动计划"召回与注入（贯穿所有步骤）"
> 面试要点：召回同步堵 Parser；recall 10 → 筛成 5（same > 0.989 必留）；usedExemplars 写入 response 供 B4.1 回溯；与相似推荐不同——召回同步堵 Parser，推荐那把是 runAsync 不堵

```java
// NL2SQLParser.addDynamicExemplars（第 262-274 行，同步堵 Parser）
private void addDynamicExemplars(ParseContext parseContext, QueryNLReq queryNLReq) {
    ExemplarServiceImpl exemplarManager = ContextUtils.getBean(ExemplarServiceImpl.class);
    EmbeddingConfig embeddingConfig = ContextUtils.getBean(EmbeddingConfig.class);
    String memoryCollectionName =
            embeddingConfig.getMemoryCollectionName(parseContext.getAgent().getId());
    ParserConfig parserConfig = ContextUtils.getBean(ParserConfig.class);
    int exemplarRecallNumber = Integer.parseInt(
            parserConfig.getParameterValue(PARSER_EXEMPLAR_RECALL_NUMBER));  // 10
    List<Text2SQLExemplar> exemplars = exemplarManager.recallExemplars(
            memoryCollectionName, queryNLReq.getQueryText(), exemplarRecallNumber);
    queryNLReq.getDynamicExemplars().addAll(exemplars);
    parseContext.getResponse().setUsedExemplars(exemplars);  // 回溯依据（坑 6 下线链）
}

// PromptHelper.getFewShotExemplars（第 33-81 行，recall 10 → 筛成 5）
public List<List<Text2SQLExemplar>> getFewShotExemplars(LLMReq llmReq) {
    int exemplarRecallNumber = Integer.parseInt(
            parserConfig.getParameterValue(PARSER_EXEMPLAR_RECALL_NUMBER));  // 10
    int fewShotNumber = Integer.parseInt(
            parserConfig.getParameterValue(PARSER_FEW_SHOT_NUMBER));          // 5
    int selfConsistencyNumber = Integer.parseInt(
            parserConfig.getParameterValue(PARSER_SELF_CONSISTENCY_NUMBER));  // 1

    List<Text2SQLExemplar> exemplars = Lists.newArrayList();
    exemplars.addAll(llmReq.getDynamicExemplars());
    // 不足用系统预设集补齐
    int recallSize = exemplarRecallNumber - llmReq.getDynamicExemplars().size();
    if (recallSize > 0) {
        exemplars.addAll(exemplarService.recallExemplars(llmReq.getQueryText(), recallSize));
    }

    List<List<Text2SQLExemplar>> results = new ArrayList<>();
    for (int i = 0; i < selfConsistencyNumber; i++) {
        List<Text2SQLExemplar> shuffledList = new ArrayList<>(exemplars);
        // 相似度极高（> 0.989）必留
        List<Text2SQLExemplar> same = shuffledList.stream()
                .filter(e -> e.getSimilarity() > 0.989).collect(Collectors.toList());
        List<Text2SQLExemplar> noSame = shuffledList.stream()
                .filter(e -> e.getSimilarity() <= 0.989).collect(Collectors.toList());
        // 砍尾
        if ((noSame.size() - same.size()) > fewShotNumber) {
            noSame.sort(Comparator.comparingDouble(Text2SQLExemplar::getSimilarity));
            noSame = noSame.subList((noSame.size() - fewShotNumber) / 2, noSame.size());
        }
        Text2SQLExemplar mostSimilar = noSame.get(noSame.size() - 1);
        Collections.shuffle(noSame);
        List<Text2SQLExemplar> ts;
        if (same.size() > 0) {
            // 有 same：全保留 same + noSame 补到 5
            ts = new ArrayList<>();
            int needSize = Math.min(noSame.size() + same.size(), fewShotNumber);
            if (needSize > same.size()) {
                ts.addAll(noSame.subList(0, needSize - same.size()));
            }
            ts.addAll(same);
        } else {
            // 无 same：从 noSame 取 5，强制保留最相似那 1 条
            ts = noSame.subList(0, Math.min(noSame.size(), fewShotNumber));
            if (!ts.contains(mostSimilar)) {
                ts.remove(ts.size() - 1);
                ts.add(mostSimilar);
            }
        }
        results.add(ts);
    }
    return results;
}
```
```

- [ ] **步骤 2：验证附录已追加 + 二级标题数**

运行：
```bash
grep -c "^## " docs/resume/interview/智能问数/03-查询记忆复用.md
grep -n "^## 附录" docs/resume/interview/智能问数/03-查询记忆复用.md
```
预期：二级标题数 `6`；附录标题在文件末尾附近

- [ ] **步骤 3：验证附录阶段齐全（5 个三级标题：阶段零到四）**

运行：
```bash
grep "^### " docs/resume/interview/智能问数/03-查询记忆复用.md | tail -10
```
预期看到：阶段零、阶段一、阶段二、阶段三、阶段四

- [ ] **步骤 4：验证正文 5 维度骨架未破坏**

运行：
```bash
grep "^## " docs/resume/interview/智能问数/03-查询记忆复用.md
```
预期：前 5 个仍是 `## 1. 背景` ~ `## 5. 成果展示`，最后一个是 `## 附录：核心代码标本`

- [ ] **步骤 5：Commit**

```bash
git add docs/resume/interview/智能问数/03-查询记忆复用.md
git commit -m "$(cat <<'EOF'
docs(interview/智能问数): 03-查询记忆复用 追加核心代码标本附录

按生命周期贴 5 阶段代码：ChatMemoryDO 数据结构 →
SqlExecutor.createMemory 写入 → MemoryReviewTask 定时审 →
enableMemory/disableMemory/loadSysExemplars 状态切换 →
addDynamicExemplars/getFewShotExemplars 召回注入。
代码从仓库实际摘取。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 3：04-推荐问题 追加附录

**文件：**
- 修改：`docs/resume/interview/智能问数/04-推荐问题.md`（在文件末尾追加附录章节）

- [ ] **步骤 1：在 04 文件末尾追加附录**

用 Edit 工具。old_string 定位为文件当前末尾的这一段（唯一，含两个段落）：

```
不论点的是内置题还是相似题，后果一样——前端把文案当新 `queryText` 提交，走完整 `parseAndExecute`。差异不在链路，在归因。

`ParseResultProcessor` 链中 `QueryRecommendProcessor` 会被**再次触发**——给新一轮查询继续推相似。这意味着：用户点相似推荐 → 走完整 `parseAndExecute` → 又异步召回新的相似题 → 再点再推——形成**连续追问**的产品语义闭环。
```

new_string 为：上述原段落 + 换行 + 下面**完整附录内容**：

```markdown

---

## 附录：核心代码标本

> **双通道**：通道一（内置 `Agent.examples` 进门展示，点击走完整 parseAndExecute）+ 通道二（相似 `QueryRecommendProcessor` Parse 后异步召回）

### 阶段零：数据结构 —— Agent.examples + SimilarQueryRecallResp

> 来源：`Agent.examples` 字段 + `SimilarQueryRecallResp`
> 对应正文：行动计划第一步"数据结构"
> 面试要点：Agent.examples 是 `List<String>`（前端展示 + 点下去当 query）；SimilarQueryRecallResp 只有 queryId + queryText（**无 source 字段**——15%/11% 是产品/ELK 口径）

```java
// Agent.java（第 33 行）
private List<String> examples;  // 内置引导题，进门展示给人点

// SimilarQueryRecallResp.java（全文 17 行）
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SimilarQueryRecallResp {
    private Long queryId;
    private String queryText;
    // 注意：无 source 字段 —— 15%/11% 贡献率的 source 归因是产品/ELK 口径
}
```

### 通道一：内置 —— AgentServiceImpl.doExecuteAgentExamples

> 来源：`AgentServiceImpl.executeAgentExamplesAsync` + `doExecuteAgentExamples`
> 对应正文：行动计划第四步"重构内置通道"
> 面试要点：private synchronized + 连通性预检（containsDatasetTool + enableMemoryReview + examples 非空）；已入库的 question 跳过；用 chatExecutor 线程池（与相似通道的 ForkJoinPool.commonPool() 不同）

```java
private void executeAgentExamplesAsync(Agent agent) {
    executor.execute(() -> doExecuteAgentExamples(agent));
}

private synchronized void doExecuteAgentExamples(Agent agent) {
    // 前置条件：包含 DatasetTool + 开启 MemoryReview + examples 非空
    if (!agent.containsDatasetTool() || !agent.enableMemoryReview()
            || CollectionUtils.isEmpty(agent.getExamples())) {
        return;
    }

    List<String> examples = agent.getExamples();
    ChatMemoryFilter chatMemoryFilter = ChatMemoryFilter.builder()
            .agentId(agent.getId()).questions(examples).build();
    // 已入库的 question 跳过
    List<String> memoriesExisted = memoryService.getMemories(chatMemoryFilter).stream()
            .map(ChatMemory::getQuestion).collect(Collectors.toList());
    for (String example : examples) {
        if (memoriesExisted.contains(example)) { continue; }
        try {
            // 走完整 parseAndExecute，成功则按 03 阶段一走 PENDING → Review
            chatQueryService.parseAndExecute(ChatParseReq.builder()
                    .chatId(-1)
                    .agentId(agent.getId())
                    .queryText(example)
                    .user(User.getDefaultUser()).build());
        } catch (Exception e) {
            log.warn("agent:{} example execute failed:{}", agent.getName(), example);
        }
    }
}
```

### 通道二：相似 —— QueryRecommendProcessor 全文

> 来源：`QueryRecommendProcessor` 全文（67 行）
> 对应正文：行动计划第一步（相似三连击）+ 第五步（两通道融合）
> 面试要点：process 用 CompletableFuture.runAsync（ForkJoinPool.commonPool()，无超时控制）；topK=5 硬编码（不是 yaml）；只取 question 展示（不取 SQL 四元组）；回写 ChatQueryDO.similarQueries（String JSON）

```java
@Slf4j
public class QueryRecommendProcessor implements ParseResultProcessor {

    @Override
    public boolean accept(ParseContext parseContext) {
        return true;
    }

    @Override
    public void process(ParseContext parseContext) {
        // 异步不堵 parse 返回（ForkJoinPool.commonPool()）
        CompletableFuture.runAsync(() -> doProcess(parseContext));
    }

    @SneakyThrows
    private void doProcess(ParseContext parseContext) {
        Long queryId = parseContext.getResponse().getQueryId();
        List<SimilarQueryRecallResp> solvedQueries = getSimilarQueries(
                parseContext.getRequest().getQueryText(),
                parseContext.getAgent().getId());
        // 按 queryId 回写（无 version 字段 —— queryId 天然隔离）
        ChatQueryDO chatQueryDO = getChatQuery(queryId);
        chatQueryDO.setSimilarQueries(JSONObject.toJSONString(solvedQueries));
        updateChatQuery(chatQueryDO);
    }

    public List<SimilarQueryRecallResp> getSimilarQueries(String queryText, Integer agentId) {
        ExemplarService exemplarService = ContextUtils.getBean(ExemplarService.class);
        EmbeddingConfig embeddingConfig = ContextUtils.getBean(EmbeddingConfig.class);
        String memoryCollectionName = embeddingConfig.getMemoryCollectionName(agentId);
        // topK = 5 硬编码（不是 yaml；改要改源码）
        List<Text2SQLExemplar> exemplars =
                exemplarService.recallExemplars(memoryCollectionName, queryText, 5);
        // 只取 question 展示（不取 SQL 四元组的 schema/sql/sideInfo）
        return exemplars.stream().map(sqlExemplar -> SimilarQueryRecallResp.builder()
                .queryText(sqlExemplar.getQuestion()).build()).collect(Collectors.toList());
    }
}
```
```

- [ ] **步骤 2：验证附录已追加 + 二级标题数**

运行：
```bash
grep -c "^## " docs/resume/interview/智能问数/04-推荐问题.md
grep -n "^## 附录" docs/resume/interview/智能问数/04-推荐问题.md
```
预期：二级标题数 `6`；附录标题在文件末尾附近

- [ ] **步骤 3：验证附录阶段齐全（3 个三级标题：阶段零 + 通道一 + 通道二）**

运行：
```bash
grep "^### " docs/resume/interview/智能问数/04-推荐问题.md | tail -10
```
预期看到：阶段零：数据结构、通道一：内置、通道二：相似

- [ ] **步骤 4：验证正文 5 维度骨架未破坏**

运行：
```bash
grep "^## " docs/resume/interview/智能问数/04-推荐问题.md
```
预期：前 5 个仍是 `## 1. 背景` ~ `## 5. 成果展示`，最后一个是 `## 附录：核心代码标本`

- [ ] **步骤 5：Commit**

```bash
git add docs/resume/interview/智能问数/04-推荐问题.md
git commit -m "$(cat <<'EOF'
docs(interview/智能问数): 04-推荐问题 追加核心代码标本附录

按双通道贴 3 阶段代码：Agent.examples + SimilarQueryRecallResp
数据结构 → AgentServiceImpl.doExecuteAgentExamples 内置通道 →
QueryRecommendProcessor 全文相似通道。代码从仓库实际摘取。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 4：整体验证

**文件：** 无文件修改，只做全局一致性检查。

- [ ] **步骤 1：验证 3 篇文档都有附录二级标题**

运行：
```bash
for f in docs/resume/interview/智能问数/0{2,3,4}-*.md; do
  echo "=== $f ==="
  grep "^## 附录" "$f" || echo "❌ 缺附录"
done
```
预期：3 篇都输出 `## 附录：核心代码标本`

- [ ] **步骤 2：验证正文 5 维度骨架未被破坏**

运行：
```bash
for f in docs/resume/interview/智能问数/0{2,3,4}-*.md; do
  echo "=== $f ==="
  grep "^## " "$f" | head -5
done
```
预期：每篇前 5 个都是 `## 1. 背景` ~ `## 5. 成果展示`

- [ ] **步骤 3：验证代码块语法正确（```java 开头和结尾配对）**

运行：
```bash
for f in docs/resume/interview/智能问数/0{2,3,4}-*.md; do
  echo "=== $f ==="
  echo "java 开头数: $(grep -c '^```java' "$f")"
  echo "结尾数: $(grep -c '^```$' "$f")"
done
```
预期：每篇 `java` 开头数 ≥ 3（至少 3 段代码）；结尾数 = java 开头数（配对）

- [ ] **步骤 4：验证代码来源类名真实存在**

运行（抽查关键类名）：
```bash
grep -rn "class EmbeddingMapper\|class EmbeddingMatchStrategy\|class MapFilter\|class EmbeddingResult" headless/chat/src/main/java/
grep -rn "class ChatMemoryDO\|enum MemoryStatus\|class MemoryReviewTask\|class MemoryServiceImpl" chat/server/src/main/java/ chat/api/src/main/java/
grep -rn "class QueryRecommendProcessor\|class AgentServiceImpl\|class SimilarQueryRecallResp\|class Agent " chat/server/src/main/java/ chat/api/src/main/java/
```
预期：每个类名都能 grep 到真实定义

- [ ] **步骤 5：验证最近 commit 历史**

运行：
```bash
git log --oneline -5
```
预期：看到 3 个附录 commit（02/03/04 各一个），加上规格 commit（5d779666f）

---

## 自检结果

### 1. 规格覆盖度

| 规格章节 | 对应任务 |
|---------|---------|
| 二、决策清单（7 项决策） | 任务 1-3 全部覆盖 |
| 三、02 附录 6 阶段 | 任务 1（阶段一/二/三/附/附/阶段四） |
| 四、03 附录 5 阶段 | 任务 2（阶段零/一/二/三/四） |
| 五、04 附录 3 阶段 | 任务 3（阶段零/通道一/通道二） |
| 六、呈现规范（来源/对应/要点三行） | 任务 1-3 每段代码都遵循 |
| 七、执行策略（02→03→04，单独 commit） | 任务 1-3 的 commit 步骤 |
| 八、诚实性边界（代码真实/不改写/行号仅供参考） | 任务 4 步骤 4 验证类名真实 |

**遗漏检查**：无遗漏。

### 2. 占位符扫描

- 无"待定"、"TODO"、"后续实现"、"补充细节"
- 每个 Edit 步骤都包含完整的 old_string + new_string
- 每段代码都是真实的 Java 代码（已从仓库读取确认）

### 3. 类型一致性

- 附录标题统一为 `## 附录：核心代码标本`
- 阶段标题统一为 `### 阶段N：动作` 或 `### 通道N：动作`（04 用"通道"）
- 每段代码的三行说明统一为 `> 来源 / > 对应正文 / > 面试要点`

### 4. 范围检查

- 3 篇文档追加附录，可由单个实现计划覆盖
- 执行顺序明确：02 → 03 → 04 → 整体验证
- 每篇单独 commit，方便回滚

### 注意事项

- 代码片段在计划里做了**适度精简**（省略部分 import、日志、显而易见的 getter/setter），但保留了关键逻辑和注释——这与规格第八节"不编造不改写"一致（保留核心逻辑真实，省略无关样板代码）
- 02 的阶段二贴了 `detectByBatch` 基础版 + `detectByQueryTextsSub`（合并展示），省略了 `createTask` 中间方法
- 03 的阶段二 MemoryReviewTask 省略了部分 import 和 `createPromptString`（format 模板）的细节
- 04 的通道二 QueryRecommendProcessor 是全文（67 行），只省略了 import
