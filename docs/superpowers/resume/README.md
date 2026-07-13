# SuperSonic 实习：简历文案汇总

## 基本信息

- **单位**：广东省智能科学与技术研究院 — 金融工商智能实验室 — 数据平台组
- **岗位**：全栈开发实习生
- **时间**：2025 - 2026（待补充具体月份）
- **项目**：SuperSonic（开源 Chat BI + Headless BI 平台，Spring Boot + React）

---

## 简历段落（终版）

```
全栈开发实习生 | 广东省智能科学与技术研究院 金融工商智能实验室

- [待定] Text2SQL 评测体系...

- 设计并实现 Chat-BI 记忆管理模块，支持历史 SQL/查询结果自动注入 LLM 提示词
  以提升语义解析准确率；引入 LLM 定期自动评审 + 管理员人工评审双机制，实现
  记忆库的持续质量管控

- 主导 Chat-BI 对话页面的交互升级，将原有的精简问答模式扩展为完整分析模式，
  新增 SQL 可视化、图表渲染、多步骤分析链路等能力，提升用户从提问到洞察的
  端到端体验

- 抽离 Chat-BI 对话能力为独立前端 SDK（supersonic-chat-sdk），基于
  React + TypeScript + Rollup 构建，支持 Chat 对话与 Copilot 嵌入式助手
  两种集成模式
```

---

## 技术栈速览（面试自我介绍用）

| 层级 | 技术 |
|------|------|
| 后端 | Java 21, Spring Boot 3.3, MyBatis-Plus, LangChain4j, Maven |
| 前端 | React 18, TypeScript, UmiJS 4, Ant Design 5, ECharts 5, Rollup |
| AI/LLM | DeepSeek, DashScope (Qwen), BGE Embedding, Prompt Engineering |
| 数据 | PostgreSQL + pgvector, H2, SQLite, MyBatis |
| 工程化 | pnpm monorepo, Docker, Git, REST API |

---

## 补充材料索引（面试中可选展开）

以下方向实际工作中有所涉及，简历中因篇幅限制未包含，面试中可根据对话流向选择性展开：

### 安全与权限

> JWT + App-Key 双因子鉴权、AES-ECB 密码加密、is_open/admin 多粒度可见性控制。适用于「项目中怎么保证数据安全？」类问题。

详见：`docs/superpowers/specs/2026-07-13-supersonic-resume-bullets-design.md` 补充材料章节

### CSMAR 数据导入管线

> Excel 数据 → PostgreSQL → REST API 自动创建 Domain/Dataset/Model/Agent 全链路自动化。适用于「有没有数据工程经验？」类问题。

详见：`~/.hermes/skills/devops/csmar-supersonic-data-pipeline/SKILL.md`

### Embedding 与语义映射

> BGE-small-zh 值级 embedding、pgvector 检索、LLM 增强映射、HanLP 分词适配。适用于「Embedding 是怎么做的？」「为什么需要 LLM 增强映射？」类问题。

详见：`~/.hermes/skills/devops/supersonic-custom-dataset-setup/SKILL.md`

### 框架级 Bug 修复

> EmbeddingMapper dataSetId 丢失、NL2SQLParser LLM 降级缺失、TextSegmentConvert metadata 截断、Jackson 枚举反序列化失败、Calcite SqlBuilder fallback 等 10+ 处修复。适用于「有没有 debug 复杂问题的经历？」「源码阅读能力怎么样？」类问题。

详见：`~/.hermes/skills/devops/csmar-supersonic-data-pipeline/SKILL.md` Post-Setup 修复清单章节

---

## 文档索引

| 文件 | 内容 |
|------|------|
| `docs/superpowers/specs/2026-07-13-supersonic-resume-bullets-design.md` | 设计文档（含各点设计思路和面试追问预案概要） |
| `docs/superpowers/resume/01-evaluation-discussion-agenda.md` | 第 1 点评测体系讨论议程 |
| `docs/superpowers/resume/02-memory-module.md` | 第 2 点 Memory 模块：文案 + 面试 Q&A（6 问） |
| `docs/superpowers/resume/03-chat-bi-ux-upgrade.md` | 第 3 点 Chat-BI 交互升级：文案 + 面试 Q&A（5 问） |
| `docs/superpowers/resume/04-chat-sdk.md` | 第 4 点 chat-sdk：文案 + 面试 Q&A（6 问） |
| `docs/superpowers/plans/2026-07-13-supersonic-resume-bullets.md` | 实现计划 |
