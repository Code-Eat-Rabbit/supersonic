# 简历实习经历包装：SuperSonic 全栈开发实习生

## 元信息

- **实习单位**：广东省智能科学与技术研究院 — 金融工商智能实验室 — 数据平台组
- **岗位 title**：全栈开发实习生
- **目标投递**：2026 届春秋招，海投策略
- **项目仓库**：SuperSonic（Chat BI + Headless BI 开源项目）
- **简历点数**：4 个（1 个待定，3 个已确定）

---

## 第 1 点：Text2SQL 测评体系（⏸️ 待定）

> **状态**：后续单独讨论，暂不纳入本次输出。

方向概述：搭建 Text2SQL 评测体系，接入 DeepSeek、DashScope 等多模型，需确定具体准确率指标等量化数据后最终定型。

---

## 第 2 点：Memory 记忆管理模块

### 简历写法

> 设计并实现 Chat-BI 记忆管理模块，支持历史 SQL/查询结果自动注入 LLM 提示词以提升语义解析准确率；引入 LLM 定期自动评审 + 管理员人工评审双机制，实现记忆库的持续质量管控

### 设计思路

- 三条能力线：SQL 注入 → 提升解析准确率 | LLM 自评 → 自动化运维 | 人工评审 → 兜底机制
- 「记忆库质量管控」将评审包装为系统化工程能力，而非一次性功能
- 措辞简洁、一句到位，面试追问时可展开详细架构

### 面试追问预案

- 注入策略：基于 chatId 关联历史 SQL，构建 few-shot 示例注入提示词
- 评审周期：LLM 定期扫描记忆库（MEMORY_REVIEW），评估记忆质量并清理低效条目
- 人工评审入口：管理员通过管理后台审核/修正 LLM 记忆

---

## 第 3 点：Chat-BI 对话交互升级

### 简历写法

> 主导 Chat-BI 对话页面的交互升级，将原有的精简问答模式扩展为完整分析模式，新增 SQL 可视化、图表渲染、多步骤分析链路等能力，提升用户从提问到洞察的端到端体验

### 设计思路

- 「主导交互升级」— 独立推动产品改进，非被动执行
- 「精简 → 完整」的对比线清晰，面试官易记住
- 三个具体扩展点（SQL 可视化、图表渲染、多步骤链路）供追问
- 技术栈：React 18 + UmiJS 4 + Ant Design 5 + ECharts

### 面试追问预案

- 精简模式 vs 完整模式的核心差异：完整模式增加了 query → parse → execute 分步展示、SQL 格式高亮、多图表类型渲染（Table/Pie/MetricTrend）
- 多步骤分析链路：对话流支持上下文关联，用户可基于上一次分析结果继续追问

---

## 第 4 点：chat-sdk 前端组件库

### 简历写法

> 抽离 Chat-BI 对话能力为独立前端 SDK（supersonic-chat-sdk），基于 React + TypeScript + Rollup 构建，支持 Chat 对话与 Copilot 嵌入式助手两种集成模式

### 设计思路

- 「抽离为独立 SDK」→ 代码架构抽象能力，非简单封装
- TypeScript + Rollup → 前端工程化关键词
- Chat + Copilot 双模式 → 产品化思维
- 简洁一句，所有关键词都是可追问的锚点

### 面试追问预案

- 工程化：Rollup 打包 ESM + UMD 双格式，peerDependencies 管理 React 共享，TypeScript 类型声明
- Copilot 模式：通过 ref 暴露 `sendCopilotMsg` 方法，外部按钮可直接触发预设查询
- 与主项目的协作：通过 pnpm link 本地引用，主站和 SDK 独立开发/独立版本
- 组件范围：ChatMsg（Table/Pie/MetricTrend/MetricCard）+ 下钻维度 + 推荐问题 + 搜索建议

---

## 不纳入简历的补充材料

以下方向在实际工作中有所涉及，但考虑到简历篇幅限制和面试深度可控性，作为补充材料（面试中被问到时可选择性展开）：

- **行列权限**：JWT + App-Key 双因子鉴权、is_open/admin 多粒度可见性控制、AES-ECB 密码加密。可作为「安全相关经验」在面试中提及
- **CSMAR 数据管线**：Excel 导入 → PostgreSQL → REST API 自动创建 Domain/Dataset/Model/Agent 全链路自动化
- **Embedding 与语义映射**：BGE-small-zh 值级 embedding、LLM 增强映射、HanLP 分词适配
- **框架级 Bug 修复**：EmbeddingMapper dataSetId 丢失、NL2SQLParser LLM 降级缺失、TextSegmentConvert metadata 截断等 10+ 处修复
