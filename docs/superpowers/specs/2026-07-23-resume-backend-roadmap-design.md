# SuperSonic 简历后端能力 Roadmap

> 目标：产出 5 个后端模块的简历叙事 + 面试 Q&A 文档
> 输出目录：`docs/superpowers/resume/`
> 状态：设计定稿，待实现

---

## 模块总览

| 序号 | 模块 | 类型 | 新增代码 | 预计工期 |
|------|------|------|---------|---------|
| ① | 相似问题推荐 | 已有（读代码+写文档） | 0 | 1d |
| ② | 语义层建模引擎 | 已有（读代码+写文档） | 0 | 2d |
| ③ | 记忆功能 | 已有（微调文档） | 0 | 0.5d |
| ④ | 外部服务插件改 Skill 架构 | 改造（写代码+写文档） | ~-190 行 | 4d |
| ⑤ | 数据结果解读增强 | 新增（写代码+写文档） | ~40 行 | 2.5d |
| ⑥ | 简历统稿 | 文档整合 | 0 | 1d |

**总计约 11 天（三条轨道可交错推进）**

---

## 模块 ① 相似问题推荐

### 简历文案

> 设计基于 embedding 向量检索的相似问题推荐系统：用户提问后异步检索历史成功问答并写入数据库，前端懒加载展示；实现 Agent 级 Memory 隔离与 LLM 自动审核机制

### 涉及模块

- `QueryRecommendProcessor`：Parse 阶段异步 embedding 召回 Top-5
- `ExemplarService.recallExemplars()`：向量库检索
- `ChatQueryDO.similarQueries`：数据库持久化
- `SimilarQuestionItem.tsx`：前端懒加载 + 展开交互
- `MemoryReviewTask`：LLM 定期审核 PENDING → ENABLED/DISABLED
- `EmbeddingConfig.getMemoryCollectionName(agentId)`：Agent 级隔离

### 产出

- `docs/superpowers/resume/04-similar-question.md`
- 简历 bullet × 1 + 面试 Q&A × 4-5

### 工作内容

| 步骤 | 内容 | 预计 |
|------|------|------|
| 阅读核心代码 + 梳理链路 | 确认 embedding 召回 → DB 异步写入完整链路 | 0.5d |
| 写简历 bullet + 面试 Q&A | 含 Memory 审核机制、Agent 隔离的设计意图 | 0.5d |

---

## 模块 ② 语义层建模引擎

### 简历文案

> 为 SchemaMapper 引入 LLM Filter 机制：在 HanLP 分词 + embedding 粗排召回候选字段后，由 LLM 对候选做语义精选；通过三步变量隔离实验将映射准确率从 82% 提升至 91%，剩余 9% 顽固 case 完成归因分析并制定改进路线

### 涉及模块

- SchemaMapper SPI 链：EmbeddingMapper / KeywordMapper / TermDescMapper 等
- LLM Filter：embedding 粗排后 LLM 精选
- 评价体系：100 题测评集、变量隔离、精度 52%→65%→82%→91%

### 产出

- `docs/superpowers/resume/05-schema-mapper.md`
- 简历 bullet × 1 + 面试 Q&A × 5-6（含评测方法论）

### 工作内容

| 步骤 | 内容 | 预计 |
|------|------|------|
| 阅读 SchemaMapper 核心代码 | 确认 LLM Filter 在代码中的介入点 | 0.5d |
| 梳理完整映射链路 | NL → HanLP → embedding → LLM Filter → 结果 | 0.5d |
| 写简历 bullet + 面试 Q&A | 含评测体系 82%→91% 的叙事 | 1d |

---

## 模块 ③ 记忆功能

### 简历文案

> 设计 Agent 记忆管理系统：成功执行的 LLM 生成 SQL 自动存入 Memory 向量库，作为 Few-shot 样本注入后续 NL2SQL 的 prompt 中；引入 LLM 定期自动评审 + 人工审核双机制，实现记忆库的持续质量管控

### 涉及模块

- `SqlExecutor`：成功执行后自动创建 Memory（PENDING）
- `MemoryReviewTask`：@Scheduled LLM 审核
- `NL2SQLParser`：`exemplarManager.recallExemplars(memoryCollectionName)` 注入 prompt
- `MemoryController`：人工审核 API

### 产出

- `docs/superpowers/resume/02-memory-module.md`（已有，微调）
- 简历 bullet × 1（已有文档中有完整 Q&A）

### 工作内容

| 步骤 | 内容 | 预计 |
|------|------|------|
| 微调现有面试文档 | 加重"为什么 PENDING 状态 + 双审核机制"的设计决策叙事 | 0.5d |

---

## 模块 ④ 外部服务插件 → Skill 架构改造

### 简历文案

> 将传统"数据库配置 + embedding 匹配"的插件系统重构为三层短路路由架构：L1 规则快速命中、L2 embedding 粗排、L3 LangChain4j tool-calling 兜底；LLM 自主决策调用时机与目标能力；新增外部服务只需添加 ToolSpecification 声明，零数据库变更

### 参照设计模式（来自 LLMentor / gogo-agent）

三层短路路由（L1 → L2 → L3，命中即返回）：
- L1 关键词/正则匹配 < 50ms
- L2 embedding 相似度匹配 < 100ms
- L3 LLM function-calling 兜底

### 改动范围

#### 新增

| 文件 | 行数 | 说明 |
|------|------|------|
| `LayeredPluginRouter.java` | ~120 | 三层短路路由 |
| `PluginToolRegistry.java` | ~60 | ToolSpecification 注册表 |

#### 改造

| 文件 | 行数 | 说明 |
|------|------|------|
| `NL2PluginParser.java` | ~10 | 用 LayeredPluginRouter 替换 PluginRecognizer 链 |

#### 复用（不改）

| 文件 | 说明 |
|------|------|
| `WebServiceQuery.java` | HTTP 调用逻辑不变 |
| `WebPageQuery.java` | iframe 构造逻辑不变 |
| `ParamOption.java` / `WebBase.java` | 参数模型不变 |
| `PluginQueryManager.java` | 改名为 SkillRegistry |

#### 删除

| 文件 | 行数 | 说明 |
|------|------|------|
| `PluginServiceImpl.java` | 213 | 不再需要 CRUD |
| `PluginController.java` | 70 | 不再需要 REST API |
| `PluginDO.java` | 40 | 不再需要 DB 持久化 |
| `PluginAddEvent.java` / `PluginUpdateEvent.java` / `PluginDelEvent.java` | 61 | 不再需要 Event 同步 |
| `PluginRecallResult.java` / `PluginParseResult.java` | 36 | 不再需要 |
| `RecallRetrieval.java` / `RecallRetrievalResp.java` | 30 | 不再需要 |

### 技术预研

阶段 0：验证 LangChain4j tool-calling 在当前 LLM 配置下可用：
- 构造 `ToolSpecification`，调用 `generate(messages, toolSpecifications)`
- 验证 LLM 能正确返回 `ToolExecutionRequest`
- 独立 demo，不改业务代码

### 产出

- `docs/superpowers/resume/06-skill-architecture.md`
- 简历 bullet × 1 + 面试 Q&A × 5-6
- 改造代码（净增约 -190 行）

### 工作内容

| 步骤 | 内容 | 预计 |
|------|------|------|
| 阶段 0: 技术预研 | 验证 LangChain4j tool-calling API | 0.3d |
| 阶段 1: 读参考代码 | LLMentor/gogo-agent 三层路由设计 | 0.5d |
| 阶段 2: 实现 LayeredPluginRouter | L1/L2/L3 短路路由 | 1d |
| 阶段 3: 实现 PluginToolRegistry | ToolSpecification 注册表 | 0.5d |
| 阶段 4: 替换 NL2PluginParser 接入 | ~10 行改动 | 0.2d |
| 阶段 5: 删除旧代码 | 7 个文件 | 0.3d |
| 阶段 6: 测试 + 面试文档 | 端到端 + Q&A | 1d |
| **阶段 7: 迁移现有插件配置** | 2 个 Skill 的 ToolSpecification 声明 | 0.2d |

---

## 模块 ⑤ 数据结果解读增强

### 简历文案

> 增强数据结果解读能力：在 LLM 基础总结之上，接入联网搜索与业务知识库 RAG 服务，使解读结果不仅描述数据本身，还能关联外部信息（市场动态、业务背景），提升解读的深度和可信度

### 改造方案

```
DataInterpretProcessor.process() 改造：

第 1 步：基础解读（现有逻辑，不改）
  └─ LLM 对 textResult 做自然语言总结

第 2 步：调搜索服务（新增）
  └─ POST https://search-api.company.com/search
      参数: { query: "{指标名} {维度值} {分析意图}" }

第 3 步：调知识库 RAG 服务（新增）
  └─ POST https://kb-api.company.com/rag/search
      参数: { query: "{查询结果摘要}", topK: 3 }

第 4 步：LLM 聚合
  └─ 基础解读 + 搜索结果片段 + 知识片段 → textSummary
```

搜索服务和知识库服务作为独立的外部应用，SuperSonic 只负责 HTTP 调用。不改任何基础设施。

### 改动量

| 改动 | 行数 | 说明 |
|------|------|------|
| DataInterpretProcessor 改造 | ~40 | 在两个 HTTP 调用 + 上下文拼接 |

### 产出

- `docs/superpowers/resume/07-data-interpret.md`
- 简历 bullet × 1 + 面试 Q&A × 3-4
- 新增代码约 40 行

### 工作内容

| 步骤 | 内容 | 预计 |
|------|------|------|
| 阶段 1: 搜索接入 | 接入搜索 API / 构造检索 query | 0.5d |
| 阶段 2: RAG 接入 | 知识库 RAG API 调用逻辑 | 0.5d |
| 阶段 3: LLM 聚合 | 拼接上下文 → LLM 综合解读 | 0.5d |
| 阶段 4: 测试 + 面试文档 | 效果验证 + Q&A | 1d |

---

## 模块 ⑥ 简历统稿

### 产出

- 一份主简历文档（含 5 个 bullet + 精简版预览）
- 模拟面试回答指引（按模块串联叙事线）

### 叙事线设计

```
面试官："讲一下你在 SuperSonic 项目做了什么"

推荐回答顺序：

① 语义层建模引擎（定位差异）——"我们不是简单做 Text2SQL，而是在物理表之上
   构建语义层，用 LLM Filter 增强 schema 映射准确率，从 82% 提升到 91%"

② 记忆功能（工程闭环）——"每次成功的 NL2SQL 自动沉淀为 Few-shot 样本，
   用 PENDING→LLM审核→ENABLED 的状态机保证质量"

③ 外部服务 Skill 化（架构演进）——"把原始的 DB 配置式插件重构为三层短路路由，
   用 LangChain4j tool-calling 让 LLM 自主决策调用时机"

④ 结果解读增强（增量亮点）——"让 LLM 不只总结数据，还能调搜索引擎和知识库
   RAG，产出有深度的归因报告"

⑤ 相似问题推荐（锦上添花）——"基于 embedding 的异步召回系统，提升用户体验"
```

### 工作内容

| 步骤 | 内容 | 预计 |
|------|------|------|
| 统稿 + 串联 | 5 个模块的简历 bullet + 叙事线 | 0.5d |
| 模拟面试 Q&A | 10 个高频问题的回答指引 | 0.5d |

---

## 轨道排期建议

```
第 1 天 ─ 轨道 1: ① 相似问题推荐（读代码）
第 2 天 ─ 轨道 1: ① 相似问题推荐（写文档）
       ─ 轨道 3: ③ 记忆功能（微调已有文档）
第 3 天 ─ 轨道 1: ② 语义层建模（读 SchemaMapper 代码）
第 4 天 ─ 轨道 1: ② 语义层建模（梳理链路）
       ─ 轨道 2: ④ Skill 改造（阶段 0: 技术预研）
第 5 天 ─ 轨道 1: ② 语义层建模（写文档）
       ─ 轨道 2: ④ Skill 改造（阶段 1: 读参考代码）
第 6 天 ─ 轨道 2: ④ Skill 改造（阶段 2: 实现路由器）
第 7 天 ─ 轨道 2: ④ Skill 改造（阶段 3-5: 注册表 + 替换 + 删除）
第 8 天 ─ 轨道 2: ④ Skill 改造（阶段 6-7: 测试 + 文档 + 迁移）
第 9 天 ─ 轨道 2: ⑤ 结果解读（阶段 1-2: 搜索 + RAG）
第10天 ─ 轨道 2: ⑤ 结果解读（阶段 3-4: 聚合 + 测试 + 文档）
第11天 ─ 轨道 3: ⑥ 简历统稿 + 模拟面试
```

---

## 关键决策记录

| 决策 | 结论 | 原因 |
|------|------|------|
| Skill 格式 | 走 LangChain4j ToolSpecification，不做文件系统 | 与 SuperSonic 技术栈一致，与 LLMentor 设计模式对齐 |
| 三层路由 | L1 规则 + L2 embedding + L3 tool-calling | 参考 gogo-agent 三层意图识别，短路降本 |
| 结果解读 | 纯外部调用（搜索 API + RAG API） | 简单实用，知识库作为独立应用 |
| 不引入新框架 | 不引入 Spring AI/@Tool 注解 | SuperSonic 基于 LangChain4j，不需要迁移框架 |
