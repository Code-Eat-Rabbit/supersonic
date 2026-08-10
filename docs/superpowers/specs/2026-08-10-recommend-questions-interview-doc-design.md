# 推荐问题面试文档重写 — 设计规格

> 日期：2026-08-10  
> 状态：待用户审查  
> 目标文件：`docs/resume/interview/智能问数/04-推荐问题.md`  
> 题纲：`docs/resume/interview/面试题纲.md` § 2.3  
> 模板对齐：`docs/superpowers/specs/2026-08-10-memory-reuse-interview-doc-design.md`（A/B/C + 难点 + 改进）  
> 体例参照：`docs/resume/interview/深度研究/04-Hybrid-Search-MCP.md`  
> 代码标本：本仓库 SuperSonic（`QueryRecommendProcessor`、`Agent.examples`、chat-sdk 相似题 UI）

---

## 1. 背景与目标

### 1.1 问题

现有 `04-推荐问题.md` 场景与贡献率叙事充分，但工程 Spec 偏薄：读者不易分清「内置 vs 相似」两条代码路径，且易与输入联想、Plugin `preset_query_collection`、记忆复用写路径混淆；`source` / 版本号等口径与 OSS 不完全对齐。

### 1.2 目标

1. 单文件重写为：**Part A 需求与效果 → Part B 工程 Spec（双通道叙事）→ Part C 薄题纲附录**。  
2. Part B 故事性强，但结构上明确：**B1 ∥ B2，二者汇合于 B3**（非 B1→B2→B3 流水线）。  
3. 含 **A6 难点** 与 **B5 后续改进**；数字与 `01` §0 / 简历对齐；与代码冲突处以代码为准。  
4. 与 `03` 交叉：同库对照用短表 + 链接，不在 04 展开 Review / `#Exemplars`。

### 1.3 非目标

- 不拆成 04a/04b。  
- 不把输入框联想写成相似推荐。  
- 不把 Plugin `preset_query_collection` 说成内置 FAQ。  
- 不编造 OSS「版本号防竞态」协议。  
- 不在本文重写 03；03 锚点若后续变更，实现时同步改链接。  
- 不改业务功能代码。

---

## 2. 总体结构（已定）

```
04-推荐问题.md
├── 文首元信息（导航、题纲、标本、诚实边界总表）
├── Part A · 需求与效果（场景、指标、难点）
├── Part B · 工程 Spec（双通道 + 汇合 + 风险 + 改进）
└── Part C · 题纲索引（薄）
```

### 2.1 Part A · 需求与效果

| 节 | 内容 |
|----|------|
| **A1 背景与动机** | 拆场景：行为助理反复查 + 连续追问；绿色金融引导开口；**不是**全站「不会提问」 |
| **A2 目标与非目标** | 目标：降低开口成本、结果旁下一跳；非目标：输入联想、另建推荐库、替代记忆复用 |
| **A3 已实现效果** | 内置 **15%** / 相似 **11%**（查询贡献率）；样例表**压缩**保留（行为与绿色各留代表性条目，不必全文堆砌） |
| **A4 指标口径** | `count(source=…)/count(全部)`；主 KPI 非 impression CTR；诚实：OSS Java **未检索到** `source` 枚举 → 标 `[产品/ELK 口径]` |
| **A5 与 03 边界** | 同一 `memory_{agentId}`；03 同步教模型 / 04 异步给人点——**对照表放 A5，不设同库专章** |
| **A6 实现难点与过程困难** | 必覆盖：场景易说成全站痛点；贡献率≠少打字证明；async 空态；examples vs plugin preset 易混；推错近邻放大风险；缺严肃 A/B |

业界/产品金句保留极短指针即可。

---

## 3. Part B · 工程 Spec（双通道叙事）

### 3.1 关系模型（必须在 B0 用图说清）

```
        ┌─ B1 通道一：进门内置 ─┐
用户 ───┤                       ├──► B3 汇合：点推荐 = 新开一轮完整问数
        └─ B2 通道二：查完相似 ─┘
                 │
                 ▼
        B4 晚了 / 空了 / 推歪了
                 │
                 ▼
        B5 下一刀往哪砍
```

| 关系 | 含义 |
|------|------|
| **B1 ∥ B2** | 并行双通道，不是先后工序 |
| **B3** | 两通道的**共同出口**（点击后果） |
| **时间线** | 会话中常先遇 B1、查完再遇 B2；但用户纯手打（不点 B1）也会触发 B2——B2 不依赖 B1 被点过 |

每一站四拍：场景句 → 代码落点 → 数据形状 → 易踩坑 / 面试一句（≤3 行）。

### 3.2 Part B 目录（已定标题）

| 节 | 标题 | 要点 |
|----|------|------|
| **B0** | 先看清两条路 | 上图 + 类职责 + 配置速查；与 03 一行对照 |
| **B1** | 通道一：进门内置 | `Agent` / `AgentDO.examples`；前端进门展示；点下去当新 query；`doExecuteAgentExamples` 是 03 冷启动种子的自动入口之一（跑 examples 成功 + Memory Review 开 → 入记忆库），本文不展开 Review 细节，链 03 B5；**勿混** `preset_query_collection`（PluginManager） |
| **B2** | 通道二：查完相似 | `QueryRecommendProcessor.process` → `CompletableFuture.runAsync`；`recallExemplars(memory_{agentId}, queryText, 5)`（topK **硬编码**）；只取 `question` → `ChatQueryDO.similarQueries`；chat-sdk `SimilarQuestionItem` 展开可再拉 |
| **B3** | 汇合：点推荐后再跑一轮问数 | 再走完整 parse/execute；与手打路径差异主要在归因；`source=preset|similar` 标清落点（**当前 OSS Java 主链路未检索到 source 枚举；产品/ELK 口径，实现对码再确认埋点位置**） |
| **B4** | 晚了、空了、推歪了 | 异步慢→空列表；按 **queryId** 回写（无 OSS version 字段）；固化题型；ENABLED 近邻仍可能语义错 |
| **B5** | 下一刀往哪砍 | 见 §3.3 |

### 3.3 B5 改进方向最低集合

| 优先级 | 方向 |
|--------|------|
| P0 | `source`（或等价归因）在可查证链路中代码化 / 与 ELK 字段对齐 |
| P0 | 相似异步空态与超时的产品约定（重试拉取 / 占位文案），写清现状 vs 期望 |
| P1 | 内置 × 相似去重与联动（点过的内置是否在相似里降权） |
| P1 | 按 Agent / 实验周切片的贡献率看板 |
| P1 | 与 03 治理联动：03 DISABLED 后 04 自动召不到（同库只读）；推荐侧负反馈能否触发 03 的 `disableMemory` 走 B4.1 链 |
| P2 | A/B；对 `source=similar\|preset` 子集看执行成功率 / 近重复手打是否下降 |

---

## 4. Part C · 薄附录

- 题纲 §2.3 题号 → A/B 锚点 + 一句口径  
- 回看清单（含：能画出 B1∥B2→B3；能区分 plugin preset；能说清与 03 同库只读）  
- 删除大段「功能实现类 Q」复述  

---

## 5. 诚实边界（文首必有）

| 说法 | 可讲 | 不可讲 |
|------|------|--------|
| 相似 | Parse 后异步；只读记忆库 question | 「边输入边联想就是本模块」 |
| 内置 | Agent.examples 列表 | 「等于 preset_query_collection」 |
| 同库 | 与 03 同一 `memory_{agentId}`；推荐不写库 | 「推荐另有一套写入链路」 |
| source 15%/11% | 产品贡献率口径 | 「Java 主链路已有 source 枚举」（除非对码证实） |
| 竞态 | queryId 回写；用户已进下一问则挂在旧题旁 | 「已上线 version 协议」 |

---

## 6. 代码锚点清单（实现对码）

| 职责 | 预期落点 |
|------|----------|
| 相似异步 | `QueryRecommendProcessor` |
| 召回 | `ExemplarService.recallExemplars` + `EmbeddingConfig.getMemoryCollectionName` |
| 持久化展示字段 | `ChatQueryDO.similarQueries` |
| 内置配置 | `Agent.examples` / `AgentDO.examples` |
| 冷启动种子自动执行（与 03 B5 关联） | `AgentServiceImpl.doExecuteAgentExamples` |
| Plugin 易混集合 | `EmbeddingConfig` preset collection + `PluginManager` |
| 前端 | `webapp/packages/chat-sdk/.../SimilarQuestionItem.tsx` 等 |

---

## 7. 原文档迁移映射

| 原 `04` 内容 | 去向 |
|--------------|------|
| §0 地图 / 诚实边界 / 调用点 | 文首 + B0–B2（改写成通道叙事） |
| §0.5 与记忆对照 | **A5**（短表） |
| 主叙事四句 / §3.1–3.2 样例 | A1 + A3（压缩） |
| §3.3–3.4 功能与指标 Q | B1–B3 + A4（去 Q&A 壳） |
| §3.5 诚实边界 | 文首表 + B4 |
| 改进相关口述 | **A6 + B5** |
| §3.6 题纲索引 | Part C |

---

## 8. 文风与体量

- B0 必须用图或等价 ASCII 标明 **∥ 与汇合**，避免读者理解成流水线。  
- 节标题用已定「通道一 / 通道二 / 汇合」故事向名称。  
- 目标体量约 **350–500 行**（现 ~283，Spec 加深后可略增；A 样例宜减）。  

---

## 9. 验收标准

1. 仅读 B0 能回答：B1 与 B2 是并行还是串行？B3 是什么？  
2. 能指出相似 topK=5 硬编码、内置来自 examples。  
3. 能区分 Agent.examples vs plugin preset collection。  
4. A6、B5 非空；无「版本号协议」主口径。  
5. 同库细节不重复 03 的 Review/`#Exemplars` 长文。  
6. Part C 可跳转题纲 §2.3。  

---

## 10. 实现顺序（批准后）

1. 对码 B1–B3 锚点与前端拉取行为。  
2. 按本规格重写 `04-推荐问题.md`。  
3. 与 03（重写后）交叉链接互检。  
4. 再走 `writing-plans` 产出逐步计划（可与 03 计划分文件）。  

---

## 11. 规格自检

| 检查项 | 结果 |
|--------|------|
| 占位符 | 无；行号实现对码时补 |
| 一致性 | B1∥B2→B3 与标题一致；A5 承载同库短表 |
| 范围 | 单文件 04，一份计划可覆盖 |
| 模糊性 | 通道关系已用图固定；source 默认产品口径 |

---

## 12. 修订记录

| 日期 | 变更 |
|------|------|
| 2026-08-10 | 初稿：A/B/C；双通道叙事；B1/B2/B3 定为通道一/通道二/汇合 |
| 2026-08-10 | 审后修订：B3 source 落点与 §5 诚实边界对齐（默认未检索到，对码确认）；B1 `doExecuteAgentExamples` 链 03 B5（去「可选」）；B5 加 P1「与 03 治理联动」；§3.1 时间线行去拗口；§6 锚点表「例题自动跑」改为「冷启动种子自动执行（与 03 B5 关联）」 |
