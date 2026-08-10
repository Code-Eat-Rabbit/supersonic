# 推荐问题面试文档重写 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 把 `docs/resume/interview/智能问数/04-推荐问题.md`（现 283 行、§0 调用点 + §3.x Q&A 混合形态）按规格重写为「Part A 需求与效果 → Part B 工程 Spec（双通道叙事）→ Part C 薄附录」单文件形态，B0 用 ASCII 图说清 B1 ∥ B2 → 汇合于 B3 的关系。

**架构：** 单文件 `.md` 重写，不动业务代码。Part B 采用「双通道」故事结构（B1 进门内置 ∥ B2 查完相似 → B3 汇合点推荐再跑一轮 → B4 风险 → B5 改进），每节固定四拍（场景句 → 代码落点 → 数据形状 → 易踩坑/面试一句）。数字以 `01-总览与业务背景.md` §0 与代码为准。

**技术栈：** Markdown；代码锚点相对仓库根（SuperSonic Java 仓库 + chat-sdk 前端）；配置锚点指向 `EmbeddingConfig`（`presetCollection` 默认 `preset_query_collection`）+ Agent `examples` 字段。

**规格：** [`docs/superpowers/specs/2026-08-10-recommend-questions-interview-doc-design.md`](../specs/2026-08-10-recommend-questions-interview-doc-design.md)（已含审后修订）

**关键约束（来自规格 §5 诚实边界 + §9 验收）：**
- 正文不得把「输入联想」说成相似推荐
- 不得把 `preset_query_collection`（Plugin）说成内置 FAQ
- 不得编造 OSS「版本号协议」——实际是按 `queryId` 回写
- 「source 枚举」全栈不存在（已由 `/tmp/04-fact-check.md` 核查确认）——正文写「OSS 未检索到 source 枚举；产品/ELK 口径」
- B0 必须用 ASCII 图说清 ∥ 与汇合（避免读者理解成流水线）
- A6、B5 非空

**文件结构：**

| 文件 | 动作 | 职责 |
|------|------|------|
| `docs/resume/interview/智能问数/04-推荐问题.md` | 重写（覆盖） | 唯一交付物 |
| `docs/resume/interview/面试题纲.md` § 2.3 | 只读核对 | 宽问第一句答题口径须与正文一致 |
| `docs/resume/interview/智能问数/01-总览与业务背景.md` §0 | 只读核对 | 数字基线 |
| `docs/resume/interview/智能问数/03-查询记忆复用.md` | 只读核对 | 同库对照（A5 短表 + B0 一行链） |
| `/tmp/04-fact-check.md` | 只读素材 | 10 锚点行号 + 摘录（任务 1-3 用） |

**本计划不含代码改动。** 体例完全沿用 03 SDD（任务 0 git 备份 → 任务 1 事实清单 → 任务 2-10 逐节重写 → 任务 11 通读验收）。每个任务以「可核对的事实」当测试。

---

## 任务 0：开工前 git 备份

**文件：**
- 操作：git tag / 备份，不写文件

- [ ] **步骤 1：记录 BASE 锚点**

运行：
```bash
cd /Users/yourton_ma/workspace/supersonic
git log -1 --oneline -- docs/resume/interview/智能问数/04-推荐问题.md
```
预期：输出 04 文件最近一次提交 hash 与 subject（任务 0 之前的 BASE）。记下 hash。

- [ ] **步骤 2：复制副作用备份**

运行：
```bash
cp docs/resume/interview/智能问数/04-推荐问题.md /tmp/04-推荐问题.md.before-rewrite
wc -l /tmp/04-推荐问题.md.before-rewrite
```
预期：输出 `283 /tmp/04-推荐问题.md.before-rewrite`（允许 ±5 行波动）。

---

## 任务 1：事实清单——把规格 §6 锚点 + `/tmp/04-fact-check.md` 整理成实现素材

**目的：** 规格明确「行号可漂移，类·方法为准」。把 `/tmp/04-fact-check.md`（已由预核查产出）+ 规格 §6 + §3.2 B1-B5 要点合并成一份「实现时直接引用」的素材表。本任务**唯一**产出物 `/tmp/04-fact-sheet.md`，不进仓库。

**文件：**
- 读：`/tmp/04-fact-check.md`（已存在）、规格 §3.2/§5/§6
- 写：`/tmp/04-fact-sheet.md`（临时）

- [ ] **步骤 1：从 `/tmp/04-fact-check.md` 抽锚点速查表**

把 `/tmp/04-fact-check.md` 的「7 大锚点总表」+ 「重点确认 7 项逐条结论」+「与规格描述的差异」三段，整合成下表格式写到 `/tmp/04-fact-sheet.md`：

```markdown
# 04 重写事实清单（临时，不进 git）

生成时间：2026-08-10
BASE commit：<任务 0 步骤 1 记下的 hash>

## 锚点速查（来自预核查 /tmp/04-fact-check.md）

| 职责 | 类·方法/字段 | 文件:行 | 备注 |
|------|--------------|---------|------|
| 相似异步主类 | `QueryRecommendProcessor.process` | chat/server/.../processor/parse/QueryRecommendProcessor.java:32 | `CompletableFuture.runAsync(doProcess)` 无自定义线程池（用 ForkJoinPool.commonPool） |
| 召回方法 | `getSimilarQueries` | QueryRecommendProcessor.java:46 | `recallExemplars(memoryCollectionName, queryText, 5)` topK 硬编码 |
| 持久化字段 | `ChatQueryDO.similarQueries` | ChatQueryDO.java:44 | `String`（JSON 序列化）；API 层 `QueryResp.similarQueries` 是 `List<SimilarQueryRecallResp>` |
| 内置配置 | `Agent.examples`（List<String>）/ `AgentDO.examples`（String JSON） | Agent.java:33 / AgentDO.java:24 | DO ↔ Domain 转：`JsonUtil.toList` / `JsonUtil.toString` |
| 冷启动种子自动执行 | `AgentServiceImpl.doExecuteAgentExamples` | AgentServiceImpl.java:125 | `private synchronized`；前置 `agent.containsDatasetTool() && enableMemoryReview() && examples 非空`；调 `chatQueryService.parseAndExecute` |
| Plugin 易混集合 | `EmbeddingConfig.presetCollection`（字段名，默认 `preset_query_collection`） | EmbeddingConfig.java:14 | 注意：字段名是 `presetCollection` 不是 `preset`；由 `PluginManager` 使用 |
| 前端展示 | `SimilarQuestionItem.tsx`（导出名 `SimilarQuestions`） | webapp/packages/chat-sdk/src/components/ChatItem/SimilarQuestionItem.tsx | `useEffect` 在 `expanded && similarQuestions.length===0` 时拉 `GET /chat/manage/getChatQuery/{queryId}` |

## source 枚举核查结论

- Java 侧（chat/ + headless/ + common/）：**未检索到** `source.*preset\|source.*similar\|source.*manual`
- 前端 chat-sdk：**未检索到**
- 结论：全栈无 source 枚举；15%/11% 是**产品/ELK 口径**，实现时如实写

## 关键代码摘录（≤ 8 行，写 B0/B2 时直接引用）

### 1. QueryRecommendProcessor.process + getSimilarQueries（核心）
（从 /tmp/04-fact-check.md 第二节复制 ≤ 12 行）

### 2. AgentServiceImpl.doExecuteAgentExamples 前置条件 + 调用链
（从 /tmp/04-fact-check.md 第二节复制 ≤ 8 行）

### 3. SimilarQuestionItem.tsx 的 useEffect 拉取行为
（从 /tmp/04-fact-check.md 第六节复制 ≤ 10 行）

## 与规格/03 体例的一致性要点

- 诚实边界表跨文档：与 03 文件「诚实边界总表」的「推荐/version」行口径一致（queryId 回写、无 OSS version 字段）
- 数字基线：15%/11%/26%、日均 150、`memory_{agentId}`、topK=5 硬编码
- 接口名：`Agent.examples`（不是 `agent.getPreset`）；`EmbeddingConfig.presetCollection`（不是 `preset`）
- 前端导出名 `SimilarQuestions` vs 文件名 `SimilarQuestionItem`——实现时按文件名引用路径，按实际导出名说组件
- 前后端类型不对齐：Java `SimilarQueryRecallResp` 无 `parseId`，前端 `SimilarQuestionType` 有 `parseId`（可在 B4 或 B0 易踩坑提一句）

## 与规格差异（无阻断）
- 全部 4 处差异（D1-D4）已在 /tmp/04-fact-check.md 记录，不影响规格描述正确性
```

- [ ] **步骤 2：确认事实清单非空**

运行：
```bash
test -s /tmp/04-fact-sheet.md && echo OK || echo EMPTY
wc -l /tmp/04-fact-sheet.md
```
预期：`OK` 且行数 ≥ 50。

- [ ] **步骤 3：Commit（事实清单不进仓库，无 commit）**

事实清单是临时产物。本步骤只确认它已生成。

---

## 任务 2：文首元信息 + 诚实边界总表 + Part A (A1–A5)

**目的：** 建立新文档骨架。A1–A5 是压缩后的需求与效果（规格 §2.1）。

**文件：**
- 写：`docs/resume/interview/智能问数/04-推荐问题.md`（覆盖）

- [ ] **步骤 1：用 Write 工具覆盖 04 文件，写文首 + 诚实边界表 + Part A 五节 + A6 占位**

结构必须含：

1. **文首元信息块**（系列导航 + 题纲 + 标本）。参考 03 文件文首：
   ```
   > 系列：智能问数
   > 简历基线：[`../../my_resume.md`](../../my_resume.md)
   > 总览：[`01-总览与业务背景.md`](./01-总览与业务背景.md)
   > 上一篇：[03-查询记忆复用](./03-查询记忆复用.md) · 回到：[01-总览与业务背景](./01-总览与业务背景.md)
   > 题纲：[`../面试题纲.md`](../面试题纲.md) § 2.3
   > 相似通道标本：`QueryRecommendProcessor`；内置通道标本：`Agent.examples`
   ```
2. **诚实边界总表**（规格 §5 逐字搬 5 行）：
   | 说法 | 可讲 | 不可讲 |
   |------|------|--------|
   | 相似 | Parse 后异步；只读记忆库 question | 「边输入边联想就是本模块」 |
   | 内置 | Agent.examples 列表 | 「等于 preset_query_collection」 |
   | 同库 | 与 03 同一 `memory_{agentId}`；推荐不写库 | 「推荐另有一套写入链路」 |
   | source 15%/11% | 产品贡献率口径 | 「Java 主链路已有 source 枚举」（**全栈未检索到，事实清单已确认**） |
   | 竞态 | queryId 回写；用户已进下一问则挂在旧题旁 | 「已上线 version 协议」 |
3. **Part A · 需求与效果**：
   - **A1 背景与动机**（≤ 25 行；拆场景：行为助理反复查 + 连续追问 / 绿色金融引导开口；**不是**全站「不会提问」。压缩自原 04 §3.1 + §3.2 + §3.3 第一个 Q）
   - **A2 目标与非目标**（目标：降低开口成本、结果旁下一跳；非目标：输入联想、另建推荐库、替代记忆复用）
   - **A3 已实现效果**（数字：内置 15% / 相似 11%（查询贡献率）；样例表**压缩**保留——行为与绿色各留 2-3 条代表性条目，不必全文堆砌；原 04 §3.2 A/B 两大表各留 2-3 行）
   - **A4 指标口径**（`count(source=…)/count(全部)`；主 KPI 非 impression CTR；诚实：OSS Java **未检索到** `source` 枚举 → 标 `[产品/ELK 口径]`；含 source 枚举表 manual/preset/similar + 贡献率表）
   - **A5 与 03 边界**（同一 `memory_{agentId}`；03 同步教模型 / 04 异步给人点——**对照表放 A5**，4 行：集合/时机/消费/写入；不设同库专章）
4. **A6 占位**（写一行 `> A6 详见任务 3 补全`）

A1–A5 内**不要**贴代码摘录（代码落点是 Part B 的事）。

- [ ] **步骤 2：核对诚实边界总表 5 行齐全**

运行：
```bash
grep -c '^| \*\*' docs/resume/interview/智能问数/04-推荐问题.md
```
预期：≥ 5（诚实边界 5 项，加 A5 边界表 3 项可能更多）。

- [ ] **步骤 3：核对 A3 数字口径**

运行：
```bash
grep -n '15%\|11%\|26%\|150' docs/resume/interview/智能问数/04-推荐问题.md | head -10
```
预期：A3 段落内同时出现 `15%`、`11%`、`26%`、`日均 150`。

- [ ] **步骤 4：核对 source 诚实写法**

运行：
```bash
grep -c '未检索到\|OSS.*未\|产品/ELK\|产品.*ELK\|\[产品' docs/resume/interview/智能问数/04-推荐问题.md
```
预期：≥ 1（A4 或诚实边界表至少一处标清 source 是产品/ELK 口径）。

- [ ] **步骤 5：Commit**

```bash
cd /Users/yourton_ma/workspace/supersonic
git add docs/resume/interview/智能问数/04-推荐问题.md
git commit -m "$(cat <<'EOF'
docs(interview): rewrite 04 recommend-questions doc header + Part A (A1–A5)

按规格 2026-08-10（含审后修订）重写 04 文首元信息与 Part A 需求/效果：
诚实边界总表 5 行（source 全栈未检索到标产品/ELK 口径）；A3 数字 15%/11%/26%；
A5 与 03 同库对照表 4 行；A6 占位待补。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 3：补 A6 实现难点与过程困难（**非空硬性要求**）

**目的：** 满足规格 §9 验收第 4 条：A6 非空。条目式短文，每条 3–6 行，覆盖规格 §2.1 A6 行的 6 类难点。

**文件：**
- 改：`docs/resume/interview/智能问数/04-推荐问题.md`（替换 A6 占位）

- [ ] **步骤 1：写 A6，逐条对应规格 §2.1 A6 难点清单**

A6 用条目式短文，每条固定三拍「难在哪 → 当时怎么扛 → 留下什么」。必须覆盖下表 6 条（标题关键词不能整类缺失）：

| # | 难点（必须出现） | 当时怎么扛（一句话） | 指向 |
|---|------------------|---------------------|------|
| 1 | 场景易说成全站痛点 | 拆场景：行为实验助理反复查（相似通道主战场）vs 绿色金融引导开口（内置通道） | A1；B1/B2 |
| 2 | 贡献率 ≠ 少打字证明 | 15%/11% 只说明「从推荐入口进来的查询占比」；没做严肃 A/B；更深要 source=similar\|preset 子集看执行成功率 + 同骨架手打是否下降 | A4；B5 |
| 3 | async 空态 / 超时 | OSS 无专门 timeout UI 协议；异步慢则列表暂空；前端 `useEffect` 在 expanded 时再拉；用户进下一问则挂在旧题旁 | B2/B4 |
| 4 | examples vs plugin preset 易混 | `Agent.examples`（前端进门展示）vs `EmbeddingConfig.presetCollection`（默认 `preset_query_collection`，给 Plugin 识别用，`PluginManager` 消费）；面试常被追问 | B1；诚实边界表 |
| 5 | 推错近邻放大风险 | 只推 ENABLED 近邻（依赖 03 治理）；但 ENABLED 仍可能语义错（如「去年」滚动 365 天教坏）；错范文先治 03 记忆库 | B4；链 03 B4.1 |
| 6 | 缺严肃 A/B | 贡献率是观测指标非因果；还没按 Agent/实验周切片常态化看板；没有 randomized exposure | B5 P0/P2 |

每条 3–6 行；**不得**写成大段产品独白。

- [ ] **步骤 2：核对 6 类难点关键词齐全**

运行：
```bash
for kw in "场景\|全站" "贡献率\|少打字" "async\|异步\|空态\|超时" "examples\|preset" "推错\|近邻\|放大" "A/B\|严肃"; do
  echo -n "$kw: "
  grep -c "$kw" docs/resume/interview/智能问数/04-推荐问题.md
done
```
预期：每项 ≥ 1。任一为 0 即缺类，回步骤 1 补。

- [ ] **步骤 3：核对 A6 体量**

运行：
```bash
awk '/^### .*A6|^## A6/{f=1} f{print} /^## [A-C][0-9]/{if(f&&!/^## A6/){exit}}' docs/resume/interview/智能问数/04-推荐问题.md | wc -l
```
预期：30–70 行（6 条 × 3–6 行 + 小标题 + 引子）。低于 30 说明每条写太薄；高于 70 说明写回大段独白。

- [ ] **步骤 4：Commit**

```bash
git add docs/resume/interview/智能问数/04-推荐问题.md
git commit -m "$(cat <<'EOF'
docs(interview): fill A6 difficulties in 04 recommend-questions doc

A6 覆盖 6 类难点：场景易说成全站痛点、贡献率≠少打字证明、async 空态、
examples vs plugin preset 易混、推错近邻放大、缺严肃 A/B；
每条「难在哪→当时怎么扛→留下什么」3–6 行。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 4：Part B0 先看清两条路（**ASCII 图说清 ∥ 与汇合**）

**目的：** 规格验收 §9 第 1 条：仅读 B0 能回答 B1 与 B2 是并行还是串行。规格 §3.1 关系模型必须用图说清。

**文件：**
- 改：`docs/resume/interview/智能问数/04-推荐问题.md`（在 A6 后追加）

- [ ] **步骤 1：写 B0 含 4 部分**

### B0.1 主线箭头图（ASCII，规格 §3.1 图逐字搬）

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

紧跟一张关系表（规格 §3.1，3 行）：
| 关系 | 含义 |
|------|------|
| **B1 ∥ B2** | 并行双通道，不是先后工序 |
| **B3** | 两通道的**共同出口**（点击后果） |
| **时间线** | 会话中常先遇 B1、查完再遇 B2；但用户纯手打（不点 B1）也会触发 B2——B2 不依赖 B1 被点过 |

### B0.2 类职责表（从事实清单搬，两列：职责 / 类·方法，**不列行号**）

7 行（按 `/tmp/04-fact-sheet.md` 锚点速查表）：
- 相似异步主类 → `QueryRecommendProcessor.process`
- 召回方法 → `QueryRecommendProcessor.getSimilarQueries`（调 `recallExemplars` topK=5 硬编码）
- 持久化字段 → `ChatQueryDO.similarQueries`（String JSON）
- 内置配置 → `Agent.examples`（List<String>）/ `AgentDO.examples`（String JSON）
- 冷启动种子自动执行 → `AgentServiceImpl.doExecuteAgentExamples`（链 03 B5）
- Plugin 易混集合 → `EmbeddingConfig.presetCollection`（默认 `preset_query_collection`，`PluginManager` 消费）
- 前端展示 → `SimilarQuestionItem.tsx`（导出名 `SimilarQuestions`）

### B0.3 配置速查（3 项）

| 配置项 | 本仓库值 | 来源 | 备注 |
|--------|---------|------|------|
| 相似召回 topK | **5** | `QueryRecommendProcessor.java:51` **硬编码** | 不走 yaml；改要改源码 |
| `s2.embedding.memory.collection.prefix` | `memory_`（默认） | yaml | 集合名 `memory_{agentId}` |
| `s2.embedding.preset.collection` | `preset_query_collection`（默认） | yaml | **Plugin 用**，**不是内置 FAQ** |

### B0.4 一行 03 对照（不展开）

`> 与 03 同库只读、不进 #Exemplars、链 [03-查询记忆复用](./03-查询记忆复用.md) A5`——**不**设同库专章。

- [ ] **步骤 2：核对 B0 ASCII 图含 ∥ 符号**

运行：
```bash
grep -c '∥\|并行双通道' docs/resume/interview/智能问数/04-推荐问题.md
```
预期：≥ 2（图里 1 处 + 关系表 1 处）。

- [ ] **步骤 3：核对无同库专章**

运行：
```bash
grep -c '^##.*同库\|^##.*另一读者' docs/resume/interview/智能问数/04-推荐问题.md
```
预期：0。

- [ ] **步骤 4：核对 03 链接只一行（不展开）**

运行：
```bash
grep -c '03-查询记忆复用' docs/resume/interview/智能问数/04-推荐问题.md
```
预期：≤ 4（文首导航 1 + A5 表 1 + A6 条目 5 链 1 + B0.4 一行链 1）。**不得**出现「同库另一读者」或「同库专章」标题。

- [ ] **步骤 5：Commit**

```bash
git add docs/resume/interview/智能问数/04-推荐问题.md
git commit -m "$(cat <<'EOF'
docs(interview): add Part B0 two-channel overview to 04 doc

B0 四部分：ASCII 双通道图（B1∥B2→B3→B4→B5，含 ∥ 符号 + 关系表）；
类职责表 7 行；配置速查 3 项（topK=5 硬编码、memory_ 前缀、preset_query_collection
注明 Plugin 用）；一行 03 同库只读链。不设同库专章。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 5：Part B1 通道一：进门内置

**目的：** 规格 §3.2 B1 行。讲清 `Agent.examples` 通道——前端进门展示 + 点下去当新 query；`doExecuteAgentExamples` 链 03 B5；**勿混** `preset_query_collection`。

**文件：**
- 改：`docs/resume/interview/智能问数/04-推荐问题.md`

- [ ] **步骤 1：按四拍写 B1**

### 场景（1–2 句）
「用户打开问数页，还没开口——内置题告诉他『可以这样问』。绿色金融第一次不知怎么起头、行为助理进门前要看的 FAQ 清单，都走这条。」

### 代码落点
- **存储**：`Agent.examples`（Domain 层 `List<String>`）/ `AgentDO.examples`（DB 层 String JSON）；DO ↔ Domain 转换：`AgentServiceImpl` 用 `JsonUtil.toList` / `JsonUtil.toString`（事实清单第 4 行）
- **前端展示**：chat-sdk 进门拉 `Agent.examples`，结果区渲染可点列表
- **点下去 = 新 query**：前端把点中的 example 文本当 `queryText` 提交，走完整 `parseAndExecute`（B3 展开）
- **冷启动种子自动执行**（规格修订后明确）：`AgentServiceImpl.doExecuteAgentExamples` 是 **03 冷启动种子的自动入口之一**（跑 examples 成功 + `agent.enableMemoryReview()` 开 → 入记忆库当种子），**本文不展开 Review 细节，链 [03 B5](./03-查询记忆复用.md)**
  - 前置条件（事实清单摘录 2）：`agent.containsDatasetTool() && enableMemoryReview() && examples 非空`
  - 调 `chatQueryService.parseAndExecute`，成功则按 03 B2 走 PENDING → Review
- **勿混** `preset_query_collection`：那是 `EmbeddingConfig.presetCollection`（字段名，不是 `preset`），给 **Plugin** embedding 识别用（`PluginManager.recognize`），不是结果旁「点一下再查」的内置 FAQ

### 数据形状
贴 1 条 `Agent.examples` 配置样例（JSON，3-4 条代表性文案，绿色 + 行为各 1-2 条）。例如：
```json
{
  "agentId": 10,
  "agentName": "绿色金融",
  "examples": [
    "绿色金融改革试验区地级市 2010–2020 年碳排放、GDP、第二产业占比面板",
    "A 股公司按 ESG 评级分组的平均 ROA / Tobin's Q，区分国企与非国企"
  ]
}
```

### 易踩坑（≤ 3 行）
- `Agent.examples` 是前端展示 + 点下去当 query；`preset_query_collection` 是 Plugin 识别用——**两套不互通**
- `AgentDO.examples` 是 String JSON，`Agent.examples` 是 `List<String>`——序列化在 `AgentServiceImpl`
- `doExecuteAgentExamples` 是 `private synchronized`，通过 `executeAgentExamplesAsync` 在 `chatExecutor` 线程池触发（与 `QueryRecommendProcessor` 的 ForkJoinPool 不是同一个池——这是 B4 可提的细节）

- [ ] **步骤 2：核对 B1 关键词**

运行：
```bash
for kw in "Agent.examples\|AgentDO.examples" "doExecuteAgentExamples" "preset_query_collection\|presetCollection" "parseAndExecute"; do
  echo -n "$kw: "; grep -c "$kw" docs/resume/interview/智能问数/04-推荐问题.md
done
```
预期：每项 ≥ 1。

- [ ] **步骤 3：核对链 03 B5**

运行：
```bash
grep -c '03 B5\|03.*B5\|冷启动种子.*自动' docs/resume/interview/智能问数/04-推荐问题.md
```
预期：≥ 1（B1 里有「链 03 B5」字样）。

- [ ] **步骤 4：Commit**

```bash
git add docs/resume/interview/智能问数/04-推荐问题.md
git commit -m "$(cat <<'EOF'
docs(interview): add Part B1 channel-one (built-in) to 04 doc

B1 四拍：Agent.examples 存储 + 前端展示 + 点下去当新 query；
doExecuteAgentExamples 是 03 冷启动种子自动入口，链 03 B5；
勿混 EmbeddingConfig.presetCollection（Plugin 用）。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 6：Part B2 通道二：查完相似

**目的：** 规格 §3.2 B2 行。讲清相似通道——Parse 后异步、topK=5 硬编码、只取 question 写 `similarQueries`、前端 `useEffect` 展开时再拉。

**文件：**
- 改：`docs/resume/interview/智能问数/04-推荐问题.md`

- [ ] **步骤 1：按四拍写 B2**

### 场景（1–2 句）
「用户刚提交一问、Parse 完——异步在结果旁摊开历史上问过的近邻题。吃的是『查完 A 还要问 B』，不是输入联想。」

### 代码落点（一条链）
1. **入口**：`QueryRecommendProcessor.process`（事实清单摘录 1）
   ```java
   @Override
   public void process(ParseContext parseContext) {
       CompletableFuture.runAsync(() -> doProcess(parseContext));
   }
   ```
   - `runAsync` 不指定线程池 → 用 `ForkJoinPool.commonPool()`（与 `doExecuteAgentExamples` 的 `chatExecutor` 不同——B4 可提）
2. **召回**：`getSimilarQueries`（事实清单摘录 1）
   ```java
   List<Text2SQLExemplar> exemplars =
       exemplarService.recallExemplars(memoryCollectionName, queryText, 5);  // topK 硬编码
   return exemplars.stream().map(sqlExemplar -> SimilarQueryRecallResp.builder()
       .queryText(sqlExemplar.getQuestion()).build()).collect(Collectors.toList());
   ```
   - 集合名 `memoryCollectionName = embeddingConfig.getMemoryCollectionName(agentId)`（前缀 `memory_`）
   - topK = **5 硬编码**（不是 yaml；改要改源码）
   - **只取 `question`** → `SimilarQueryRecallResp.queryText`（不取 SQL 四元组的其他三项——与 03 的消费差异）
3. **持久化**：`ChatQueryDO.similarQueries`（String JSON）
   - 写：`chatQueryDO.setSimilarQueries(JSONObject.toJSONString(solvedQueries))`
   - 读：`ChatQueryRepositoryImpl` 反序列化为 `List<SimilarQueryRecallResp>`
4. **前端拉取**：`SimilarQuestionItem.tsx`（导出名 `SimilarQuestions`，事实清单摘录 3）
   - `useEffect` 在 `expanded && similarQuestions.length===0 && queryId` 时调 `querySimilarQuestions(queryId)` → `GET /chat/manage/getChatQuery/{queryId}`
   - 异步未写完则列表暂空，展开时再拉

### 数据形状
贴 1 条 `similarQueries` 持久化样例（JSON，2-3 条）：
```json
{
  "queryId": 8821,
  "similarQueries": "[{\"queryId\":8815,\"queryText\":\"xxx 行为实验未发报酬人员有哪些\"},{\"queryId\":8802,\"queryText\":\"xxx 实验预算花费多少\"}]"
}
```

### 易踩坑（≤ 3 行）
- topK=5 是**硬编码**，不是 yaml 配置——改要改源码
- 只取 `question` 文本展示；SQL 四元组的 schema/sql/sideInfo **不进** `similarQueries`（与 03 的 `#Exemplars` 消费完全不同）
- Java `SimilarQueryRecallResp` 字段只有 `queryId + queryText`；前端 `SimilarQuestionType` 多一个 `parseId`——前后端类型不对齐（`parseId` 在前端始终 undefined，B4 可提）

- [ ] **步骤 2：核对 B2 关键词**

运行：
```bash
for kw in "QueryRecommendProcessor" "CompletableFuture.runAsync\|runAsync" "recallExemplars" "similarQueries" "topK.*5\|topK.*硬编码\|硬编码.*5" "SimilarQuestionItem\|SimilarQuestions"; do
  echo -n "$kw: "; grep -c "$kw" docs/resume/interview/智能问数/04-推荐问题.md
done
```
预期：每项 ≥ 1。

- [ ] **步骤 3：核对「只取 question」明确**

运行：
```bash
grep -c '只取.*question\|只取 question\|只读.*question\|只拿 question' docs/resume/interview/智能问数/04-推荐问题.md
```
预期：≥ 1（B2 易踩坑或代码落点都要说清）。

- [ ] **步骤 4：Commit**

```bash
git add docs/resume/interview/智能问数/04-推荐问题.md
git commit -m "$(cat <<'EOF'
docs(interview): add Part B2 channel-two (similar) to 04 doc

B2 四拍：QueryRecommendProcessor.process CompletableFuture.runAsync（ForkJoinPool）
→ getSimilarQueries recallExemplars topK=5 硬编码 → 只取 question →
ChatQueryDO.similarQueries (String JSON) → 前端 useEffect 展开时拉
getChatQuery/{queryId}。前后端类型不对齐（前端 SimilarQuestionType 多 parseId）。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 7：Part B3 汇合：点推荐后再跑一轮问数

**目的：** 规格 §3.2 B3 行。讲清点击后果——两条通道点击后都当新 query 走完整 parse/execute；与手打差异主要在归因；`source=preset|similar` 标清落点（OSS 未检索到 source 枚举，产品/ELK 口径）。

**文件：**
- 改：`docs/resume/interview/智能问数/04-推荐问题.md`

- [ ] **步骤 1：按四拍写 B3**

### 场景（1–2 句）
「不论点的是内置题还是相似题，后果一样——前端把文案当新 `queryText` 提交，走完整 `parseAndExecute`。差异不在链路，在归因。」

### 代码落点
- **点击后路径**：前端把 `queryText`（来自 `Agent.examples` 或 `SimilarQuestionRecallResp.queryText`）当新 query 调 `chatQueryService.parseAndExecute`——与手打路径**完全相同**
- **链路**：`parseAndExecute` → `ChatQueryParser` 做 SchemaMapper / S2SQL → SqlExecutor →（若成功）`ParseResultProcessor` 链（再次触发 `QueryRecommendProcessor` 给下一题继续推相似——形成「连环追问」）
- **归因 `source`**（规格 §3.2 B3 修订后明确）：
  - 期望值 `preset` / `similar` / `manual`——但 **OSS Java 主链路当前未检索到 source 枚举**（事实清单已确认）
  - 产品/ELK 口径：前端自定义埋点（点击 handler 打 `source=preset|similar`）/ 网关侧 query 参数 / 未接线
  - **实现对码时再确认埋点位置**——本任务正文写「当前 OSS 未检索到 source 枚举；产品/ELK 口径」

### 数据形状
贴 1 条点击推荐触发的 parseAndExecute 请求样例（前端埋点视角）：
```
POST /chat/parse/execute
{
  "agentId": 10,
  "queryText": "xxx 行为实验未发报酬人员有哪些",  // 点相似题进来的
  "chatId": 7,
  "source": "similar"  // ← 产品/ELK 口径；OSS Java 侧未检索到此字段
}
```

### 易踩坑（≤ 3 行）
- 两条通道点击后**链路完全相同**——差异只在 `source` 归因字段
- `source` 在 OSS Java 主链路**未检索到**——别声称「Java 已有 source 枚举」
- 点击后会**再次触发** `QueryRecommendProcessor`（给下一题继续推相似）——这是「连续追问」的产品语义闭环

- [ ] **步骤 2：核对 B3 source 诚实写法**

运行：
```bash
grep -c '未检索到 source\|未检索到.*source\|source.*未检索到\|OSS.*未.*source' docs/resume/interview/智能问数/04-推荐问题.md
```
预期：≥ 1（B3 易踩坑 + 诚实边界表至少一处）。

- [ ] **步骤 3：核对 B3 点击后链路 = 完整 parseAndExecute**

运行：
```bash
grep -c 'parseAndExecute\|完整.*parse\|完整问数' docs/resume/interview/智能问数/04-推荐问题.md
```
预期：≥ 1（B3 代码落点说清点击后走完整链路）。

- [ ] **步骤 4：Commit**

```bash
git add docs/resume/interview/智能问数/04-推荐问题.md
git commit -m "$(cat <<'EOF'
docs(interview): add Part B3 confluence (click → full parse) to 04 doc

B3 四拍：点击后当新 queryText 走完整 parseAndExecute（两通道链路相同）；
差异在归因 source=preset|similar——OSS Java 未检索到 source 枚举，
产品/ELK 口径，对码再确认埋点位置。点击会再次触发 QueryRecommendProcessor
形成连续追问闭环。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 8：Part B4 晚了、空了、推歪了

**目的：** 规格 §3.2 B4 行。三类风险——异步慢 → 空列表；按 queryId 回写（无 OSS version 字段）；固化题型；ENABLED 近邻仍可能语义错。

**文件：**
- 改：`docs/resume/interview/智能问数/04-推荐问题.md`

- [ ] **步骤 1：按四拍写 B4**

### 场景（1–2 句）
「相似异步天然有三类失败态：慢了用户进下一问、召回空列表、推错近邻。都不是抛异常，而是产品层的『不完美』——讲清现状怎么兜。」

### 代码落点（3 类风险逐条）

**风险 1：async 慢了 → 空列表**
- 触发：`CompletableFuture.runAsync` 用 ForkJoinPool.commonPool()，无超时控制
- 现状兜底：前端 `useEffect` 在 `expanded && similarQuestions.length===0` 时调 `GET /chat/manage/getChatQuery/{queryId}` 再拉——异步写完后第二次读就有
- 极端：用户已经进下一问，旧 `queryId` 上的推荐「挂在上一题结果旁」（按 queryId 回写，不错挂到新题）

**风险 2：竞态错挂**
- OSS 实现：按 `queryId` 回写 `ChatQueryDO.similarQueries`——**无独立 version 字段**
- 用户快速连发 query（A → B → C）：三次异步各自回写各自的 queryId，互不覆盖
- 风险：若用户已进 B 的 Parse，A 的异步回来仍挂 A 的 queryId——**挂在旧题旁**，产品上可接受（用户还能回去看 A 的结果）
- **诚实边界**：OSS 没有「版本号协议」，面试别编；若 fork 加了再讲

**风险 3：推错近邻 / 固化题型**
- 「推错」：`recallExemplars` 只返回 ENABLED 记忆（依赖 03 治理），但 ENABLED ≠ 语义正确——如「去年」滚动 365 天的 SQL 已过审入库，召回到相似题会带歪（链 03 B4.1 治理链）
- 「固化」：金融侧只点引导例题、行为侧只点运维 FAQ——研究长尾更少被问；产品权衡，非 bug

### 数据形状
贴一条「async 慢 → 二次拉取成功」的前端时序（伪代码 ≤ 8 行）：
```
T0: 用户提交 queryId=100，parse 触发 QueryRecommendProcessor async
T1: 前端渲染结果区，similarQueries=[]（async 未写完）
T2: 用户展开「相似题」→ useEffect → GET getChatQuery/100 → similarQueries=[]（仍空）
T3: async 完成，ChatQueryDO.similarQueries 写入
T4: 用户再展开 → useEffect → GET getChatQuery/100 → similarQueries=[...3 条]
```

### 易踩坑（≤ 3 行）
- OSS 无超时控制、无 version 字段——空态靠前端二次拉，错挂靠 queryId 隔离
- 推错近邻根因在 03 治理（DISABLED + removeExemplar），不在 04 召回侧——04 同库只读，跟着 03 走
- `QueryRecommendProcessor` 用 ForkJoinPool.commonPool()，`doExecuteAgentExamples` 用 `chatExecutor`——异步策略不一致（性能复盘时可提）

- [ ] **步骤 2：核对 B4 三类风险齐全**

运行：
```bash
for kw in "async.*慢\|异步.*慢\|空列表\|空态" "queryId\|竞态\|错挂\|version" "推错\|固化\|近邻.*错\|长尾"; do
  echo -n "$kw: "; grep -c "$kw" docs/resume/interview/智能问数/04-推荐问题.md
done
```
预期：每项 ≥ 1。

- [ ] **步骤 3：核对无「version 协议」误述**

运行：
```bash
grep -nE '版本号.*协议|version.*协议|version 字段.*已' docs/resume/interview/智能问数/04-推荐问题.md | grep -v '无.*version\|未.*version\|勿.*version\|OSS.*无' || echo "(OK 或仅否定语境)"
```
预期：要么 0 命中，要么仅在否定/纠错语境。

- [ ] **步骤 4：Commit**

```bash
git add docs/resume/interview/智能问数/04-推荐问题.md
git commit -m "$(cat <<'EOF'
docs(interview): add Part B4 risks (late/empty/wrong) to 04 doc

B4 四拍：三类风险——async 慢 → 空列表（前端 useEffect 二次拉）；
竞态错挂按 queryId 回写（OSS 无 version 字段，勿编协议）；
推错近邻根因在 03 治理（同库只读跟着走）+ 固化题型（产品权衡）。
含二次拉取时序伪代码 + ForkJoinPool vs chatExecutor 异步策略差异。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 9：Part B5 下一刀往哪砍（**非空硬性要求**，P0/P1/P2 清单）

**目的：** 规格验收 §9 第 4 条：B5 非空。规格 §3.3 最低集合 6 条改进方向（修订后含「与 03 治理联动」）。

**文件：**
- 改：`docs/resume/interview/智能问数/04-推荐问题.md`

- [ ] **步骤 1：写 B5，至少 6 条改进方向（规格 §3.3 表格逐字搬）**

B5 标题：「B5 下一刀往哪砍」。形式为**优先队列式清单**，每条 3 拍「问题 → 拟改法 → 预期收益/成本」。

必须包含下表 6 条（**不得删减**）：

| 优先级 | 方向 | 问题 | 拟改法 | 预期 |
|--------|------|------|--------|------|
| **P0** | `source` 在可查证链路中代码化 / 与 ELK 字段对齐 | OSS Java 主链路无 source 枚举；15%/11% 是产品/ELK 口径，面试讲不硬气 | 前端点击 handler / 网关 query 参数加 source；或 Java 加枚举对齐 | 归因可观测、可严肃验收 |
| **P0** | 相似异步空态与超时的产品约定 | OSS 无 timeout；列表暂空靠前端二次拉 | 明确重试次数 / 占位文案 / 超时秒数 | 写清现状 vs 期望，B 端 UX 一致 |
| **P1** | 内置 × 相似去重与联动 | 点过的内置是否在相似里降权？现状两通道无联动 | 点过的内置在相似召回里过滤或降权 | 减少重复、提高多样性 |
| **P1** | 按 Agent / 实验周切片的贡献率看板 | 全站 15%/11%，按场景拆不够系统 | 看 source × agentId × 周切片 | 分域叙事可验证（行为抬相似、绿色抬内置） |
| **P1** | 与 03 治理联动 | 03 DISABLED 后 04 自动召不到（同库只读）；但 04 侧用户负反馈无闭环 | 推荐侧负反馈能否触发 03 的 `disableMemory` 走 B4.1 链 | 跨模块污染治理闭环 |
| **P2** | 严肃 A/B；对 `source=similar\|preset` 子集看执行成功率 / 近重复手打是否下降 | 贡献率是观测非因果 | A/B + 子集成功率 + 手打近重复率 | 证明「真帮到」而非「占比好看」 |

文末一行口径（沿用 03 B4.2 末句体例）：「改进讲『为什么现在的设计会痛』+『下一步动哪一层』，不空喊『上推荐算法』。」

- [ ] **步骤 2：核对 6 条齐全 + P0/P1/P2 分级**

运行：
```bash
echo "P0:"; grep -c '^| \*\*P0\*\*\|^P0' docs/resume/interview/智能问数/04-推荐问题.md
echo "P1:"; grep -c '^| \*\*P1\*\*\|^P1' docs/resume/interview/智能问数/04-推荐问题.md
echo "P2:"; grep -c '^| \*\*P2\*\*\|^P2' docs/resume/interview/智能问数/04-推荐问题.md
for kw in "source.*代码化\|source.*对齐" "空态.*超时\|超时.*占位" "内置.*相似.*联动\|点过的内置" "Agent.*切片\|实验周.*切片" "03.*治理.*联动\|disableMemory" "A/B\|执行成功率"; do
  echo -n "$kw: "; grep -c "$kw" docs/resume/interview/智能问数/04-推荐问题.md
done
```
预期：P0≥2、P1≥3、P2≥1；6 个关键词每项 ≥ 1。

- [ ] **步骤 3：Commit**

```bash
git add docs/resume/interview/智能问数/04-推荐问题.md
git commit -m "$(cat <<'EOF'
docs(interview): add Part B5 improvement backlog (P0/P1/P2) to 04 doc

B5 至少 6 条改进方向：P0 source 代码化 + 异步空态超时约定；
P1 内置相似联动 + 按域切片 + 与 03 治理联动（DISABLED 同库只读、
推荐负反馈触发 disableMemory）；P2 严肃 A/B + 子集执行成功率。
每条「问题→改法→预期」。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 10：Part C 薄附录——题纲索引 + 回看清单

**目的：** 规格 §4：题纲 §2.3 题号 → A/B 锚点 + 一句口径；回看清单；**不**堆大段「第一句答题」复述。

**文件：**
- 改：`docs/resume/interview/智能问数/04-推荐问题.md`

- [ ] **步骤 1：写 Part C**

### 标题
`## Part C · 题纲索引（薄）`

### 引子（1 句）
「题纲 §2.3 题号 → 本文锚点 + 一句口径。口径已在 A/B 讲过，这里只做跳转。」

### 1. 题纲 §2.3 题号 → 锚点表（6 分组）

读题纲 `docs/resume/interview/面试题纲.md` 第 152–194 行（§2.3 完整分组），按下表列锚点：

| 题纲分组 | 焦点 | 本文锚点 | 一句口径 |
|---------|------|---------|---------|
| 宽问 A1–A4 | 痛点 / 数字与动机 | A1 + A3 + A4 | 拆场景（行为反复查 vs 绿色引导）；贡献率 15%/11% 同分母；不要全站叙事 |
| 宽问 B5–B8 | 两种推荐模式设计逻辑 | A2 + B0 图 + B1 + B2 | B1∥B2 → 汇合 B3；内置不依赖当前输入、相似吃连续追问 |
| C9–C11 | 与 2.2 记忆复用关系 | A5 + B0.4 + B2 易踩坑 | 同一 `memory_{agentId}`；03 同步四元组 vs 04 异步只取 question |
| D12–D15 | 异步召回工程细节 | B2 + B4 | runAsync ForkJoinPool；topK=5 硬编码；按 queryId 回写无 version；空态二次拉 |
| E16–E18 | 管理员预配置 | A1 绿色引导 + B1 | 管理员按 Agent 维护 examples；现状手工，未做自动 Top-N |
| F19–F20 | 推荐负作用 | A6 条目 5/6 + B4 + B5 P1 | 固化题型（产品权衡）；推错近邻根因在 03 治理（同库只读） |

### 2. 回看清单（≥ 6 条勾选）

```markdown
### 回看清单

- [ ] 能画 B0 的双通道图，说出 **B1 ∥ B2 → 汇合 B3**，不是流水线
- [ ] 能区分 `Agent.examples`（内置展示）vs `EmbeddingConfig.presetCollection`（Plugin 识别用）
- [ ] 能讲相似通道：`QueryRecommendProcessor.process` runAsync → topK=5 硬编码 → 只取 question → `similarQueries`
- [ ] 能讲点击后果：两通道都当新 query 走完整 parseAndExecute，差异在 source 归因
- [ ] 对 `source` / version 能按诚实边界表划清「产品口径 vs OSS 代码」——**全栈未检索到 source 枚举**
- [ ] 能讲 03 与 04 同库只读：03 DISABLED 后 04 自动召不到（B5 P1 联动）
- [ ] 场景金句：相似 = 结果旁连续追问，**不是输入联想**
```

- [ ] **步骤 2：核对 Part C 含题纲 6 分组**

运行：
```bash
for kw in "痛点\|动机\|全站" "两种.*推荐\|通道\|设计逻辑" "记忆复用.*关系\|同一.*memory" "异步.*工程\|runAsync\|queryId" "管理员.*预配\|examples" "负作用\|固化\|推错"; do
  echo -n "$kw: "; grep -c "$kw" docs/resume/interview/智能问数/04-推荐问题.md
done
```
预期：每项 ≥ 1。

- [ ] **步骤 3：Commit**

```bash
git add docs/resume/interview/智能问数/04-推荐问题.md
git commit -m "$(cat <<'EOF'
docs(interview): add Part C thin appendix to 04 recommend-questions doc

题纲 §2.3 题号→锚点 + 一句口径（6 分组，对齐代码，不复述大段口述）；
回看清单 ≥6 条勾选；含「B0 双通道图」+「source 全栈未检索到诚实」+
「03 同库只读联动」+「相似≠输入联想金句」。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 11：通读 + 诚实边界全局扫描 + 验收条款对照

**目的：** 整篇写完后，把规格 §5 诚实边界与 §9 验收条款 1–6 全部对照一遍，修掉漏网。

**文件：**
- 改：`docs/resume/interview/智能问数/04-推荐问题.md`

- [ ] **步骤 1：全局禁词扫描**

规格 §1.3 非目标 + §5 诚实边界 + §9 第 4 条：不得以这些作主口径。

运行：
```bash
echo "=== 主口径禁词（应为 0 或仅在诚实边界表「不可讲」列 / 否定语境）==="
for kw in "边输入边联想\|输入联想.*本模块\|输入联想.*就是" "等于 preset_query_collection\|preset_query_collection.*内置" "Java 主链路.*source 枚举\|Java.*已有 source" "已上线.*version\|版本号.*协议" "推荐另.*写入链路\|另.*向量库"; do
  echo -n "$kw: "; grep -nE "$kw" docs/resume/interview/智能问数/04-推荐问题.md | grep -v '不可讲\|不/\|禁止\|纠错\|勿\|不是\|未' || echo "(仅在边界表/纠错或 0 命中)"
done
```
预期：每个禁词要么 0 命中，要么仅出现在诚实边界表「不可讲」列或明确否定语境中。

- [ ] **步骤 2：验收条款对照（规格 §9 六条）**

逐条核对（人工读 + grep 证据）：

| # | 条款 | 核对方法 |
|---|------|----------|
| 1 | 仅读 B0 能回答 B1∥B2 还是串行；B3 是什么 | 任务 4 步骤 2 已验 ∥ 符号 + 关系表 |
| 2 | 相似 topK=5 硬编码、内置来自 examples | grep `硬编码.*5\|topK.*5` ≥ 1；`Agent.examples` ≥ 1 |
| 3 | 区分 Agent.examples vs plugin preset collection | 任务 5 步骤 2 已验 + 诚实边界表第 2 行 |
| 4 | A6、B5 非空；无「版本号协议」主口径 | 任务 3 + 任务 9 + 步骤 1 禁词扫描 |
| 5 | 同库细节不重复 03 的 Review/`#Exemplars` 长文 | grep `#Exemplars\|storeExemplar\|MemoryReviewTask\|@Scheduled` 应该 ≤ 2（仅作对照提一句，不展开） |
| 6 | Part C 可跳转题纲 §2.3 | 任务 10 步骤 2 已验 6 分组 |

任一条款不满足 → 回对应任务补。

- [ ] **步骤 3：体量核对**

运行：
```bash
wc -l docs/resume/interview/智能问数/04-推荐问题.md
```
预期：350–500 行（规格 §8）。低于 350 说明某节写薄了；高于 500 说明某节写回了大段独白。

- [ ] **步骤 4：题纲交叉引用一致性**

运行：
```bash
grep -n '15%\|11%\|26%\|preset\|similar\|memory_{agentId}' docs/resume/interview/面试题纲.md | grep '2.3\|推荐'
grep -n '15%\|11%\|preset\|similar' docs/resume/interview/面试题纲.md | head
```
预期：题纲 §2.3 宽问第一句答题与正文数字一致（15%/11%、preset/similar、`memory_{agentId}`）。题纲旧稿若仍写「版本号机制」——**不改题纲**（规格非目标），只在 Part C 回看清单保留「口语按本文纠正」。

- [ ] **步骤 5：与 03 体例交叉一致性核对**

读 `docs/resume/interview/智能问数/03-查询记忆复用.md` 的诚实边界表 + A5（与 04 同库对照），确认：
- 04 诚实边界表「同库」行与 03 诚实边界表「推荐/version」行口径一致
- 04 A5 对照表与 03 A5 边界表互相指向
- `memory_{agentId}`、`preset_query_collection` 等命名两文档一致

- [ ] **步骤 6：Commit（若有修改）**

```bash
git add docs/resume/interview/智能问数/04-推荐问题.md
git diff --cached --stat || echo "无修改"
git commit -m "$(cat <<'EOF'
docs(interview): final pass on 04 recommend-questions doc — honesty boundary sweep

通读全文，对照规格 §5 诚实边界与 §9 验收 6 条；修掉漏网禁词作主口径的
残留；体量对齐 350–500 行；题纲交叉引用一致（题纲旧稿口径不改，正文以
本文件为准）；与 03 重写后的诚实边界表、A5 对照表互检一致。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)" || echo "（无修改则跳过 commit）"
```

- [ ] **步骤 7：清理临时文件**

运行：
```bash
rm -f /tmp/04-fact-sheet.md /tmp/04-fact-check.md /tmp/04-推荐问题.md.before-rewrite
echo "cleaned"
```
预期：`cleaned`。备份在 git 历史里仍可回滚（任务 0 步骤 1 记下的 hash）。

---

## 自检

**1. 规格覆盖度** — 对照规格 §2 总体结构 + §3 Part B 目录：
- 文首 + 诚实边界 5 行：任务 2（写入）+ 任务 11（全局扫）✓
- Part A：任务 2（A1–A5）+ 任务 3（A6）✓
- Part B：任务 4（B0）+ 任务 5（B1）+ 任务 6（B2）+ 任务 7（B3）+ 任务 8（B4）+ 任务 9（B5）✓
- Part C：任务 10 ✓
- §5 诚实边界：任务 2（5 行）+ 任务 11（全局扫）✓
- §6 代码锚点：预核查 `/tmp/04-fact-check.md` + 任务 1 事实清单 ✓
- §7 原文档迁移映射：任务 2–10 逐节从原 04 对应段搬 ✓
- §8 文风体量：任务 11 体量核对（350–500）✓
- §9 验收 6 条：任务 11 步骤 2 逐条对照 ✓
- §10 实现顺序（对码 → 重写 → 交叉）：预核查 + 任务 1 / 任务 2–10 / 任务 11 ✓

无遗漏章节。

**2. 占位符扫描** — 通读计划：
- 无「TODO / 待定 / 补充细节」
- 每个代码步骤都给了 grep 命令或具体字段清单
- A6 / B5 两处给了明确的「必须覆盖条目表」
- 体量给了数值区间（30–70 / 350–500）
- 6 处代码摘录全部引用 `/tmp/04-fact-check.md` 的真实摘录（不编造）

**3. 类型一致性** — 关键名/锚点在所有任务中一致：
- 类·方法名统一：`QueryRecommendProcessor.process` / `getSimilarQueries` / `ExemplarService.recallExemplars` / `EmbeddingConfig.getMemoryCollectionName` / `EmbeddingConfig.presetCollection`（**不是 `preset`**）/ `AgentServiceImpl.doExecuteAgentExamples` / `chatQueryService.parseAndExecute` / `chatExecutor` —— 与事实核查 `/tmp/04-fact-check.md` 一致
- 字段名统一：`Agent.examples`（List<String>）/ `AgentDO.examples`（String JSON）/ `ChatQueryDO.similarQueries`（String JSON）/ `SimilarQueryRecallResp.queryText` —— 与事实核查一致
- 前端导出名 vs 文件名：`SimilarQuestionItem.tsx`（文件）/ `SimilarQuestions`（导出）—— 任务 4-6 都按文件名引用路径，按实际导出名说组件
- 集合名统一：`memory_{agentId}`（前缀 `memory_`）/ `preset_query_collection`（默认）—— 与事实核查一致
- 数字基线统一：15% / 11% / 26% / 日均 150 / topK=5 硬编码 —— 与规格、题纲、01 §0 一致

无类型漂移。

---

## 执行交接

**计划已完成并保存到 `docs/superpowers/plans/2026-08-10-recommend-questions-interview-doc-rewrite.md`。两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**
