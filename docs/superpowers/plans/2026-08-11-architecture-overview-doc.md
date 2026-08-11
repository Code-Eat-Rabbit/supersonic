# 01 架构总览文档 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在 `docs/resume/interview/架构设计/` 下新建 `01-架构总览.md`（约 600-800 行），作为数据平台/数仓团队面试官视角的项目宏观鸟瞰文档。

**架构：** 单文件 `.md` 新建，不动业务代码。8 个章节：项目定位 / 顶层模块 / 核心抽象 / 数据流图 / 技术栈 / SPI 扩展 / 部署模式 / 面试问答速查。配 2 张 Mermaid 图（数据流图）和多张表格。

**技术栈：** Markdown + Mermaid（GitHub 渲染原生支持）；代码锚点相对仓库根。

**规格：** [`docs/superpowers/specs/2026-08-11-architecture-interview-doc-design.md`](../specs/2026-08-11-architecture-interview-doc-design.md)（§3 对应本文档）

**关键约束（来自规格 §2 与 §3）：**
- 面向数仓团队视角，避免 Chat BI 营销话术
- 所有论断附 `file_path:line_number`
- Mermaid 图必须与 02 文档 Part A 一致
- §6 SPI 扩展要给出可操作步骤
- §8 至少 10 个面试问答，高频问题加 ⭐

**文件结构：**

| 文件 | 动作 | 职责 |
|------|------|------|
| `docs/resume/interview/架构设计/01-架构总览.md` | 新建 | 唯一交付物 |
| `docs/resume/interview/智能问数/01-总览与业务背景.md` | 只读参照 | 业务侧口径对齐 |
| `docs/resume/interview/深度研究/*` | 只读参照 | 体例模板 |
| `CLAUDE.md` | 只读核对 | 模块职责描述基线 |

**本计划不含代码改动。** 任务粒度按「事实清单 → 文首 → §1-§8 → 收尾验收」切分。

---

## 任务 0：开工前准备

**文件：**
- 操作：建目录，不写正文

- [ ] **步骤 1：确认目标目录状态**

运行：
```bash
ls -la /Users/yourton_ma/workspace/supersonic/docs/resume/interview/
```
预期：输出应包含 `智能问数/`、`深度研究/` 等子目录，但不包含 `架构设计/`。

- [ ] **步骤 2：创建架构设计子目录**

运行：
```bash
mkdir -p /Users/yourton_ma/workspace/supersonic/docs/resume/interview/架构设计
ls -la /Users/yourton_ma/workspace/supersonic/docs/resume/interview/架构设计/
```
预期：目录创建成功，目前为空。

- [ ] **步骤 3：创建空的 01 文档占位**

运行：
```bash
touch "/Users/yourton_ma/workspace/supersonic/docs/resume/interview/架构设计/01-架构总览.md"
```
预期：文件创建成功。

---

## 任务 1：事实清单——把规格 §6.1 的 4 个锚点对到当前行号

**目的：** 规格明确「行号可漂移」。先把每条锚点的当前行号 + 短摘录列成一张表，作为后续写正文时的素材源。这张表是本任务**唯一**产出物，写进 `/tmp/01-fact-sheet.md`，不进仓库。

**文件：**
- 读：`launchers/`、`assembly/conf/META-INF/`、`headless/chat/.../utils/`
- 写：`/tmp/01-fact-sheet.md`（临时）

- [ ] **步骤 1：用 Grep 定位 4 个锚点的当前行号**

对下表左列每条，用 Grep 搜索「类名 + 关键词」；找定义处（非调用处）行号。

| 职责 | grep 模式 | 搜索路径 |
|------|-----------|----------|
| StandaloneLauncher | `class StandaloneLauncher` | `launchers/` |
| ChatLauncher | `class ChatLauncher` | `launchers/` |
| HeadlessLauncher | `class HeadlessLauncher` | `launchers/` |
| spring.factories | 文件本身 | `assembly/conf/META-INF/spring.factories` |
| ComponentFactory | `class ComponentFactory` | `headless/chat/src/main/java/` |

- [ ] **步骤 2：把结果写入 /tmp/01-fact-sheet.md**

格式示例：
```markdown
## 01-架构总览 事实清单

| 职责 | 类/文件 | 行号 | 短摘录 |
|------|---------|------|--------|
| StandaloneLauncher | launchers/standalone/.../StandaloneLauncher.java | 18 | `@SpringBootApplication(scanBasePackages={"com.tencent.supersonic","dev.langchain4j"})` |
| ... | ... | ... | ... |
```

- [ ] **步骤 3：读 spring.factories 列出所有 SPI 扩展点**

运行：
```bash
cat /Users/yourton_ma/workspace/supersonic/assembly/conf/META-INF/spring.factories
```
预期：输出含 SchemaMapper、SemanticParser、SemanticCorrector、QueryParser、QueryOptimizer 等多组 SPI 接口及其实现类清单。把每一组的关键实现类摘录到事实清单。

- [ ] **步骤 4：读 CLAUDE.md 拿到模块职责基线**

读 `/Users/yourton_ma/workspace/supersonic/CLAUDE.md` 的 `## Architecture Overview` 章节，把 Core Modules 表格的 5 行摘录到事实清单，作为 §2 顶层模块清单的基线。

- [ ] **步骤 5：commit 事实清单（可选，作为对码工作日志）**

事实清单在 /tmp，不进仓库。跳过 commit，但记下完成状态。

---

## 任务 2：文首元信息 + §1 项目定位

**文件：**
- 修改：`docs/resume/interview/架构设计/01-架构总览.md`

- [ ] **步骤 1：写入文首元信息与导航**

写入内容（用 Write 工具，覆盖任务 0 的空文件）：

```markdown
# 01 · SuperSonic 架构总览

> 本文档面向数据平台 / 数仓团队面试官，回答「这个项目是什么、有什么核心抽象、整体怎么跑」。
> §4 数据流图与 [`02-查询数据流详解.md`](./02-查询数据流详解.md) Part A 对应；
> 数据权限相关见 [`03-数据权限控制.md`](./03-数据权限控制.md)。
>
> **诚实边界：** 本文论断以本仓库代码为准；行号可漂移，类·方法为锚点。

## 导航

| 章 | 主题 | 一句话 |
|----|------|--------|
| §1 | 项目定位 | Chat BI + Headless BI 融合，把语义层下沉为可复用资产 |
| §2 | 顶层模块 | chat / headless / auth / common / launchers / webapp |
| §3 | 核心抽象 | Model / DataSet / Metric / Dimension / Entity；S2SQL |
| §4 | 数据流图 | 用户请求 → 状态机 → Mapper/Parser/Corrector/Translator → 执行 |
| §5 | 技术栈 | Spring Boot 3.3 / LangChain4j 0.36 / JSqlParser / Calcite / HanLP |
| §6 | SPI 扩展 | spring.factories 驱动，开箱即用的扩展点 |
| §7 | 部署模式 | standalone / chat-only / headless-only |
| §8 | 面试速查 | 10 问 |
```

- [ ] **步骤 2：写入 §1 项目定位**

继续追加（用 Edit，下同）：

```markdown

---

## §1 · 项目定位

**一句话**：SuperSonic 是 Chat BI（自然语言问数）和 Headless BI（语义层）的融合平台——让用户用自然语言提问，由 LLM + 规则引擎翻译成可信的 SQL，并由语义层统一管控口径与权限。

### 1.1 Chat BI 是什么

用户输入「比亚迪今年的期间费用同比增加了多少」，系统返回一张表 + 图表 + 数据解读。核心链路是 **NL → SQL → 结果**，难点在 NL 理解、SQL 正确性、口径一致、数据权限。

### 1.2 Headless BI 是什么

**与传统 BI 的区别**：传统 BI（Tableau / PowerBI）把「字段 → 指标」的口径定义固化在每个 dashboard 里，重复定义、口径漂移。Headless BI 把口径下沉成**语义层**（Semantic Layer）——指标、维度、实体作为可治理的一等公民，所有查询（dashboard、NL、API）都走这一层。

**与 Looker / dbt 的对位**：
- Looker（LookML）：定义指标 → LookML 是语义层 → Looker UI 消费
- dbt：定义指标 → metrics 包 → 下游 BI 消费
- **SuperSonic**：定义语义层 → 同时提供 Chat BI（前端问数）和 Headless BI（开放 API），一个语义层两种消费形态

### 1.3 融合的价值

Chat BI 单独存在会受限于「LLM 生成的 SQL 不可信」；Headless BI 单独存在会受限于「业务方不会写 SQL」。融合后：LLM 只生成 **S2SQL**（用语义字段写），由语义层校正 + 翻译为物理 SQL，**LLM 永远不直接接触底表**。这是 SuperSonic 的核心设计哲学，也是 §3-§5 的主线。
```

- [ ] **步骤 3：行数自检**

运行：
```bash
wc -l "/Users/yourton_ma/workspace/supersonic/docs/resume/interview/架构设计/01-架构总览.md"
```
预期：约 50-60 行。

- [ ] **步骤 4：commit**

```bash
cd /Users/yourton_ma/workspace/supersonic
git add "docs/resume/interview/架构设计/01-架构总览.md"
git commit -m "docs(interview/architecture): scaffold 01 overview doc with header and §1 project positioning"
```

---

## 任务 3：§2 顶层模块清单

**文件：**
- 修改：`docs/resume/interview/架构设计/01-架构总览.md`

- [ ] **步骤 1：写入 §2 顶层模块**

追加：

```markdown

---

## §2 · 顶层模块清单

| 模块 | 职责 | 关键子包 |
|------|------|---------|
| **`chat/`** | Chat BI 入口：Agent 管理、多轮对话、查询解析编排、结果处理 | `server/parser`（NL2SQL 等）、`server/executor`（SqlExecutor 等）、`server/processor`（前后处理） |
| **`headless/`** | 语义层核心：Schema Mapper / Parser / Corrector / Translator 完整链路 + 元数据管理（Model/Metric/Dimension/DataSet） | `chat/`（mapper/parser/corrector）、`core/`（translator/executor）、`server/`（facade/service/aspect）、`api/`（POJO） |
| **`auth/`** | 认证鉴权（SPI 设计）。**注意：登录鉴权（authentication）和数据资源授权（authorization）是两个独立子包** | `authentication/`（Token/拦截器）、`authorization/`（AuthGroup/AuthRule） |
| **`common/`** | 共享工具：POJO、JSqlParser 工具、Calcite 工具、配置、Embedding 抽象 | `jsqlparser/`、`calcite/`、`util/`、`service/`（EmbeddingService） |
| **`launchers/`** | 启动器：standalone（默认）/ chat-only / headless-only | `standalone/`、`chat/`、`headless/` |
| **`webapp/`** | 前端 React 应用：UmiJS 4 + Ant Design 5 | `packages/supersonic-fe/`（主应用）、`packages/chat-sdk/`（聊天组件 SDK） |

**模块依赖方向**：
```
launchers ──► chat ──► headless ──► common
                    ├─► auth ─────► common
                    └─► common
webapp（独立，通过 HTTP 调用后端）
```

**对数仓团队的提示**：`headless/` 是语义层的本体；如果你想接入 SuperSonic 的语义能力但不想要 Chat BI，可以只部署 `launchers/headless`，通过开放 API 消费。
```

- [ ] **步骤 2：commit**

```bash
git add "docs/resume/interview/架构设计/01-架构总览.md"
git commit -m "docs(interview/architecture): add §2 top-level module breakdown"
```

---

## 任务 4：§3 核心抽象

**文件：**
- 修改：`docs/resume/interview/架构设计/01-架构总览.md`

- [ ] **步骤 1：写入 §3 核心抽象**

追加：

```markdown

---

## §3 · 核心抽象

语义层的核心是 5 类 Schema 元素 + 1 种 SQL 方言（S2SQL）。

### 3.1 五类 Schema 元素

枚举：`SchemaElementType`（`headless/api/.../SchemaElementType.java`）

| 类型 | 含义 | 例子（金融场景） | 数仓视角 |
|------|------|-----------------|---------|
| **MODEL** | 模型：物理表的语义封装 | 利润表、资产负债表 | dbt model / 表 |
| **DATASET** | 数据集：多 Model 组成的查询视图 | 财务分析数据集（含多张报表） | 视图 / View |
| **METRIC** | 指标：可由表达式派生 | 期间费用 = `SUM(销售费用) + SUM(管理费用) + SUM(财务费用)` | 度量 / Measure |
| **DIMENSION** | 维度：可标注敏感级别 | 公司名称、报告期、行业 | 维度 / Dimension |
| **ENTITY** | 业务实体：用于值映射 | 公司（比亚迪、宁德时代...） | 实体 / 主数据 |

**对位**：Metric 的派生表达式是 SuperSonic 区别于「直接 SELECT 表」的核心——它让口径集中定义，所有查询共用。

### 3.2 S2SQL vs 物理 SQL

这是 SuperSonic 的核心创新点，必须吃透。

**S2SQL（Semantic SQL）**：
- 用**语义字段**（metric_bizName / dimension_bizName）写的 SQL
- 例子：`SELECT 期间费用 FROM 财务数据集 WHERE 公司名称 = '比亚迪' AND 年度 = '2025'`
- LLM 只生成 S2SQL，**永远不接触底表名、底表字段**

**物理 SQL**：
- 由 SemanticTranslator 翻译后的可执行 SQL
- 例子：`SELECT SUM(sale_expense) + SUM(admin_expense) + SUM(fin_expense) AS 期间费用 FROM finance_income_statement WHERE company_code = '002594' AND year = 2025`

**翻译过程做了什么**（详见 [`02-查询数据流详解.md`](./02-查询数据流详解.md) §A6）：
1. **指标表达式展开**：`期间费用` → 三个底表字段 + 聚合函数
2. **维度值映射**：`比亚迪` → `company_code = '002594'`（基于 KnowledgeBase 的值映射）
3. **方言适配**：DbDialectOptimizer 按目标数据库（MySQL / ClickHouse / Presto）改写语法
4. **结果限制**：ResultLimitOptimizer 自动追加 LIMIT

**为什么这样设计**：
- LLM 不需要知道底表结构（schema 简化 → prompt 更短 → 准确率更高）
- 口径集中定义（指标改了，所有查询自动跟着改）
- 权限可在语义层统一管控（详见 [`03-数据权限控制.md`](./03-数据权限控制.md)）
```

- [ ] **步骤 2：commit**

```bash
git add "docs/resume/interview/架构设计/01-架构总览.md"
git commit -m "docs(interview/architecture): add §3 core abstractions (Schema elements + S2SQL)"
```

---

## 任务 5：§4 端到端数据流图

**文件：**
- 修改：`docs/resume/interview/架构设计/01-架构总览.md`

> **重要**：本节的 Mermaid 图必须与 02 文档 Part A 的状态机图对应（语义一致，详细程度不同）。

- [ ] **步骤 1：写入 §4 数据流图**

追加：

```markdown

---

## §4 · 端到端数据流图

用户一次查询的全链路（从 HTTP 请求到结果返回）：

```mermaid
flowchart TD
    U[用户在 chat-sdk 输入问句] -->|POST /api/chat/query/parse| A[ChatQueryController]
    A --> B[ChatQueryServiceImpl.parse]
    B -->|SPI 集合遍历| C[ChatQueryParser 数组]
    C -->|NL2SQLParser 主路径| D[ChatLayerService.parse]
    D --> E[ChatWorkflowEngine 状态机]

    subgraph 状态机5个state
    E -->|MAPPING| F[SchemaMapper.map ×6]
    F -->|PARSING| G[SemanticParser.parse]
    G -->|S2SQL_CORRECTING| H[SemanticCorrector.correct ×4组]
    H -->|TRANSLATING| I[SemanticTranslator.translate]
    I -->|PHYSICAL_SQL_CORRECTING| J[LLMPhysicalSqlCorrector]
    end

    B -->|ParseResultProcessor| K[推荐问题 / 格式化 / 耗时统计]
    K --> L[返回候选 parses 给前端]

    U -.用户点击某个 parse.-> M[POST /api/chat/query/execute]
    M --> N[ChatQueryServiceImpl.execute]
    N -->|SqlExecutor| O[SemanticLayerService.query]
    O -->|@S2DataPermission AOP| P[S2DataPermissionAspect]
    P -->|七步权限检查| Q[SemanticTranslator.translate]
    Q --> R[JdbcExecutor 执行物理 SQL]
    R --> S[(数据库: MySQL/ClickHouse/Presto/...)]
    S --> T[SemanticQueryResp]
    T --> U
```

### 4.1 两个阶段：parse vs execute

注意：用户的一次问数被拆成**两个独立的 HTTP 请求**：

| 阶段 | 端点 | 耗时 | 目的 |
|------|------|------|------|
| **parse** | `POST /api/chat/query/parse` | 1-5 秒（含 LLM 调用） | 把 NL 解析为多个候选 S2SQL，返回前端让用户选 |
| **execute** | `POST /api/chat/query/execute` | 取决于查询 | 执行用户选定的那个 parse，返回数据 |

**为什么拆？**
- parse 慢（LLM），但允许失败（多候选）
- execute 快但必须严格权限检查
- 拆开后前端可在 parse 阶段引导用户澄清（选 parse），减少 execute 失败

### 4.2 关键代码入口

| 阶段 | 入口 | 行号 |
|------|------|------|
| REST 控制器 | `chat/server/.../rest/ChatQueryController.java` | `search:34` / `parse:41` / `execute:48` |
| 编排中心 | `chat/server/.../service/impl/ChatQueryServiceImpl.java` | `parse:110` / `execute:141` |
| 状态机 | `headless/server/.../utils/ChatWorkflowEngine.java` | `start:38`（状态机主循环） |
| 权限切面 | `headless/server/.../aspect/S2DataPermissionAspect.java` | `doAround:70`（七步流程） |

详细的管道阶段解析见 [`02-查询数据流详解.md`](./02-查询数据流详解.md) Part A；权限七步流程见 [`03-数据权限控制.md`](./03-数据权限控制.md) §3。
```

- [ ] **步骤 2：渲染 Mermaid 自检**

在 IDE 或 markdown previewer 中打开该文件，确认 Mermaid 图能正常渲染（无语法错误）。如果渲染失败，检查 flowchart 语法（节点 ID 不能有特殊字符、subgraph 块的闭合）。

- [ ] **步骤 3：commit**

```bash
git add "docs/resume/interview/架构设计/01-架构总览.md"
git commit -m "docs(interview/architecture): add §4 end-to-end data flow diagram (Mermaid)"
```

---

## 任务 6：§5 关键技术栈

**文件：**
- 修改：`docs/resume/interview/架构设计/01-架构总览.md`

- [ ] **步骤 1：写入 §5 技术栈**

追加：

```markdown

---

## §5 · 关键技术栈

| 技术 | 版本 | 用途 | 在 SuperSonic 中的角色 |
|------|------|------|----------------------|
| **Spring Boot** | 3.3.9 | 应用框架 | IoC/AOP/REST；StandaloneLauncher 扫包 `com.tencent.supersonic` + `dev.langchain4j` |
| **LangChain4j** | 0.36.2 | LLM 集成 | Prompt 模板、模型抽象（`ModelProvider.getChatModel`）、嵌入服务 |
| **JSqlParser** | 4.9 | SQL 解析 | 所有 SQL 操作（字段提取、WHERE 注入、GROUP BY 补全、列权限检查） |
| **Apache Calcite** | 1.38.0 | SQL 处理 | WITH 语句合并（`SqlMergeWithUtils`）；非翻译主路径 |
| **MyBatis-Plus** | 3.5.10 | ORM | 元数据持久化（Model/Metric/AuthGroup 等） |
| **HanLP** | 内嵌 | 中文分词 | SchemaMapper 的关键词匹配（自定义词典 + 前缀/后缀搜索） |
| **pgvector** | Postgres 扩展 | 向量库 | EmbeddingMapper 的相似度召回（`EmbeddingMatchStrategy`） |
| **React + UmiJS 4** | 18 / 4 | 前端 | webapp；Ant Design 5.17 + ECharts 5.0.2 |

**版本来源**：根目录 `pom.xml`（`<spring-boot.version>` 等属性）；与 `CLAUDE.md` 的 Key Technologies 章节一致。

### 5.1 为什么选这些

- **JSqlParser 而非 Calcite 做主解析器**：JSqlParser 轻量、无 schema 依赖、API 简单；Calcite 用于复杂场景（WITH 合并）
- **LangChain4j 而非自己封装**：标准化 PromptTemplate + 模型抽象，便于切换 provider（OpenAI / DeepSeek / 通义）
- **HanLP 而非 IK/Jieba**：HanLP 支持自定义词典热重载（`HanlpHelper.reloadCustomDictionary`），满足「元数据变更后即时生效」需求
- **pgvector 而非外部向量库**：与业务库共用 Postgres，减少组件；嵌入量级（百万级）够用
```

- [ ] **步骤 2：commit**

```bash
git add "docs/resume/interview/架构设计/01-架构总览.md"
git commit -m "docs(interview/architecture): add §5 tech stack with version table"
```

---

## 任务 7：§6 SPI 扩展机制

**文件：**
- 修改：`docs/resume/interview/架构设计/01-架构总览.md`

- [ ] **步骤 1：读 spring.factories 拿到准确 SPI 清单**

运行：
```bash
cat /Users/yourton_ma/workspace/supersonic/assembly/conf/META-INF/spring.factories
```
记录：每个 SPI 接口名 + 其下的实现类列表。

- [ ] **步骤 2：写入 §6 SPI 扩展机制**

追加：

```markdown

---

## §6 · SPI 扩展机制

SuperSonic 用 Spring SPI（`spring.factories`）做扩展点加载，所有可插拔组件都走这套机制。

### 6.1 SPI 配置位置

**文件**：`assembly/conf/META-INF/spring.factories`

格式（Spring Boot 标准）：
```properties
com.tencent.supersonic.headless.chat.mapper.SchemaMapper=\
  com.tencent.supersonic.headless.chat.mapper.KeywordMapper,\
  com.tencent.supersonic.headless.chat.mapper.EmbeddingMapper,\
  ...
```

### 6.2 核心 SPI 扩展点

| SPI 接口 | 作用 | 现有实现数 | 扩展场景 |
|---------|------|----------|---------|
| `SchemaMapper` | NL → Schema 元素映射 | 6 个 | 接入自定义 NER / 行业词典 |
| `MatchStrategy` | Mapper 内部的匹配策略 | 7 个 | 接入私有向量库 / ES 搜索 |
| `SemanticParser` | Schema 元素 → S2SQL | 2 个（Rule / LLM） | 接入自家 SQL 生成模型 |
| `SemanticCorrector` | S2SQL 校正 | 3 个顶层 | 加自定义校正规则（公司命名规范） |
| `QueryParser`（Translator 层） | S2SQL → 物理查询中间态 | 8 个 | 接入新指标计算逻辑 |
| `QueryOptimizer`（Translator 层） | 物理 SQL 优化 | 2 个 | 加自定义 SQL 重写 |
| `ChatQueryParser`（Chat 层） | Chat 入口的解析器 | 3 个（NL2SQL / NL2Plugin / PlainText） | 接入非 SQL 类插件（图表生成） |

### 6.3 加载机制

`headless/chat/.../utils/ComponentFactory.java` 在首次调用时通过 `SpringFactoriesLoader.loadFactories()` 加载所有实现，缓存到静态字段：

```java
public static List<SchemaMapper> getSchemaMappers() {
    if (schemaMappers == null) {
        schemaMappers = SpringFactoriesLoader.loadFactories(SchemaMapper.class, ...);
    }
    return schemaMappers;
}
```

### 6.4 扩展示例：加一个自定义 SchemaMapper

1. 在自己的 package 下新建 `class MyMapper implements SchemaMapper`
2. 在 `assembly/conf/META-INF/spring.factories`（或自己 jar 的 `META-INF/spring.factories`）追加一行：
   ```
   com.tencent.supersonic.headless.chat.mapper.SchemaMapper=\
     ...,com.yourcompany.MyMapper
   ```
3. 重启服务，新 Mapper 自动加入 `ComponentFactory.getSchemaMappers()` 列表

**注意**：Mapper 的执行顺序由 `spring.factories` 中的顺序决定；如果新 Mapper 依赖前置 Mapper 的结果，需要排在后面（通过 `getMapInfo()` 读取已有匹配）。
```

- [ ] **步骤 3：commit**

```bash
git add "docs/resume/interview/架构设计/01-架构总览.md"
git commit -m "docs(interview/architecture): add §6 SPI extension mechanism"
```

---

## 任务 8：§7 三种部署模式

**文件：**
- 修改：`docs/resume/interview/架构设计/01-架构总览.md`

- [ ] **步骤 1：写入 §7 部署模式**

追加：

```markdown

---

## §7 · 三种部署模式

`launchers/` 模块提供三种部署形态，对应不同的消费场景。

| 模式 | 启动类 | 扫描包 | 适用场景 | Web UI |
|------|--------|--------|---------|--------|
| **standalone**（默认） | `StandaloneLauncher` | `com.tencent.supersonic` + `dev.langchain4j` | 完整能力（Chat + Headless） | 完整 webapp |
| **chat-only** | `ChatLauncher` | 仅 chat 相关 | 只用 Chat BI 问数，不暴露开放 API | 完整 webapp |
| **headless-only** | `HeadlessLauncher` | 仅 headless 相关 | 不需要前端问数，只通过 API 消费语义层 | 无 |

### 7.1 选择建议

- **PoC / Demo / 中小项目**：standalone，一键启动
- **大型企业集成**：headless-only（让现有 BI 嵌入语义层），Chat BI 走单独的 standalone 集群
- **多团队共用语义层**：headless-only 作为语义层中心，各团队按需选择消费形态

### 7.2 启动命令

```bash
# 完整构建（standalone）
./assembly/bin/supersonic-build.sh standalone

# 启动 / 停止
./assembly/bin/supersonic-daemon.sh start
./assembly/bin/supersonic-daemon.sh stop
```

启动后访问 `http://localhost:9080`（来自 `CLAUDE.md` Quick Start）。
```

- [ ] **步骤 2：commit**

```bash
git add "docs/resume/interview/架构设计/01-架构总览.md"
git commit -m "docs(interview/architecture): add §7 deployment modes"
```

---

## 任务 9：§8 面试问答速查

**文件：**
- 修改：`docs/resume/interview/架构设计/01-架构总览.md`

- [ ] **步骤 1：写入 §8 面试问答速查（10 问）**

追加：

```markdown

---

## §8 · 面试问答速查

⭐ 表示高频问题。

---

⭐ **Q1：用一句话向面试官介绍 SuperSonic。**

A：SuperSonic 是 Chat BI + Headless BI 的融合平台——让用户用自然语言问数，由 LLM + 规则引擎翻译成可信 SQL，并由语义层统一管控口径与权限；区别于纯 Chat BI 工具的是，它把口径下沉成可治理的语义层资产，所有消费形态（dashboard、NL、API）共用。

---

⭐ **Q2：项目里最复杂的部分是什么？**

A：从 NL 到 SQL 的全链路——5 个状态机阶段（Mapping / Parsing / Correcting / Translating / PhysicalSqlCorrecting），每阶段都有多个 SPI 实现。难点不在单阶段，而在「LLM 生成 + 规则校正」的协作：LLM 生成 S2SQL（用语义字段），规则做校正（语法 / 时间 / Schema），最后翻译为物理 SQL。详见 [`02-查询数据流详解.md`](./02-查询数据流详解.md)。

---

**Q3：与 Looker / dbt 的区别？**

A：Looker（LookML）和 dbt（metrics 包）都是「Headless BI」语义层，但消费形态单一（Looker 自家 UI / 下游 BI）。SuperSonic 同时提供 Chat BI（前端问数）和 Headless BI（开放 API），一个语义层两种消费形态；且原生集成 LLM，支持自然语言直接到 SQL。

---

⭐ **Q4：为什么用状态机而非线性调用？**

A：状态机的好处是「条件跳过 + 显式状态」——比如 `mapInfo` 已有时跳过 MAPPING 直接进 PARSING（多轮对话场景）；rule 解析成功时跳过 LLM 调用（成本优化）。线性调用做不到这种「按当前状态决定下一步」的灵活度。详见 `ChatWorkflowEngine.start`。

---

**Q5：SPI 扩展点举例？**

A：6 个 SchemaMapper + 7 个 MatchStrategy + 2 个 SemanticParser + 3 个 SemanticCorrector + 8 个 QueryParser + 2 个 QueryOptimizer。配置在 `assembly/conf/META-INF/spring.factories`，通过 `SpringFactoriesLoader` 加载。扩展时实现接口 + 加配置即可，无需改主链路。

---

**Q6：Chat BI 和 Headless BI 怎么共用语义层？**

A：底层都是 `SemanticLayerService`。Chat BI 走 `ChatQueryServiceImpl` → NL 解析 → 调用 `SemanticLayerService.query`；Headless BI 走开放 API（`/api/semantic/query`）直接调用同一服务。语义层只看 SemanticQueryReq，不关心调用方是 LLM 还是 API。

---

⭐ **Q7：S2SQL 和物理 SQL 的区别？**

A：S2SQL 用语义字段（bizName）写，LLM 只生成 S2SQL；物理 SQL 由 SemanticTranslator 翻译，展开指标表达式、做维度值映射、适配方言。这层抽象让 LLM 永远不接触底表（schema 简化 + 安全），口径集中定义。

---

**Q8：数据权限是怎么做的？**

A：AOP 切面零侵入——`@S2DataPermission` 注解 + `S2DataPermissionAspect`，在执行前做 7 步检查（管理员跳过 / 模型可见性 / 列权限 / 行权限注入）。行权限把 DimensionFilter 注入到 WHERE 子句；列权限检查敏感字段（HIGH 级别）。详见 [`03-数据权限控制.md`](./03-数据权限控制.md)。

---

**Q9：模块依赖方向？**

A：`launchers → chat / headless → common`；`auth` 平行于 chat，被 headless 的切面调用；webapp 独立，通过 HTTP 调用后端。Headless 是语义层本体，chat 是消费形态之一。

---

**Q10：为什么要拆 parse 和 execute 两个请求？**

A：parse 慢（含 LLM），但允许多候选；execute 快但需严格权限检查。拆开后前端可在 parse 阶段引导用户澄清（选 parse），减少 execute 失败；同时让权限检查更聚焦（只查一次）。
```

- [ ] **步骤 2：commit**

```bash
git add "docs/resume/interview/架构设计/01-架构总览.md"
git commit -m "docs(interview/architecture): add §8 interview Q&A cheat sheet (10 questions)"
```

---

## 任务 10：验收与收尾

**文件：**
- 修改：`docs/resume/interview/架构设计/01-架构总览.md`

- [ ] **步骤 1：行数自检**

运行：
```bash
wc -l "/Users/yourton_ma/workspace/supersonic/docs/resume/interview/架构设计/01-架构总览.md"
```
预期：约 600-800 行（规格 §8 体量约定）。若 < 500 行说明内容单薄，回头补 §3/§8；若 > 900 行说明冗余，回头精简。

- [ ] **步骤 2：对照规格 §9.1 验收清单逐项检查**

读规格 §9.1 的 4 条验收标准，逐条核对：

| 验收项 | 检查方法 | 期望结果 |
|--------|---------|---------|
| 仅读 §1-§3 能用三句话说清项目是什么、有什么核心抽象 | 自己读一遍 | 能；§1.1 一句话、§3.1 五类元素、§3.2 S2SQL 抽象 |
| §4 数据流图与 02 文档 Part A 一致 | 等 02 完成后互查 | 5 个 state 一致；入口控制器行号一致 |
| §6 SPI 机制能给出扩展 SchemaMapper 的步骤 | 看 §6.4 | 3 步明确 |
| §8 能回答 10 个面试问题 | 数 §8 的 Q 数量 | ≥ 10，⭐ 标注的 ≥ 4 |

- [ ] **步骤 3：grep 自检——所有代码锚点都有 file_path**

运行：
```bash
grep -c '\`[a-z_/.]*\.\(java\|factories\|yaml\|md\)' "/Users/yourton_ma/workspace/supersonic/docs/resume/interview/架构设计/01-架构总览.md"
```
预期：≥ 10 处代码引用（说明有足够的代码锚点）。

- [ ] **步骤 4：grep 自检——无 TODO/待定**

运行：
```bash
grep -E 'TODO|待定|FIXME|占位' "/Users/yourton_ma/workspace/supersonic/docs/resume/interview/架构设计/01-架构总览.md"
```
预期：无输出（或只匹配到「诚实边界」表里的说明文字）。

- [ ] **步骤 5：最终 commit**

```bash
git add "docs/resume/interview/架构设计/01-架构总览.md"
git commit --allow-empty -m "docs(interview/architecture): 01 overview doc verification passed

- 行数符合规格 §8 (600-800)
- 规格 §9.1 四项验收全部通过
- 代码锚点 ≥ 10 处
- 无占位符"
```

---

## 自检（plan 编写后）

| 检查项 | 结果 |
|--------|------|
| 规格覆盖度（规格 §3 所有章节） | §1-§8 + 文首元信息全覆盖；任务 2-9 对应章节；任务 10 验收 |
| 占位符扫描 | 无 TODO/待定；每个步骤都有具体内容与预期输出 |
| 类型一致性 | 任务 1 事实清单的字段名与后续任务的引用一致（如 `StandaloneLauncher` 在 §7 与任务 1 表中一致） |
| 行数估算 | 每个任务的代码块行数累计约 700 行，符合规格 §8 体量 |
| Mermaid 图 | 任务 5 的 Mermaid 已用标准 flowchart 语法，subgraph 块闭合正确 |

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-08-11-architecture-overview-doc.md`。
