# 面试文档代码附录设计

- **日期**：2026-08-12
- **主题**：给 02/03/04 三篇专题文档末尾追加"附录：核心代码标本"
- **状态**：已与用户对齐设计方向，待规格审查

---

## 一、背景与动机

上一轮已完成 4 篇面试文档的 5 维度重写（commit `6fd725c42`）。用户审阅后决定在附录部分贴上相关的具体实践代码，作为面试时被追问代码细节的速查参考。

## 二、决策清单（已与用户确认）

| 决策点 | 选择 |
|--------|------|
| 覆盖范围 | 只给 02/03/04 加附录；01 总览不加 |
| 段数限制 | 不限制（按需贴，该贴多少贴多少） |
| 组织方式 | **按执行链路分阶段**（不按方法散列） |
| 02 阶段四 MapFilter | 贴（含 llmMatched 白名单分支） |
| 03 数据结构位置 | 放最前面铺垫（阶段零） |
| 代码来源 | 从当前仓库实际摘取，不编造不改写 |
| 正文影响 | 5 维度骨架正文完全不动，只在末尾追加 `## 附录` |

---

## 三、02-SchemaMapper 附录设计

**执行链路**：`EmbeddingMapper.doMap` → `EmbeddingMatchStrategy.detectByBatch`（向量召回）→ `detectWithLLM`（LLM 重排增强 ⭐）→ `MapFilter`（规则后置）

| 阶段 | 小节标题 | 代码来源 | 对应正文 |
|------|---------|---------|---------|
| 阶段一 | 入口 —— EmbeddingMapper.doMap | `EmbeddingMapper.java:35` | 行动计划链路图 |
| 阶段二 | 向量召回 —— detectByBatch（基础版） | `EmbeddingMatchStrategy.java:139` 基础分支 | 行动计划第一步（并行化） |
| 阶段三 ⭐ | LLM 重排增强 —— detectWithLLM + LLM 分支 | `EmbeddingMatchStrategy.java:91-184` | 行动计划第二步（五件套） |
| 附 | LLM_FILTER_PROMPT 模板常量 | `EmbeddingMatchStrategy.java` 顶部常量 | 迭代优化坑 1-4 |
| 附 | 数据结构 —— EmbeddingResult | `EmbeddingResult.java` 全文 | 行动计划第二步数据字段 |
| 阶段四 | 规则后置 —— MapFilter 白名单 | `MapFilter.java`（含 llmMatched 跳过短词过滤分支） | 行动计划第二步白名单 |

---

## 四、03-查询记忆复用 附录设计

**生命周期**：SQL 执行成功落库 → MemoryReviewTask 定时审 → 人工审阅与状态切换 → Parser 召回注入

| 阶段 | 小节标题 | 代码来源 | 对应正文 |
|------|---------|---------|---------|
| 阶段零 | 数据结构 —— ChatMemoryDO / MemoryStatus | `ChatMemoryDO.java` 全文 + `MemoryStatus.java` | 行动计划第一步数据结构 |
| 阶段一 | 写入 —— SQL 执行成功落库 | `SqlExecutor.java:52` 调用 createMemory + `MemoryServiceImpl.createMemory:53` | 行动计划第一步入库点 |
| 阶段二 | 自动审阅 —— MemoryReviewTask 定时执行 | `MemoryReviewTask.java` 全文（含 @Scheduled / processMemory / processResponse / INSTRUCTION） | 行动计划第二步 |
| 阶段三 | 人工审阅与状态切换 | `MemoryServiceImpl.enableMemory:177` + `disableMemory:185` + `loadSysExemplars:226` | 迭代优化坑 6 + 行动计划第四/五步 |
| 阶段四 | 召回注入 —— Parser 前同步 | `NL2SQLParser.addDynamicExemplars:262` + `PromptHelper.getFewShotExemplars:33` | 行动计划"召回与注入" |

---

## 五、04-推荐问题 附录设计

**双通道**：通道一（内置 Agent.examples 进门展示）+ 通道二（相似 QueryRecommendProcessor Parse 后异步召回）

| 阶段 | 小节标题 | 代码来源 | 对应正文 |
|------|---------|---------|---------|
| 阶段零 | 数据结构 —— Agent.examples + SimilarQueryRecallResp | `Agent.java:33` examples 字段 + `SimilarQueryRecallResp.java` 全文 | 行动计划第一步数据结构 |
| 通道一 | 内置 —— AgentServiceImpl.doExecuteAgentExamples | `AgentServiceImpl.java:125`（private synchronized + 连通性预检） | 行动计划第四步 |
| 通道二 | 相似 —— QueryRecommendProcessor 全文 | `QueryRecommendProcessor.java` 全文（process / doProcess / getSimilarQueries） | 行动计划第一步+第五步 |

---

## 六、呈现规范

每段代码统一用以下格式：

```markdown
### 阶段 N：动作 —— 方法名

> 来源：`完整类名.方法名`
> 对应正文：行动计划第 N 步 / 迭代优化坑 X
> 面试要点：1 句话讲清这段代码被追问时怎么答

​```java
// 完整代码，不做删改
​```
```

附录顶层结构：

```markdown
---

## 附录：核心代码标本

> 执行链路：X → Y → Z（一句话串完）

### 阶段一：xxx
...
### 阶段二：xxx
...
```

---

## 七、执行策略

- 3 篇文档独立修改，每篇末尾追加 `## 附录` 二级标题
- 每篇单独 commit
- 改动顺序：先 02，再 03，再 04
- commit message 前缀：`docs(interview/智能问数): xx 追加核心代码标本附录`

---

## 八、诚实性边界

1. **代码真实性**——所有代码从当前仓库实际摘取，不编造、不改写、不美化
2. **不破坏包装**——代码注释/类名里的 SuperSonic 痕迹保留（面试官看不到仓库），但正文叙事仍按"我"的工作讲
3. **行号仅供参考**——代码演进后行号会变，附录里只标"方法名"，不标具体行号（避免失准）

---

## 九、验证标准

每篇文档改完后验证：
- 附录二级标题 `## 附录：核心代码标本` 存在
- 各阶段三级标题 `### 阶段` 存在
- 代码块语法正确（```java 开头，``` 结尾）
- 来源类名是真实的 Java 类（可用 grep 验证）
- 正文 5 维度骨架未被破坏（5 个 `## ` 二级标题仍在）
