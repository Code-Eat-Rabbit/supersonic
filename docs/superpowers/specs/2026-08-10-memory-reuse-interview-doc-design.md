# 查询记忆复用面试文档重写 — 设计规格

> 日期：2026-08-10  
> 状态：待用户审查  
> 目标文件：`docs/resume/interview/智能问数/03-查询记忆复用.md`  
> 题纲：`docs/resume/interview/面试题纲.md` § 2.2  
> 代码标本：本仓库 SuperSonic（`chat/` + `headless/` + `common/`），非独立自研 Memory 模块  
> 体例参照：`docs/resume/interview/深度研究/04-Hybrid-Search-MCP.md`（调用点优先 + 短代码 + 易踩坑）

---

## 1. 背景与目标

### 1.1 问题

现有 `03-查询记忆复用.md` 经一轮「调用点表」补强后，主体仍是产品/效果向 Q&A，技术实现偏弱：读者难以按一条记忆的生命周期读懂代码，且部分旧话术（1–5 分、Top-3、线上 300）与实现不符。

### 1.2 目标

1. **按代码反推工程 Spec**，与现有需求/效果/评测内容合并为**单文件**重写。
2. 文档形态定为：**Part A 需求与效果（开篇）→ Part B 工程 Spec（正文，生命周期叙事）→ Part C 薄题纲附录**。
3. 数字与 `智能问数/01-总览与业务背景.md` §0 对齐；与代码冲突处以代码为准，写进诚实边界。
4. 可读性优先：Part B 用「一条记忆写出去再被读回来」主线，而非模块说明书平铺或题纲 Q&A 堆叠。

### 1.3 非目标

- 不拆成 `03a` / `03b` 两篇。
- 不在本文展开相似推荐实现（不设「同库另一读者」专章）；仅在 A5/B0 **一行**指向 `04-推荐问题.md`。
- 不把 02 SchemaMapper、04 推荐问题一并大改（可后续复用本规格的 A/B/C 模板）。
- 不改业务/框架功能代码；本规格只约束面试文档重写。
- 不把「1–5 分自动入库 / Top-3 few-shot / 线上抽 300 得 87%」写回正文。

---

## 2. 总体结构（已定）

```
03-查询记忆复用.md
├── 文首元信息（系列导航、题纲、标本、诚实边界总表）
├── Part A · 需求与效果          ← 原产品/评测精华，压缩
├── Part B · 工程 Spec            ← 代码主轴 + 原实现类内容合并
└── Part C · 题纲索引（薄）       ← 题号→锚点，少口语长文
```

### 2.1 Part A · 需求与效果（开篇，体量约原文档相关内容的 1/3）

| 小节 | 内容 | 素材来源 |
|------|------|----------|
| **A1 背景与动机** | T1 后卡在 Parser；静态 few-shot / 有害示范；要动态同构范文 | 原 §2.1–2.2 痛点（压缩） |
| **A2 目标与非目标** | 目标：过审记忆进 `#Exemplars`；非目标：自研向量框架、替代 SchemaMapper | 新写 + 诚实边界 |
| **A3 已实现效果** | 端到端 72%→87%；库 800+；冷启动种子 **200** 等**数字** | 原指标；操作细节不在此展开 |
| **A4 评测口径** | 同一批 200、无 HITL、T0/T1/T2、+15pp 归因、Parser 条件切片 | 原 §2.3（表格式压缩） |
| **A5 与 02/04 边界** | SchemaMapper / 记忆 / 推荐一句话分工；推荐「同库异步只读」**一行**链 04 | 现 §0.2 |

业界论文（DIN-SQL / DAIL-SQL 等）保留 **3～5 行指针**，不展开成长文。

**数字 vs 运营分工（已定）**：效果**数字**进 A3；冷启动怎么灌、周人审怎么做等**操作**进 B5。

### 2.2 Part B · 工程 Spec（正文，生命周期叙事）

主线故事：

```
挂四元组 → 执行 SUCCESS 落 PENDING
  → MemoryReviewTask 定时扫 → POSITIVE 则 ENABLED + 入向量
  →（旁路：人审 / 用户反馈 score）
  → 进程启动 ApplicationRunner 回灌 ENABLED
  → 下一次 query：recall → 筛成 few-shot → #Exemplars → 新 S2SQL
```

每一站（B2/B3 内的小节）固定四拍：

1. **这一站在解决什么**（1～2 句场景）  
2. **代码落点**（类·方法 + 短摘录，路径相对仓库根）  
3. **数据长什么样**（字段 / JSON / 状态变化）  
4. **易踩坑 / 面试一句**（≤ 3 行）

#### Part B 目录（已定标题）

| 节 | 标题 | 要点 |
|----|------|------|
| **B0** | 一张总图 | 组件 + 主线箭头 + 类职责表 + 配置键速查；**一行**注明相似推荐同库见 04 |
| **B1** | 这条记忆长什么样 | `s2_chat_memory` 字段；`Text2SQLExemplar`；集合 `memory_{agentId}`；embedding 对象=`question` |
| **B2** | 写出来：SUCCESS → PENDING → Review 定时扫 → ENABLED | 含 **MemoryReviewTask `@Scheduled(60s)`** 与 **ApplicationRunner 启动回灌** 两站；旁路人审 / score≥5/≤1 |
| **B3** | 读回去：recall → `#Exemplars` | `NL2SQLParser.addDynamicExemplars`；recall=10；`PromptHelper`→few-shot=5；`OnePassSCSqlGenStrategy` 模板 |
| **B4** | 记忆帮倒忙时：污染、下线与未还的债 | 负迁移案例；DISABLED + `removeExemplar`；无 TTL；Review 默认不看执行结果集；开源 Review「不重点抠日期」与金融场景张力 |
| **B5** | 空库到 800+：冷启动、人审与转化 | `[运营]` 标注；4 Agent 种子分配；周人审；漏斗 ~5% / PENDING→ENABLED ~50–60%；**不重复**讲调度实现 |

**明确删除的原设想**：「同库另一读者」独立成章（原草案 B4）——不做。

### 2.3 Part C · 薄附录

- 题纲 §2.2 题号 → A/B 锚点 + **一句**口径（对齐代码）  
- 回看清单（勾选）  
- **不**再堆大段「第一句答题」复述（口径已在 A/B）

---

## 3. 诚实边界（必须写进文首或 A2，并在 B 中落实）

| 说法 | 可讲 | 不可讲 |
|------|------|--------|
| 实现归属 | 开源 SuperSonic 链路；业务侧开 Review、冷启动、人审、评测 | 「我从零自研记忆向量框架」 |
| 审核形态 | `POSITIVE` / `NEGATIVE`；人审；反馈 score≥5/≤1 | 「1–5 分、≥4 自动入库」 |
| 召回条数 | 向量召回 **10** → 注入约 **5** | 「Top-3 few-shot」作主口径 |
| 评测集 | 离线 **200**、无 HITL；T1→T2 +15pp | 「线上 300」作 87% 主口径 |
| 表字段 | 无表内 embedding、无复用次数 | 「表里有 hit count」 |
| 执行成功 | 只 PENDING；ENABLED 要过审 | 「不报错就进 few-shot」 |
| NEGATIVE | 记 llm_review；status 常仍 PENDING | 「NEGATIVE 自动 DISABLED」 |
| 推荐 / version | 一行链 04；async 按 queryId | 编造 OSS「版本号协议」 |

---

## 4. 代码锚点清单（实现时必须对过再写）

重写前用本仓库再核对；摘录以当时行号为准，文档中写 **类·方法**，行号可随代码漂移更新。

| 职责 | 类 · 方法（预期） |
|------|-------------------|
| DO / 表 | `ChatMemoryDO` / schema `s2_chat_memory` |
| 挂四元组 | `LLMResponseService.addParseInfo` |
| 落 PENDING | `SqlExecutor.execute`（SUCCESS + `LLMSqlQuery`） |
| 创建去重 | `MemoryServiceImpl.createMemory` |
| 定时审 | `MemoryReviewTask.review` / `processMemory` / `processResponse` |
| 入/出向量 | `MemoryServiceImpl.enableMemory` / `disableMemory` |
| 启动回灌 | `MemoryServiceImpl` ApplicationRunner（`run`） |
| 召回注入 | `NL2SQLParser.addDynamicExemplars` |
| 筛 few-shot | `PromptHelper.getFewShotExemplars` |
| Prompt | `OnePassSCSqlGenStrategy` |
| 向量 CRUD | `ExemplarServiceImpl.storeExemplar` / `recallExemplars` |
| 配置 | `assembly/conf/s2-config.yaml`：`exemplar-recall.number`、`few-shot.number`；Agent `MEMORY_REVIEW.enable` |

---

## 5. 原文档迁移映射

| 原 `03` 内容 | 去向 |
|--------------|------|
| §0 地图 / 诚实边界 / 字段表 / 调用点表 | 文首 + B0–B2（改写成叙事，不保留「大表贴在最前、后文又讲一遍」） |
| §2.1 电梯稿、痛点、业界、替代方案 | A1（压缩）；业界缩为指针 |
| §2.2 审核 prompt、人审、800+、冷启动 | B2（审核/定时任务代码）+ B5（运营数字与节奏） |
| §2.2 prompt / 10→5 筛选 | B3 |
| §2.3 测评集与 +15pp | A4（压缩）；JSON 示例可留 1 个或链 01 |
| §2.4 技术债 / 帮倒忙 | B4 |
| §2.5 题纲索引 | Part C（更新锚点） |
| 与推荐同库大段对照 | **删除专章**；A5/B0 一行 + 链 04 |

---

## 6. 文风与体量

- 节首用场景句（「执行刚返回 SUCCESS…」），不用「本章旨在…」。  
- 先代码后口径；Part B 内口语框 ≤ 3 行。  
- 每个主路径至少 1 个真实代码锚点。  
- 目标体量：约 **550–750 行**（可低于现 618 若 A 压缩到位；B 因代码摘录可略增）。  
- 配置与默认值写明「本仓库 yaml vs Parameter 默认」。

---

## 7. 验收标准

重写完成后应满足：

1. 不看后文 Q&A，仅读 Part B 能讲清：PENDING 谁写、谁审、谁入向量、谁召回、注入几条。  
2. 能指出 `MemoryReviewTask` 与 ApplicationRunner 各自解决什么问题。  
3. 文中无「1–5 分 / Top-3 / 线上 300」主口径；题纲宽问已对齐处保持一致。  
4. 无「同库另一读者」专章；04 仅一行链接。  
5. A3 有 800+/200 等数字；B5 有运营细节且标 `[运营]`。  
6. Part C 可按题纲 §2.2 跳转，无大段重复口述。

---

## 8. 实现顺序（批准本规格后）

1. 再扫写/读/审/启动四路径，固化「事实清单」（可附在实现计划中）。  
2. 按本规格重写 `03-查询记忆复用.md`（可先备份或 git 对比）。  
3. 抽查题纲 §2.2 与 `01` 数字交叉引用是否仍有效。  
4. （可选）用同一 A/B/C 模板规划 02/04，不在本规格范围内实施。

实现计划：本规格用户批准后，再走 `writing-plans` 产出逐步计划。

---

## 9. 规格自检（编写时已过）

| 检查项 | 结果 |
|--------|------|
| 占位符 / TODO | 无未决 TODO；行号以实现对码时为准 |
| 内部一致性 | A3 数字 / B5 运营；B2 含定时任务与 Runner；无同库专章 |
| 范围 | 单文件 `03` 重写，可一份实现计划覆盖 |
| 模糊性 | Part B 标题与四拍结构已选定；审核口径以 POSITIVE/NEGATIVE 为准 |

---

## 10. 修订记录

| 日期 | 变更 |
|------|------|
| 2026-08-10 | 初稿：形态 B（效果开篇 + Spec 正文）；Part B 生命周期叙事；去掉同库专章；B2 纳入定时扫与 ApplicationRunner；B4/B5 定名 |
