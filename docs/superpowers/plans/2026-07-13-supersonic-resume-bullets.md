# SuperSonic 实习简历包装 实现计划

> **面向 AI 代理的工作者：** 使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 基于设计文档产出 4 条简历 bullet points + 每条对应的面试追问预案 + 待定评测体系讨论会

**架构：** 纯文案生成任务，无代码。每条 bullet 需最终调优措辞 + 配套面试 Q&A 卡片。第 1 点（评测体系）单独安排讨论会话确定量化指标。

**技术栈：** Markdown 文案，参考 SuperSonic 源码做事实核查

---

### 前置：确认设计文档

确认 `docs/superpowers/specs/2026-07-13-supersonic-resume-bullets-design.md` 已审阅通过。

---

### 任务 1：第 2 点 Memory 简历文案 + 面试预案

**产出：** `docs/superpowers/resume/02-memory-module.md`

- [ ] **步骤 1：终版简历文案（1 句）**

内容：
> 设计并实现 Chat-BI 记忆管理模块，支持历史 SQL/查询结果自动注入 LLM 提示词以提升语义解析准确率；引入 LLM 定期自动评审 + 管理员人工评审双机制，实现记忆库的持续质量管控

- [ ] **步骤 2：面试追问 Q&A（3-5 问）**

格式：Q → A（结构化回答，含技术细节）

覆盖方向：
- 记忆注入机制（何时触发、注入格式、token 预算管理）
- LLM 自动评审的实现方式（周期、评估标准、清理策略）
- 人工评审入口与权限控制
- 与多轮对话（REWRITE_MULTI_TURN）的关系
- 记忆库存储方案（数据库表结构）

- [ ] **步骤 3：Commit**

```bash
git add docs/superpowers/resume/02-memory-module.md
git commit -m "docs: resume bullet 2 - memory module + interview Q&A"
```

---

### 任务 2：第 3 点 Chat-BI 交互升级 简历文案 + 面试预案

**产出：** `docs/superpowers/resume/03-chat-bi-ux-upgrade.md`

- [ ] **步骤 1：终版简历文案（1 句）**

内容：
> 主导 Chat-BI 对话页面的交互升级，将原有的精简问答模式扩展为完整分析模式，新增 SQL 可视化、图表渲染、多步骤分析链路等能力，提升用户从提问到洞察的端到端体验

- [ ] **步骤 2：面试追问 Q&A（3-5 问）**

覆盖方向：
- 精简模式 vs 完整模式的具体差异（UI 对比、用户流程）
- SQL 可视化实现方式（sql-formatter + syntax highlighter 选型）
- 图表渲染类型（Table/Pie/MetricTrend/MetricCard）及各自适用场景
- 多步骤分析链路的技术实现（parse → execute 分步渲染、状态机）
- 前端技术栈选型考量（UmiJS vs CRA、Ant Design 版本）

- [ ] **步骤 3：Commit**

```bash
git add docs/superpowers/resume/03-chat-bi-ux-upgrade.md
git commit -m "docs: resume bullet 3 - chat-bi UX upgrade + interview Q&A"
```

---

### 任务 3：第 4 点 chat-sdk 组件库 简历文案 + 面试预案

**产出：** `docs/superpowers/resume/04-chat-sdk.md`

- [ ] **步骤 1：终版简历文案（1 句）**

内容：
> 抽离 Chat-BI 对话能力为独立前端 SDK（supersonic-chat-sdk），基于 React + TypeScript + Rollup 构建，支持 Chat 对话与 Copilot 嵌入式助手两种集成模式

- [ ] **步骤 2：面试追问 Q&A（3-5 问）**

覆盖方向：
- 组件抽离的架构决策（为什么抽离 SDK、与主项目的依赖关系）
- Rollup 打包配置（ESM/UMD 双格式、peerDependencies 管理、tree-shaking）
- Chat 模式 vs Copilot 模式的设计差异（独立页面 vs 嵌入式）
- Copilot 的 API 设计（ref 暴露 sendCopilotMsg，外部触发机制）
- 主项目引用方式（pnpm link 本地开发、npm publish 发布流程）
- TypeScript 类型安全设计（导出类型定义、泛型约束）

- [ ] **步骤 3：Commit**

```bash
git add docs/superpowers/resume/04-chat-sdk.md
git commit -m "docs: resume bullet 4 - chat-sdk + interview Q&A"
```

---

### 任务 4：第 1 点评测体系讨论会准备

**产出：** `docs/superpowers/resume/01-evaluation-discussion-agenda.md`

- [ ] **步骤 1：讨论议程大纲**

内容：梳理评测体系讨论需要确定的议题清单

- 需确定的指标：整体准确率、easy/medium/hard 分级准确率、执行准确率 vs 逻辑形式准确率
- 需要的数据：evaluation/ 目录下是否有已有测评结果可引用
- 简历措辞方向：强调「搭建体系」还是「指标结果」
- 模型对比维度：DeepSeek vs DashScope vs 其他

- [ ] **步骤 2：摸底现有数据**

从 `evaluation/` 目录查找已有测评结果（error_case.json, 日志文件等），整理到议程中作为讨论基础。

- [ ] **步骤 3：Commit**

```bash
git add docs/superpowers/resume/01-evaluation-discussion-agenda.md
git commit -m "docs: resume bullet 1 - evaluation discussion agenda"
```

---

### 任务 5：简历合集 + 补充材料整合

**产出：** `docs/superpowers/resume/README.md`

- [ ] **步骤 1：简历段落总稿**

将所有已确认 bullet 整合为一段连续的简历描述：

```
全栈开发实习生 | 广东省智能科学与技术研究院 金融工商智能实验室 数据平台组

- 设计并实现 Chat-BI 记忆管理模块...
- 主导 Chat-BI 对话页面的交互升级...
- 抽离 Chat-BI 对话能力为独立前端 SDK...
- [待定] Text2SQL 测评体系...
```

- [ ] **步骤 2：补充材料索引**

列出可选展示的补充方向（权限、数据管线、Embedding、Bug 修复），标注何时提及（如面试官问到安全/数据工程时）。

- [ ] **步骤 3：Commit**

```bash
git add docs/superpowers/resume/README.md
git commit -m "docs: resume master doc - all bullets + supplementary index"
```

---

### 任务 6：Anki 闪卡（可选）

**产出：** `docs/superpowers/resume/anki-cards.md`

- [ ] **步骤 1：生成面试追问 Anki 卡片**

将每条 bullet 的 Q&A 转换为 Anki 格式（Q&A，非 Cloze），标签 `LC-100-resume`，方便面试前刷题式复习。

- [ ] **步骤 2：Commit**

```bash
git add docs/superpowers/resume/anki-cards.md
git commit -m "docs: resume interview prep anki cards"
```
