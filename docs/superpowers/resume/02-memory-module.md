# Memory 记忆管理模块 — 简历文案 + 面试预案

## 简历文案（终版）

> 设计并实现 Chat-BI 记忆管理模块，支持历史 SQL/查询结果自动注入 LLM 提示词以提升语义解析准确率；引入 LLM 定期自动评审 + 管理员人工评审双机制，实现记忆库的持续质量管控

---

## 面试追问 Q&A

### Q1：记忆注入的具体机制是什么？什么时候触发？

**A：** 采用基于向量检索的 few-shot 注入策略。

- **触发时机**：用户每次提交自然语言查询时，系统先在同一 Agent 的启用记忆库中做语义相似度检索
- **存储方式**：每条记忆（question + S2SQL + dbSchema + sideInfo）在被启用后，通过 BGE 模型生成向量存入 pgvector
- **检索逻辑**：将用户当前问题向量化 → 在 `memory_collection_{agentId}` 中做 ANN 检索 → TOP K 相似记忆作为 Text2SQLExemplar 注入 LLM 提示词
- **注入格式**：以 few-shot example 形式拼接在 prompt 中，结构为 `Question: xxx → SQL: xxx`，帮助 LLM 理解当前数据集的问答模式
- **去重保护**：创建记忆时检查同 Agent 下是否已有相同 question 的启用记忆，有则跳过

### Q2：LLM 自动评审是怎么做的？

**A：** 通过 `MemoryReviewTask` 定时任务实现。

- **执行周期**：`@Scheduled(fixedDelay = 60 * 1000)`，每 60 秒执行一次
- **扫描范围**：遍历所有 Agent，对每个开启了 `enableMemoryReview` 的 Agent，拉取其待评审记忆
- **评审方式**：将记忆的 question + dbSchema + sideInfo + s2sql 拼入评审 prompt 模板，调用 LLM 判断 SQL 正确性
- **评审 prompt**：角色设定为「资深数据工程师」，要求输出 `opinion=(POSITIVE|NEGATIVE),comment=(评审意见)`
- **结果处理**：
  - POSITIVE → 自动将记忆状态设为 ENABLED，并写入向量数据库供后续检索
  - NEGATIVE → 保持 PENDING 状态，等待人工介入
- **幂等保护**：如果记忆已被 LLM 或人工评审过（`llmReviewRet` 或 `humanReviewRet` 非空），跳过不重复评审

### Q3：人工评审的入口和流程？

**A：** 通过 REST API 暴露。

- **接口**：`POST /api/chat/memory/updateMemory`，传入 `humanReviewRet: POSITIVE/NEGATIVE`
- **前端展示**：管理后台分页查询记忆列表（`POST /api/chat/memory/pageMemories`），按状态/评审结果筛选
- **评审后动作**：
  - 人工设为 POSITIVE → 记忆 ENABLED，写入向量数据库
  - 人工设为 NEGATIVE → 记忆 DISABLED，从向量数据库移除（若之前已启用）
- **批量操作**：支持 `batchDelete` 批量删除记忆

### Q4：记忆是如何影响 LLM 查询准确率的？

**A：** 通过两个环节：

1. **提示词增强**：相似历史问题+正确 SQL 作为 few-shot 注入，LLM 在生成 S2SQL 时有了具体的「格式参考」和「字段映射示例」——尤其是对于 CSMAR 这类自定义数据集，few-shot 能够大幅降低字段名理解错误
2. **向量检索召回**：`loadSysExemplars()` 在服务启动时将所有已启用记忆加载到向量数据库，确保每次查询都能召回最相关的历史范例

### Q5：记忆库的技术架构（存储层）？

**A：**

- **关系型存储**：`s2_chat_memory` 表（MyBatis-Plus），字段：id, agentId, queryId, question, sideInfo, dbSchema, s2sql, status(PENDING/ENABLED/DISABLED), llmReviewRet, llmReviewCmt, humanReviewRet, humanReviewCmt, createdBy, createdAt, updatedBy, updatedAt
- **向量存储**：pgvector 的 `memory_collection_{agentId}` 集合，存储 Text2SQLExemplar（question + sql + dbSchema + sideInfo）
- **生命周期**：
  ```
  创建(PENDING) → LLM评审POSITIVE → ENABLED → 写入向量库
                → LLM评审NEGATIVE → 等待人工评审
                → 人工评审POSITIVE → ENABLED → 写入向量库
                → 人工评审NEGATIVE → DISABLED
  ENABLED → 人工 DISABLED → 从向量库移除
  ```

### Q6：MEMORY_REVIEW 和 REWRITE_MULTI_TURN 的区别？

**A：**

- **MEMORY_REVIEW**：对历史记忆做「质量评审」，决定哪些记忆值得作为 few-shot 示例注入后续查询。关注的是「这条 SQL 写得对吗？」
- **REWRITE_MULTI_TURN**：对当前多轮对话做「指代消解」，如用户先问「张三的持仓」，再问「他的教育背景是什么」，系统需要把「他」改写为「张三」。关注的是「当前这句话到底在问什么？」
- 两者协同：REWRITE_MULTI_TURN 先消解指代 → 再结合 MEMORY_REVIEW 筛选出的靠谱 few-shot → 一起发给 LLM 生成 S2SQL
