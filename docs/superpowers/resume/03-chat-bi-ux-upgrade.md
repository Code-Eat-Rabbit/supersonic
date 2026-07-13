# Chat-BI 对话交互升级 — 简历文案 + 面试预案

## 简历文案（终版）

> 主导 Chat-BI 对话页面的交互升级，将原有的精简问答模式扩展为完整分析模式，新增 SQL 可视化、图表渲染、多步骤分析链路等能力，提升用户从提问到洞察的端到端体验

---

## 面试追问 Q&A

### Q1：精简模式和完整分析模式的核心差异是什么？

**A：** 两种模式通过 Agent 配置中的 `toolConfig.simpleMode` 开关控制，在 ChatItem 组件渲染层面有条件展示。

| 能力 | 精简模式（simpleMode=true） | 完整分析模式（simpleMode=false） |
|------|--------------------------|-------------------------------|
| 自然语言问答 | ✅ | ✅ |
| 查询条件调整 | ❌ 不可调整 | ✅ 支持维度筛选（dimensionFilters）、日期范围、实体切换 |
| 调试信息 | ❌ 不显示 | ✅ 当 debugMode=true 时显示 Schema 映射、解析耗时等 |
| SQL 可视化 | ❌ | ✅ SqlItem 组件：语法高亮 + 格式化 + LLM 请求/响应展示 |
| 图表渲染 | ❌ 不可见 | ✅ ECharts 渲染（Table/Pie/MetricTrend/MetricCard） |
| 多解析结果切换 | ❌ | ✅ ExpandParseTip：多种 SQL 候选方案供用户选择 |
| 相似问题推荐 | ❌ | ✅ SimilarQuestionItem：根据当前查询推荐相关追问 |
| 数据导出 | ❌ | ✅ CSV 导出 |
| LLM 请求/响应 | ❌ | ✅ 开发者可查看 LLM prompt + response |

精简模式本质是「只给结论」，完整模式是「展示推理过程 + 允许用户介入调整」。

### Q2：SQL 可视化是怎么实现的？

**A：** SqlItem 组件基于 `react-syntax-highlighter` + `sql-formatter` 实现：

- **格式化**：`sql-formatter` 库将后端返回的 S2SQL/物理 SQL 标准格式化（大小写统一、缩进对齐）
- **语法高亮**：`react-syntax-highlighter` 用 SQL 语言模式渲染关键字高亮
- **信息分层展示**：
  - `parsedS2SQL`：语义层 SQL（LLM 生成的中间表示）
  - `correctedS2SQL`：纠正后的语义 SQL
  - `querySQL`：最终执行 SQL
  - `correctedQuerySQL`：物理优化后的 SQL
- **调试面板**：开发者模式下展示 LLM 请求（prompt）和响应（completion/response），用于问题排查
- **显示条件**：`isDeveloper && isDebugMode && !isSimpleMode` — 仅开发者在完整模式下可见

### Q3：多步骤分析链路的技术实现？

**A：** ChatItem 组件内部维护一个状态机，驱动 NLP → Parse → Execute 三阶段渲染：

```
用户输入 → [Parse 阶段] → 多候选展示 → [Execute 阶段] → 结果渲染
```

1. **Parse 阶段**（`chatParse`）：
   - 调用 `/api/chat/query/parse`，后端返回 `selectedParses`（最优解析）+ `candidateParses`（候选）
   - `parseInfos.length === 1`：自动进入 Execute
   - `parseInfos.length > 1`：展示 `ExpandParseTip`，用户选择一种解析方案

2. **用户干预**：
   - 切换解析方案 → `onSelectParseInfo()` 利用 `dataCache` 复用已执行结果，避免重复请求
   - 调整筛选条件 → `onFiltersChange/onDateInfoChange` 后调用 `onRefresh()` 重新 queryData
   - 实体切换 → `onSwitchEntity()` 切换分析粒度

3. **Execute 阶段**（`chatExecute` + `getExecuteSummary`）：
   - Execute 后启动伪流式轮询（`getExecuteSummary`，500ms 间隔），持续更新 `textSummary`
   - 直到 `queryMode != null` → 流式结束，展示最终结果

4. **结果渲染**：`ExecuteItem` 组件根据 `queryMode` 分发到不同图表组件（Table/Pie/MetricTrend/MetricCard/WebPage）

### Q4：图表渲染支持哪些类型？技术选型是什么？

**A：** 基于 **ECharts 5.4** 渲染，根据后端返回的 `queryMode` 分发：

| queryMode | 组件 | 场景 |
|-----------|------|------|
| `table_query` | ChatMsg/Table | 明细数据表格 |
| `agg_query` | ChatMsg/Pie | 聚合统计饼图 |
| `metric_trend` | ChatMsg/MetricTrend | 指标趋势图（单指标/多指标） |
| `metric_card` | ChatMsg/MetricCard | 指标卡片（含环比） |
| `web_page` | ChatMsg/WebPage | 外部网页嵌入 |
| `plain_text` | ChatMsg/Text | 纯文本回答 |

图表组件支持 **下钻维度**（DrillDownDimensions）：用户点击图表的数据点，可展开到更细粒度的维度查看明细。

### Q5：前端技术栈为什么选 UmiJS + Ant Design？

**A：** SuperSonic 前端架构：

- **框架**：React 18 + UmiJS 4（约定式路由 + 插件体系，适合中后台场景快速开发）
- **UI 组件库**：Ant Design 5.17（企业级中后台的标准选择）
- **图表**：ECharts 5.4（国产生态，中文文档完善）
- **状态管理**：ahooks（非 Redux，轻量级 hooks 方案，适合 Chat-BI 这种局部状态为主的场景）
- **流式渲染**：轮询 `getExecuteSummary` 实现伪流式（后端暂不支持 SSE）
- **构建**：UmiJS 内置 Webpack 5，生产构建产物通过 `start-fe-prod.sh` 打包为 tar.gz，部署到 Spring Boot 的 `classpath:/webapp/`
