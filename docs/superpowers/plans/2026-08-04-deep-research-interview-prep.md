# 深度研究面试准备 — 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 产出与「业务背景」同款的 `三、深度研究-面试准备.md`（L0/L1/L2 分层），同步修正旧文档口径，并用标本跑通耗时实测后回填。

**架构：** 面试问题驱动学习——按 L1 主题打开 `miro-flow-solution` 标本对齐工程细节，再写入答题要点；耗时/超时不预设数字，实测后回填；跨文档以规格 L0 为准统一口径。

**技术栈：** Markdown 面试文档；标本仓库 Python/FastAPI/MCP/Hydra（`miro-flow-solution`）；可选 CLI `main.py trace` 做耗时采样。

**规格：** `docs/superpowers/specs/2026-08-04-deep-research-interview-prep-design.md`

**标本根目录：** `/Users/yourton_ma/workspace/agent_project/research-agent/miro-flow-solution`

---

## 文件结构

| 文件 | 职责 |
|------|------|
| 创建：`docs/resume/interview/三、深度研究-面试准备.md` | 主交付：L0 事实库 + L1 深挖 + L2 速查 + 待实测清单 + 对照表 |
| 修改：`docs/resume/interview/一、业务背景-面试准备.md` | 职责口径（博士后咨询）；去掉未验证的深度研究平均 90s / 120s 硬写 |
| 修改：`docs/resume/interview/非技术面试-产品与指标准备.md` | §4 去掉「平均 90s」「失败率 15–20%」；机制话术保留 |
| 可选修改：`docs/resume/interview/面试题纲.md` | 仅在实测完成后，将第一句/追问中的超时数字与实测对齐 |

**明确不创建：** 模拟面试完整脚本；miro-flow / Data Agent 功能代码改动。

---

### 任务 1：搭建主文档骨架 + L0 事实库

**文件：**
- 创建：`docs/resume/interview/三、深度研究-面试准备.md`

- [ ] **步骤 1：创建文件并写入头部 + L0（可直接粘贴）**

```markdown
# 三、深度研究 — 面试准备

> 配套题纲：[`面试题纲.md`](./面试题纲.md) § 三、深度研究 + 模型选型（Research Agent 侧）
> 简历基线：[`../my_resume.md`](../my_resume.md)
> 设计规格：[`../../superpowers/specs/2026-08-04-deep-research-interview-prep-design.md`](../../superpowers/specs/2026-08-04-deep-research-interview-prep-design.md)
> 学习方式：面试问题驱动 + 按需回看标本 `miro-flow-solution`
> 适用场景：Chat-BI / 智能问数方向（后端 + Agent 开发）

---

## 0. L0 事实库（一处定义）

### 0.1 职责与来源

| 项 | 口径 |
|----|------|
| Owner | 我从 0-1 搭建深度研究服务（工程 harness：编排运行时、工具接入、服务化、追踪与熔断） |
| 算法博士后 | **咨询**：Prompt 调优建议、测评集怎么选/怎么跑——不主导实现 |
| 起源 | 业余阿里云 Research Agent 比赛 → 魔改接入 Data Agent（双层解读、对接 Java 查数主链路、领域知识库） |
| 复习标本 | `miro-flow-solution`：把工程细节摸熟；面试不主动对比 MiroFlow，也不把开源框架说成「我发明的」 |

### 0.2 产品定位

- **默认**：描述性解读（<2s）——只基于查数结果做结构化摘要 + 关键指标解释
- **可选**：深度研究——多步联网交叉验证 + 归因；失败/超时 → **静默回退**描述性解读，不阻断主链路
- **触发**：用户主动选（非默认全开）
- **通信**：独立 Python 微服务 ↔ Java 主链路（REST；深度研究偏异步长任务）

### 0.3 硬指标

| 指标 | 取值 | 说明 |
|------|------|------|
| GAIA-165 | 整体 53%（L1 68% / L2 47% / L3 19%）；SOTA ~80% | 简历已写 |
| MCP 工具调用成功率 | ~98% | 简历已写；定义见 L1-F |
| 超时上限 | **待实测后填入** | 与端到端耗时一起定 |
| 端到端耗时 | **待实测后填入** | 见文末「待实测回填清单」 |
| 失败/回退率 | **不写入、不主动交代** | 被追问只讲机制 |

### 0.4 诚实边界

- 53% 是有参照的真实位置；短板在 Level 3 多步推理
- 价值在：跑通链路 + 工程化（追踪/熔断/断点续跑/不挡主链路），不是算法创新
- 这是 harness 工程；Prompt/评测有博士后建议

---

## 1. 开场（宽问 / 锥问）

（任务 2 起按节填充）

---

## 2. L1 追问链

（按 A→G 填充）

---

## 3. L2 速查

（任务 7 填充）

---

## 4. 待实测回填清单

| 项 | 状态 | 填入位置 |
|----|------|----------|
| 端到端耗时（典型任务） | 待测 | §0.3 + 开场第一句 |
| 超时上限配置 | 待测 | §0.3 + D10 + 题纲第一句（可选同步） |

---

## 5. 与题纲 / 简历对照表

（任务 7 填充）
```

- [ ] **步骤 2：确认文件存在且 L0 四小节齐全**

运行：

```bash
test -f docs/resume/interview/三、深度研究-面试准备.md && rg -n "^## 0\.|^### 0\." docs/resume/interview/三、深度研究-面试准备.md
```

预期：文件存在；输出含 `## 0.` 与 `0.1`–`0.4`。

- [ ] **步骤 3：Commit**

```bash
git add docs/resume/interview/三、深度研究-面试准备.md
git commit -m "$(cat <<'EOF'
docs(interview): scaffold deep research prep with L0 facts

EOF
)"
```

---

### 任务 2：开场 + L1-A（GAIA）+ L1-B（Java→Python）

**文件：**
- 修改：`docs/resume/interview/三、深度研究-面试准备.md`
- 回看标本：
  - `miro-flow-solution/main.py`（`trace` / `common-benchmark` 入口）
  - `miro-flow-solution/common_benchmark.py`（pass@k、已有 log 续跑扫描）
  - `miro-flow-solution/server/app.py`（FastAPI + WebSocket 产品层）

- [ ] **步骤 1：打开标本对齐「评测入口」与「服务层」**

阅读上述三个文件的入口与类职责，在笔记中记下：benchmark 如何跳过已有 log、server 如何启动任务（用于 B 的通信叙事对照）。

- [ ] **步骤 2：写入「## 1. 开场」与「### A. GAIA」「### B. 语言切换」**

在 `## 1. 开场` 下写入（耗时数字保持「待实测」占位，勿写死 90s/120s）：

```markdown
## 1. 开场（宽问 / 锥问）

| 层级 | 面试官问法 | 第一句答题 |
|------|-----------|-----------|
| 宽问 | 深度研究模块做了什么？ | 查询结果默认经 LLM 做描述性解读（<2s）；深度研究作为可选项做多步联网交叉验证与归因，失败或超时则静默回退描述性解读，不阻断主链路。GAIA-165 整体 53%（L1 68% / L2 47% / L3 19%），短板在复杂多步推理。 |
| 锥问 | 为什么专门写 SOTA 80%？ | 只看 53% 没法定位水平；leaderboard 第一名约 80% 给出参照。L1 68% 可用，L3 19% 是多步推理短板。 |
| 锥问 | 前面 Java，为什么深度研究用 Python？ | 需要 LLM 生态（工具协议、多 Agent 编排、检索）Python 更成熟；独立微服务对接主链路，查数主链路 Java 不动。 |
```

在 `## 2. L1 追问链` 下追加 A、B 两节，每题含：**第一句 / 要点 / 易踩坑 / 回看标本**。

**A1–A3 要点必须覆盖：**

- Level 衰减：68→47→19；差距集中在多步工具链与交叉验证
- 失败类型优先序：多跳推理失败 > 工具链中断 > 超时（超时阈值待实测后再说）
- 诚实：单人业余时间位置真实，不吹 SOTA

**回看标本（写入文档）：**

- `main.py` → `common-benchmark` / `trace`
- `common_benchmark.py`（pass@k、已有 log 加载）

**B4–B6 要点必须覆盖：**

- 选型：LLM/MCP/Agent 生态 → Python；主链路稳定 → Java 不动
- 通信：REST（查数同步）+ 异步任务（深度研究）；跨服务用同一 `traceId` 串联（与业务背景 ELK 叙事一致）
- 决策：你 0-1 owner；博士后咨询 Prompt/评测

**回看标本：** `server/app.py`、`server/bridge/runner.py`

- [ ] **步骤 3：自检 A/B 无「90s / 120s / 失败率」硬数字**

运行：

```bash
rg -n "90s|120s|15-20%|失败率" docs/resume/interview/三、深度研究-面试准备.md || true
```

预期：无匹配，或仅出现在「待实测 / 不主动交代」说明中。

- [ ] **步骤 4：Commit**

```bash
git add docs/resume/interview/三、深度研究-面试准备.md
git commit -m "$(cat <<'EOF'
docs(interview): add deep research opening + GAIA + Java/Python Q&A

EOF
)"
```

---

### 任务 3：L1-C（双层解读）+ L1-D（失败回退）

**文件：**
- 修改：`docs/resume/interview/三、深度研究-面试准备.md`
- 参考（只读对齐，勿照抄未验证数字）：`docs/resume/interview/非技术面试-产品与指标准备.md` §4.1–4.2
- 回看标本：`miro-flow-solution/src/core/pipeline.py`（`execute_task_pipeline` 收尾/落盘）、`miro-flow-solution/src/core/orchestrator.py`（`handle_max_turns_reached` / 循环退出）

- [ ] **步骤 1：回看 pipeline / orchestrator 的失败与结束路径**

确认：任务何时标 completed/failed；max_turns 到达后如何收束。用于定义「失败」：最终结果不可用（超时、整体失败、无可用报告），而非「中间任一步偶发失败立刻整单失败」。

- [ ] **步骤 2：写入 C7–C9、D10–D12**

**C 必须讲清：**

- 同一查询结果：描述性 = 不超出表内数据的结构化解读；深度 = 外网/知识库交叉验证 + 归因
- 边界是产品决策：延迟、失败面、需求分层（多数只要「是什么」，少数要「为什么」）
- 触发：用户主动；可提「引导点击」但不替用户自动开深度研究

**D 必须讲清：**

- 失败定义：超时或最终深度报告不可用 → 回退（具体超时秒数写「待实测」）
- 静默回退：用户仍看到描述性解读；ELK/日志记失败原因（与业务背景可观测叙事一致）
- D12：不交代失败率数字；不编「连续三次回退后用户行为」；只讲产品取舍

- [ ] **步骤 3：Commit**

```bash
git add docs/resume/interview/三、深度研究-面试准备.md
git commit -m "$(cat <<'EOF'
docs(interview): add dual-layer interpret and silent fallback Q&A

EOF
)"
```

---

### 任务 4：L1-E（Main-Sub 编排）

**文件：**
- 修改：`docs/resume/interview/三、深度研究-面试准备.md`
- 回看标本：
  - `miro-flow-solution/src/core/orchestrator.py`（`Orchestrator`、`run_sub_agent`、主循环）
  - `miro-flow-solution/src/utils/tool_utils.py`（`expose_sub_agents_as_tools`）
  - `miro-flow-solution/src/logging/task_tracer.py`（`start_sub_agent_session`、分会话 message history）
  - 配置示例：`miro-flow-solution/config/agent_llm_qwen37plus.yaml`（`max_turns` / `max_tool_calls_per_turn`）

- [ ] **步骤 1：对照源码画出一句话数据流**

主 Agent 拆任务 → 子 Agent 作为工具被调用 → `start_sub_agent_session` 隔离上下文 → 子 Agent 回传摘要/报告 → 主 Agent 汇总。确认主/子可配置不同 `llm_client`。

- [ ] **步骤 2：写入 E13–E16**

必须覆盖：

- 子会话隔离：避免上下文膨胀；信息缺失时靠主 Agent 把任务描述写全（这是真实 trade-off）
- 并发：主 Agent 调度多个子任务；上限与配置相关（结合 `max_turns` / 工具并发叙事，勿编造未读过的魔法数字）
- 汇总：结构化/摘要报告优于原始 tool dump；质量差时主 Agent 可重派或降级结论置信度
- E16：你 0-1 + 比赛魔改；博士后咨询；时间量级用你真实记忆（若不确定写「业余比赛基础 + 实习期工程化接入」，勿编精确人天）

- [ ] **步骤 3：Commit**

```bash
git add docs/resume/interview/三、深度研究-面试准备.md
git commit -m "$(cat <<'EOF'
docs(interview): add Main-Sub agent orchestration Q&A

EOF
)"
```

---

### 任务 5：L1-F（Hybrid Search + MCP）

**文件：**
- 修改：`docs/resume/interview/三、深度研究-面试准备.md`
- 回看标本：
  - `miro-flow-solution/src/retrieval/router.py`（`route_query`：local/web/hybrid 规则）
  - `miro-flow-solution/src/retrieval/fusion.py`
  - `miro-flow-solution/src/tool/mcp_servers/hybrid_search_mcp_server.py`
  - `miro-flow-solution/src/tool/manager.py`（工具注册/调用/纠错）
  - `miro-flow-solution/config/tool/tool-hybrid-search.yaml`

- [ ] **步骤 1：读 `route_query`，用自己的话复述路由规则**

强制 mode → 无本地索引走 web → local/web 关键词命中 → 默认 hybrid + 权重归一。写入答题要点时用业务语言（附件/政策/最新新闻），不要只背函数名。

- [ ] **步骤 2：写入 F17–F20**

必须覆盖：

- F17：何时 local / web / hybrid（对应 router 逻辑）
- F18：MCP 成功 = 工具返回有效结果；失败常见超时/空召回/解析失败；降级：备选工具 → 部分完成仍输出已有结论（**98% 是工具调用成功率，不是深度研究任务成功率**）
- F19–F20：金融研报/政策归因、行为科学相似研究各 **1 个** 具体 case（用你真实经历；若细节模糊，写「案例骨架 + 待你补专有名词」，实现时向用户确认一句即可）

- [ ] **步骤 3：Commit**

```bash
git add docs/resume/interview/三、深度研究-面试准备.md
git commit -m "$(cat <<'EOF'
docs(interview): add Hybrid Search and MCP tool Q&A

EOF
)"
```

---

### 任务 6：L1-G（追踪 / 并发 / 熔断 / 断点续跑）

**文件：**
- 修改：`docs/resume/interview/三、深度研究-面试准备.md`
- 回看标本：
  - `miro-flow-solution/src/logging/task_tracer.py`（`StepRecord`、`save`、status）
  - `miro-flow-solution/src/core/pipeline.py`（落盘时机）
  - `miro-flow-solution/common_benchmark.py`（扫描已有 log、跳过已完成 attempt）
  - 配置：`max_turns` / `max_tool_calls_per_turn`（如 `config/agent_llm_qwen37plus.yaml`：20 / 10）

- [ ] **步骤 1：确认断点续跑判定**

`common_benchmark` 若发现 attempt 已有 log 且已有 judge/boxed answer，则加载而非重跑。答题话术：「以日志落盘状态判断任务是否已完成，批量评测可跳过已完成题。」

- [ ] **步骤 2：写入 G21–G24**

必须覆盖：

- G21：结构化 step log 落盘 → 按 task_id / turn 回放；举例「某次工具返回异常导致后续推理跑偏」类排查（可用标本日志字段说明，勿虚构生产事故细节）
- G22：单任务异常隔离（一题失败不影响并行其他题）；并发数来自评测/服务配置
- G23：熔断 = `max_turns` + `max_tool_calls_per_turn`；过小会截断正常长任务——这是 trade-off
- G24：断点续跑判定如上；省时间体感：重跑评测集时跳过已完成题

- [ ] **步骤 3：Commit**

```bash
git add docs/resume/interview/三、深度研究-面试准备.md
git commit -m "$(cat <<'EOF'
docs(interview): add tracing, circuit-break, and resume Q&A

EOF
)"
```

---

### 任务 7：L2 速查 + 对照表 + 开场完整化

**文件：**
- 修改：`docs/resume/interview/三、深度研究-面试准备.md`

- [ ] **步骤 1：写入「## 3. L2 速查」**

覆盖：

- 模型选型（主/子是否可不同模型；GAIA 用过的模型族；性价比一句话）
- E16 时间/带队（指向 L0）
- D12 行为分析（只讲机制）
- F19–F20 若任务 5 已写可在此做 3 行速查索引

- [ ] **步骤 2：写入「## 5. 对照表」**

列：题纲题号 | 文档锚点 | 层（L1/L2）| 标本路径。确保题纲 §三 A1–G24 + 模型选型 B/C 均有落点。

- [ ] **步骤 3：Commit**

```bash
git add docs/resume/interview/三、深度研究-面试准备.md
git commit -m "$(cat <<'EOF'
docs(interview): add L2 cheat sheet and outline coverage map

EOF
)"
```

---

### 任务 8：跨文档口径同步

**文件：**
- 修改：`docs/resume/interview/一、业务背景-面试准备.md`
- 修改：`docs/resume/interview/非技术面试-产品与指标准备.md`

- [ ] **步骤 1：改业务背景职责口径**

将类似表述：

> 算法/模型相关的深度研究 Python 侧由算法博士后独立主导，我以工程化方式参与

改为：

> 深度研究 Python 服务由我从 0-1 搭建（工程 harness）；算法博士后提供 Prompt/测评集咨询，不主导实现

同步检查 §0.4 分工表备注、A3 追问要点、文末指标速查中任何「博士后主导深度研究」表述。

- [ ] **步骤 2：弱化未验证耗时/失败率**

在业务背景中：

- `平均 ~90s` → 改为「深度研究单独计，耗时见深度研究准备文档（待实测）」或删除均值
- `深度研究 120s 超时` → 改为「超时上限见深度研究准备文档（待实测）」

在非技术面试 §4：

- 删除或改写「平均 90s」「失败率约 15–20%」
- 保留双层解读三原因、静默回退机制、Main-Sub、GAIA 53% 话术

- [ ] **步骤 3：全文扫描残留**

```bash
rg -n "博士后独立主导|平均 ~90s|失败率约 15|深度研究 120s|平均 90s" docs/resume/interview/
```

预期：无「主导」旧口径；无未标注的 90s/15–20%/120s 硬断言（题纲可暂留，待任务 10 再改）。

- [ ] **步骤 4：Commit**

```bash
git add docs/resume/interview/一、业务背景-面试准备.md docs/resume/interview/非技术面试-产品与指标准备.md
git commit -m "$(cat <<'EOF'
docs(interview): align deep research ownership and drop unverified metrics

EOF
)"
```

---

### 任务 9：耗时实测（标本或可用环境）

**文件：**
- 工作目录：`miro-flow-solution`
- 产出记录写入：`docs/resume/interview/三、深度研究-面试准备.md` §4（先记原始数据，任务 10 再提炼话术）

- [ ] **步骤 1：确认环境可跑单任务**

```bash
cd /Users/yourton_ma/workspace/agent_project/research-agent/miro-flow-solution
# 确认 .env / API Key 可用；打印配置不报错
uv run python main.py print-config 2>&1 | head -40
```

预期：Hydra 配置可加载。若缺 Key，停在本步，在 §4 注明「阻塞：缺 API Key」，改用历史 logs 目录中已有 trace 的时间戳估算（`TaskTracer.start_time` / `end_time`）。

- [ ] **步骤 2：跑 2–3 个短任务并记录墙钟时间**

优先用项目已有 `trace` 入口（示例，以实现时实际 config 名为准）：

```bash
# 示例：单任务 trace（覆盖与参数以 print-config / README 为准）
time uv run python main.py trace "比亚迪2024年净利润变化的主要原因是什么？"
```

若全量 Agent 成本过高：从 `logs/` 已有任务 JSON 读取 `start_time`/`end_time`，采样 ≥3 条，计算耗时分布。

记录表（写入 §4）：

| 样本 | 来源（trace/历史log） | 耗时秒 | 轮次/工具调用（若有） |
|------|----------------------|--------|----------------------|
| 1 | | | |
| 2 | | | |
| 3 | | | |

- [ ] **步骤 3：根据分布提议超时上限**

规则：超时建议略高于 P95 样本（或「最慢样本 × 1.2」），并写清依据。若样本不足，标注「建议值，样本 n=…」。

- [ ] **步骤 4：Commit 原始实测记录（可与话术回填同 commit，见任务 10）**

---

### 任务 10：回填耗时话术 + 可选同步题纲

**文件：**
- 修改：`docs/resume/interview/三、深度研究-面试准备.md`（§0.3、开场、D10、§4 状态）
- 可选：`docs/resume/interview/面试题纲.md`（第一句与 A3 中的超时表述）

- [ ] **步骤 1：把实测结果写入 L0 与相关答题**

将「待实测」替换为具体数字或区间（例如「典型 60–150s，超时设为 Xs」——以任务 9 真实数据为准，此处不预设）。

- [ ] **步骤 2（可选）：同步题纲第一句**

仅当实测已完成且你希望题纲与准备文档一致时，改 `面试题纲.md` 中「超时 120s」为实测口径。

- [ ] **步骤 3：最终扫描**

```bash
rg -n "待实测|90s|15-20%" docs/resume/interview/三、深度研究-面试准备.md
rg -n "博士后独立主导" docs/resume/interview/
```

预期：主文档无残留「待实测」（若任务 9 被 Key 阻塞，则允许保留并在 §4 标明阻塞原因）；全目录无「博士后独立主导」。

- [ ] **步骤 4：Commit**

```bash
git add docs/resume/interview/三、深度研究-面试准备.md
# 若改了题纲：
# git add docs/resume/interview/面试题纲.md
git commit -m "$(cat <<'EOF'
docs(interview): fill deep research latency from measured runs

EOF
)"
```

---

## 自检（对照规格）

| 规格章节 | 对应任务 |
|----------|----------|
| §2 L0 职责/产品/指标/诚实边界 | 任务 1、8、10 |
| §3 方案 C + 分层 | 任务 1–7（文档结构） |
| §4.1 L1 全主题 | 任务 2–6 |
| §4.2 L2 | 任务 7 |
| §5.1 主文件目录 | 任务 1、7 |
| §5.2 跨文档同步 | 任务 8、10 |
| §6 耗时实测 | 任务 9–10 |
| 不写失败率 / 不吹 MiroFlow | 任务 2–3、8 扫描步骤 |

占位符：计划中「待实测」仅作为任务 9–10 的显式工作项；答题正文在任务 10 前允许保留，完成后必须清除或标注阻塞原因。
