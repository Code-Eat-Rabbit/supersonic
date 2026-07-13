# 面试追问 Anki 闪卡

> **格式**：Q&A（非 Cloze），中文注释，标签 `LC-100-resume`
> **使用**：复制到 Anki，或通过 AnkiConnect API 批量导入

---

## Memory 模块（4 张）

### Card 1
**Q：** 记忆注入机制是什么？什么时候触发？
**A：** 基于向量检索的 few-shot 注入。用户每次 NL 查询时，将问题向量化 → 在 pgvector 的 `memory_collection_{agentId}` 中做 ANN 检索 → TOP K 相似记忆作为 Text2SQLExemplar 注入 LLM prompt。仅注入 ENABLED 状态的记忆。
**标签：** LC-100-resume LC-100-memory

### Card 2
**Q：** LLM 自动评审的实现方式？
**A：** `MemoryReviewTask` 定时任务（@Scheduled 60s）。遍历 Agent → 拉取 PENDING 记忆 → 拼入评审 prompt（角色：资深数据工程师）→ 调用 LLM 输出 `opinion=(POSITIVE|NEGATIVE)`。POSITIVE → 自动 ENABLED + 写入向量库；NEGATIVE → 保持 PENDING 等待人工。
**标签：** LC-100-resume LC-100-memory

### Card 3
**Q：** 人工评审的入口是什么？
**A：** `POST /api/chat/memory/updateMemory`，传入 `humanReviewRet: POSITIVE/NEGATIVE`。前端管理后台分页查询记忆列表，按状态/评审结果筛选。支持批量删除。
**标签：** LC-100-resume LC-100-memory

### Card 4
**Q：** MEMORY_REVIEW 和 REWRITE_MULTI_TURN 的区别？
**A：** MEMORY_REVIEW 是「SQL 质量评审」——判断这条 SQL 是否值得作为 few-shot 注入后续查询。REWRITE_MULTI_TURN 是「指代消解」——把「他的教育背景是什么」中的「他」改写为具体人名。两者协同：先消解指代 → 再结合靠谱 few-shot → 发给 LLM。
**标签：** LC-100-resume LC-100-memory

---

## Chat-BI 交互升级（4 张）

### Card 5
**Q：** 精简模式 vs 完整分析模式的核心差异？
**A：** 通过 Agent 的 `toolConfig.simpleMode` 控制。精简模式：只展示问答结果。完整模式：额外展示 SQL 可视化（语法高亮）、图表渲染（ECharts）、维度筛选/日期范围调整、多解析结果切换、相似问题推荐、数据导出。精简模式 = 只给结论，完整模式 = 展示推理过程 + 允许用户介入。
**标签：** LC-100-resume LC-100-chatbi

### Card 6
**Q：** Chat-BI 的多步骤分析链路是怎么实现的？
**A：** ChatItem 内部状态机：Parse 阶段（调用 chatParse，若多候选则展示 ExpandParseTip 供用户选择）→ 用户干预（切换解析/调整筛选/实体切换）→ Execute 阶段（chatExecute + getExecuteSummary 伪流式轮询 500ms 间隔）→ ExecuteItem 按 queryMode 分发到不同图表组件。dataCache 缓存已执行结果避免重复请求。
**标签：** LC-100-resume LC-100-chatbi

### Card 7
**Q：** 前端技术栈为什么选 UmiJS + Ant Design？
**A：** React 18 + UmiJS 4（约定式路由 + 插件体系，适合中后台） + Ant Design 5.17（企业级中后台标准） + ECharts 5.4（国产生态、中文文档完善） + ahooks 轻量状态管理（非 Redux，Chat-BI 场景以局部状态为主）。构建通过 start-fe-prod.sh 打包 tar.gz 部署到 Spring Boot classpath:/webapp/。
**标签：** LC-100-resume LC-100-chatbi

### Card 8
**Q：** SQL 可视化是怎么实现的？
**A：** SqlItem 组件：sql-formatter 格式化 SQL → react-syntax-highlighter 语法高亮。展示四层 SQL：parsedS2SQL（LLM 中间表示）、correctedS2SQL（纠正后）、querySQL（最终执行）、correctedQuerySQL（物理优化后）。开发者模式下额外展示 LLM 请求/响应。
**标签：** LC-100-resume LC-100-chatbi

---

## chat-sdk（4 张）

### Card 9
**Q：** 为什么要抽离 chat-sdk？依赖关系是什么？
**A：** 复用 + 解耦。Chat-BI 能力被多场景消费（主站/第三方嵌入/demo），通过 pnpm link 本地引用。SDK 的 peerDependencies 声明 React 共享（避免重复打包），Rollup 排除宿主依赖只打包 SDK 自身代码。
**标签：** LC-100-resume LC-100-sdk

### Card 10
**Q：** Rollup 打包配置？为什么不用 Webpack？
**A：** SDK 是组件库（library）非应用（application）。Rollup 对库打包支持更好：ESM/UMD 多格式输出、tree-shaking 更彻底、产物更干净。配置：ESM（dist/index.es.js）+ UMD（dist/index.umd.js）。构建链路：tsc 类型检查 → Rollup ESM → Rollup UMD。
**标签：** LC-100-resume LC-100-sdk

### Card 11
**Q：** Chat 和 Copilot 两种模式的设计差异？
**A：** Chat = 独立对话页面（主动输入+多轮对话）。Copilot = 嵌入式助手（外部按钮触发预设查询，通过 ref 暴露 sendCopilotMsg()）。Chat 支持 Agent 选择面板，Copilot 由外部按钮指定 Agent。
**标签：** LC-100-resume LC-100-sdk

### Card 12
**Q：** SDK 如何隔离主题样式？
**A：** Less + CSS Modules（组件级隔离）。PREFIX_CLS 统一前缀避免 CSS 冲突。Ant Design 为 dependencies（SDK 内部需要），React 为 peerDependencies（与宿主共享版本，防止 hooks 报错）。
**标签：** LC-100-resume LC-100-sdk
