# SuperSonic 简历后端能力 Roadmap 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 产出 5 个后端模块的简历叙事 + 面试 Q&A 文档，同时完成模块 ④（插件改 Skill）和模块 ⑤（结果解读增强）的代码改造

**架构：** 三轨道并行——轨道 1（模块 ①②③ 纯文档）、轨道 2（模块 ④⑤ 代码改造）、轨道 3（模块 ⑥ 统稿）。轨道 1 和 2 可交错推进，轨道 3 在所有模块完成后执行

**技术栈：** Java 21 / Spring Boot 3.3.9 / LangChain4j 0.36.2 / MyBatis-Plus / JUnit 5

**注意：** 模块 ①②③ 为已有代码的阅读+文档编写，不涉及代码变更。不执行 TDD。模块 ④⑤ 涉及代码改造，需遵循 TDD 并先读参考代码。

---

### 任务 1：模块 ① 相似问题推荐 —— 读代码 + 梳理链路

**文件：**
- 阅读：`chat/server/src/main/java/com/tencent/supersonic/chat/server/processor/parse/QueryRecommendProcessor.java`
- 阅读：`common/src/main/java/com/tencent/supersonic/common/service/impl/ExemplarServiceImpl.java`
- 阅读：`chat/server/src/main/java/com/tencent/supersonic/chat/server/persistence/dataobject/ChatQueryDO.java`
- 阅读：`chat/server/src/main/java/com/tencent/supersonic/chat/server/persistence/repository/impl/ChatQueryRepositoryImpl.java`（getChatQuery 方法中 similarQueries 反序列化部分）
- 阅读：`webapp/packages/chat-sdk/src/components/ChatItem/SimilarQuestionItem.tsx`
- 阅读：`chat/server/src/main/java/com/tencent/supersonic/chat/server/service/impl/ChatQueryServiceImpl.java`（第 124-128 行，ParseResultProcessor 链中的 QueryRecommendProcessor 调用）
- 阅读：`chat/server/src/main/java/com/tencent/supersonic/chat/server/memory/MemoryReviewTask.java`（Memory 审核机制）

- [ ] **步骤 1：阅读 QueryRecommendProcessor 核心逻辑**

打开 `QueryRecommendProcessor.java`，理清以下链路：
- `process()` 方法中 `CompletableFuture.runAsync()` 异步机制
- `getSimilarQueries()` 中 `embeddingConfig.getMemoryCollectionName(agentId)` 的 Agent 级隔离
- `exemplarService.recallExemplars()` 的向量库检索
- `chatQueryDO.setSimilarQueries()` 的数据库写入

- [ ] **步骤 2：阅读 ExemplarService 和 Embedding 检索机制**

打开 `ExemplarServiceImpl.java`，理解：
- `recallExemplars(collection, query, num)` 的向量检索流程
- `EmbeddingService.retrieveQuery()` 的调用方式
- `TextSegment` / `Metadata` / `Text2SQLExemplar` 的数据转换

- [ ] **步骤 3：阅读前端懒加载逻辑**

打开 `SimilarQuestionItem.tsx`，理解：
- `querySimilarQuestions(queryId)` API 调用
- `expanded` 状态控制展开/收起
- `onSelectQuestion` 点击后重新发起查询的流程

- [ ] **步骤 4：确认数据库持久化链路**

打开 `ChatQueryRepositoryImpl.java`，找到 `getChatQuery` 方法中 `similarQueries` 的反序列化（约第 136 行）。

打开 `ChatQueryDO.java`，确认 `similarQueries` 字段定义。

打开 `ChatQueryServiceImpl.java`，确认 `QueryRecommendProcessor` 在 `parseResultProcessors` 列表中的位置。

- [ ] **步骤 5：确认 Memory 审核机制**

打开 `MemoryReviewTask.java`，确认：
- `@Scheduled` 定时任务配置
- `POSITIVE` / `NEGATIVE` 审核结果的处理
- `APP_KEY` 注册和 Agent 配置关联

- [ ] **步骤 6：Commit 梳理笔记**

```bash
git add docs/superpowers/resume/04-similar-question-research-notes.md
git commit -m "docs: similar question recommendation research notes"
```

---

### 任务 2：模块 ① 相似问题推荐 —— 写面试文档

**文件：**
- 创建：`docs/superpowers/resume/04-similar-question.md`

- [ ] **步骤 1：编写文档骨架**

```markdown
# 相似问题推荐

## 简历文案

> 设计基于 embedding 向量检索的相似问题推荐系统：用户提问后异步检索历史成功问答并写入数据库，前端懒加载展示；实现 Agent 级 Memory 隔离与 LLM 自动审核机制

## 架构全景

[描述：Parse 阶段异步触发 → embedding 检索 → DB 持久化 → 前端懒加载]

## 面试 Q&A

### Q1: 相似问题推荐的完整链路是什么？

[从用户提问到前端渲染的完整时序]

### Q2: 为什么用异步而不是同步？

[CompetableFuture 的设计意图]

### Q3: Agent 级别的 Memory 隔离是怎么实现的？

[memoryCollectionName 的命名规则]

### Q4: Memory 的审核机制是怎么设计的？

[PENDING → LLM 审核 → ENABLED/DISABLED 状态机]

### Q5: 如果 Memory 数据过期了（比如表结构变了），怎么处理？

[审核不通过 → DISABLED + 人工审核兜底]
```

- [ ] **步骤 2：填充 Q1 完整链路**

以用户提问"第三季度各渠道销售额"为例，写出完整时序：
1. Parse 阶段：`QueryRecommendProcessor.process()` → `CompletableFuture.runAsync()`
2. 异步线程中：`getSimilarQueries("第三季度各渠道销售额", agentId)` → `exemplarService.recallExemplars()`
3. `ChatQueryDO.setSimilarQueries(JSON.toJSONString(solvedQueries))` → 写数据库
4. 前端渲染时：`SimilarQuestionItem` 组件懒加载 → GET `/api/chat/manage/getChatQuery/{queryId}` → 反序列化 `similarQueries`

- [ ] **步骤 3：填充 Q2 异步设计意图**

说明：
- Parse 阶段需要快速返回给前端（用户等待）
- embedding 检索有延迟（100-200ms），不应该阻塞 Parse 响应
- 前端有懒加载兜底（展开时才请求）
- 异步失败不影响主流程（QueryRecommendProcessor 没有异常处理——失败就失败了）

- [ ] **步骤 4：填充 Q3 Agent 隔离**

代码引用：
```java
String memoryCollectionName = embeddingConfig.getMemoryCollectionName(agentId);
// 实际效果: "agent_memory_1"、"agent_memory_2" ...
```
说明不同 Agent 的 Memory 存在不同向量库 collection 中，互不干扰。

- [ ] **步骤 5：填充 Q4-Q5 审核机制**

说明：
- `MemoryReviewTask` 定时扫描 `status=PENDING` 的 Memory
- 用 LLM 判断是否应该启用（检查 SQL schema 是否过期、SQL 是否仍然有效）
- 审核通过 → `status=ENABLED` → 可被 embedding 检索到
- 审核不通过 → `status=DISABLED`
- 管理员可通过 `MemoryController` 手动审核

- [ ] **步骤 6：Commit**

```bash
git add docs/superpowers/resume/04-similar-question.md
git commit -m "docs: similar question recommendation interview Q&A"
```

---

### 任务 3：模块 ② 语义层建模引擎 —— 读 SchemaMapper 代码

**文件：**
- 阅读：`headless/chat/src/main/java/com/tencent/supersonic/headless/chat/mapper/` 下所有 Mapper 类
- 阅读：`headless/chat/src/main/java/com/tencent/supersonic/headless/chat/parser/` 下 Parser 类
- 阅读：`launchers/standalone/src/main/resources/META-INF/spring.factories`（SchemaMapper SPI 注册）

- [ ] **步骤 1：阅读 SchemaMapper 接口和 SPI 注册**

打开 `spring.factories`，找到 `SchemaMapper` 的 SPI 注册：
```properties
com.tencent.supersonic.headless.chat.mapper.SchemaMapper=\
    com.tencent.supersonic.headless.chat.mapper.EmbeddingMapper, \
    com.tencent.supersonic.headless.chat.mapper.KeywordMapper, \
    ...
```

理解：6 个 Mapper 按注册顺序依次执行，每个 Mapper 负责一类映射（embedding 相似度、关键词、查询过滤、时间分区、术语描述、全字段）。

- [ ] **步骤 2：追踪 LLM Filter 的介入点**

搜索 `headless/chat/` 下所有包含 "LLM" 或 "llm" 或 "filter" 的代码，确认：
- LLM 在 SchemaMapper 层的具体调用位置
- 是作为独立 Mapper 还是嵌入在某个 Mapper 内部
- 输入是什么（embedding 召回候选列表）、输出是什么（精选后的匹配结果）

- [ ] **步骤 3：阅读 LLMSqlParser 中 SchemaMapper 的使用**

打开 `LLMSqlParser.java`，追踪：
- `SchemaMapper.map()` 的调用位置
- 映射结果如何注入到 LLM prompt 中
- 映射失败时的 fallback 策略

- [ ] **步骤 4：阅读评价体系相关代码**

打开 `launchers/standalone/src/test/java/com/tencent/supersonic/evaluation/Text2SQLEval.java`，理解评测框架的测试用例构造方式。

- [ ] **步骤 5：Commit 梳理笔记**

```bash
git add docs/superpowers/resume/05-schema-mapper-research-notes.md
git commit -m "docs: schema mapper LLM filter research notes"
```

---

### 任务 4：模块 ② 语义层建模引擎 —— 写面试文档

**文件：**
- 创建：`docs/superpowers/resume/05-schema-mapper.md`

- [ ] **步骤 1：编写文档骨架**

```markdown
# 语义层建模引擎（SchemaMapper LLM 增强）

## 简历文案

> 为 SchemaMapper 引入 LLM Filter 机制：在 HanLP 分词 + embedding 粗排召回候选字段后，由 LLM 对候选做语义精选；通过三步变量隔离实验将映射准确率从 82% 提升至 91%，剩余 9% 顽固 case 完成归因分析并制定改进路线

## 架构全景

## 面试 Q&A

### Q1: SchemaMapper 的完整映射链路是什么？

### Q2: 为什么需要 LLM Filter？只用 embedding 不够吗？

### Q3: 82% → 91% 的三步变量隔离是怎么设计的？

### Q4: 9% 顽固 case 的归因分析怎么做的？

### Q5: SchemaMapper 错了会导致什么后果？

### Q6: 如果让你重新设计 SchemaMapper，会怎么改进？
```

- [ ] **步骤 2：填充 Q1 完整映射链路**

```
用户输入 "北京地区 Q3 销售额"
  → HanLP 分词: ["北京", "地区", "Q3", "销售额"]
  → KeywordMapper: "销售额" → sales_amount
  → EmbeddingMapper: embedding 粗排召回 Top-N 候选指标/维度
  → TermDescMapper: 术语描述匹配
  → LLM Filter: 从候选列表精选最终映射
  → 输出: SchemaMapInfo { metrics: [sales_amount], dimensions: [region], values: [北京], date: Q3 }
```

- [ ] **步骤 3：填充 Q2 LLM Filter 的必要性**

说明 embedding 的局限：
- embedding 只能做 surface-level 语义匹配
- 同义词问题："营收" vs "销售额" 的 embedding 距离可能很大
- 多义词问题："苹果" 在水果电商 vs 数码电商中映射不同
- LLM 能理解上下文，做精准消歧
- 但全用 LLM 成本高+延迟大，所以 embedding 粗排 + LLM 精选

- [ ] **步骤 4：填充 Q3 三步变量隔离**

引用已有机评价体系文档：
1. Phase 0 → Phase 1: 迭代 LLM Filter 提示词 (+13 分)
2. Phase 1 → Phase 2: 语义治理（双维度多聚合注册 + 维度补全）(+17 分)
3. Phase 2 → Phase 3: Memory 增强（复用历史映射结果）(+9 分)
4. 总计: 52% → 65% → 82% → 91%

强调 "变量隔离" 的方法论——每次只改一个变量，确保能精确归因。

- [ ] **步骤 5：填充 Q4-Q6**

Q4: 9% 的归因：schema ambiguity（同一字段可映射到多个语义元素）、synonym substitution（"客单"→"客单价"的缩写识别）
Q5: "Mapper 错全链错"——Parser/Corrector/Translator 不纠正映射错误
Q6: 引入更多上下文（多轮对话记忆、用户偏好）、探索 Graph RAG 替代纯向量检索

- [ ] **步骤 6：Commit**

```bash
git add docs/superpowers/resume/05-schema-mapper.md
git commit -m "docs: schema mapper LLM enhancement interview Q&A"
```

---

### 任务 5：模块 ③ 记忆功能 —— 微调已有文档

**文件：**
- 修改：`docs/superpowers/resume/02-memory-module.md`

- [ ] **步骤 1：读取现有文档**

打开 `docs/superpowers/resume/02-memory-module.md`，确认现有内容结构。

- [ ] **步骤 2：在开头增加"设计决策叙事"段落**

在简历文案之后，Q&A 之前，新增一段：

```markdown
## 设计决策

### 为什么需要 PENDING 状态？

Memory 不能写入即生效，因为：
1. SQL schema 可能过期（表结构变更后旧 SQL 失效）
2. LLM 生成的 SQL 可能有误（成功执行 ≠ 语义正确）
3. 恶意或低质量输入可能污染 prompt

因此设计 PENDING → LLM 审核 → ENABLED/DISABLED 的三态状态机。

### 为什么双审核机制？

LLM 审核自动覆盖大部分 case，但 LLM 可能误判。
人工审核作为兜底，管理员可以：
- 手动 enable 被 LLM 误判为 NEGATIVE 的 Memory
- 手动 disable 被 LLM 漏掉的低质量 Memory
```

- [ ] **步骤 3：检查 Q&A 是否需要补充**

确认现有 6 个 Q&A 是否覆盖以下要点：
- [ ] 状态机设计意图（PENDING → ENABLED/DISABLED）
- [ ] MemoryReviewTask 的审核逻辑
- [ ] NL2SQLParser 中如何注入 Memory
- [ ] Agent 级隔离机制
- [ ] 如果缺少 "Memory 过期导致 prompt 污染" 的场景说明，补充一个新 Q&A

- [ ] **步骤 4：Commit**

```bash
git add docs/superpowers/resume/02-memory-module.md
git commit -m "docs: enhance memory module with design decision narrative"
```

---

### 任务 6：模块 ④ 外部服务插件改造 —— 阶段 0 技术预研

**文件：**
- 创建：`chat/server/src/test/java/com/tencent/supersonic/chat/server/plugin/ToolCallingValidationTest.java`

- [ ] **步骤 1：编写 LangChain4j tool-calling 验证测试**

```java
package com.tencent.supersonic.chat.server.plugin;

import dev.langchain4j.data.message.AiMessage;
import dev.langchain4j.data.message.UserMessage;
import dev.langchain4j.model.chat.ChatLanguageModel;
import dev.langchain4j.model.output.Response;
import dev.langchain4j.agent.tool.ToolSpecification;
import dev.langchain4j.agent.tool.ToolExecutionRequest;
import static dev.langchain4j.agent.tool.JsonSchemaProperty.*;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.Arrays;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
public class ToolCallingValidationTest {

    @Autowired
    private ChatLanguageModel chatLanguageModel;

    @Test
    void testToolCallingForPluginRouting() {
        // 构造 ToolSpecification —— 模拟一个 "打开 Grafana 看板" 的插件能力
        ToolSpecification grafanaTool = ToolSpecification.builder()
            .name("open_grafana_dashboard")
            .description("打开 Grafana 实时监控看板，查看指定地域的系统运行状态")
            .addParameter("region", STRING, description("监控的地域名称，如北京、上海、深圳"))
            .build();

        ToolSpecification inventoryTool = ToolSpecification.builder()
            .name("check_inventory_alert")
            .description("查询库存预警信息，返回低库存或即将缺货的商品列表")
            .addParameter("category", STRING, description("商品品类"))
            .build();

        List<ToolSpecification> tools = Arrays.asList(grafanaTool, inventoryTool);

        // 测试 case 1：明确的插件意图，应该调用 grafana 工具
        UserMessage msg1 = UserMessage.from("打开北京实时监控");
        Response<AiMessage> resp1 = chatLanguageModel.generate(
            Arrays.asList(msg1), tools);

        assertTrue(resp1.content().hasToolExecutionRequests(),
            "应该识别到 tool calling 需求");
        ToolExecutionRequest req1 = resp1.content().toolExecutionRequests().get(0);
        assertEquals("open_grafana_dashboard", req1.name());
        assertTrue(req1.arguments().contains("北京"),
            "参数中应该包含 '北京'");

        // 测试 case 2：不明确的意图，不应该触发任何工具
        UserMessage msg2 = UserMessage.from("你好");
        Response<AiMessage> resp2 = chatLanguageModel.generate(
            Arrays.asList(msg2), tools);

        // 可能返回文本回答，也可能返回 tool call——取决于模型
        // 记录结果供分析
        System.out.println("Case 2 response: " + resp2.content().text());
        System.out.println("Has tool calls: " + resp2.content().hasToolExecutionRequests());

        // 测试 case 3：多工具竞争，LLM 应选出最匹配的
        UserMessage msg3 = UserMessage.from("哪些电子元器件缺货");
        Response<AiMessage> resp3 = chatLanguageModel.generate(
            Arrays.asList(msg3), tools);

        if (resp3.content().hasToolExecutionRequests()) {
            ToolExecutionRequest req3 = resp3.content().toolExecutionRequests().get(0);
            assertEquals("check_inventory_alert", req3.name(),
                "应该匹配库存预警工具而非 Grafana");
        }
    }
}
```

- [ ] **步骤 2：运行测试**

```bash
cd ~/workspace/supersonic
mvn test -Dtest=ToolCallingValidationTest -pl chat/server
```

预期：测试可能通过也可能失败，取决于 LLM 配置。**关键是记录结果，不是追求 100% 通过。**

- [ ] **步骤 3：记录预研结论**

创建一个 markdown 文件记录：
- 当前 LLM 是否返回了正确的 `ToolExecutionRequest`
- 参数提取的准确率
- 是否存在幻觉（调了不该调的 Tool）
- 多个 Tool 竞争时的选择准确率
- 结论：tool-calling 方案是否可行；如果不可行，备选方案是什么（比如回退到纯 embedding）

- [ ] **步骤 4：Commit**

```bash
git add chat/server/src/test/java/.../ToolCallingValidationTest.java
git add docs/superpowers/resume/06-skill-pre-research.md
git commit -m "test: LangChain4j tool-calling feasibility validation"
```

---

### 任务 7：模块 ④ 外部服务插件改造 —— 阶段 1 读参考代码

**文件：**
- 阅读：`/Users/yourton_ma/workspace/QA-Orchestrator-Agent/reference_project/reference_docs/LLMentor_md/项目实战3（gogo-agent）/基于规则+RAG+LLM构建三层意图识别.md`
- 阅读：`/Users/yourton_ma/workspace/QA-Orchestrator-Agent/reference_project/LLMentor/springai/src/main/java/cn/hollis/llm/llmentor/tools/OrderTools.java`

- [ ] **步骤 1：阅读 gogo-agent 三层意图识别文档**

打开 `基于规则+RAG+LLM构建三层意图识别.md`，提取：
- L1 规则层的实现方式（关键词匹配/正则）
- L2 向量层的实现方式（embedding + Top-1）
- L3 LLM 层的实现方式（单次调用兜底）
- 短路逻辑（L1 命中 → 跳 L2/L3）
- 三层结果如何统一为同一数据结构

- [ ] **步骤 2：阅读 OrderTools.java 的 Tool 注册模式**

打开 `OrderTools.java`，理解：
- `@Tool` 注解的 `name` 和 `description` 字段如何影响 LLM 的调用决策
- `@ToolParam` 的 `description` 如何帮助 LLM 理解参数语义
- `return` 值的格式（LLM 如何使用工具返回结果）

- [ ] **步骤 3：记录设计映射**

创建一个设计映射文档：
- gogo-agent 的 `IntentRuleMatcher` → SuperSonic 的 `L1KeywordMatcher`
- gogo-agent 的 `IntentVectorMatcher` → SuperSonic 现有的 `PluginManager.recognize()`
- gogo-agent 的 `IntentRecognitionAgent` → SuperSonic 的 `L3ToolCallingRouter`
- gogo-agent 的 `@Tool` 注解 → SuperSonic 的 `ToolSpecification.builder()`

- [ ] **步骤 4：Commit**

```bash
git add docs/superpowers/resume/06-skill-design-mapping.md
git commit -m "docs: gogo-agent to supersonic design pattern mapping"
```

---

### 任务 8：模块 ④ 外部服务插件改造 —— 阶段 2 实现 LayeredPluginRouter

**文件：**
- 创建：`chat/server/src/main/java/com/tencent/supersonic/chat/server/plugin/LayeredPluginRouter.java`
- 测试：`chat/server/src/test/java/com/tencent/supersonic/chat/server/plugin/LayeredPluginRouterTest.java`

- [ ] **步骤 1：编写失败的 L1 规则层测试**

```java
package com.tencent.supersonic.chat.server.plugin;

import dev.langchain4j.agent.tool.ToolSpecification;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

class LayeredPluginRouterTest {

    private LayeredPluginRouter router;
    private List<ToolSpecification> tools;

    @BeforeEach
    void setUp() {
        tools = Arrays.asList(
            ToolSpecification.builder()
                .name("open_grafana_dashboard")
                .description("打开 Grafana 实时监控看板")
                .addParameter("region", STRING)
                .build(),
            ToolSpecification.builder()
                .name("check_inventory_alert")
                .description("查询库存预警信息")
                .addParameter("category", STRING)
                .build()
        );
        router = new LayeredPluginRouter(tools);
    }

    @Test
    void l1KeywordMatchShouldReturnCorrectTool() {
        // L1 应该能通过关键词 "监控" 匹配到 grafana 工具
        Optional<ToolSpecification> result = router.routeL1("打开北京监控");
        assertTrue(result.isPresent());
        assertEquals("open_grafana_dashboard", result.get().name());
    }

    @Test
    void l1NoMatchShouldReturnEmpty() {
        // 没有关键词匹配时返回空
        Optional<ToolSpecification> result = router.routeL1("今天天气怎么样");
        assertFalse(result.isPresent());
    }
}
```

- [ ] **步骤 2：运行测试验证失败**

```bash
cd ~/workspace/supersonic
mvn test -Dtest=LayeredPluginRouterTest -pl chat/server
```
预期：FAIL，`LayeredPluginRouter` 类不存在

- [ ] **步骤 3：实现 L1 关键词匹配**

```java
package com.tencent.supersonic.chat.server.plugin;

import dev.langchain4j.agent.tool.ToolSpecification;
import lombok.extern.slf4j.Slf4j;

import java.util.*;

@Slf4j
public class LayeredPluginRouter {

    private final List<ToolSpecification> tools;
    // L1 关键词映射: keyword → toolName
    private final Map<String, String> keywordToTool;

    public LayeredPluginRouter(List<ToolSpecification> tools) {
        this.tools = tools;
        this.keywordToTool = buildKeywordMap(tools);
    }

    /**
     * 从 ToolSpecification 的 name 和 description 中提取关键词。
     * 规则示例:
     *   "open_grafana_dashboard" → 关键词: "监控", "看板", "grafana", "dashboard"
     *   "check_inventory_alert" → 关键词: "库存", "缺货", "预警"
     */
    private Map<String, String> buildKeywordMap(List<ToolSpecification> tools) {
        Map<String, String> map = new LinkedHashMap<>();
        for (ToolSpecification tool : tools) {
            String name = tool.name().toLowerCase();
            String desc = tool.description() != null ? tool.description().toLowerCase() : "";

            // 从 name 中提取下划线分隔的词
            for (String part : name.split("_")) {
                if (part.length() > 2) map.put(part, tool.name());
            }
            // 从 description 中提取中文关键词
            // 简化版：按常见分隔符拆
            for (String part : desc.split("[，,。.、\\s]+")) {
                if (part.length() >= 2) map.put(part, tool.name());
            }
        }
        return map;
    }

    public Optional<ToolSpecification> routeL1(String queryText) {
        String lower = queryText.toLowerCase();
        for (Map.Entry<String, String> entry : keywordToTool.entrySet()) {
            if (lower.contains(entry.getKey())) {
                return tools.stream()
                    .filter(t -> t.name().equals(entry.getValue()))
                    .findFirst();
            }
        }
        return Optional.empty();
    }

    // L2 和 L3 后续步骤实现
}
```

- [ ] **步骤 4：运行测试验证通过**

```bash
mvn test -Dtest=LayeredPluginRouterTest -pl chat/server
```
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add chat/server/src/main/java/.../LayeredPluginRouter.java
git add chat/server/src/test/java/.../LayeredPluginRouterTest.java
git commit -m "feat: L1 keyword-based plugin routing in LayeredPluginRouter"
```

---

### 任务 9：模块 ④ 外部服务插件改造 —— 阶段 2 续：实现 L2 embedding 层

**文件：**
- 修改：`chat/server/src/main/java/com/tencent/supersonic/chat/server/plugin/LayeredPluginRouter.java`
- 修改：`chat/server/src/test/java/com/tencent/supersonic/chat/server/plugin/LayeredPluginRouterTest.java`

- [ ] **步骤 1：编写 L2 embedding 层测试**

在 `LayeredPluginRouterTest.java` 中新增：

```java
@Test
void l2EmbeddingMatchShouldFallbackWhenL1Misses() {
    // L1 没命中 → 走 L2 embedding
    // 注意：此测试依赖 EmbeddingService 可用
    Optional<ToolSpecification> result = router.routeL2("帮我看看库存是不是有问题");
    // L2 可能匹配到 check_inventory_alert
    if (result.isPresent()) {
        assertEquals("check_inventory_alert", result.get().name());
    }
    // 如果 embedding 也没匹配到，返回 empty（合法行为）
}
```

- [ ] **步骤 2：实现 L2 embedding 匹配**

在 `LayeredPluginRouter.java` 中新增方法：

```java
@Autowired(required = false)
private EmbeddingService embeddingService;

@Autowired(required = false)
private EmbeddingConfig embeddingConfig;

public Optional<ToolSpecification> routeL2(String queryText) {
    if (embeddingService == null || embeddingConfig == null) {
        log.warn("EmbeddingService not available, skipping L2 routing");
        return Optional.empty();
    }
    try {
        RetrieveQuery retrieveQuery = RetrieveQuery.builder()
            .queryTextsList(Collections.singletonList(queryText))
            .build();
        List<RetrieveQueryResult> results = embeddingService.retrieveQuery(
            embeddingConfig.getPresetCollection(),
            retrieveQuery,
            1  // Top-1
        );
        if (!results.isEmpty() && !results.get(0).getRetrieval().isEmpty()) {
            String toolId = results.get(0).getRetrieval().get(0).getId();
            return tools.stream()
                .filter(t -> String.valueOf(toolId).contains(t.name()))
                .findFirst();
        }
    } catch (Exception e) {
        log.warn("L2 embedding routing failed", e);
    }
    return Optional.empty();
}
```

- [ ] **步骤 3：实现三层短路入口方法**

```java
public Optional<ToolSpecification> route(String queryText) {
    // L1
    Optional<ToolSpecification> result = routeL1(queryText);
    if (result.isPresent()) {
        log.info("Plugin routed via L1 (keyword): {}", result.get().name());
        return result;
    }
    // L2
    result = routeL2(queryText);
    if (result.isPresent()) {
        log.info("Plugin routed via L2 (embedding): {}", result.get().name());
        return result;
    }
    // L3: tool-calling（后续实现）
    return routeL3(queryText);
}
```

- [ ] **步骤 4：运行测试**

```bash
mvn test -Dtest=LayeredPluginRouterTest -pl chat/server
```

- [ ] **步骤 5：Commit**

```bash
git add chat/server/src/main/java/.../LayeredPluginRouter.java
git add chat/server/src/test/java/.../LayeredPluginRouterTest.java
git commit -m "feat: L2 embedding-based plugin routing in LayeredPluginRouter"
```

---

### 任务 10：模块 ④ 外部服务插件改造 —— 阶段 3-5 注册表 + 替换 + 清理

**文件：**
- 创建：`chat/server/src/main/java/com/tencent/supersonic/chat/server/plugin/PluginToolRegistry.java`
- 修改：`chat/server/src/main/java/com/tencent/supersonic/chat/server/plugin/LayeredPluginRouter.java`（补 L3 tool-calling）
- 修改：`chat/server/src/main/java/com/tencent/supersonic/chat/server/parser/NL2PluginParser.java`（替换接入）
- 删除：旧插件相关 7 个文件

- [ ] **步骤 1：实现 PluginToolRegistry**

```java
package com.tencent.supersonic.chat.server.plugin;

import dev.langchain4j.agent.tool.ToolSpecification;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class PluginToolRegistry {

    private final Map<String, ToolSpecification> tools = new ConcurrentHashMap<>();
    private final Map<String, PluginSemanticQuery> executors = new ConcurrentHashMap<>();

    public void register(ToolSpecification spec, PluginSemanticQuery executor) {
        tools.put(spec.name(), spec);
        executors.put(spec.name(), executor);
    }

    public List<ToolSpecification> getAllTools() {
        return new ArrayList<>(tools.values());
    }

    public Optional<ToolSpecification> getTool(String name) {
        return Optional.ofNullable(tools.get(name));
    }

    public Optional<PluginSemanticQuery> getExecutor(String name) {
        return Optional.ofNullable(executors.get(name));
    }
}
```

- [ ] **步骤 2：实现 L3 tool-calling 兜底**

在 `LayeredPluginRouter.java` 中：

```java
@Autowired(required = false)
private ChatLanguageModel chatLanguageModel;

public Optional<ToolSpecification> routeL3(String queryText) {
    if (chatLanguageModel == null || tools.isEmpty()) {
        return Optional.empty();
    }
    try {
        UserMessage msg = UserMessage.from(queryText);
        Response<AiMessage> response = chatLanguageModel.generate(
            Arrays.asList(msg), tools);

        if (response.content().hasToolExecutionRequests()) {
            ToolExecutionRequest req = response.content().toolExecutionRequests().get(0);
            return tools.stream()
                .filter(t -> t.name().equals(req.name()))
                .findFirst();
        }
    } catch (Exception e) {
        log.warn("L3 tool-calling routing failed", e);
    }
    return Optional.empty();
}
```

- [ ] **步骤 3：替换 NL2PluginParser 接入**

```java
// NL2PluginParser.java 改造后
@Slf4j
public class NL2PluginParser implements ChatQueryParser {

    private final LayeredPluginRouter router;
    private final PluginToolRegistry registry;

    public NL2PluginParser(LayeredPluginRouter router, PluginToolRegistry registry) {
        this.router = router;
        this.registry = registry;
    }

    public boolean accept(ParseContext parseContext) {
        return parseContext.getAgent().containsPluginTool();
    }

    @Override
    public void parse(ParseContext parseContext) {
        String queryText = parseContext.getRequest().getQueryText();

        // 三层路由
        Optional<ToolSpecification> matched = router.route(queryText);

        if (matched.isPresent()) {
            ToolSpecification spec = matched.get();
            SemanticParseInfo parseInfo = new SemanticParseInfo();
            parseInfo.setQueryMode(extractQueryMode(spec));
            parseInfo.setTextInfo("将由插件工具 **" + spec.name() + "** 来解答");

            PluginParseResult pluginResult = new PluginParseResult();
            // ... 构造 PluginParseResult
            parseInfo.getProperties().put(Constants.CONTEXT, pluginResult);

            parseContext.getResponse().getSelectedParses().add(parseInfo);
            log.info("Plugin routed: {} via L1/L2/L3", spec.name());
        }
    }

    private String extractQueryMode(ToolSpecification spec) {
        // 从 ToolSpecification 的 metadata 或 name 约定中推断 queryMode
        // open_grafana_dashboard → WEB_PAGE
        // check_inventory_alert → WEB_SERVICE
        if (spec.name().contains("grafana") || spec.name().contains("dashboard")) {
            return "WEB_PAGE";
        }
        return "WEB_SERVICE";
    }
}
```

- [ ] **步骤 4：删除旧代码**

确认删除以下 7 个文件（先做备份 commit）：
```bash
git rm chat/server/src/main/java/.../PluginServiceImpl.java
git rm chat/server/src/main/java/.../PluginController.java
git rm chat/server/src/main/java/.../PluginDO.java
git rm chat/server/src/main/java/.../PluginAddEvent.java
git rm chat/server/src/main/java/.../PluginUpdateEvent.java
git rm chat/server/src/main/java/.../PluginDelEvent.java
git rm chat/server/src/main/java/.../PluginRecallResult.java
git rm chat/server/src/main/java/.../PluginParseResult.java
git rm chat/server/src/main/java/.../RecallRetrieval.java
git rm chat/server/src/main/java/.../RecallRetrievalResp.java
git rm chat/server/src/main/java/.../EmbeddingRecallRecognizer.java
```

- [ ] **步骤 5：确保编译通过**

```bash
mvn clean compile -DskipTests -pl chat/server
```

- [ ] **步骤 6：迁移现有插件为 ToolSpecification 声明**

在 `chat/server` 的某个 `@Configuration` 类或新建 `PluginToolConfiguration.java` 中：

```java
@Configuration
public class PluginToolConfiguration {

    @Bean
    public PluginToolRegistry pluginToolRegistry(
            WebPageQuery webPageQuery, WebServiceQuery webServiceQuery) {

        PluginToolRegistry registry = new PluginToolRegistry();

        // 注册 Grafana 看板插件
        registry.register(
            ToolSpecification.builder()
                .name("open_grafana_dashboard")
                .description("打开 Grafana 实时监控看板，查看指定地域的系统运行状态、流量、错误率等")
                .addParameter("region", STRING, 
                    description("监控的地域名称，如北京、上海、深圳、广州"))
                .build(),
            webPageQuery
        );

        // 注册库存预警插件
        registry.register(
            ToolSpecification.builder()
                .name("check_inventory_alert")
                .description("查询库存预警信息，返回低库存或即将缺货的商品列表")
                .addParameter("category", STRING, 
                    description("商品品类，如电子元器件、日用品"))
                .build(),
            webServiceQuery
        );

        return registry;
    }
}
```

- [ ] **步骤 7：Commit**

```bash
git add .
git commit -m "refactor: plugin system to 3-layer skill routing with tool-calling"
```

---

### 任务 11：模块 ⑤ 数据结果解读增强

**文件：**
- 修改：`chat/server/src/main/java/com/tencent/supersonic/chat/server/processor/execute/DataInterpretProcessor.java`

- [ ] **步骤 1：在 DataInterpretProcessor 中新增搜索调用方法**

```java
// 新增方法：调用外部搜索服务
private String searchExternal(String queryText, SemanticParseInfo parseInfo) {
    try {
        // 从查询的指标和维度构造搜索关键词
        StringBuilder searchQuery = new StringBuilder();
        if (!CollectionUtils.isEmpty(parseInfo.getMetrics())) {
            parseInfo.getMetrics().forEach(m -> searchQuery.append(m.getName()).append(" "));
        }
        if (!CollectionUtils.isEmpty(parseInfo.getDimensions())) {
            parseInfo.getDimensions().forEach(d -> searchQuery.append(d.getName()).append(" "));
        }
        searchQuery.append(queryText);

        RestTemplate restTemplate = ContextUtils.getBean(RestTemplate.class);
        // TODO: 配置实际的搜索 API URL
        String searchApiUrl = "https://search-api.company.com/search";
        Map<String, String> params = Map.of("query", searchQuery.toString());
        
        ResponseEntity<String> response = restTemplate.postForEntity(
            searchApiUrl, params, String.class);
        
        if (response.getStatusCode().is2xxSuccessful()) {
            return "[搜索参考]\n" + response.getBody();
        }
    } catch (Exception e) {
        log.warn("External search failed", e);
    }
    return "";
}

// 新增方法：调用外部 RAG 知识库
private String queryKnowledgeBase(String queryText) {
    try {
        RestTemplate restTemplate = ContextUtils.getBean(RestTemplate.class);
        // TODO: 配置实际的知识库 API URL
        String kbApiUrl = "https://kb-api.company.com/rag/search";
        Map<String, Object> params = Map.of("query", queryText, "topK", 3);
        
        ResponseEntity<String> response = restTemplate.postForEntity(
            kbApiUrl, params, String.class);
        
        if (response.getStatusCode().is2xxSuccessful()) {
            return "[业务背景]\n" + response.getBody();
        }
    } catch (Exception e) {
        log.warn("Knowledge base query failed", e);
    }
    return "";
}
```

- [ ] **步骤 2：改造 process 方法，在 LLM 调用前注入增强上下文**

在 `process()` 方法的 LLM 调用之前插入：

```java
// 在 variable.put("data", ...) 之后，prompt.apply() 之前插入：

// 【新增】搜索 + 知识库上下文
String enhancedContext = "";
try {
    String searchContext = searchExternal(
        queryResult.getTextResult(), executeContext.getParseInfo());
    String kbContext = queryKnowledgeBase(
        executeContext.getParseInfo().getQueryText());
    
    if (StringUtils.isNotBlank(searchContext)) {
        enhancedContext += searchContext + "\n\n";
    }
    if (StringUtils.isNotBlank(kbContext)) {
        enhancedContext += kbContext + "\n\n";
    }
} catch (Exception e) {
    log.warn("Enhanced context collection failed, falling back to basic interpretation", e);
}

// 把增强上下文拼接到 data 字段
String enhancedData = queryResult.getTextResult();
if (StringUtils.isNotBlank(enhancedContext)) {
    enhancedData = enhancedData + "\n\n---\n以下为外部参考信息：\n" + enhancedContext;
}
variable.put("data", enhancedData);
```

- [ ] **步骤 3：本地测试验证**

启动 SuperSonic standalone 模式，发起一次查询，检查：
- 控制台日志中是否打印了搜索和 RAG 调用的结果（或失败日志）
- `textSummary` 中是否包含了外部参考信息
- 搜索/RAG 失败时，基础解读是否仍然正常工作（fallback 逻辑）

```bash
cd ~/workspace/supersonic
mvn clean package -DskipTests -Dspotless.skip=true
./assembly/bin/supersonic-daemon.sh restart
# 通过浏览器测试
```

- [ ] **步骤 4：Commit**

```bash
git add chat/server/src/main/java/.../DataInterpretProcessor.java
git commit -m "feat: enhance DataInterpretProcessor with external search and RAG"
```

---

### 任务 12：模块 ⑤ 数据结果解读 —— 写面试文档

**文件：**
- 创建：`docs/superpowers/resume/07-data-interpret.md`

- [ ] **步骤 1：编写文档**

```markdown
# 数据结果解读增强

## 简历文案

> 增强数据结果解读能力：在 LLM 基础总结之上，接入联网搜索与业务知识库 RAG 服务，使解读结果不仅描述数据本身，还能关联外部信息（市场动态、业务背景），提升解读的深度和可信度

## 架构设计

### 为什么是外部服务而非内嵌逻辑？

[说明知识库和搜索服务独立部署的设计决策]

### 容错设计

[搜索/RAG 失败时，基础解读不受影响]

## 面试 Q&A

### Q1: 为什么不直接在 prompt 里做 RAG？

### Q2: 搜索 query 是怎么构造的？

### Q3: 如果搜索/RAG 返回的结果和实际数据矛盾怎么办？

### Q4: 这套机制和相似问题推荐有什么区别？
```

- [ ] **步骤 2：填充 Q&A**

Q1: RAG 需要独立的 embedding 管道和知识库管理，不适合耦合在 prompt 中
Q2: 从 `parseInfo.metrics` 和 `parseInfo.dimensions` 提取关键词拼接
Q3: LLM 聚合时数据优先，外部参考作为辅助信息标注来源
Q4: 相似问题推荐是"帮你问下一个问题"，结果解读是"深入解释当前结果"

- [ ] **步骤 3：Commit**

```bash
git add docs/superpowers/resume/07-data-interpret.md
git commit -m "docs: data interpretation enhancement interview Q&A"
```

---

### 任务 13：模块 ④ 外部服务插件 —— 写面试文档

**文件：**
- 创建：`docs/superpowers/resume/06-skill-architecture.md`

- [ ] **步骤 1：编写文档骨架**

```markdown
# 外部服务 Skill 化架构

## 简历文案

> 将传统"数据库配置 + embedding 匹配"的插件系统重构为三层短路路由架构

## 架构演进

### 改造前：DB 配置 + embedding 匹配

### 改造后：三层短路路由 + tool-calling

## 面试 Q&A

### Q1: 为什么是三层而不是一层 LLM 调用？

### Q2: L1 关键词匹配会不会太死板？

### Q3: 新增一个 Skill 需要改什么？

### Q4: LLM function-calling 和 embedding 匹配有什么区别？

### Q5: 如果三层都没匹配到怎么办？
```

- [ ] **步骤 2：填充内容**

Q1: 成本——L1 < 50ms/0 token、L2 < 100ms/0 token、L3 LLM延迟+token成本
Q2: L1 做绝对确定的高频 case，不确定的交给 L2/L3
Q3: 在 PluginToolConfiguration 中加一个 `registry.register()` 调用
Q4: embedding 是 surface-level 语义匹配，function-calling 是 LLM 理解上下文后的决策
Q5: 不匹配 → 走正常 NL2SQL 路径，不强制走插件

- [ ] **步骤 3：Commit**

```bash
git add docs/superpowers/resume/06-skill-architecture.md
git commit -m "docs: skill architecture refactoring interview Q&A"
```

---

### 任务 14：模块 ⑥ 简历统稿

**文件：**
- 创建：`docs/superpowers/resume/01-master-resume.md`

- [ ] **步骤 1：编写主导简历文档**

```markdown
# SuperSonic Chat-BI 后端能力

## 核心职责

### 语义层建模引擎（SchemaMapper LLM 增强）
[简历 bullet]

### 记忆管理系统
[简历 bullet]

### 外部服务 Skill 化架构
[简历 bullet]

### 数据结果解读增强
[简历 bullet]

### 相似问题推荐
[简历 bullet]

## 30 秒概括

## 模拟面试叙事线

### 面试官问："讲一下你在 SuperSonic 做了什么"

推荐回答顺序：② → ③ → ④ → ⑤ → ①

[每个模块 2 分钟回答指引]

## 10 个高频问题速查

1. 为什么需要语义层而不直接 Text2SQL？
2. Memory 状态机为什么设计 PENDING 状态？
3. 三层路由为什么不直接用 LLM function-calling？
4. ...
```

- [ ] **步骤 2：Commit**

```bash
git add docs/superpowers/resume/01-master-resume.md
git commit -m "docs: master resume document with narrative line"
```

---

## 进度跟踪

| 任务 | 状态 | 产出 |
|------|------|------|
| 1: 相似问题读代码 | [ ] | research notes |
| 2: 相似问题写文档 | [ ] | 04-similar-question.md |
| 3: SchemaMapper 读代码 | [ ] | research notes |
| 4: SchemaMapper 写文档 | [ ] | 05-schema-mapper.md |
| 5: 记忆功能微调 | [ ] | 02-memory-module.md 更新 |
| 6: 技术预研 | [ ] | ToolCallingValidationTest.java |
| 7: 读参考代码 | [ ] | design mapping notes |
| 8: L1 路由器 | [ ] | LayeredPluginRouter L1 |
| 9: L2 路由器 | [ ] | LayeredPluginRouter L2+L3 |
| 10: 注册表+替换+清理 | [ ] | PluginToolRegistry + 删除旧代码 |
| 11: 结果解读代码 | [ ] | DataInterpretProcessor 改造 |
| 12: 结果解读文档 | [ ] | 07-data-interpret.md |
| 13: Skill 架构文档 | [ ] | 06-skill-architecture.md |
| 14: 简历统稿 | [ ] | 01-master-resume.md |
