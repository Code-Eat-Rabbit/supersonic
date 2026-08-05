# 任务 9：规格验收自检报告（对照设计 §10）

## 状态

`通过`

执行日期：2026-08-05

## 自动验收命令及输出

### 1. 调用链关键符号

命令：

```bash
rg -n "create_pipeline_components|expose_sub_agents_as_tools|run_main_agent|run_sub_agent|in sequence|_handle_summary" "$DOC"
```

输出摘要（命中 42 行，以下保留各关键链路的直接证据）：

```text
109:### 2.2 `create_pipeline_components`：按 Agent 隔离 ToolManager
114:def create_pipeline_components(cfg: DictConfig, logs_dir: str | None = None):
198:        final_answer, final_boxed_answer = await orchestrator.run_main_agent(
224:### 3.1 `expose_sub_agents_as_tools`：把配置项转换为工具定义
229:def expose_sub_agents_as_tools(sub_agents_cfg: DictConfig):
292:            tool_definitions += expose_sub_agents_as_tools(self.cfg.sub_agents)
387:            # 7. Execute tool calls (in sequence)
412:                        sub_agent_result = await self.run_sub_agent(
527:## 5. 调用链精读④：`run_sub_agent`
534:    async def run_sub_agent(
809:        final_answer_text = await self._handle_summary_with_context_limit_retry(
941:        final_answer_text = await self._handle_summary_with_context_limit_retry(
1063:            # 7. Execute tool calls (in sequence)
1080:                    sub_agent_result = await self.run_sub_agent(
1222:2. `src/core/pipeline.py`：`create_pipeline_components` 与 `execute_task_pipeline`。
1224:4. `src/core/orchestrator.py`：先看 `run_main_agent` 的 tool 段，再看 `run_sub_agent` 的独立会话、子循环与摘要回传。
```

结论：通过。配置装配、子 Agent 工具化、Main 主循环、Sub 执行、摘要回传及 Main final summary 均有源码摘录和解释。

### 2. 并发口径

命令：

```bash
rg -n "简历口径|run_parallel_inference|max_tool_calls_per_turn" "$DOC"
```

输出摘要（命中 28 行，保留关键证据）：

```text
107:- `max_turns` 是会话轮次上限，`max_tool_calls_per_turn` 是单轮工具调用上限；后者不等于并发数。
508:2. **`max_tool_calls_per_turn` 是截断上限，不是并发度**：切片 `tool_calls[0][:max_tool_calls]` 只处理前 N 个调用
1046:> 这套编排有两道基础预算：`max_turns` 控制 Agent 循环深度，`max_tool_calls_per_turn` 控制单轮工具调用数
1097:`common_benchmark.py:369-393` 的 `run_parallel_inference` 确实使用了 `Semaphore + gather(return_exceptions=True)`：
1100:    async def run_parallel_inference(
1134:### 8.3 简历口径模板（可背）
1191:  - 上限分两层：`max_turns` 限制 Agent 循环深度，`max_tool_calls_per_turn` 限制单轮接收的工具调用数。
1226:6. 对比 `common_benchmark.py` 的 `run_parallel_inference`：确认 `Semaphore + gather` 控制的是多题并行，不是单题内子 Agent 并发。
```

结论：通过。文档明确区分单题内顺序调度、多题并行和单轮调用数量上限。

### 3. 禁止越界

命令：

```bash
rg -n "我发明|JSON schema 强校验已落地|标本已用 asyncio.gather" "$DOC" || true
```

输出：

```text
7:> 复习标本：`miro-flow-solution`（对齐工程细节；面试不主动对比 MiroFlow，不宣称「我发明框架」）
30:| 结构化报告 | 逻辑结构（结论/证据/缺口/不确定性）；标本多为自然语言 summary | 「代码级 JSON schema 强校验已落地」 |
31:| 归属 | 工程 harness owner；标本对齐细节 | 「我发明了这套编排框架」 |
```

结论：通过。三处命中均位于“不宣称/不可讲”的诚实边界中，不是肯定声称；未命中“标本已用 asyncio.gather”。

### 4. 范围未膨胀

命令：

```bash
rg -n "Hybrid Search|工具调用成功率|断点续跑|DataInterpretProcessor" "$DOC" || true
```

输出：

```text
21:- Hybrid Search / MCP 98% / GAIA 断点续跑全文 / Java↔Python 集成契约 / 完整 TaskTracer 回放教程。
```

结论：通过。唯一命中位于非目标清单，正文没有展开这些主题；`DataInterpretProcessor` 无命中。

### 5. `02` 已索引化

命令：

```bash
rg -n "03-Main-Sub-Agent编排" "$IDX"
test ! -n "$(rg -n '^#### E13' "$IDX" || true)"
```

输出：

```text
6:> Main-Sub 精读：[`03-Main-Sub-Agent编排.md`](./03-Main-Sub-Agent编排.md)
195:> 详解已迁至专项：[`03-Main-Sub-Agent编排.md`](./03-Main-Sub-Agent编排.md)（调用链精读 + 并发口径 + E13–E16）。
200:| E13 | 子任务描述开新会话；独立 session/history；只回传 summary | [03 §9 E13](./03-Main-Sub-Agent编排.md#e13-子会话隔离具体怎么做信息缺失怎么办) · 精读 [§5](./03-Main-Sub-Agent编排.md#5-调用链精读run_sub_agent) |
201:| E14 | 动态委派；标本单题内顺序执行；`10` 是单轮上限不是并发度 | [03 §9 E14](./03-Main-Sub-Agent编排.md#e14-子任务怎么分配最多同时跑几个) · [§8 并发专节](./03-Main-Sub-Agent编排.md#8-专节顺序执行-vs-简历并发) |
202:| E15 | 子 Agent 先 summary 再回传；主 Agent 二次汇总；无 JSON 强校验 | [03 §9 E15](./03-Main-Sub-Agent编排.md#e15-主-agent-如何汇总子-agent-质量差怎么办) |
203:| E16 | 0-1 工程 owner；比赛原型 + 实习接入；博士后咨询 | [03 §9 E16](./03-Main-Sub-Agent编排.md#e16-模块是谁做的花了多久) |
344:- **事实源 / 详答：** [§0.1 职责与来源](#01-职责与来源)；详答回看 [03 §9 E16](./03-Main-Sub-Agent编排.md#e16-模块是谁做的花了多久)。
411:| 三-E13 | [03 E13 子会话隔离](./03-Main-Sub-Agent编排.md#e13-子会话隔离具体怎么做信息缺失怎么办) | L1 | `src/core/orchestrator.py`；`src/logging/task_tracer.py` |
412:| 三-E14 | [03 E14 子任务调度](./03-Main-Sub-Agent编排.md#e14-子任务怎么分配最多同时跑几个) | L1 | `src/utils/tool_utils.py`；`src/core/orchestrator.py`；`config/agent_llm_qwen37plus.yaml` |
413:| 三-E15 | [03 E15 主 Agent 汇总](./03-Main-Sub-Agent编排.md#e15-主-agent-如何汇总子-agent-质量差怎么办) | L1 | `src/core/orchestrator.py` |
414:| 三-E16 | [03 E16 Owner / 时间](./03-Main-Sub-Agent编排.md#e16-模块是谁做的花了多久) | L2 | `src/core/orchestrator.py`；本文 §0.1 |
```

第二条命令输出为空，退出码为 `0`。

结论：通过。`02` 的 E 节仅保留 E13–E16 一句话索引和 `03` 锚点，无 `#### E13` 长正文。题纲第 226 行也已指向 `03-Main-Sub-Agent编排.md`。

### 6. 篇幅粗检

命令：

```bash
wc -l "$DOC"
```

输出：

```text
1226 docs/resume/interview/深度研究/03-Main-Sub-Agent编排.md
```

结论：通过。1226 行高于建议的 400 行精读目标。

## 人工口述自评

- **按 §2→§6 讲完一次委派：通过。** 可按 pipeline 配置装配 → 暴露 `agent-*` 伪工具 → Main 循环识别委派 → `run_sub_agent` 创建独立 session/history → Sub summary 作为 tool result 回写 Main history → Main final summary 的顺序完整口述。§2、§3、§4、§5、§6 均有“面试时怎么说”。
- **回答“同时跑几个”：通过。** 可直接指向 §8：当前单题内是 `for + await` 顺序执行；`max_tool_calls_per_turn=10` 是单轮截断上限，不是并发度；`run_parallel_inference` 的 `Semaphore + gather` 是多题并行。
- **E13–E16 口述覆盖：通过。** `03` §9 四题均包含第一句、要点、易踩坑和精读回链。

## 设计 §10 结论

- 调用链可口述：通过
- 并发追问：通过
- 题覆盖：通过
- 诚实边界：通过
- 范围控制：通过
- `02`、对照表和题纲索引：通过

## 修正与提交

未发现需要修正 `03` 或 `02` 的验收缺口，未创建修复提交。`01-集成设计.md` 未被 stage。

## 最终整分支审查修复（2026-08-05）

- **I1：已修复。** 将 `03-Main-Sub-Agent编排.md` §1.3 的计划祈使句替换为面向读者的配置摘要，补齐 Main 20/10 与轻工具、Sub worker 50/10 与重工具、配置支持异构但 GAIA 示例通常同模，以及当前 pipeline 复用首个 Sub LLM client 的实现边界。
- **M6：已修复。** 将 `2026-08-05-main-sub-agent-deep-dive.md` 中已完成任务的步骤复选框统一勾选为 `[x]`。
- **范围检查：** 保持 §1.3 标题不变，§9 B4 锚点无需调整；未修改 `01-集成设计.md`，未扩展 Hybrid/MCP 内容。
