# Hybrid Search + MCP 与工程化能力专项精读 — 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 新建 `04-Hybrid-Search-MCP.md` 与 `05-工程化能力.md` 两篇约五章精读文档；将 `02` 的 F/G 迁出为索引；将 `03` §8–§9 收成指向 `05` 的短指针。

**架构：** 文档双轨——纵向调用链精读（关键代码 + 旁注 + 面试说法/易踩坑）+ 末尾题索引。`04` 强制顺序：接 `03` → 工具注册/发现/调用/降级 → Hybrid（含证据链与引用）→ 访谈/研报知识库与案例。`05` 为预算/并发权威源。

**技术栈：** Markdown；标本 `miro-flow-solution`（retrieval / tool manager / hybrid MCP / task_tracer / common_benchmark / Hydra yaml）。

**规格：** `docs/superpowers/specs/2026-08-06-hybrid-search-and-engineering-interview-prep-design.md`

**标本根目录：** `/Users/yourton_ma/workspace/agent_project/research-agent/miro-flow-solution`

---

## 文件结构

| 文件 | 职责 |
|------|------|
| 创建：`docs/resume/interview/深度研究/04-Hybrid-Search-MCP.md` | F17–F20 权威精读：工具 harness → Hybrid → 业务库/案例 → 题索引 |
| 创建：`docs/resume/interview/深度研究/05-工程化能力.md` | G21–G24 权威精读：追踪 → 熔断/并发 → 断点续跑 → 题索引 |
| 修改：`docs/resume/interview/深度研究/02-面试问答.md` | F/G 改为索引；L2-F19/F20 短指针；§5 对照表；文首加 `04`/`05` 链接 |
| 修改：`docs/resume/interview/深度研究/03-Main-Sub-Agent编排.md` | §0.2 更新；§8–§9 收成短指针链到 `05` |
| 修改：`docs/resume/interview/面试题纲.md` | F/G 节下增加详解路径一行（不改编题干） |
| 修改：`docs/superpowers/specs/2026-08-04-deep-research-interview-prep-design.md` | 加 F/G 拆分说明句 |
| 修改：`docs/superpowers/specs/2026-08-05-main-sub-agent-deep-dive-design.md` | 加预算/并发权威改归 `05` 的说明句 |

**明确不修改：** `miro-flow-solution` / SuperSonic 功能代码；`01-集成设计.md` 正文（除非已有「见 02 F/G」指针才补链）。

---

## 标本锚点速查（实现时按文件核对行号，若漂移以符号名为准）

| 符号 / 主题 | 文件 |
|-------------|------|
| `route_query` / LOCAL_HINTS / WEB_HINTS | `src/retrieval/router.py` |
| `SearchHit` / `RoutePlan` | `src/retrieval/schemas.py` |
| `weighted_fusion` / `_dedupe` | `src/retrieval/fusion.py` |
| `chunk_text` / `LocalIndexStore` | `src/retrieval/local_index.py` |
| `build_task_index` | `src/retrieval/ingest.py` |
| `search_web` | `src/retrieval/web_retriever.py` |
| `VectorBackend` | `src/retrieval/vector_backend.py` |
| `hybrid_search` MCP | `src/tool/mcp_servers/hybrid_search_mcp_server.py` |
| 工具 yaml | `config/tool/tool-hybrid-search.yaml` |
| `execute_tool_call` / Server 纠错 / 空结果 / MarkItDown fallback | `src/tool/manager.py` ~L255+ |
| Sub `tool_config` 挂载示例 | `config/agent_llm_qwen37plus.yaml` |
| 证据/引用 Prompt 口径 | `config/agent_prompts/sub_worker.py`（原文摘录+URL）；业务侧见 `01` ResearchDirective |
| `StepRecord` / `TaskTracer.log_step` / `save` | `src/logging/task_tracer.py` |
| 主循环阶段性 save / max_turns 截断 | `src/core/orchestrator.py` |
| pipeline `finally` 终态 | `src/core/pipeline.py` |
| `scan_latest_attempt` / `run_single_task` / `run_parallel_inference` | `common_benchmark.py` |
| 预算数字 | `config/agent_llm_qwen37plus.yaml` Main 20/10、Sub 50/10 |
| 现成速答正文（迁出源） | `02-面试问答.md` §F / §G |
| 现成熔断/并发长文（迁入 `05` 后压缩） | `03` §8–§9 |

---

### 任务 1：创建 `04` 骨架 + §1 衔接 + §2 工具 harness

**文件：**
- 创建：`docs/resume/interview/深度研究/04-Hybrid-Search-MCP.md`

- [ ] **步骤 1：创建文件，写入头部与 §1–§2**

必须包含（可按规格扩写，但不得缺项）：

```markdown
# Hybrid Search + MCP — 代码精读与面试深挖

> 对应简历：问数结果深度研究 · Hybrid Search / MCP
> 题纲：[`../面试题纲.md`](../面试题纲.md) § 三 F17–F20
> 索引本：[`02-面试问答.md`](./02-面试问答.md)（F 节已迁出至本文）
> 上一章：[`03-Main-Sub-Agent编排.md`](./03-Main-Sub-Agent编排.md)
> 设计规格：[`../../superpowers/specs/2026-08-06-hybrid-search-and-engineering-interview-prep-design.md`](../../superpowers/specs/2026-08-06-hybrid-search-and-engineering-interview-prep-design.md)
> 复习标本：`miro-flow-solution`

## 1. 与上一章的关系 + 本章地图 + 诚实边界
- 明确：`03` 主循环里「普通 MCP」→ `ToolManager.execute`；本章讲工具如何注册/发现/调用/降级，再讲 Hybrid 这一把工具
- `agent-*` 伪工具不展开（归 `03`）
- 诚实边界表：98%≠任务成功；0.6/0.4≠最优；关键词路由≠语义路由；vector 回退本地；知识库不报规模；无引用 schema 强校验

## 2. 工具如何注册、发现、调用与降级
- 注册：`tool-*.yaml` → Sub `tool_config`；贴 `tool-hybrid-search.yaml` 关键字段
- 发现/调用：`ToolManager.execute_tool_call(server_name, tool_name, arguments)` 统一入口
- 降级：超时 / 空内容 / Server 名纠错 / MarkItDown 备用读取（贴关键分支，不整文件）
- 98% 定义 + 降级顺序可背模板
- 「面试时怎么说」+「易踩坑」
```

核对行号：打开 `manager.py` 的 `execute_tool_call`、auto-correction、empty result、MarkItDown fallback，旁注用真实行号或「以符号名为准」。

- [ ] **步骤 2：自检 §1–§2**

运行：

```bash
rg -n "任务成功率|生产向量库|发明" "docs/resume/interview/深度研究/04-Hybrid-Search-MCP.md" || true
rg -n "execute_tool_call|tool-hybrid-search|98%" "docs/resume/interview/深度研究/04-Hybrid-Search-MCP.md"
```

预期：无把 98% 说成任务成功率的违规句；能命中工具链关键词。

- [ ] **步骤 3：Commit**

```bash
git add "docs/resume/interview/深度研究/04-Hybrid-Search-MCP.md"
git commit -m "$(cat <<'EOF'
docs: draft Hybrid Search interview deep-dive §§1-2

EOF
)"
```

---

### 任务 2：撰写 `04` §3 Hybrid + 证据链与引用

**文件：**
- 修改：`docs/resume/interview/深度研究/04-Hybrid-Search-MCP.md`

- [ ] **步骤 1：追加 §3，覆盖路由→召回→融合→MCP 返回→证据/引用**

必须钉死的结论（写进正文，不要只放注释）：

1. `route_query`：强制 mode；`no_local_index`→web；local/web hints；双命中或都未命中→hybrid；权重归一
2. 本地：`ingest` → `chunk_text` → `LocalIndexStore`；`VectorBackend` 回退诚实边界
3. Web：`search_web`；空召回仍可只交本地侧
4. `weighted_fusion`：加权、按 `url` 或 `source:chunk_id` 去重、Top K；默认 0.6/0.4 标本基线
5. `hybrid_search` 返回 JSON：`route`/`reason`/`mix`/`local_hits`/`web_hits`/`results`
6. **证据链与引用（专小节）：**
   - 工具层：`SearchHit` 字段表（source/title/url/snippet/score/chunk_id）
   - 报告层：Prompt 摘录+URL；业务 Directive 证据强度（交叉引用 `01`，不整篇复制）
   - 诚实：无代码级引用 schema 强校验
   - 可背一句话：先产出可追溯 hit，再按出处写结论并标缺口

贴码范围：`router.py` 的 `route_query` 近全文；`fusion.py` 的 `weighted_fusion`+`_dedupe`；`hybrid_search` 返回 dict 段；`SearchHit` dataclass。本地/Web 用文字+函数签名即可，避免过长。

- [ ] **步骤 2：自检证据/引用诚实边界**

```bash
rg -n "schema 强校验|JSON schema|脚注" "docs/resume/interview/深度研究/04-Hybrid-Search-MCP.md"
rg -n "SearchHit|chunk_id|证据" "docs/resume/interview/深度研究/04-Hybrid-Search-MCP.md"
```

预期：明确写「无强校验」或等价诚实句；命中 hit 字段与证据叙述。

- [ ] **步骤 3：Commit**

```bash
git add "docs/resume/interview/深度研究/04-Hybrid-Search-MCP.md"
git commit -m "$(cat <<'EOF'
docs: add Hybrid Search route-fusion and citation section

EOF
)"
```

---

### 任务 3：撰写 `04` §4 业务库/案例 + §5 F 题索引

**文件：**
- 修改：`docs/resume/interview/深度研究/04-Hybrid-Search-MCP.md`
- 参考（只读迁出源）：`docs/resume/interview/深度研究/02-面试问答.md` 的 F17–F20、F19 两案例、F20

- [ ] **步骤 1：写 §4 知识库 + F19 两案例**

知识库主口径（强制）：

- 主要是 **访谈材料** + **清洗后的研报**
- 可讲授权、来源/版本/更新时间、chunk 可追溯
- 不虚构条数/向量规模
- 维护：上传→抽取→分块→索引；修订 upsert/重建
- 与联网融合：链回 §3；权重仅标本基线

F19：从 `02` 迁入并略加深，金融归因 + 行为科学；禁止编造论文标题/页码；时间相邻≠因果。

- [ ] **步骤 2：写 §5 面试题索引 F17–F20 + 回看清单**

体例对齐 `03` §10：

| 字段 | 要求 |
|------|------|
| 第一句 | 可背 |
| 要点 | 3–5 条 |
| 易踩坑 | 必有 |
| 详见 | 链到本文 §2–§4 锚点 |
| 回看标本 | 具体路径 |

从 `02` 迁入时：**更新 F20** 主口径为访谈+清洗研报（覆盖旧泛化清单）。

- [ ] **步骤 3：通读 `04` 五章齐全性检查**

```bash
rg -n "^## " "docs/resume/interview/深度研究/04-Hybrid-Search-MCP.md"
```

预期：恰好约 5 个一级章（1–5），顺序为衔接→工具链→Hybrid→业务→题索引。

- [ ] **步骤 4：Commit**

```bash
git add "docs/resume/interview/深度研究/04-Hybrid-Search-MCP.md"
git commit -m "$(cat <<'EOF'
docs: finish Hybrid Search deep-dive with KB cases and F index

EOF
)"
```

---

### 任务 4：创建 `05` 骨架 + §1 衔接 + §2 追踪回放

**文件：**
- 创建：`docs/resume/interview/深度研究/05-工程化能力.md`
- 参考：`02` G21；`task_tracer.py`；`orchestrator.py` / `pipeline.py` 落盘点

- [ ] **步骤 1：创建文件，写入头部与 §1–§2**

```markdown
# 工程化能力 — 追踪、熔断、并发与断点续跑

> 题纲：[`../面试题纲.md`](../面试题纲.md) § 三 G21–G24
> 索引本：[`02-面试问答.md`](./02-面试问答.md)（G 节已迁出至本文）
> 上一章工具：[`04-Hybrid-Search-MCP.md`](./04-Hybrid-Search-MCP.md)
> 编排章：[`03-Main-Sub-Agent编排.md`](./03-Main-Sub-Agent编排.md)（§8–§9 指针指向本文）
> 设计规格：[`../../superpowers/specs/2026-08-06-hybrid-search-and-engineering-interview-prep-design.md`](...)

## 1. 与前两章的关系 + 地图 + 诚实边界
- 03=编排；04=工具；05=可观测/预算/评测并发/续跑
- 诚实：不报未测省时；多题并行≠单题内并行；660s 临时建议

## 2. 全链路追踪与回放（G21）
- StepRecord / TaskTracer 字段
- 主循环阶段性 save vs pipeline.finally 终态
- 回放路径：task_id → step 时间线 → message history
- 排查模板（工具结构异常跑偏）——方法可讲，不虚构事故损失
- 面试说法 + 易踩坑
```

- [ ] **步骤 2：核对标本字段名**

打开 `task_tracer.py`，确认正文中的字段名与 `StepRecord` / `TaskTracer` 一致（`step_name`、`message`、`timestamp`、`status`、`metadata` 等）。

- [ ] **步骤 3：Commit**

```bash
git add "docs/resume/interview/深度研究/05-工程化能力.md"
git commit -m "$(cat <<'EOF'
docs: draft engineering interview deep-dive §§1-2

EOF
)"
```

---

### 任务 5：撰写 `05` §3 预算熔断 + 两类并发（迁入 `03` §8–§9 权威内容）

**文件：**
- 修改：`docs/resume/interview/深度研究/05-工程化能力.md`
- 只读迁出源：`03-Main-Sub-Agent编排.md` §8–§9；`02` G22–G23

- [ ] **步骤 1：写 §3，成为预算/并发权威详解**

必须包含：

1. 标本 Main 20/10、Sub worker 50/10（标明示例）
2. `max_turns` vs `max_tool_calls_per_turn` 对照表（可从 `03` §8.4 迁入）
3. 触顶后仍尝试 final summary
4. 单题内顺序 `for` 证据（orchestrator 注释 `in sequence`）
5. 多题并行：`Semaphore` + `gather(return_exceptions=True)`（`common_benchmark.run_parallel_inference`）
6. 简历「并发」可背口径模板
7. 面试说法 + 易踩坑

可从 `03` §8–§9 **整段迁入后再精炼**，但权威落点必须在 `05`；勿留下「完整追问见 02」的过时指针。

- [ ] **步骤 2：自检并发口径**

```bash
rg -n "同时跑 10|gather 并行|max_tool_calls_per_turn=10.*并发" "docs/resume/interview/深度研究/05-工程化能力.md" || true
rg -n "Semaphore|return_exceptions|in sequence|简历" "docs/resume/interview/深度研究/05-工程化能力.md"
```

预期：无把 `10` 说成并发度的违规肯定句；有顺序 vs 多题并行对照。

- [ ] **步骤 3：Commit**

```bash
git add "docs/resume/interview/深度研究/05-工程化能力.md"
git commit -m "$(cat <<'EOF'
docs: add budget and concurrency section to engineering deep-dive

EOF
)"
```

---

### 任务 6：撰写 `05` §4 断点续跑 + §5 G 题索引

**文件：**
- 修改：`docs/resume/interview/深度研究/05-工程化能力.md`
- 参考：`02` G24；`common_benchmark.py`

- [ ] **步骤 1：写 §4 断点续跑状态机**

钉死：

- `scan_latest_attempt`：先当 `RUN_FAILED`；有 `final_boxed_answer` → `RUN_COMPLETED`；有 `judge_result` → `RESULT_JUDGED`
- 文件存在 ≠ 完成
- `run_single_task`：PENDING/RUN_FAILED 重跑；有答案补 judge；有 judge 复用；pass@k 提前停
- 省时：只讲机制，不写未测小时数

- [ ] **步骤 2：写 §5 G21–G24 题索引 + 回看清单 + `03` 迁移附录**

附录一句：`03` §8–§9 已改为详见本文 §3。

- [ ] **步骤 3：五章齐全性检查**

```bash
rg -n "^## " "docs/resume/interview/深度研究/05-工程化能力.md"
```

预期：约 5 个一级章，顺序衔接→追踪→熔断/并发→续跑→题索引。

- [ ] **步骤 4：Commit**

```bash
git add "docs/resume/interview/深度研究/05-工程化能力.md"
git commit -m "$(cat <<'EOF'
docs: finish engineering deep-dive with resume and G index

EOF
)"
```

---

### 任务 7：迁移 `02` 的 F/G 为索引；更新 L2 与对照表

**文件：**
- 修改：`docs/resume/interview/深度研究/02-面试问答.md`

- [ ] **步骤 1：文首增加 `04`/`05` 链接**

在现有 `03` 精读链接旁增加：

```markdown
> Hybrid / MCP 精读：[`04-Hybrid-Search-MCP.md`](./04-Hybrid-Search-MCP.md)
> 工程化精读：[`05-工程化能力.md`](./05-工程化能力.md)
```

- [ ] **步骤 2：将 § F 整段替换为索引表（对齐 E 节样式）**

```markdown
### F. Hybrid Search + MCP

> 详解已迁至专项：[`04-Hybrid-Search-MCP.md`](./04-Hybrid-Search-MCP.md)
> `02` 仅保留题号索引。

| 题号 | 一句话 | 详解 |
|------|--------|------|
| F17 | 强制 mode / hints / 无索引→web / 默认 hybrid | [04 §…](./04-Hybrid-Search-MCP.md#...) |
| F18 | 98%=单次有效工具结果；降级链 | [04 §…](./04-Hybrid-Search-MCP.md#...) |
| F19 | 金融+行为科学两案例 | [04 §…](./04-Hybrid-Search-MCP.md#...) |
| F20 | 访谈+清洗研报；融合排序 | [04 §…](./04-Hybrid-Search-MCP.md#...) |
```

锚点以 `04` 实际 heading id 为准（实现时从 `04` 复制真实链接）。

- [ ] **步骤 3：将 § G 整段替换为索引表**

同理链到 `05` 的 G21–G24 锚点。

- [ ] **步骤 4：§3.4 L2-F19/F20 改为短指针**

删除与 `04` 重复的长案例正文，改为 3 条速查 +「详见 04」。

- [ ] **步骤 5：更新 §5 对照表**

将三-F17…F20、三-G21…G24 的「文档锚点」列改指 `04`/`05`。

- [ ] **步骤 6：确认 `02` 不再残留 F/G 长详答**

```bash
rg -n "^#### F1|^#### G2" "docs/resume/interview/深度研究/02-面试问答.md" || true
rg -n "详解已迁至专项：.*04-|详解已迁至专项：.*05-" "docs/resume/interview/深度研究/02-面试问答.md"
```

预期：无 `#### F17` 级长答标题（或仅索引）；有迁出说明。

- [ ] **步骤 7：Commit**

```bash
git add "docs/resume/interview/深度研究/02-面试问答.md"
git commit -m "$(cat <<'EOF'
docs: move F/G answers to Hybrid and engineering deep-dives

EOF
)"
```

---

### 任务 8：压缩 `03` §8–§9 为短指针

**文件：**
- 修改：`docs/resume/interview/深度研究/03-Main-Sub-Agent编排.md`

- [ ] **步骤 1：更新 §0.2 非目标**

写明：预算/并发/追踪/断点续跑详解归 `05`；Hybrid/MCP 归 `04`。可保留「编排循环里何时截断」的一句话指针。

- [ ] **步骤 2：将 §8 压成短节**

保留：

- 两道预算一句话（`max_turns` / `max_tool_calls_per_turn`）
- 标本数字一行（示例）
- 链到 [`05` §3](./05-工程化能力.md)（用真实锚点）

删除与 `05` 重复的长贴码与长表（或压到半页内且明确「权威见 05」）。

- [ ] **步骤 3：将 §9 压成短节**

保留：

- 「单题内顺序 for」一句 + 代码路径
- 简历口径一句
- 链到 `05` §3 完整对照

- [ ] **步骤 4：更新 §10 / 回看清单里 G22/G23 交叉引用 → `05`**

- [ ] **步骤 5：Commit**

```bash
git add "docs/resume/interview/深度研究/03-Main-Sub-Agent编排.md"
git commit -m "$(cat <<'EOF'
docs: point Main-Sub budget/concurrency sections to engineering deep-dive

EOF
)"
```

---

### 任务 9：题纲与旧规格交叉引用 + 全量验收

**文件：**
- 修改：`docs/resume/interview/面试题纲.md`
- 修改：`docs/superpowers/specs/2026-08-04-deep-research-interview-prep-design.md`
- 修改：`docs/superpowers/specs/2026-08-05-main-sub-agent-deep-dive-design.md`

- [ ] **步骤 1：题纲 F/G 节下加详解路径（不改编题干）**

在 F 节标题下增加一行，例如：

```markdown
> 详解：[`深度研究/04-Hybrid-Search-MCP.md`](./深度研究/04-Hybrid-Search-MCP.md)
```

在 G 节标题下：

```markdown
> 详解：[`深度研究/05-工程化能力.md`](./深度研究/05-工程化能力.md)
```

- [ ] **步骤 2：更新 `2026-08-04` 规格拆分说明**

在现有 Main-Sub 拆分更新旁追加：

```markdown
> **拆分更新（2026-08-06）：** Hybrid Search + MCP（F17–F20）与工程化（G21–G24）
> 深挖已拆至 `2026-08-06-hybrid-search-and-engineering-interview-prep-design.md`
> 与 `深度研究/04-Hybrid-Search-MCP.md`、`深度研究/05-工程化能力.md`。
```

- [ ] **步骤 3：更新 `2026-08-05` 规格**

在非目标或拆分说明处追加：预算/并发权威详解改归 `05`；本规格对应的 `03` §8–§9 仅为编排侧短指针。

- [ ] **步骤 4：全量验收（对照规格 §9）**

```bash
# 文件存在
test -f "docs/resume/interview/深度研究/04-Hybrid-Search-MCP.md"
test -f "docs/resume/interview/深度研究/05-工程化能力.md"

# 知识库主口径
rg -n "访谈材料|清洗" "docs/resume/interview/深度研究/04-Hybrid-Search-MCP.md"

# 证据/引用诚实
rg -n "强校验|SearchHit|chunk_id" "docs/resume/interview/深度研究/04-Hybrid-Search-MCP.md"

# 02 已索引化
rg -n "详解已迁至专项" "docs/resume/interview/深度研究/02-面试问答.md"

# 03 指向 05
rg -n "05-工程化能力" "docs/resume/interview/深度研究/03-Main-Sub-Agent编排.md"

# 禁止口径抽检
rg -n "生产向量库已|98%.*任务成功|节省.*小时" "docs/resume/interview/深度研究/04-Hybrid-Search-MCP.md" "docs/resume/interview/深度研究/05-工程化能力.md" || true
```

预期：前几项均有命中；禁止口径抽检无违规肯定句（或仅出现在「不可讲」表中）。

手动口述检查（实现者自检，写入 commit message 或 PR 说明即可）：

1. 能按「接 03 → 工具链 → Hybrid+引用 → 访谈/研报 → F 题」讲完 `04`
2. 能按「追踪 → 熔断/并发 → 续跑 → G 题」讲完 `05`
3. `03` 与 `05` 在熔断/并发上无两套互相矛盾的长文

- [ ] **步骤 5：Commit**

```bash
git add \
  "docs/resume/interview/面试题纲.md" \
  "docs/superpowers/specs/2026-08-04-deep-research-interview-prep-design.md" \
  "docs/superpowers/specs/2026-08-05-main-sub-agent-deep-dive-design.md"
git commit -m "$(cat <<'EOF'
docs: cross-link F/G deep-dives in outline and prior specs

EOF
)"
```

---

## 自检（计划 vs 规格）

| 规格需求 | 对应任务 |
|----------|----------|
| 创建 `04` 五章；先工具链后 Hybrid；证据/引用 | 任务 1–3 |
| 知识库=访谈+清洗研报；F19/F20 | 任务 3 |
| 创建 `05` 五章；追踪/熔断并发/续跑 | 任务 4–6 |
| `05` 为预算/并发权威；`03` §8–§9 短指针 | 任务 5、8 |
| `02` F/G 迁出索引；对照表；L2 短指针 | 任务 7 |
| 题纲 + 旧规格拆分说明 | 任务 9 |
| 不改业务代码 | 文件结构「明确不修改」 |
| 诚实边界（98%、向量、省时、并发） | 各任务自检命令 + 任务 9 抽检 |

占位符扫描：本计划无「TODO/待定/类似任务 N」。TDD 不适用于纯文档交付；以 rg 抽检与口述验收代替测试红绿。

---

## 执行交接

计划已完成后保存到本文件。实现时推荐：

1. **子代理驱动（推荐）** — 每任务一个子代理 + 任务间审查  
2. **内联执行** — 当前会话按 executing-plans 批量推进并设检查点  

选哪种方式？
