# Chat-BI 对话交互升级 — 面试深度文档

> 基于源码验证的完整面试预案，覆盖前因后果、架构全景、源码级 Q&A、遇到的坑。

---

## 1. 简历文案（终版）

> 主导 Chat-BI 对话页面的交互升级，将原有的精简问答模式扩展为完整分析模式，新增 SQL 可视化、图表渲染、多步骤分析链路等能力，提升用户从提问到洞察的端到端体验

---

## 2. 前后端交互全景图

```
                              ChatItem 组件生命周期
              ┌─────────────────────────────────────────────────────┐
              │                                                     │
用户输入 ──────▶  sendMsg()                                         │
              │     │                                               │
              │     │  ① POST /api/chat/query/parse                 │
              │     │  ───────────────────────────────────▶  后端    │
              │     │  { queryText, chatId, agentId }        │      │
              │     │                                        │      │
              │     │  ◀───────────────────────────────────  │      │
              │     │  { selectedParses[], candidateParses[],│      │
              │     │    parseTimeCost, queryId }            │      │
              │     │                                        │      │
              │     ├── 单候选 ──▶ onExecute() ──────────────│──────│
              │     │              ② POST /api/chat/query/   │      │
              │     │                 execute                │      │
              │     │  ───────────────────────────────────▶  │      │
              │     │  { queryText, queryId, parseId }       │      │
              │     │                                        │      │
              │     │  ◀───────────────────────────────────  │      │
              │     │  { queryState, queryMode, textSummary }│      │
              │     │                                        │      │
              │     │  queryMode == null? ──▶ ③ 轮询         │      │
              │     │  POST /api/chat/query/getExecuteSummary│      │
              │     │  ── 500ms ──▶  ── 500ms ──▶  ...     │      │
              │     │  直到 queryMode != null                 │      │
              │     │                                        │      │
              │     └── 多候选 ──▶ 展示 ExpandParseTip       │      │
              │          用户选择                              │      │
              │          │                                    │      │
              │          │  ②' POST /api/chat/query/parse    │      │
              │          │  (带 parseId + selectedParse)      │      │
              │          │  ────────────────────────────▶     │      │
              │          │                                    │      │
              │          └──▶ onExecute() ──▶ ② + ③ 同上     │      │
              │                                                │      │
              │  【渲染态：用户可随时介入】                       │      │
              │                                                │      │
              │  改筛选/日期                                     │      │
              │  ──▶ ④ POST /api/chat/query/queryData  ──▶    │      │
              │      不走 parse，直接替换 WHERE 重查             │      │
              │                                                │      │
              │  切解析方案                                       │      │
              │  ──▶ 查 dataCache ── 命中: 0请求 / 未命中: ②   │      │
              │                                                │      │
              │  切数据实体                                       │      │
              │  ──▶ ⑤ POST /api/chat/query/switchQuery ──▶   │      │
              │                                                │      │
              │  ┌────────────────────────────────────────┐    │      │
              │  │  结果渲染 (ExecuteItem → ChatMsg)       │    │      │
              │  │  ┌──────┐ ┌───┐ ┌──────────┐ ┌───────┐ │    │      │
              │  │  │Table │ │Pie│ │MetricTrend│ │MetricCard│  │      │
              │  │  └──────┘ └───┘ └──────────┘ └───────┘ │    │      │
              │  │  ┌───────┐ ┌──────────┐               │    │      │
              │  │  │WebPage│ │Plain Text│  +下钻+表格切换│    │      │
              │  │  └───────┘ └──────────┘               │    │      │
              │  └────────────────────────────────────────┘    │      │
              │                                                │      │
              │  ▼ 追问 ──▶ 回到 sendMsg()，新一轮               │      │
              └─────────────────────────────────────────────────────┘

                              ─ 数据流向图例 ─
              ▶ 前端 → 后端请求       ◀ 后端 → 前端响应
              ① parse  ② execute  ③ 轮询  ④ 重查  ⑤ 切实体
```

三个核心信息：
1. 请求不是平的——parse → execute → poll 是串行链路，但 queryData / switchQuery 是随时可触发的旁路
2. parse 可能被调用两次——单候选只调一次，多候选时用户选择触发第二次 parse（带 parseId）
3. dataCache 是请求的断路器——用户切解析方案时，如果缓存命中，零请求完成切换

---

## 3. 30秒概括

精简模式是一个「对话机器人」——问一句、回一句，用户看不到中间过程。完整分析模式把它升级成了「分析工作台」——用户提问后，可以看到 LLM 的每一步推理（Schema 映射 → 多候选 SQL → 执行 SQL），可以在中途介入（切换解析方案、调整筛选条件、切换数据实体），可以查看 SQL 细节、导出数据、追问相关问题。

技术上做了一件事：**把原来 1 个黑盒接口拆成了 7 个可介入的接口**，围绕 parse → execute → poll 三阶段链路，在前端构建了组件化的分析体验。

---

## 4. 背景与动机

### 场景设定

SuperSonic 的 Chat-BI 模块允许用户用自然语言查询数据库。在实验室的 CSMAR 数据集上搭建了 Agent，用户（研究员/同学）通过对话页面提问，比如「统计减持后股价下跌超过 5% 的高管占比」。

### 痛点 1：用户不信任「黑盒回答」

精简模式下，用户提问 → 系统返回一个结果。用户看不到 SQL、不知道 LLM 怎么理解的、无法验证结果是否正确。当一个研究课题依赖这些数据做结论时，「黑盒」是不可接受的——用户需要看到推理链路。

### 痛点 2：LLM 可能出错，用户无法纠正

Schema 映射阶段，LLM 可能会把「减持比例」理解成 COUNT 而非 SUM。精简模式下，用户看到错误结果只能重新提问——他不知道怎么「修正」，因为看不到中间过程。研究员可能反复问同一个问题、调整措辞，试图「碰」出正确结果。

### 痛点 3：从「问答」到「分析」的体验断层

精简模式只能输出文本。但用户真正需要的是：看趋势图、下钻到明细、换维度对比、导出 CSV 做进一步分析。精简模式的输出无法进入任何分析工作流——用户得把结果复制到 Excel 再手动处理。

三个痛点共同指向一个结论：**精简模式只能验证「系统能跑」，完整分析模式才能验证「系统有用」。**

---

## 5. 前后端接口全景

### 5.1 升级前：1 个黑盒接口

```
用户输入 → POST /api/chat/query/query
              ├─ 入参: queryText, chatId, modelId
              └─ 返回: MsgDataType（queryResults + queryColumns + response）

前端只做一件事：把返回的文本渲染出来。
```

`chatQuery` 函数至今定义在 `service/index.ts` 中，但**没有任何组件调用它**——它是升级前的遗物，已被三阶段链路替代。

### 5.2 升级后：7 个可介入的接口

核心链路 — 三阶段拆分：

```
                  入参                                    返回
POST /api/chat/query/parse        queryText, chatId,      selectedParses[], candidateParses[],
                                  agentId, modelId        parseTimeCost, queryId

POST /api/chat/query/execute      queryText, chatId,      queryColumns, queryResults,
                                  queryId, parseId        queryState, queryMode

POST /api/chat/query/             queryId                 textSummary (streaming),
getExecuteSummary                                         queryMode (null→非null时结束)
```

辅助接口 — 用户介入：

```
POST /api/chat/query/queryData    dimensions, metrics,    重新执行后的 MsgDataType
                                  dateInfo, dimensionFilters,
                                  parseId, queryId

POST /api/chat/query/switchQuery  entityId, modelId       切换实体后的 MsgDataType

POST /api/chat/query/             modelId, bizName,       维度值列表
queryDimensionValue               agentId, elementID, value

GET  /api/chat/manage/            queryId                 相似问题列表
getChatQuery/{queryId}
```

### 5.3 核心叙事：拆接口 = 拆控制权

升级前，`chatQuery` 是一个不可打断的原子操作——请求发出去，结果一次性回来。用户在整个过程中没有任何控制点。

升级后，每一步都是独立请求：
- **parse** 返回多个候选方案 → 用户看到了选择权
- **execute** 执行选中方案 → 用户可以换方案再执行（dataCache 缓存已有结果，不重复请求）
- **getExecuteSummary** 轮询 → 用户看到 LLM 在「想」，不是干等
- **queryData** → 用户改完筛选条件，随时重查，不需要重新走 parse
- **switchQuery** → 用户切换数据域，前端自动调 parse 重解析
- **queryDimensionValue** → 维度筛选框里搜索候选值，实时联想
- **getChatQuery** → 解答完推荐相关问题，形成追问闭环

面试语境下的一句话总结：**把 1 个 RPC 拆成了 7 个 RESTful 接口，每个接口代表用户分析链路中的一个可控步骤——这就是从「聊天机器人」到「分析工作台」的技术内核。**

---

## 6. 组件架构全景

### 6.1 ChatItem — 单一组件承载整条分析链路

ChatItem 不是简单渲染一条消息，它是一个 **599 行的状态机**，驱动 NLP → Parse → Execute → Render 的完整生命周期。

```
ChatItem (index.tsx, 599 行)
│
├── ParseTip (解析阶段)
│   ├── 多候选切换 (parseInfoOptions)
│   ├── 维度筛选 (dimensionFilters → FilterSection)
│   ├── 日期范围 (dateInfo → DateOptions)
│   └── 实体切换 (entityInfo → SwitchEntity)
│
├── ExpandParseTip (多候选面板，首次解析有多个候选时弹出)
│   └── onExpandSelectParseInfo → 重调 parse + 传 parseId/parseInfo
│
├── SqlItem (SQL 可视化，仅 developer + debugMode + !simpleMode)
│   ├── Schema 映射 (llmReq.schema, terms, priorExts)
│   ├── Few-shot 示例 (llmResp.sqlRespMap[...].fewShots)
│   ├── LLM/Rule 解析 S2SQL (sqlInfo.parsedS2SQL)
│   ├── 修正 S2SQL (sqlInfo.correctedS2SQL)
│   ├── 物理 SQL 修正 (sqlInfo.correctedQuerySQL)
│   ├── 最终执行 SQL (sqlInfo.querySQL)
│   └── 导出调试日志 (onExportLog → .log 文件)
│
├── ExecuteItem (执行 + 结果渲染)
│   ├── 加载中 → "数据查询中" + Loading 动画
│   ├── 失败 → 错误提示 + 可展开的异常日志
│   └── 成功 → 按 queryMode 分发：
│       ├── table_query  → ChatMsg/Table  (表格)
│       ├── agg_query    → ChatMsg/Pie     (饼图)
│       ├── metric_trend → ChatMsg/MetricTrend (趋势图，单/多指标)
│       ├── metric_card  → ChatMsg/MetricCard  (指标卡片 + 环比)
│       ├── web_page     → ChatMsg/WebPage     (外部网页嵌入)
│       └── plain_text   → ChatMsg/Text        (纯文本)
│       └── ChatMsg 内部还包含:
│           ├── DrillDownDimensions (图表下钻)
│           ├── 表格/图表切换 Switch
│           └── MarkDown / Message (文本渲染)
│
├── SimilarQuestionItem (相似问题推荐，仅完整模式 + 非纯文本)
│
└── Tools (底部工具栏，仅完整模式)
    ├── CSV 导出 (onExportData)
    ├── 重新执行 (onReExecute → deleteQueryInfo)
    └── 反馈评分 (score)
```

### 6.2 状态机（决策树）

```
ChatItem mount
│
├─ 有 msgData？（即：从历史记录恢复）
│   │
│   └─ 是 ──────────────────────────────────────── 跳过所有步骤，直接进入「渲染态」
│          parseInfo ← msgData.chatContext
│          executeMode ← true
│          data ← msgData
│
└─ 否（正常提问流程）
    │
    └─ sendMsg() ──────────────────── parseLoading ← true
        │
        │  POST /api/chat/query/parse
        │
        ├─ 失败 / 无候选 ──────────── parseTip ← 错误信息 → 结束
        │
        └─ 成功
            │
            ├─ 候选数 = 1 ────────────────────────────────────────┐
            │   parseInfo ← 唯一的候选                              │
            │   executeMode ← false（尚未执行）                     │
            │   onExecute(parseInfo)  →  进入「执行」               │
            │                                                      │
            └─ 候选数 > 1 ──────── preParseMode ← true             │
                │                 showExpandParseTip ← true        │
                │                                                  │
                │  用户看到多候选面板，选择一个方案                   │
                │                                                  │
                │  ┌─ 选方案A（ExpandParseTip 里选）                 │
                │  │   onExpandSelectParseInfo(parseInfoA)          │
                │  │   → 重调 parse（带 parseId）                    │
                │  │   → 取 selectedParses[0] 为最终方案             │
                │  │   → onExecute(最终方案)                        │
                │  │                                                │
                │  └─ 选方案B（用户在 ParseTip 里切）                 │
                │      onSelectParseInfo(parseInfoB)                │
                │      │                                            │
                │      ├─ dataCache 里有 parseInfoB 的结果？         │
                │      │   └─ 是 → 直接从缓存取 data，不发请求       │
                │      │                                            │
                │      └─ dataCache 里没有？                         │
                │          └─ onExecute(parseInfoB)                 │
                │                                                   │
                └──────────────────────────────────────────────────┘
                                    │
                                    ▼
                            【执行 onExecute】
                                    │
                    executeLoading ← true（首次）
               或   entitySwitchLoading ← true（切换/刷新）
                                    │
                    POST /api/chat/query/execute
                                    │
                    ├─ 失败 → executeTip ← 错误信息
                    │
                    └─ 成功 → data ← res.data
                               │
                               ├─ queryState != 'INVALID' 且 queryId 存在？
                               │   │
                               │   └─ 是 → 启动伪流式轮询
                               │           │
                               │           │  getExecuteSummary(queryId)
                               │           │  │
                               │           │  ├─ queryMode == null（还没完）
                               │           │  │   → 更新 textSummary
                               │           │  │   → 等 500ms 再轮询 ◄─ 循环
                               │           │  │
                               │           │  └─ queryMode != null（完成！）
                               │           │      → data ← 最终结果
                               │           │      → 停止轮询
                               │           │
                               └───────────┴──→ 进入「渲染态」
```

**「渲染态」里的用户操作：**

```
【渲染态】
│
├─ 用户改维度筛选 / 改日期
│   onRefresh()
│   → 不走 parse（不重新理解问题）
│   → 直接 POST /api/chat/query/queryData（带新筛选条件）
│   → data ← 新结果
│   → dataCache 更新
│
├─ 用户切换实体（如从减持表切到高管表）
│   onSwitchEntity(entityId)
│   → POST /api/chat/query/switchQuery
│   → parseInfo ← 新的 chatContext
│   → data ← 新结果
│   → dataCache 更新
│
└─ 用户切换解析方案（在 ParseTip 里点另一个候选）
    onSelectParseInfo(另一个 parseInfo)
    │
    ├─ dataCache 命中 → 直接取缓存，不请求
    └─ dataCache 未命中 → onExecute(另一个 parseInfo) → 走完整「执行」流程
```

**错误恢复：**

```
用户点「重新执行」
→ deleteQueryInfo(queryId)
→ resetState()（所有状态清零）
→ initChatItem(msg, undefined) → sendMsg() → 重新开始完整链路
```

### 6.3 simpleMode 的控制逻辑

`isSimpleMode` 不是控制 API 调用路径，而是**控制渲染内容**。核心差异点：

| 位置 | simpleMode=true | simpleMode=false |
|------|----------------|------------------|
| ParseTip | 不渲染 | 渲染维度筛选/日期/实体切换 |
| SqlItem | 不渲染 | 渲染 SQL 分层展示 |
| ExecuteItem 标题栏 | 隐藏 | 显示"数据查询 (耗时:xxms)" |
| ExecuteItem 容器 | 简化样式 | 带左边框 + 完整边距 |
| SimilarQuestionItem | 不渲染 | 渲染相似问题 |
| Tools | 不渲染导出/重执行 | 渲染完整工具栏 |

---

## 7. 按用户旅程逐站展开

### 站 1：提问 → 解析（含自动执行）

**sendMsg() 的完整请求序列：**

```
sendMsg() 被调用
│
│  第①次请求：
│  POST /api/chat/query/parse
│  Body: { queryText, chatId, dataSetId, agentId }
│
│  返回: selectedParses[], candidateParses[], parseTimeCost, queryId
│        （每个 parse 已包含 sqlInfo, dimensionFilters, dateInfo, properties.CONTEXT）
│
├─ 候选数 = 1
│   │
│   │  自动调用 onExecute(parseInfoValue)
│   │  │
│   │  │  第②次请求：
│   │  │  POST /api/chat/query/execute
│   │  │  Body: { queryText, agentId, chatId, queryId, parseId }
│   │  │
│   │  │  返回: queryColumns, queryResults, queryState, queryMode, queryId
│   │  │
│   │  └─ queryState != 'INVALID' 且 queryId 存在？
│   │      │
│   │      └─ 是 → 第③~N次请求（伪流式轮询）：
│   │              POST /api/chat/query/getExecuteSummary
│   │              Body: { queryId }
│   │              每 500ms 一次，直到 queryMode != null
│   │
│   └─ 总结：1个候选时，sendMsg 触发 1次parse + 1次execute + N次轮询
│
└─ 候选数 > 1
    │
    └─ 只发第①次请求（parse），然后停住
       显示 ExpandParseTip，等用户选
       不自动调 execute！
       （因为 parseInfos.length > 1 时不走 onExecute，第 266-268 行有条件判断）

   总结：多候选时，sendMsg 只发 1 次 parse 请求
```

**关键细节：多候选时 parseInfo 什么时候设置？**

```typescript
// sendMsg() 第 266 行
if (!(currentAgent?.enableFeedback === 1 && parseInfos.length > 1)) {
    setParseInfo(parseInfoValue);  // 只有单候选或 feedback 关闭时才设
}
```

多候选 + feedback 开启时，parseInfo 暂时不设——因为此时还没有确定的方案。等用户在站 2 里选了之后，才通过 `onExpandSelectParseInfo` 或 `onSelectParseInfo` 设置。

### 站 2：多候选选择 → 用户介入

**请求次数总览：**

| 场景 | parse | execute | 轮询 | queryData | switchQuery | 合计（不含轮询） |
|------|-------|---------|------|-----------|-------------|-----------------|
| 单候选（自动） | 1 | 1 | N | 0 | 0 | 2+N |
| 多候选→ExpandTip选 | 2 | 1 | N | 0 | 0 | 3+N |
| ParseTip切方案（缓存命中） | 0 | 0 | 0 | 0 | 0 | 0 |
| ParseTip切方案（缓存未命中） | 0 | 1 | N | 0 | 0 | 1+N |
| 改筛选/日期 | 0 | 0 | 0 | 1 | 0 | 1 |
| 切换实体 | 0 | 0 | 0 | 0 | 1 | 1 |

**用户操作 A：在 ExpandParseTip 里选择候选方案**

```
用户点击候选 B
│
│  onExpandSelectParseInfo(parseInfoB)
│
│  第②次请求（sendMsg 后第二次请求）：
│  POST /api/chat/query/parse
│  Body: { queryText, chatId, dataSetId, agentId, parseId, queryId, selectedParse: parseInfoB }
│  （带 parseId + selectedParse → 后端对这个方案做深入解析）
│
│  返回: selectedParses[0]（更完整的 dimensionFilters + dateInfo + sqlInfo）
│
│  然后自动调 onExecute(selectedParses[0])
│  │
│  │  第③次请求：
│  │  POST /api/chat/query/execute
│  │
│  │  之后：第④~N次轮询 getExecuteSummary
│
└─ 总结：ExpandParseTip 选择触发 1次parse + 1次execute + N次轮询
```

**用户操作 B：在 ParseTip 里切换方案（executeMode 已进入后）**

```
用户点击候选标签切换
│
│  onSelectParseInfo(parseInfoB)
│
├─ dataCache[parseInfoB.id] 有值？
│   │
│   └─ 是 → setData(缓存结果)  ← 0 次请求！直接切
│
└─ dataCache[parseInfoB.id] 无值？
    │
    │  第?次请求：
    │  POST /api/chat/query/execute（针对 parseInfoB）
    │  → 之后 N 次轮询
    │
    └─ 总结：parseTip 切换 = 0次请求（命中缓存）或 1次execute+N次轮询
```

**用户操作 C：改筛选条件 / 改日期**

```
用户修改维度筛选 or 日期范围 → onRefresh()
│
│  第?次请求：
│  POST /api/chat/query/queryData
│  Body: { dimensions, metrics, dateInfo, dimensionFilters, parseId, queryId }
│  （不走 parse！不重新理解问题！直接用新筛选条件重查）
│
│  返回: MsgDataType（新的 queryResults + queryColumns）
│
└─ 总结：onRefresh = 1 次 queryData 请求，无 parse 无轮询
```

**用户操作 D：切换实体**

```
用户切到另一个数据域 → onSwitchEntity(entityId)
│
│  第?次请求：
│  POST /api/chat/query/switchQuery
│  Body: { queryText: entityId, modelId, chatId }
│
│  返回: MsgDataType（新的 chatContext + entityInfo + queryResults）
│
└─ 总结：onSwitchEntity = 1 次 switchQuery 请求，无 parse 无轮询
```

### 站 3：SQL 可视化 — 零请求，纯渲染

**数据从哪来？ — parse 响应的一次性传递**

```typescript
// sendMsg() 中 — 站1 的 parse 请求
const parseData = await chatParse({...});  // POST /api/chat/query/parse
const parseInfoValue = parseInfos[0];      // 已包含 sqlInfo
setParseInfo(parseInfoValue);              // 存入状态

// parseInfo 的结构（parse 响应直接给的）：
parseInfo = {
  sqlInfo: {
    parsedS2SQL:      "SELECT ...",   // ← 四层 SQL 全在
    correctedS2SQL:   "SELECT ...",
    querySQL:         "SELECT ...",
    correctedQuerySQL: "SELECT ..."
  },
  properties: {
    CONTEXT: {
      llmReq:  { schema, terms, priorExts },  // ← Schema 映射 + 术语
      llmResp: { sqlRespMap: { "0": { fewShots } } }  // ← Memory 召回记录
    }
  }
}
```

**execute 阶段不更新 sqlInfo：**

```typescript
// onExecute — 站4 的 execute 请求
const res = await chatExecute(...);  // POST /api/chat/query/execute
updateData(res);                     // 只更新 data（queryResults, queryColumns）
// parseInfo 不变！sqlInfo 也不变！
```

**SqlItem 渲染时：**

```typescript
// ChatItem render (line 530-546)
{parseInfo?.sqlInfo && isDeveloper && isDebugMode && !isSimpleMode && (
  <SqlItem
    sqlInfo={parseInfo.sqlInfo}      // ← 直接读 parseInfo，零请求
    llmReq={parseInfo.properties.CONTEXT.llmReq}
    llmResp={parseInfo.properties.CONTEXT.llmResp}
    queryMode={parseInfo.queryMode}
    sqlTimeCost={parseTimeCost?.sqlTime}
    executeErrorMsg={executeErrorMsg}  // ← 唯一来自 execute 的字段
  />
)}
```

除 `executeErrorMsg`（execute 失败时才有值）外，SqlItem 的所有 props 在站 1 的 parse 响应中就已经就绪了。

**SqlItem 内部：7 个 Tab**

```
sqlType 值          │ 内容来源                   │ 用户看到什么
────────────────────┼───────────────────────────┼──────────────────────────
"schemaMap"         │ llmReq.schema + terms     │ LLM 收到的字段/术语/取值映射
"fewShots"          │ llmResp.sqlRespMap[0]     │ Memory 召回的历史范例（问题+SQL）
                    │   .fewShots               │
"parsedS2SQL"       │ sqlInfo.parsedS2SQL       │ LLM 或 Rule 直出的语义 SQL
"correctedS2SQL"    │ sqlInfo.correctedS2SQL    │ SemanticCorrector 修正后的 SQL
"correctedQuerySQL" │ sqlInfo.correctedQuerySQL │ 物理表翻译后再次修正
"querySQL"          │ sqlInfo.querySQL          │ 最终发给数据库执行的 SQL
"error" (隐式)       │ executeErrorMsg           │ 执行失败时的异常日志
```

如果该字段不存在（null/空），对应的 Tab 不渲染。

**显示条件 — 五个条件同时满足：**

```typescript
{!isMobile && parseInfo?.sqlInfo && isDeveloper && isDebugMode && !isSimpleMode && (
  <SqlItem ... />
)}
```

1. 非移动端（SQL 在手机上不好看）
2. 有 SQL 信息
3. 开发者身份
4. 调试模式开启
5. 非精简模式

**导出调试日志：**

```typescript
onExportLog() {
  // 把所有调试信息拼成一个 .log 文件下载
  text = "问题：" + question
       + "Schema映射：" + fieldNameList + values + terms
       + "Few-shot示例：" + fewShots
       + "解析S2SQL：" + format(parsedS2SQL)
       + "修正S2SQL：" + format(correctedS2SQL)
       + "物理SQL修正：" + format(correctedQuerySQL)
       + "最终执行SQL：" + format(querySQL)
       + "异常日志：" + executeErrorMsg
  exportTextFile(text, `supersonic-debug-${agentId}-${queryId}.log`)
}
```

面试要点：导出日志是把 LLM 从收到 prompt 到生成 SQL 再到执行的全部上下文一次性导出。排查成本从「重新问一遍 + 解释上下文」降到「发个文件」。

**面试叙事：**

> SqlItem 不是靠额外请求拿到 SQL 的。parse 接口返回的 selectedParses 里已经包含了四层 SQL + Schema 映射 + Few-shot 示例。前端只做了一件事：把这些数据用 Tab 切换 + 语法高亮渲染出来。这也解释了为什么 SQL 渲染速度快——它和解析结果是同一批数据，parse 回来就能立刻展示，不需要等 execute。

### 站 4：执行 + 伪流式

**第②次请求：execute**

```typescript
POST /api/chat/query/execute
Body: {
  queryText: "统计减持后 CAR_5d < -3% 的事件里按行业分组看股价反应",
  agentId: 7,
  chatId: 0,
  queryId: 2083,   // parse 阶段分配的 ID
  parseId: 17       // 用户选择的解析方案 ID
}
```

**execute 的三种返回状态：**

```typescript
// 状态 A：正在执行（需要轮询）
{ code: 200, data: {
    queryId: 2083,
    queryState: "SUCCESS",
    queryMode: null,        // ← null！表示还没完
    textSummary: "正在分析...",
    queryColumns: null,
    queryResults: null
}}

// 状态 B：执行完成
{ code: 200, data: {
    queryId: 2083,
    queryState: "SUCCESS",
    queryMode: "agg_query",  // ← 非 null，完成了
    queryColumns: [...],
    queryResults: [...],
    textSummary: "减持后 CAR_5d < -3% 的事件共 47 起..."
}}

// 状态 C：执行失败
{ code: 200, data: {
    queryState: "INVALID",
    response: "查询失败：字段 CAR_5d 不存在"
}}
```

**伪流式轮询的核心逻辑：**

```typescript
const getSummary = async (data, queryId) => {
    const res2 = await getExecuteSummary(queryId);  // 第③次请求

    if (res2.data.queryMode == null) {
        // 还没完 → 更新 textSummary，继续等
        res2.data = { ...data, textSummary: res2.data.textSummary };
        setData(res2.data);
        setTimeout(() => getSummary(data, queryId), 500);  // ← 500ms 后再来
    } else {
        // 完成了！停止轮询
        setData(res2.data);
    }
};
```

**ExecuteItem 的三态渲染：**

- 态 1：加载中（executeLoading = true）→ "数据查询中" + Loading 动画
- 态 2：失败（executeTip 非空）→ "数据查询失败" + 可展开异常日志
- 态 3：成功（data 存在且无错误）→ "数据查询 (耗时: 234ms)"

**为什么用轮询而不是 SSE？**

Chat-BI 的查询不是「逐 token 生成」，而是四个异构阶段串行：

```
LLM 生成 S2SQL  →  翻译为物理 SQL  →  数据库执行  →  LLM 生成文字总结
   (100-500ms)       (10-50ms)         (50-2000ms)      (200-1000ms)
```

后端在每个阶段完成时写 `s2_chat_query` 表的对应字段。`getExecuteSummary` 就是读这条记录。

三个原因选择轮询：

1. **更新粒度是「句子级」而非「token 级」**：textSummary 每次是一个完整句子，不是逐字。整个查询通常只有 2-3 次文本变化。500ms 轮询和 SSE 推送对用户没有可感知差异。

2. **后端已经持久化了查询状态**：`getExecuteSummary` 是零成本的读操作，不改变后端推送模型。改 SSE 需要维护连接池、处理断连恢复——收益极小。

3. **用户中途刷新页面的容错**：轮询方案下，刷新后 `msgData` 已有最新状态，继续轮询即可。SSE 方案下连接断了，你仍然要调接口查当前状态——最终还是回到轮询逻辑。

> 面试叙事：我评估过 SSE 方案。在这个场景里，textSummary 是句子级更新的，每条查询通常只有 2-3 次文本变化；同时后端已经通过数据库持久化了查询状态。轮询 500ms 对用户体验无明显影响，但它零成本复用了后端已有的状态表，并且天然支持页面刷新后的状态恢复。这不是因为不会做 SSE——而是判断之后，轮询是更适合这个场景的方案。

### 站 5：结果渲染 → 图表分发

**ExecuteItem 的路由逻辑：**

```typescript
{data?.queryMode === 'PLAIN_TEXT' || data?.queryMode === 'WEB_SERVICE' ?
    data?.textResult                       // 纯文本：直接渲染
  : data?.queryMode === 'WEB_PAGE' ?
    <WebPage id={queryId} data={data} />   // 外部网页：iframe 嵌入
  :
    <ChatMsg                               // 结构化数据：进 ChatMsg
      isSimpleMode={isSimpleMode}
      data={data}
      forceShowTable={showMsgContentTable}
      onMsgContentTypeChange={setMsgContentType}
    />
}
```

**ChatMsg 内部：根据 queryMode 分发：**

| 后端 queryMode | 前端组件 | 用户看到 |
|---------------|---------|---------|
| `table_query` | Table | 明细数据表格 |
| `agg_query` | Pie/Bar | 饼图/柱状图 |
| `metric_trend` | MetricTrend | 趋势折线图（单/多指标） |
| `metric_card` | MetricCard | 大数字卡片 + 环比 |
| `web_page` | WebPage | 外部网页嵌入 |
| `plain_text` | Text | 纯文本回答 |

**图表/表格切换：** 趋势/柱状/饼图类型时，标题栏出现「表格」开关，用户可随时切换到原始数据视图。

**下钻维度：** 后端返回 `recommendedDimensions`，用户点击下钻维度 → 更细粒度查询。

**simpleMode 差异：** 完整模式展示图表，精简模式只渲染 Markdown 文本总结。同一数据源，两种渲染方式。

### 站 6：收尾 — 追问、导出、反馈

**相似问题推荐：** execute 的最终响应里附带 `similarQueries`。失败时自动展开面板，引导用户换问法。

**CSV 导出：** 用 `column.name`（中文别名）做表头，fallback 到 `column.nameEn`。仅完整模式 + 非纯文本结果时显示。

**Tools 工具栏：** 查询结束后出现（成功或失败），包含导出 CSV、重新执行（deleteQueryInfo → resetState → sendMsg 完整重来）、反馈打分。

**用户旅程闭环总结：**

```
提出问题 → 看到多种理解可选 → 查看 SQL 透明验证
   │            │                    │
   │        (站1 parse)          (站3 SqlItem)
   │            │                    │
   │        ◀── 不满意？换方案 ──────┘
   │         (站2 多候选切换)
   │            │
   │            ▼ 满意，执行
   │         (站4 execute + 伪流式)
   │            │
   │            ▼ 看结果
   │         (站5 图表/表格/下钻)
   │         │      │        │
   │    改筛选重查  切表格   下钻细化
   │    (queryData) (Switch) (DrillDown)
   │         │      │        │
   │         └──────┴────────┘
   │            │
   │            ▼
   │       导出 CSV / 问下一个问题 / 打分
   │            (站6)
   │            │
   └── 追问 ────┘ 回到站1，新一轮
```

---

## 8. 遇到的坑

### 坑 1：多候选时 parseInfo 不设置，导致组件空引用

```typescript
// sendMsg() 第 266-268 行
if (!(currentAgent?.enableFeedback === 1 && parseInfos.length > 1)) {
    setParseInfo(parseInfoValue);
}
```

多候选 + feedback 开启时，parseInfo 保持 `undefined`。但渲染树里的 ParseTip/SqlItem/ExecuteItem 都依赖 parseInfo。后果：ExpandParseTip 展示多候选时，下方区域异常空白。修复：preParseMode 期间渲染 loading placeholder。

### 坑 2：dataCache 的 key 冲突风险

```typescript
dataCache[parseInfoValue.id!] = { tip, data };
```

`id` 是后端的 parseId，不同 parse 请求中可能复用。用户先执行方案 A（id=17），又执行方案 B（id 也是 17），缓存被覆盖，切回 A 时拿到 B 的结果。修复：用 `queryId + parseId` 组合作为缓存 key。

### 坑 3：伪流式轮询没有超时保护

```typescript
if (res2.data.queryMode == null) {
    setTimeout(() => getSummary(data, queryId), 500);  // 无限递归
}
```

后端异常挂起时前端永远轮询。executeLoading 已变 false，但 data 始终不更新——用户看到 loading 结束但结果不出来。修复：设定最大轮询次数（60 次 = 30 秒），超时后展示「查询超时，请重试」。

---

## 9. 面试追问 Q&A

### Q1：精简模式和完整分析模式的核心差异是什么？

A：两种模式通过 Agent 配置中的 `toolConfig.simpleMode` 开关控制，在 ChatItem 组件渲染层面有条件展示。

| 能力 | 精简模式（simpleMode=true） | 完整分析模式（simpleMode=false） |
|------|--------------------------|-------------------------------|
| 自然语言问答 | ✅ | ✅ |
| 查询条件调整 | ❌ 不可调整 | ✅ 支持维度筛选、日期范围、实体切换 |
| 调试信息 | ❌ 不显示 | ✅ 当 debugMode=true 时显示 Schema 映射、解析耗时等 |
| SQL 可视化 | ❌ | ✅ SqlItem：语法高亮 + 格式化 + LLM 请求/响应展示 |
| 图表渲染 | ❌ 不可见 | ✅ ECharts 渲染（Table/Pie/MetricTrend/MetricCard） |
| 多解析结果切换 | ❌ | ✅ ExpandParseTip：多种 SQL 候选方案供用户选择 |
| 相似问题推荐 | ❌ | ✅ SimilarQuestionItem：根据当前查询推荐相关追问 |
| 数据导出 | ❌ | ✅ CSV 导出 |
| LLM 请求/响应 | ❌ | ✅ 开发者可查看 LLM prompt + response |

精简模式本质是「只给结论」，完整模式是「展示推理过程 + 允许用户介入调整」。

### Q2：SQL 可视化是怎么实现的？

A：SqlItem 组件基于 `react-syntax-highlighter` + `sql-formatter` 实现：
- **格式化**：`sql-formatter` 将后端返回的 S2SQL/物理 SQL 标准格式化
- **语法高亮**：`react-syntax-highlighter` 用 SQL 语言模式渲染
- **信息分层展示**：parsedS2SQL / correctedS2SQL / querySQL / correctedQuerySQL 四层 Tab 切换
- **调试面板**：开发者可查看 Schema 映射（LLM 收到的字段/术语/取值）和 Few-shot 示例
- **导出日志**：一次性导出全部调试上下文为 .log 文件
- **显示条件**：`isDeveloper && isDebugMode && !isSimpleMode`

### Q3：多步骤分析链路的技术实现？

A：ChatItem 组件内部维护一个状态机，驱动 NLP → Parse → Execute 三阶段渲染：

```
用户输入 → [Parse 阶段] → 多候选展示 → [Execute 阶段] → 结果渲染
```

1. **Parse 阶段**（`chatParse`）：调 `/api/chat/query/parse`，后端返回 selectedParses + candidateParses。parseInfos.length === 1 自动进入 Execute；> 1 展示 ExpandParseTip 等用户选
2. **Execute 阶段**（`chatExecute` + `getExecuteSummary`）：Execute 后启动伪流式轮询（getExecuteSummary，500ms），直到 queryMode != null 结束
3. **用户介入**：切换方案（dataCache 缓存复用）、调整筛选（queryData 重查不重 parse）、实体切换（switchQuery）
4. **结果渲染**：ExecuteItem 根据 queryMode 分发到 Table/Pie/MetricTrend/MetricCard/WebPage 组件

### Q4：图表渲染支持哪些类型？技术选型是什么？

A：基于 ECharts 5.4 渲染，根据 queryMode 分发：

| queryMode | 组件 | 场景 |
|-----------|------|------|
| `table_query` | Table | 明细数据表格 |
| `agg_query` | Pie | 聚合统计饼图 |
| `metric_trend` | MetricTrend | 指标趋势图（单/多指标） |
| `metric_card` | MetricCard | 指标卡片（含环比） |
| `web_page` | WebPage | 外部网页嵌入 |
| `plain_text` | Text | 纯文本回答 |

支持图表/表格切换（Switch 开关）和下钻维度（DrillDownDimensions）。

### Q5：前端技术栈为什么选 UmiJS + Ant Design？

A：SuperSonic 前端架构：
- **框架**：React 18 + UmiJS 4（约定式路由 + 插件体系，适合中后台快速开发）
- **UI 组件库**：Ant Design 5.17（企业级中后台标准）
- **图表**：ECharts 5.4（国产生态，中文文档完善）
- **状态管理**：ahooks（轻量级 hooks 方案）
- **流式渲染**：轮询 `getExecuteSummary` 实现伪流式
- **构建**：UmiJS 内置 Webpack 5

### Q6：parse 和 execute 为什么要拆成两个接口？

A：parse 阶段可能产生多个候选方案，用户需要看到并选择一个，前端才能把选定的 parseId 传给 execute。如果合在一个接口里，后端需要「猜测」用户想选哪个——把前端的决策权让渡给了后端。拆开之后，parse 负责「理解问题给出选项」，execute 负责「执行选中方案」，职责清晰。单候选时前端自动调 execute 让用户感觉不到两次请求，但架构上它们仍然是独立的。

### Q7：用户改完筛选条件后为什么直接调 queryData 而不重新 parse？

A：parse 的作用是「把自然语言翻译成 SQL 结构」。用户改筛选条件时，维度/指标的选取没有变，变的只是 WHERE 条件的值。重新 parse 可能导致 LLM 给出不同的 SQL 结构，破坏用户已经在看的那套分析框架。queryData 接口只传维度、指标、筛选条件，不传自然语言——后端直接替换 WHERE 条件后重查，不走 LLM。保证结果可比。

### Q8：SqlItem 展示四层 SQL 有什么实际价值？

A：四层 SQL 对应 Text2SQL 链路的四个环节：LLM 生成 → 语义纠错 → 物理翻译 → 物理纠错。对于普通用户，看一层最终 SQL 够了。对于调试场景，每一层都可能暴露问题：
- parsedS2SQL 错了 → LLM 理解有误，需调整 prompt 或 Schema
- correctedS2SQL 改了 → SemanticCorrector 规则可能过拟合
- correctedQuerySQL 存在 → 物理翻译阶段兼容性问题
这四层不是给普通用户看的——它们的存在价值是把调试链路可视化，让排查方向一目了然。就像浏览器 Network 面板，99% 的用户用不到，但出问题时不可或缺。
