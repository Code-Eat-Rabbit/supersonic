# 数据结果解读增强

## 简历文案

> 增强数据结果解读能力：在 LLM 基础总结之上，接入联网搜索与业务知识库 RAG 服务，使解读结果不仅描述数据本身，还能关联外部信息（市场动态、业务背景），提升解读的深度和可信度

---

## 架构设计

### 改造前：DataInterpretProcessor 只能做数据翻译

```java
// 当前实现
variable.put("question", queryResult.getTextResult());  // ← 数据表格文本
variable.put("data", queryResult.getTextResult());       // ← 同一个东西（疑似 bug）
Prompt prompt = PromptTemplate.from(chatApp.getPrompt()).apply(variable);
String answer = chatLanguageModel.generate(prompt.toUserMessage()).content().text();
queryResult.setTextSummary(answer);
```

问题：
- 两个 prompt 变量填的是同一个 `textResult`
- LLM 只能看到扁平表格数据，没有业务背景
- 输出只能是"QUARTER3 销售额 520 万，渠道 A 占比 44%..."的描述性重述

### 改造后：搜索结果 + 知识库 → LLM 聚合

```
DataInterpretProcessor.process() 改造后

第 1 步：基础解读（现有逻辑，不变）
  └─ LLM 对查询结果做自然语言总结

第 2 步：联网搜索（新增）
  ├─ 从 parseInfo.metrics + parseInfo.dimensions 提取关键词
  ├─ 构造搜索 query: "{指标名} {维度值} Q3 销售趋势"
  └─ POST https://search-api.company.com/search
      返回: [{ title: "Q3电商行业分析报告", snippet: "行业增速放缓至3.2%..." }]

第 3 步：知识库 RAG 检索（新增）
  └─ POST https://kb-api.company.com/rag/search
      参数: { query: "{查询结果摘要}", topK: 3 }
      返回: [{ content: "渠道B在Q3进行了代理商体系调整...", score: 0.92 }]

第 4 步：LLM 二次聚合
  └─ 基础解读 + 搜索结果 + 知识片段 → textSummary
```

搜索服务和知识库服务作为独立的外部应用部署，SuperSonic 只负责 HTTP 调用。

### 为什么是外部服务而非内嵌？

- 搜索和知识库有独立的索引/embedding/权限管理需求，不适合耦合在 Chat BI 内部
- 外部服务可以独立迭代——搜索算法优化、知识库更新都不需要重启 SuperSonic
- 符合 SuperSonic "外部服务插件化" 的整体设计哲学

---

## 容错设计

搜索和 RAG 调用都是 best-effort —— 失败不影响基础解读：

```java
try {
    String searchContext = searchExternal(textResult, parseInfo);
    if (StringUtils.isNotBlank(searchContext)) {
        enhancedData += searchContext + "\n\n";
    }
} catch (Exception e) {
    log.warn("External search failed, falling back to basic interpretation", e);
}

try {
    String kbContext = queryKnowledgeBase(parseInfo.getQueryText());
    if (StringUtils.isNotBlank(kbContext)) {
        enhancedData += kbContext + "\n\n";
    }
} catch (Exception e) {
    log.warn("Knowledge base query failed", e);
}
```

即使两个外部服务全部不可用，`textSummary` 仍然包含 LLM 基础解读——和改造前一模一样。

---

## 面试 Q&A

### Q1: 为什么不直接在 prompt 里做 RAG？

RAG 需要独立的 embedding 管道和知识库管理（文档切片、向量化、索引更新），不适合作为 prompt 的一部分。而且如果每次解读都做全量 RAG，token 消耗和延迟不可控。

当前方案：只检索 Top-3 最相关的知识片段作为上下文注入 prompt——既丰富了解读，又不显著增加 token 消耗。

### Q2: 搜索 query 是怎么构造的？

从当前查询的语义元数据中提取：

```java
StringBuilder searchQuery = new StringBuilder();
parseInfo.getMetrics().forEach(m -> searchQuery.append(m.getName()).append(" "));
parseInfo.getDimensions().forEach(d -> searchQuery.append(d.getName()).append(" "));
// 结果如："销售额 渠道 Q3 市场趋势"
```

不做复杂的 NLP 改写——直接拼接字段名即可。搜索引擎本身会做分词和意图识别，不需要上层过度处理。

### Q3: 如果搜索/RAG 返回的结果和实际数据矛盾怎么办？

LLM 聚合时数据优先。prompt 中明确要求：外部参考信息标注来源，当与实际数据冲突时以数据为准。

### Q4: 这套机制和相似问题推荐有什么区别？

| 维度 | 相似问题推荐 | 结果解读增强 |
|------|-----------|-----------|
| 触发阶段 | Parse（异步） | Execute 后 Processor 链 |
| 数据来源 | 历史 Memory 向量库 | 搜索引擎 + 业务知识库 |
| 目的 | "你还可以问什么" | "当前结果意味着什么" |
| 用户感知 | 点击推荐问题 → 新查询 | 在结果下方看到增强解读 |
| 外部依赖 | 无（依赖内部向量库） | 搜索 API + 知识库 API |

### Q5: 如果要进一步扩展，还能做什么？

三个方向：
1. **归因分析**：让 LLM 自动发起下钻查询 + 调贡献度分析服务（依赖模块 ④ 的 tool-calling 能力）
2. **异常检测**：接入时序异常检测服务，自动标注异常数据点
3. **建议操作**：基于解读结果生成业务建议（"建议关注渠道B恢复情况"），需要接入规则引擎或业务决策模型
