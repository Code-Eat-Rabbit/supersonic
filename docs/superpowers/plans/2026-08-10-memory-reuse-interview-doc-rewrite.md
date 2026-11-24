# 查询记忆复用面试文档重写 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 把 `docs/resume/interview/智能问数/03-查询记忆复用.md`（现 617 行、产品 Q&A 为主）按规格重写成「Part A 开篇 + Part B 生命周期叙事正文 + Part C 薄附录」单文件形态，A6/B4.1/B4.2 三节非空且覆盖规格难点清单。

**架构：** 单文件 `.md` 重写，不动业务代码。Part B 按「写出去 → 审 → 回灌 → 读回来 → 帮倒忙」叙事主线，每节固定四拍（场景 → 代码落点 → 数据样例 → 易踩坑）。数字以 `01-总览与业务背景.md` §0 与代码为准。

**技术栈：** Markdown；代码锚点相对仓库根（SuperSonic Java 仓库）；配置锚点指向 `assembly/conf/s2-config.yaml`。

**规格：** [`docs/superpowers/specs/2026-08-10-memory-reuse-interview-doc-design.md`](../specs/2026-08-10-memory-reuse-interview-doc-design.md)

**关键约束（来自规格 §3 诚实边界与 §7 验收）：**
- 正文不得以「1–5 分 / Top-3 few-shot / 线上抽 300」作主口径
- A6 至少覆盖 7 类难点：语义成功≠执行成功、有害示范、冷启动、评测贵、Review 偏弱、负迁移、只进不出
- B4.2 至少含 P0/P1 改进方向，可面试口述「下一刀砍哪」
- 不写「同库另一读者」专章；04 仅一行链接

**文件结构：**

| 文件 | 动作 | 职责 |
|------|------|------|
| `docs/resume/interview/智能问数/03-查询记忆复用.md` | 重写（覆盖） | 唯一交付物 |
| `docs/resume/interview/面试题纲.md` § 2.2 | 只读核对 | 宽问第一句答题口径须与正文一致 |
| `docs/resume/interview/智能问数/01-总览与业务背景.md` §0 | 只读核对 | 数字基线 |
| `docs/resume/interview/深度研究/04-Hybrid-Search-MCP.md` | 只读参照 | 体例模板 |

**本计划不含代码改动。** 任务粒度按「事实清单 → 文首与 Part A → Part B 各节 → Part C → 收尾验收」切分；每个任务以「可核对的事实」当测试。

---

## 任务 0：开工前 git 备份

**文件：**
- 操作：git tag / 分支，不写文件

- [ ] **步骤 1：在当前工作树打一个 rollback 锚点**

运行：
```bash
cd /Users/yourton_ma/workspace/supersonic
git stash push -m "before-03-rewrite-$(date +%s)" -- docs/resume/interview/智能问数/03-查询记忆复用.md 2>/dev/null; git log -1 --oneline -- docs/resume/interview/智能问数/03-查询记忆复用.md
```
预期：输出该文件最近一次提交的 hash 与 subject，作为「若重写失败可回滚」的锚点。记下 hash。

- [ ] **步骤 2：复制一份副作用备份**

运行：
```bash
cp docs/resume/interview/智能问数/03-查询记忆复用.md /tmp/03-查询记忆复用.md.before-rewrite
wc -l /tmp/03-查询记忆复用.md.before-rewrite
```
预期：输出 `617 /tmp/03-查询记忆复用.md.before-rewrite`（允许小幅波动，行数应在 610–620）。

---

## 任务 1：事实清单——把规格 §4 的 13 个锚点对到当前行号

**目的：** 规格明确「行号可漂移，类·方法为准」。先把每条锚点的当前行号 + 短摘录列成一张表，作为后续写 Part B 时「类·方法 + 短摘录」的素材源。这张表是本任务**唯一**产出物，写进 `/tmp/03-fact-sheet.md`，不进仓库。

**文件：**
- 读：`chat/`、`headless/`、`common/`、`assembly/conf/s2-config.yaml`
- 写：`/tmp/03-fact-sheet.md`（临时）

- [ ] **步骤 1：用 Grep 定位 13 个锚点的当前行号**

对下表左列每条，用 Grep 在 `chat/ headless/ common/` 下搜索「类名 + 方法名」；找定义处（非调用处）行号。

| 职责 | 类 · 方法 | grep 模式 |
|------|-----------|-----------|
| DO | `ChatMemoryDO` | `class ChatMemoryDO` |
| 挂四元组 | `LLMResponseService.addParseInfo` | `addParseInfo` |
| 落 PENDING | `SqlExecutor.execute` | `class SqlExecutor` |
| 创建去重 | `MemoryServiceImpl.createMemory` | `createMemory` |
| 定时审 | `MemoryReviewTask.review` | `class MemoryReviewTask` |
| 定时审·单条 | `MemoryReviewTask.processMemory` / `processResponse` | `processMemory\|processResponse` |
| 入向量 | `MemoryServiceImpl.enableMemory` | `enableMemory` |
| 出向量 | `MemoryServiceImpl.disableMemory` | `disableMemory` |
| 启动回灌 | `MemoryServiceImpl` ApplicationRunner | `implements ApplicationRunner` 或 `void run(` 在 `MemoryServiceImpl` |
| 召回注入 | `NL2SQLParser.addDynamicExemplars` | `addDynamicExemplars` |
| 筛 few-shot | `PromptHelper.getFewShotExemplars` | `getFewShotExemplars` |
| Prompt | `OnePassSCSqlGenStrategy` | `class OnePassSCSqlGenStrategy` |
| 向量 CRUD | `ExemplarServiceImpl.storeExemplar` / `recallExemplars` | `storeExemplar\|recallExemplars` |

- [ ] **步骤 2：核对配置默认值**

Grep `assembly/conf/s2-config.yaml`（注意 `assembly/conf/` 才是有效路径，不是 `assembly/conf./`）查：
- `parser.exemplar-recall.number`（期望 `10`）
- `parser.few-shot.number`（期望 `5`）
- `parser.self-consistency.number`（期望 `1`）
- Agent 侧 `MEMORY_REVIEW.enable`（业务 Agent 应为 true；系统默认 false）

若任何值与规格 §0.4 / §0.5 描述不符，以**代码/yaml**为准并把差异写进事实清单「差异」栏。

- [ ] **步骤 3：抽出 4 段关键短摘录（每段 ≤ 8 行）**

为以下 4 处各摘 ≤ 8 行原代码，保存到事实清单，写 Part B 时直接引用（避免引用时再翻代码）：
1. `MemoryReviewTask` 的 `@Scheduled` 注解 + `review` 方法签名
2. `MemoryServiceImpl` 的 `run(...)`（ApplicationRunner 回灌）主体骨架
3. `NL2SQLParser.addDynamicExemplars` 召回→挂请求段
4. `PromptHelper.getFewShotExemplars` 按 similarity 分桶段

- [ ] **步骤 4：把事实清单落盘并确认非空**

运行：
```bash
test -s /tmp/03-fact-sheet.md && echo OK || echo EMPTY
wc -l /tmp/03-fact-sheet.md
```
预期：`OK` 且行数 ≥ 60。事实清单模板见下：

```markdown
# 03 重写事实清单（临时）

## 锚点表
| 职责 | 类·方法 | 文件:行 | 摘录 |
|------|---------|--------|------|
| ... | ... | ... | ... |

## 配置默认值
- exemplar-recall.number = ?
- few-shot.number = ?
- self-consistency.number = ?
- MEMORY_REVIEW.enable = ?

## 4 段关键摘录
1. MemoryReviewTask @Scheduled：
2. MemoryServiceImpl.run：
3. NL2SQLParser.addDynamicExemplars：
4. PromptHelper.getFewShotExemplars：

## 与规格差异
- ...
```

- [ ] **步骤 5：Commit（事实清单不进仓库，此步无 commit）**

事实清单是临时产物，放 `/tmp/`。本步骤只确认它已生成，不动 git。

---

## 任务 2：重写文首元信息 + Part A（A1–A5）

**目的：** 建立新文档骨架。A1–A5 是压缩后的需求与效果，体量约为原 §2.1–2.3 的 1/3（规格 §2.1）。

**文件：**
- 写：`docs/resume/interview/智能问数/03-查询记忆复用.md`（覆盖）

- [ ] **步骤 1：先把文档骨架与 Part A 五节写完**

直接用 Write 工具覆盖 `03-查询记忆复用.md`。结构必须含：

1. **文首元信息块**（系列导航 + 题纲 + 标本 + 诚实边界总表）。诚实边界总表照规格 §3 全部 8 行搬过来。
2. **Part A · 需求与效果**，含：
   - **A1 背景与动机**（≤ 20 行；T1 卡 Parser、静态 few-shot / 有害示范、动态同构范文——压缩自原 §2.1 电梯稿与痛点表）
   - **A2 目标与非目标**（目标：过审记忆进 `#Exemplars`；非目标：自研向量框架、替代 SchemaMapper）
   - **A3 已实现效果**（数字：端到端 72%→87%；库 800+；冷启动种子 200；**不**展开操作细节）
   - **A4 评测口径**（表格：同一批 200、无 HITL、T0/T1/T2、+15pp 归因、Parser 条件切片约 75%→90%）
   - **A5 与 02/04 边界**（表格 3 行；04 仅一行「同库异步只读」链）
3. **A6 先占位**（写一行 `> 本节在任务 3 补全`，避免 Write 时漏锚点）

A1–A5 内**不要**贴代码摘录（代码落点是 Part B 的事）；A3 数字与 A4 表格要对得上 `01` §0 与题纲 §2.2 宽问第一句答题。

- [ ] **步骤 2：核对诚实边界总表的 8 行齐全**

运行：
```bash
grep -c '^| \*\*' docs/resume/interview/智能问数/03-查询记忆复用.md
```
预期：≥ 8（诚实边界 8 项，加 A5 边界表 3 项可能更多）。若 < 8 说明表丢了行。

- [ ] **步骤 3：核对 A3 数字口径**

运行：
```bash
grep -n '800\|200\|87%\|72%\|+15pp\|15pp' docs/resume/interview/智能问数/03-查询记忆复用.md | head -20
```
预期：A3 段落内同时出现 `800+`、`200`、`72%→87%`、`+15pp`。

- [ ] **步骤 4：核对 04 只占一行**

运行：
```bash
grep -c '04-推荐问题' docs/resume/interview/智能问数/03-查询记忆复用.md
```
预期：≤ 3（文首导航 1、Part A 链 1、Part B0 注脚 1）。**不得**出现「同库另一读者」专章标题。

- [ ] **步骤 5：Commit**

```bash
cd /Users/yourton_ma/workspace/supersonic
git add docs/resume/interview/智能问数/03-查询记忆复用.md
git commit -m "$(cat <<'EOF'
docs(interview): rewrite 03 query-memory doc header + Part A (A1–A5)

按规格 2026-08-10 重写 03 文首元信息与 Part A 需求/效果（压缩到约原文 1/3）：
诚实边界总表 8 行；A3 数字对齐 800+/200/72%→87%/+15pp；A5 与 02/04 分工，
04 仅一行链；A6 占位待补。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 3：补 A6 实现难点与过程困难（**非空硬性要求**）

**目的：** 满足规格 §7 验收第 6 条：A6 至少覆盖 7 类难点；条目式短文，每条 3–6 行。

**文件：**
- 改：`docs/resume/interview/智能问数/03-查询记忆复用.md`（替换 A6 占位）

- [ ] **步骤 1：写 A6，逐条对应规格 §2.1.1 难点清单**

A6 用条目式短文，每条固定三拍「难在哪 → 当时怎么扛 → 留下什么」。必须覆盖下表 7 条（标题关键词不能整类缺失）：

| 难点（必须出现） | 当时怎么扛（一句话） | 指向 |
|------------------|---------------------|------|
| 语义成功 ≠ 执行成功 | PENDING 不入库；过审才 ENABLED | B2 |
| 有害示范 / 静态域错位 | 演示域「超音数」滚动 365 天教错金融「去年=自然年」 | 动机回扣 A1；改进 B4.2 |
| 冷启动鸡生蛋 | 先灌 200 种子（4 Agent 分摊 ~40–60/个）才能召满约 5 条 | 数字在 A3；做法在 B5 |
| 评测贵且口径不唯一 | gold SQL 不唯一；200 人工标到上限；行为域覆盖不足 | 承接 A4 |
| Review 信号偏弱 | 开源 prompt 不重点抠日期、不看执行结果表；金融靠人审兜 | B2 如实写；改进 B4.2 |
| 负迁移 / 污染 | 错 SQL 过审带歪后续；DISABLED + removeExemplar | 案例简述在此；展开 B4.1 |
| 只进不出 | 无 TTL、无召回反馈降权；语义层变更旧 SQL 过时 | B4.2 改进方向 |

每条 3–6 行；**不得**写成大段产品独白。

- [ ] **步骤 2：核对 7 类难点关键词齐全**

运行：
```bash
for kw in "语义成功" "有害示范\|域错位" "冷启动" "评测" "Review\|审核.*弱" "负迁移\|污染" "只进不出\|TTL"; do
  echo -n "$kw: "
  grep -c "$kw" docs/resume/interview/智能问数/03-查询记忆复用.md
done
```
预期：每项 ≥ 1。任一为 0 即缺类，回步骤 1 补。

- [ ] **步骤 3：核对 A6 体量**

A6 行数应在 35–80 行（7 条 × 3–6 行 + 小标题 + 引子）。运行：
```bash
awk '/^### .*A6|^## A6/{f=1} f{print} /^## [A-C][0-9]/{if(f&&!/^## A6/){exit}}' docs/resume/interview/智能问数/03-查询记忆复用.md | wc -l
```
预期：35–80。低于 35 说明每条写太薄；高于 80 说明写回大段独白。

- [ ] **步骤 4：Commit**

```bash
git add docs/resume/interview/智能问数/03-查询记忆复用.md
git commit -m "$(cat <<'EOF'
docs(interview): fill A6 difficulties in 03 memory-reuse doc

A6 覆盖 7 类难点：语义成功≠执行成功、有害示范、冷启动、评测贵、
Review 偏弱、负迁移、只进不出；每条「难在哪→当时怎么扛→留下什么」3–6 行。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 4：Part B0 总图 + B1 这条记忆长什么样

**目的：** Part B 开篇给一张组件 + 主线箭头图 + 类职责表 + 配置键速查；B1 把 `s2_chat_memory` 字段与 `Text2SQLExemplar` 讲清。

**文件：**
- 改：`docs/resume/interview/智能问数/03-查询记忆复用.md`（在 A6 后追加）

- [ ] **步骤 1：写 B0 总图**

B0 含 4 部分（规格 §2.2 表 B0 行）：
1. **主线箭头图**（ASCII，5–10 行；画清 `挂四元组 → SUCCESS 落 PENDING → MemoryReviewTask → ENABLED+入向量 → ApplicationRunner 回灌 → recall → #Exemplars`）
2. **类职责表**（直接引用任务 1 事实清单的锚点表，列「职责 / 类·方法」两列，不列行号——行号会漂）
3. **配置键速查表**（`exemplar-recall.number=10`、`few-shot.number=5`、`self-consistency.number=1`、Agent `MEMORY_REVIEW.enable`；标注「本仓库 yaml 值 vs Parameter 默认」差异列）
4. **一行**注明：「相似推荐同库、异步只读，见 [04-推荐问题](./04-推荐问题.md)」——**不**展开

- [ ] **步骤 2：写 B1 这条记忆长什么样**

B1 按四拍结构（规格 §2.2「四拍」）：
1. **场景**（1–2 句：「执行刚返回 SUCCESS，要把这条经验沉淀下来——它长什么样？」）
2. **代码落点**：`ChatMemoryDO` / 表 `s2_chat_memory`（字段表，从原 §0.4 搬）；`Text2SQLExemplar`（集合名 `memory_{agentId}`，embedding 对象=`question`）
3. **数据样例**：贴 1 条 JSON（DB 一行 + 向量 metadata 一份），字段对齐事实清单
4. **易踩坑**（≤ 3 行）：
   - 表里**无** embedding、**无** `recall_count`
   - embedding 只打 `question`，SQL 在向量侧是 metadata payload
   - 状态机 `PENDING/ENABLED/DISABLED` 在 DB 的 `status` 字段，向量库**不存**状态

- [ ] **步骤 3：核对 B0 配置键齐全**

运行：
```bash
grep -nE 'exemplar-recall\.number|few-shot\.number|self-consistency\.number|MEMORY_REVIEW' docs/resume/interview/智能问数/03-查询记忆复用.md | head
```
预期：4 个配置键全出现，且至少 `exemplar-recall=10` 与 `few-shot=5` 在 B0 可见。

- [ ] **步骤 4：核对 B0 一行 04 链接（不展开）**

运行：
```bash
grep -c '^##.*同库\|^##.*另一读者\|^##.*相似推荐' docs/resume/interview/智能问数/03-查询记忆复用.md
```
预期：0（不得有以这些词为标题的章节）。04 链接应只在正文行内一行出现。

- [ ] **步骤 5：Commit**

```bash
git add docs/resume/interview/智能问数/03-查询记忆复用.md
git commit -m "$(cat <<'EOF'
docs(interview): add Part B0 overview + B1 memory shape to 03 doc

B0 总图（主线箭头 + 类职责表 + 配置键速查 + 一行 04 链接）；
B1 四拍：场景/代码落点/数据样例/易踩坑；字段表对齐事实清单。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 5：Part B2 写出来——SUCCESS → PENDING → Review 定时扫 → ENABLED

**目的：** 写路径主体。规格 §2.2 表 B2 行明确含 `MemoryReviewTask @Scheduled(60s)` 与 `ApplicationRunner` 启动回灌两站；旁路人审 / score≥5/≤1。

**文件：**
- 改：`docs/resume/interview/智能问数/03-查询记忆复用.md`

- [ ] **步骤 1：按四拍写 B2 主站**

B2 分 3 小站（每站四拍）：

**B2.1 挂四元组 + 执行 SUCCESS → 落 PENDING**
- 场景：「LLM 写完 S2SQL、执行返回 SUCCESS，这时候要把四元组挂上、把 DB 行写到 PENDING」
- 代码落点：`LLMResponseService.addParseInfo`（挂 `properties[sql_exemplar]=Text2SQLExemplar`）→ `SqlExecutor.execute`（仅 `QueryState.SUCCESS` 且 `LLMSqlQuery` 模式；**规则 SQL 不入库**）→ `MemoryServiceImpl.createMemory`（同 agent + 同 question 已有 ENABLED → 跳过）
- 数据样例：贴 PENDING 一行 DB JSON
- 易踩坑：执行成功 ≠ ENABLED；规则 SQL 不进记忆

**B2.2 MemoryReviewTask 定时审（60s）**
- 场景：「PENDING 积起来了，谁来把它们过审」
- 代码落点：`MemoryReviewTask.review` `@Scheduled(60s)` → `processMemory`/`processResponse`；需 `Agent.enableMemoryReview()`，Agent `MEMORY_REVIEW.enable=true`；已有 llm/human review 跳过
- 数据样例：贴 INSTRUCTION prompt（中英对照，从原 §2.2 审核段搬；标注「默认不重点抠日期」）；POSITIVE/NEGATIVE 表格（系统动作列写清 POSITIVE→ENABLED+storeExemplar；NEGATIVE→保持 PENDING 等人审；格式失败→不改状态）
- 易踩坑：开源 prompt 不看执行结果表、不重点抠日期；金融场景靠人审兜底

**B2.3 ApplicationRunner 启动回灌 + 旁路（人审 / 用户反馈）**
- 场景：「进程重启后向量索引会丢，怎么把 ENABLED 灌回来」
- 代码落点：`MemoryServiceImpl` 实现 `ApplicationRunner` 的 `run(...)`；旁路：人审（human_review / human_comment，冲突以人审为准）；用户反馈 score≥5/≤1（ChatManage 触发 enable/disable）
- 数据样例：贴启动回灌伪代码（从事实清单摘录骨架）
- 易踩坑：回灌只灌 ENABLED；DISABLED 不回灌；score≥5/≤1 是直接启停，**不**经过 Review

- [ ] **步骤 2：核对 B2 三站锚点齐全**

运行：
```bash
for kw in "MemoryReviewTask" "@Scheduled" "ApplicationRunner" "addParseInfo" "createMemory" "enableMemory"; do
  echo -n "$kw: "; grep -c "$kw" docs/resume/interview/智能问数/03-查询记忆复用.md
done
```
预期：每项 ≥ 1。

- [ ] **步骤 3：核对审核 prompt 含「不重点抠日期」**

运行：
```bash
grep -c '不.*抠.*日期\|NO NEED to check date' docs/resume/interview/智能问数/03-查询记忆复用.md
```
预期：≥ 1。这是诚实边界关键点（规格 §3、§2.1.1 Review 信号偏弱）。

- [ ] **步骤 4：Commit**

```bash
git add docs/resume/interview/智能问数/03-查询记忆复用.md
git commit -m "$(cat <<'EOF'
docs(interview): add Part B2 write-path (PENDING→Review→ENABLED) to 03 doc

B2 三小站四拍：挂四元组+SUCCESS 落 PENDING；MemoryReviewTask 60s 定时审
（POSITIVE→ENABLED+入向量，NEGATIVE→等人审）；ApplicationRunner 启动回灌 +
旁路人审/用户反馈 score≥5/≤1。审核 prompt 如实写「不重点抠日期」。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 6：Part B3 读回去——recall → `#Exemplars`

**目的：** 读路径。规格 §2.2 表 B3 行：`NL2SQLParser.addDynamicExemplars`；recall=10；`PromptHelper`→few-shot=5；`OnePassSCSqlGenStrategy` 模板。

**文件：**
- 改：`docs/resume/interview/智能问数/03-查询记忆复用.md`

- [ ] **步骤 1：按四拍写 B3**

B3 一站四拍：
- 场景：「下一次用户来问，Parser 前怎么把同构范文捞回来」
- 代码落点：`NL2SQLParser.addDynamicExemplars` → `ExemplarService.recallExemplars`（候选池 ≤ 10，集合 `memory_{agentId}`）→ 挂到 `QueryNLReq.dynamicExemplars`（同步，堵在 Parser 前）→ `PromptHelper.getFewShotExemplars` 筛成 5（similarity>0.989 必留；不足 10 用系统集 `text2dsl_agent_collection` 补）→ `OnePassSCSqlGenStrategy` 拼 `#Exemplars: {{exemplar}}`
- 数据样例：
  - 10→5 筛选算法（从原 §2.2 「10 → 5 具体怎么筛」段搬，5 步算法）
  - 一条 `#Exemplars` 填好的 prompt 示例（从原 §2.2 完整 prompt 示例段搬，「宁德时代去年的营收」）
  - 配置表（`exemplar-recall.number=10`、`few-shot.number=5`、`self-consistency.number=1`）
- 易踩坑：
  - 召回**同步**堵 Parser（推荐那把是 `runAsync`，不堵）
  - 召回 10 ≠ 注入 10；真正进 prompt 是筛后的约 5
  - 范文是**四元组**不是单条 SQL；`{{exemplar}}` 每条一行 `Question,Schema,SideInfo,SQL`

- [ ] **步骤 2：核对 10/5 配置在 B3 出现**

运行：
```bash
grep -nE 'exemplar-recall.number.*10|few-shot.number.*5|recall.*10|注入.*5|few-shot.*5' docs/resume/interview/智能问数/03-查询记忆复用.md | head
```
预期：≥ 2 行命中。

- [ ] **步骤 3：核对 Prompt 模板 `#Exemplars` 占位符**

运行：
```bash
grep -c '#Exemplars:\s*{{exemplar}}\|#Exemplars: {{exemplar}}' docs/resume/interview/智能问数/03-查询记忆复用.md
```
预期：≥ 1。

- [ ] **步骤 4：Commit**

```bash
git add docs/resume/interview/智能问数/03-查询记忆复用.md
git commit -m "$(cat <<'EOF'
docs(interview): add Part B3 read-path (recall→#Exemplars) to 03 doc

B3 四拍：NL2SQLParser.addDynamicExemplars 召回 10 → QueryNLReq.dynamicExemplars
→ PromptHelper.getFewShotExemplars 筛 5（similarity>0.989 必留）→
OnePassSCSqlGenStrategy 拼四元组范文 #Exemplars。含 10→5 算法与填好的 prompt 示例。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 7：Part B4.1 污染怎么发生、怎么下线（**非空硬性要求**）

**目的：** 规格验收 §7 第 7 条要求 B4.2 非空，§2.2.1 要求 B4.1 含负迁移案例 + DISABLED + removeExemplar + 人审/反馈回溯。

**文件：**
- 改：`docs/resume/interview/智能问数/03-查询记忆复用.md`

- [ ] **步骤 1：按四拍写 B4.1**

B4.1 标题：「B4.1 污染怎么发生、怎么下线」。四拍：
- 场景：「A6 里说错 SQL 过审会带歪后续——具体怎么发生、发现后怎么拔」
- 代码落点：
  - 案例：原 §2.3 帮倒忙「去年→滚动 365 天」案；与 A6 呼应（**不**重述动机）
  - 下线链：用户反馈答错 → 按 `queryId` / 当日 `usedExemplars` 回溯 → `MemoryService` DISABLED → `disableMemory` → `removeExemplar(memory_{id})` → 冲突 case 进评测集回归
- 数据样例：贴一条「答错→DISABLED」的 DB 状态变化（status: ENABLED → DISABLED；llm_review 不变；human_review=NEGATIVE + human_comment）
- 易踩坑：
  - NEGATIVE **默认不**自动 DISABLED（规格 §3 诚实边界表第 7 行）
  - `removeExemplar` 只清向量，DB 行留着作账
  - 无主动 TTL，下线靠「反馈触发」，污染有半衰期

- [ ] **步骤 2：核对下线链关键词**

运行：
```bash
for kw in "DISABLED" "removeExemplar\|removeExemplar" "queryId\|usedExemplars" "滚动\|365"; do
  echo -n "$kw: "; grep -c "$kw" docs/resume/interview/智能问数/03-查询记忆复用.md
done
```
预期：每项 ≥ 1。

- [ ] **步骤 3：Commit**

```bash
git add docs/resume/interview/智能问数/03-查询记忆复用.md
git commit -m "$(cat <<'EOF'
docs(interview): add Part B4.1 pollution + offline to 03 memory-reuse doc

B4.1 四拍：负迁移案例（去年→滚动 365 天）；下线链 queryId→DISABLED→
removeExemplar→进评测回归；NEGATIVE 默认不自动 DISABLED；无 TTL 半衰期。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 8：Part B4.2 后续改进方向（**非空硬性要求**，P0/P1/P2 清单）

**目的：** 规格验收 §7 第 7 条 + §2.2.1 最低集合（6 条）。面试可答「下一刀砍哪」。

**文件：**
- 改：`docs/resume/interview/智能问数/03-查询记忆复用.md`

- [ ] **步骤 1：写 B4.2，至少 6 条改进方向**

B4.2 标题：「B4.2 后续改进方向」。形式为**优先队列式清单**，每条 3 拍「问题 → 拟改法 → 预期收益/成本」。

必须包含下表 6 条（**不得删到空**，可加不可减）：

| 优先级 | 方向 | 问题 | 拟改法 | 预期 |
|--------|------|------|--------|------|
| **P0** | Review Rules 强制校验时间口径 | 开源 prompt 不抠日期，金融「去年=自然年」漏审 | 改 prompt Rules（加「去年/近 X 月」判定）；必要时把**执行结果预览**纳入审核输入 | 对齐金融场景；改 prompt 输入，非换框架 |
| **P0** | 召回后反馈闭环 | 错范文被召回无降权，污染半衰期长 | 用户否决/答错 → 自动降权或 DISABLED | 缩短污染半衰期 |
| **P1** | TTL / 长期未召回降权 | 只进不出；语义层变更旧 SQL 过时 | N 天未召回降权；schema 变更时批量失效或重审 | 解决只进不出 |
| **P1** | 表字段补 `recall_count` / `last_recalled_at` | 现表无 hit count，运营盲 | 加字段（或等价观测） | 运营可观测 |
| **P2** | 端到端集扩到 500–1000 并补行为实验域 | 200 偏小、行为域覆盖不足；Parser 条件切片未常态化 | 扩集 + 行为实验域补标 + 条件切片常态化 | 评测债 |
| **P2** | Review 与人审冲突率看板；NEGATIVE 队列 SLA | 运营不可见 | 看板 + SLA | 运营可观测 |

文末一行口径（规格 §2.2.1 末句）：「改进讲『为什么现在的设计会痛』+『下一步动哪一层』，不空喊『上强化学习』。」

- [ ] **步骤 2：核对 6 条齐全 + P0/P1/P2 分级**

运行：
```bash
echo "P0:"; grep -c '^| \*\*P0\*\*\|^P0' docs/resume/interview/智能问数/03-查询记忆复用.md
echo "P1:"; grep -c '^| \*\*P1\*\*\|^P1' docs/resume/interview/智能问数/03-查询记忆复用.md
echo "P2:"; grep -c '^| \*\*P2\*\*\|^P2' docs/resume/interview/智能问数/03-查询记忆复用.md
for kw in "时间口径\|自然年" "反馈闭环\|降权" "TTL\|未召回" "recall_count\|hit count" "500\|扩.*集" "冲突率\|SLA"; do
  echo -n "$kw: "; grep -c "$kw" docs/resume/interview/智能问数/03-查询记忆复用.md
done
```
预期：P0≥2、P1≥2、P2≥2；6 个关键词每项 ≥ 1。

- [ ] **步骤 3：Commit**

```bash
git add docs/resume/interview/智能问数/03-查询记忆复用.md
git commit -m "$(cat <<'EOF'
docs(interview): add Part B4.2 improvement backlog (P0/P1/P2) to 03 doc

B4.2 至少 6 条改进方向：P0 时间口径校验 + 召回反馈闭环；
P1 TTL + recall_count；P2 评测扩集 + 冲突率看板。每条「问题→改法→预期」。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 9：Part B5 空库到 800+——冷启动、人审与转化

**目的：** 规格 §2.2 表 B5 行：`[运营]` 标注；4 Agent 种子分配；周人审；漏斗 ~5% / PENDING→ENABLED ~50–60%；**不重复**讲调度实现。

**文件：**
- 改：`docs/resume/interview/智能问数/03-查询记忆复用.md`

- [ ] **步骤 1：写 B5（运营向，标 `[运营]`）**

B5 标题：「B5 空库到 800+：冷启动、人审与转化」。本节不重复 B2 的调度实现，只讲运营动作与数字。

含：
- **`[运营]` 冷启动种子分配表**（4 Agent：公司研究 ~60 / 绿色经济 ~50 / 经济研究 ~50 / 行为实验 ~40，合 ~200；解释「为什么单 Agent 要 40–60」——为召满约 5 条同构骨架）
- **`[运营]` 周人审节奏**（我 + 数据工程师周批次 ~0.5–1h；清 NEGATIVE + 抽检 POSITIVE；冲突进评测集；单条 30s–1min）
- **漏斗表**（周查询 ~1050 → 成功且 LLM_S2SQL ~700–800 → 新 PENDING ~80–100 → 新 ENABLED ~50；全量→ENABLED ~5%；PENDING→ENABLED ~50–60%）
- **诚实边界一行**：40–60 是工程定标，非论文「飞轮阈值」（对齐原 §2.2 文献说明：JPMorganChase continual learning 论文讲的是 10–20 条早期收益，勿混）

- [ ] **步骤 2：核对 `[运营]` 标注与漏斗数字**

运行：
```bash
echo "运营标注: "; grep -c '\[运营\]' docs/resume/interview/智能问数/03-查询记忆复用.md
echo "5% 漏斗: "; grep -c '5%\|~5%\|约 5%' docs/resume/interview/智能问数/03-查询记忆复用.md
echo "PENDING→ENABLED 转化: "; grep -c '50%\|50–60%\|50-60%' docs/resume/interview/智能问数/03-查询记忆复用.md
echo "4 Agent: "; grep -c '公司研究\|绿色经济\|经济研究\|行为实验' docs/resume/interview/智能问数/03-查询记忆复用.md
```
预期：`[运营]` ≥ 2；5% 与 50–60% 各 ≥ 1；4 个 Agent 名各 ≥ 1。

- [ ] **步骤 3：Commit**

```bash
git add docs/resume/interview/智能问数/03-查询记忆复用.md
git commit -m "$(cat <<'EOF'
docs(interview): add Part B5 cold-start + human-review + funnel to 03 doc

B5 运营向（[运营] 标注）：4 Agent 种子 ~200 分配；周人审节奏；
漏斗 ~5% 全量→ENABLED、~50–60% PENDING→ENABLED；
40–60 是工程定标非论文阈值。不重复 B2 调度实现。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 10：Part C 薄附录——题纲索引 + 回看清单

**目的：** 规格 §2.3：题号→锚点 + 一句口径；回看清单（勾选）；**不**堆大段「第一句答题」复述。

**文件：**
- 改：`docs/resume/interview/智能问数/03-查询记忆复用.md`

- [ ] **步骤 1：写 Part C**

含：
1. **题纲 §2.2 题号 → 锚点表**（列：题号分组 / 焦点 / 锚点 A 或 B 节号 / **一句**口径——对齐代码，**不**复述大段口述）。分组按题纲原分组：宽问、A 成功标准、B 存什么/生命周期/embedding、C Review 输入、D 人审运营、E 87%/+15pp/题型、F 负迁移/污染/技术债、与 2.3 同库。
2. **回看清单**（勾选式，从原 §2.5 清单搬并校准到新锚点）：
   - [ ] 能默画 PENDING → ENABLED → 向量 状态机，说出 NEGATIVE 不会自动 DISABLED
   - [ ] 能列 `s2_chat_memory` 关键字段，说明 embedding 不在表里
   - [ ] 能报配置：recall=10、few-shot=5、self-consistency=1、MEMORY_REVIEW 默认 false、业务 Agent 打开
   - [ ] 能区分静态 `text2dsl_agent_collection` vs 动态 `memory_{agentId}`
   - [ ] 能用同一套 200 条讲 T0/T1/T2，不跟「线上 300」混
   - [ ] 题纲若仍写「1–5 分 / Top-3 / 线上 300」——口语按本文纠正
   - [ ] 能口述 B4.2「下一刀砍哪」（P0 时间口径 + 反馈闭环）

- [ ] **步骤 2：核对 Part C 含题纲 8 个分组**

运行：
```bash
for kw in "宽问\|怎么做的" "A1\|成功标准\|技术成功" "B4\|存什么\|生命周期" "C7\|Review 输入\|审核输入" "D11\|人审\|运营" "E14\|87%\|+15pp" "F18\|F19\|F20\|负迁移\|污染\|技术债" "2.3\|同库\|同一向量"; do
  echo -n "$kw: "; grep -c "$kw" docs/resume/interview/智能问数/03-查询记忆复用.md
done
```
预期：每项 ≥ 1。

- [ ] **步骤 3：Commit**

```bash
git add docs/resume/interview/智能问数/03-查询记忆复用.md
git commit -m "$(cat <<'EOF'
docs(interview): add Part C thin appendix to 03 memory-reuse doc

题纲 §2.2 题号→锚点 + 一句口径（对齐代码，不复述大段口述）；
回看清单 7 条勾选项；含「能口述 B4.2 下一刀砍哪」。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## 任务 11：通读 + 诚实边界 8 条全局扫描

**目的：** 整篇写完后，把规格 §3 诚实边界与 §7 验收条款 1–8 全部对照一遍，修掉漏网。

**文件：**
- 改：`docs/resume/interview/智能问数/03-查询记忆复用.md`

- [ ] **步骤 1：全局禁词扫描**

规格 §1.3 非目标 + §3 诚实边界 + §7 第 3 条：不得以这些作主口径。

运行：
```bash
echo "=== 主口径禁词（应为 0 或仅在诚实边界表「不可讲」列）==="
for kw in "1–5 分\|1-5 分" "≥4 自动入库\|≥4.*入库" "Top-3 few-shot\|Top-3" "线上.*300\|线上抽 300" "表里.*embedding\|表.*存.*embedding" "表.*hit count\|表.*recall_count.*存" "不报错.*进 few-shot\|不报错就进" "NEGATIVE.*自动.*DISABLED\|NEGATIVE.*自动 DISABLED" "同库另一读者\|另一读者"; do
  echo -n "$kw: "; grep -nE "$kw" docs/resume/interview/智能问数/03-查询记忆复用.md | grep -v '不可讲\|不/\|禁止\|纠错' || echo "(仅在边界表或 0 命中)"
done
```
预期：每个禁词要么 0 命中，要么仅出现在诚实边界表的「不可讲」列或明确「纠错」语境中。任一在正文作主口径出现 → 回对应任务修。

- [ ] **步骤 2：验收条款对照（规格 §7 八条）**

逐条核对（人工读 + grep 证据）：

| # | 条款 | 核对方法 |
|---|------|----------|
| 1 | 不读 Q&A 也能讲清 PENDING/审/向量/召回/注入 | 读 Part B2+B3，确认四拍齐全 |
| 2 | 指出 MemoryReviewTask 与 ApplicationRunner 各自解决什么 | grep 两者各 ≥ 1，且分属 B2.2 / B2.3 |
| 3 | 无禁词主口径 | 步骤 1 |
| 4 | 无同库专章；04 一行 | 任务 4 步骤 4 已验 |
| 5 | A3 有 800+/200；B5 有运营细节且标 `[运营]` | 任务 2 步骤 3 + 任务 9 步骤 2 |
| 6 | A6 非空覆盖 7 类 | 任务 3 步骤 2 |
| 7 | B4.2 非空 P0/P1 | 任务 8 步骤 2 |
| 8 | Part C 可按题纲 §2.2 跳转 | 任务 10 步骤 2 |

任一条款不满足 → 回对应任务补。

- [ ] **步骤 3：体量核对**

运行：
```bash
wc -l docs/resume/interview/智能问数/03-查询记忆复用.md
```
预期：550–750 行（规格 §6）。低于 550 说明某节写薄了；高于 750 说明某节写回了大段独白。

- [ ] **步骤 4：题纲交叉引用一致性**

运行：
```bash
grep -n '72%\|87%\|800\|200\|POSITIVE\|NEGATIVE\|10\|5' docs/resume/interview/面试题纲.md | grep '2.2\|查询记忆'
grep -n '72%\|87%\|800\|200\|POSITIVE\|NEGATIVE' docs/resume/interview/面试题纲.md | head
```
预期：题纲 §2.2 宽问第一句答题与正文数字一致（72%→87%、200、800+、POSITIVE/NEGATIVE）。若题纲旧稿仍写「1–5 分 / Top-3 / 线上 300」，**不改题纲**（规格非目标 §1.3），只在 Part C 回看清单保留「题纲若仍写… 口语按本文纠正」。

- [ ] **步骤 5：Commit（若有修改）**

```bash
git add docs/resume/interview/智能问数/03-查询记忆复用.md
git diff --cached --stat || echo "无修改"
git commit -m "$(cat <<'EOF'
docs(interview): final pass on 03 memory-reuse doc — honesty boundary sweep

通读全文，对照规格 §3 诚实边界与 §7 验收 8 条；修掉漏网禁词作主口径的
残留；体量对齐 550–750 行；题纲交叉引用一致（题纲旧稿口径不改，正文以
本文件为准）。

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)" || echo "（无修改则跳过 commit）"
```

- [ ] **步骤 6：清理临时文件**

运行：
```bash
rm -f /tmp/03-fact-sheet.md /tmp/03-查询记忆复用.md.before-rewrite
echo "cleaned"
```
预期：`cleaned`。备份在 git 历史里仍可回滚（任务 0 步骤 1 记下的 hash）。

---

## 自检

**1. 规格覆盖度** — 对照规格 §2 总体结构：
- Part A：任务 2（A1–A5）+ 任务 3（A6）✓
- Part B：任务 4（B0+B1）+ 任务 5（B2）+ 任务 6（B3）+ 任务 7（B4.1）+ 任务 8（B4.2）+ 任务 9（B5）✓
- Part C：任务 10 ✓
- §3 诚实边界：任务 2（写入文首）+ 任务 11（全局扫）✓
- §4 代码锚点：任务 1 事实清单 ✓
- §5 原文档迁移映射：任务 2–10 逐节从原文对应段搬 ✓
- §6 文风体量：任务 11 体量核对 ✓
- §7 验收 8 条：任务 11 步骤 2 逐条对照 ✓
- §8 实现顺序（再扫四路径 → 重写 → 抽查）：任务 1 / 任务 2–10 / 任务 11 ✓

无遗漏章节。

**2. 占位符扫描** — 通读计划：
- 无「TODO / 待定 / 补充细节」
- 每个代码步骤都给了 grep 命令或具体字段清单，不是「写适当内容」
- A6 / B4.1 / B4.2 三处给了明确的「必须覆盖条目表」，不是「自行发挥」
- 体量给了数值区间（35–80 / 550–750），不是「适当」

**3. 一致性** — 关键名 / 锚点在所有任务中一致：
- 类·方法名统一：`MemoryReviewTask.review` / `MemoryServiceImpl.createMemory` / `enableMemory` / `disableMemory` / `NL2SQLParser.addDynamicExemplars` / `PromptHelper.getFewShotExemplars` / `OnePassSCSqlGenStrategy` / `ExemplarServiceImpl.storeExemplar` / `recallExemplars` / `ApplicationRunner.run` —— 与规格 §4 一致
- 配置键统一：`exemplar-recall.number=10` / `few-shot.number=5` / `self-consistency.number=1` / `MEMORY_REVIEW.enable` —— 与规格 §4、§0.5 一致
- 状态枚举统一：`PENDING` / `ENABLED` / `DISABLED`；`POSITIVE` / `NEGATIVE` —— 与规格 §3 一致
- 4 Agent 名统一：公司研究 / 绿色经济 / 经济研究 / 行为实验 —— 与原 §2.2 表一致

无类型漂移。

---

## 执行交接

**计划已完成并保存到 `docs/superpowers/plans/2026-08-10-memory-reuse-interview-doc-rewrite.md`。两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**
