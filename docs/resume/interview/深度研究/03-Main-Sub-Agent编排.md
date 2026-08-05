# Main–Sub Agent 编排 — 代码精读与面试深挖

> 对应简历：问数结果深度研究 · 第二点（Main–Sub Agent 编排）
> 题纲：[`../面试题纲.md`](../面试题纲.md) § 三 E13–E16
> 索引本：[`02-面试问答.md`](./02-面试问答.md)（E 节已迁出至本文）
> 设计规格：[`../../../superpowers/specs/2026-08-05-main-sub-agent-deep-dive-design.md`](../../../superpowers/specs/2026-08-05-main-sub-agent-deep-dive-design.md)
> 复习标本：`miro-flow-solution`（对齐工程细节；面试不主动对比 MiroFlow，不宣称「我发明框架」）

---

## 0. 目标与诚实边界

### 0.1 本文做什么

- 按一次任务跑通 Main→Sub→回传→final summary 的调用链，贴关键代码并注释。
- 钉死「简历并发」与「标本顺序执行」的可答辩关系。
- 承接原 `02` E13–E16 详答，供面试深挖。

### 0.2 本文不做什么

- Hybrid Search / MCP 98% / GAIA 断点续跑全文 / Java↔Python 集成契约 / 完整 TaskTracer 回放教程。

### 0.3 诚实边界总表

| 说法 | 可讲 | 不可讲 |
|------|------|--------|
| 子会话隔离 | 新 `message_history` + 独立 session；只回传 summary | 「子 Agent 共享主会话全量上下文」 |
| 动态拆分 | 主 Agent 按 tool 描述决定是否委派 | 「每类问题写死固定角色路由表」（无额外依据时） |
| 并发 | 架构可并行无依赖子任务；业务需另加并发/超时/隔离 | 标本 `for` 说成已 `gather`；把 `10` 说成同时跑 10 个 |
| 结构化报告 | 逻辑结构（结论/证据/缺口/不确定性）；标本多为自然语言 summary | 「代码级 JSON schema 强校验已落地」 |
| 归属 | 工程 harness owner；标本对齐细节 | 「我发明了这套编排框架」 |

---

## 1. 架构总览

### 1.1 角色

| 角色 | 职责 | 标本依据 |
|------|------|----------|
| Main Agent | 拆任务、选工具/子 Agent、汇总最终答案 | `run_main_agent`；工具偏轻（如 `tool-reasoning`） |
| Sub Agent（如 `agent-worker`） | 独立会话内检索/阅读/代码等，产出 summary | `run_sub_agent`；工具更重 |
| Tool 化外壳 | `agent-` 前缀暴露为可调用工具 | `expose_sub_agents_as_tools` |
| TaskTracer | 主/子 history 分存；`session_id = {name}_{counter}` | `start_sub_agent_session` |

### 1.2 一次任务数据流

```mermaid
flowchart TD
  A[pipeline 装配 ToolManager + LLM] --> B[run_main_agent]
  B --> C[expose 子 Agent 进 tool_definitions]
  C --> D[主循环 turn: LLM 决策]
  D --> E{tool call?}
  E -->|普通 MCP| F[main ToolManager.execute]
  E -->|server 名 agent-*| G[run_sub_agent 新 session]
  G --> H[子循环 + 子 final summary]
  H --> I[summary 作为 tool result 回主 history]
  F --> J[结果写回主 history]
  I --> D
  J --> D
  E -->|无 tool / 触顶| K[主 Agent final summary]
```

### 1.3 配置骨架（标本示例，非业务最优）

以 `config/agent_llm_qwen37plus.yaml` 为准列出 Main/Sub 的 `llm`、`tool_config`、`max_turns`、`max_tool_calls_per_turn`；注明 Main/Sub llm 块分开故**支持**异构，GAIA 示例通常同模。

---

## 2. 调用链精读①：配置装配

### 2.1 配置先定义 Main/Sub 的能力边界

`main_agent` 与 `sub_agents.agent-worker` 各自拥有独立的 LLM、工具和轮次预算。以下仅删除密钥、采样参数等环境噪音，保留影响编排的关键字段。

文件：`config/agent_llm_qwen37plus.yaml:7-67`

```yaml
main_agent:
  prompt_class: MainAgentPrompt_GAIA
  llm:
    model_name: "qwen3.7-plus"
  tool_config:
    - tool-reasoning
  max_turns: 20
  max_tool_calls_per_turn: 10

sub_agents:
  agent-worker:
    prompt_class: SubAgentWorkerPrompt
    llm:
      model_name: "qwen3.7-plus"
    tool_config:
      - tool-searching
      - tool-reading
      - tool-code
      - tool-image-video
      - tool-audio
    max_turns: 50
    max_tool_calls_per_turn: 10
```

旁注：

- Main Agent 只配置 `tool-reasoning`，负责规划、委派与汇总；`agent-worker` 持有搜索、阅读、代码和多模态等执行工具。
- Main/Sub 的 `llm` 配置块相互独立，因此架构上支持异构模型；这份 GAIA 示例恰好都使用 `qwen3.7-plus`，不能据此说成只能同模。
- `max_turns` 是会话轮次上限，`max_tool_calls_per_turn` 是单轮工具调用上限；后者不等于并发数。

### 2.2 `create_pipeline_components`：按 Agent 隔离 ToolManager

文件：`src/core/pipeline.py:200-234`

```python
def create_pipeline_components(cfg: DictConfig, logs_dir: str | None = None):
    """
    Creates and initializes the core components of the agent pipeline.

    Args:
        cfg: The Hydra configuration object.

    Returns:
        Tuple of (main_agent_tool_manager, sub_agent_tool_managers, output_formatter)
    """
    # Create ToolManagers for main agent and sub-agents
    main_agent_mcp_server_configs, main_agent_blacklist = create_mcp_server_parameters(
        cfg, cfg.main_agent, logs_dir
    )
    main_agent_tool_manager = ToolManager(
        main_agent_mcp_server_configs,
        tool_blacklist=main_agent_blacklist,
    )

    sub_agent_tool_managers = {}
    if cfg.sub_agents is not None and cfg.sub_agents:
        for sub_agent in cfg.sub_agents:
            sub_agent_mcp_server_configs, sub_agent_blacklist = (
                create_mcp_server_parameters(cfg, cfg.sub_agents[sub_agent], logs_dir)
            )
            sub_agent_tool_manager = ToolManager(
                sub_agent_mcp_server_configs,
                tool_blacklist=sub_agent_blacklist,
            )
            sub_agent_tool_managers[sub_agent] = sub_agent_tool_manager

    # Create OutputFormatter
    output_formatter = OutputFormatter()

    return main_agent_tool_manager, sub_agent_tool_managers, output_formatter
```

旁注：Main Agent 创建一个 `ToolManager`；每个 Sub Agent 也分别创建一个 `ToolManager`，再按子 Agent 名称放入字典。这不是把所有工具塞进同一个全局管理器，而是在装配期落实工具集合与黑名单隔离。`create_mcp_server_parameters` 会依据各自的 `tool_config` 加载工具配置。

### 2.3 `execute_task_pipeline`：运行时入口完成 LLM 与 Orchestrator 装配

文件：`src/core/pipeline.py:111-155`

```python
        # Initialize main agent LLM client
        # Require agent-specific LLM configuration
        if hasattr(cfg.main_agent, "llm") and cfg.main_agent.llm is not None:
            main_agent_llm_client = LLMClient(
                task_id=task_id, llm_config=cfg.main_agent.llm
            )
        else:
            raise ValueError(
                "No LLM configuration found in main_agent. Please ensure the agent configuration includes an LLM section."
            )

        # Initialize sub agent LLM client
        # Require agent-specific LLM configuration for sub-agents
        if cfg.sub_agents is not None and cfg.sub_agents:
            first_sub_agent = next(iter(cfg.sub_agents.values()))
            if hasattr(first_sub_agent, "llm") and first_sub_agent.llm is not None:
                sub_agent_llm_client = LLMClient(
                    task_id=f"{task_id}_sub", llm_config=first_sub_agent.llm
                )
            else:
                raise ValueError(
                    "No LLM configuration found in sub-agent. Please ensure the agent configuration includes an LLM section."
                )
        else:
            sub_agent_llm_client = None
            logger.info("No sub agents defined, using main agent only for the task")

        # Initialize orchestrator
        orchestrator = Orchestrator(
            main_agent_tool_manager=main_agent_tool_manager,
            sub_agent_tool_managers=sub_agent_tool_managers,
            llm_client=main_agent_llm_client,
            sub_agent_llm_client=sub_agent_llm_client,
            output_formatter=output_formatter,
            task_log=task_log,
            cfg=cfg,
            human_interaction=human_interaction,
        )

        task_log.status = "running"
        final_answer, final_boxed_answer = await orchestrator.run_main_agent(
            task_description=task_description,
            task_file_name=task_file_name,
            task_id=task_id,
        )
```

旁注：真正的 Python 运行时入口是 pipeline。它从配置创建 Main/Sub 的 `LLMClient`，把 LLM、两个层级的 `ToolManager`、日志与配置注入 `Orchestrator`，最后调用 `run_main_agent`。当前实现只读取第一个 Sub Agent 的 LLM 配置并复用一个 `sub_agent_llm_client`，所以「配置结构支持异构」不等于「多个 Sub Agent 已逐个实例化不同 LLMClient」。

### 面试时怎么说

1. 我先用 YAML 把 Main 与 Sub 的模型、工具和预算边界配置化，Main 偏规划汇总，Sub 偏执行。
2. pipeline 装配时，Main 有一个独立 `ToolManager`，每个 Sub 也各有一个，工具权限不是全局共享。
3. `execute_task_pipeline` 再创建 LLM client 和 `Orchestrator`，由 `run_main_agent` 正式进入编排循环。
4. 配置块允许 Main/Sub 选不同模型，但这份标本当前只从第一个 Sub 配置创建共享的 Sub LLM client，我会明确区分架构能力与现状。

### 易踩坑

- 不要说「整个 Data Agent 都在 Python 里装配」：这里只能证明深度研究 Agent harness 的 Python 装配链；Data Agent 主体还涉及 Java/Spring 等边界。
- 不要把 `max_tool_calls_per_turn: 10` 解释成同时并发 10 个工具，它只是单轮调用数量上限。
- 不要仅凭 Main/Sub 各有 `llm` 块就宣称多个 Sub Agent 已实现逐角色异构模型；当前 pipeline 取的是 `first_sub_agent`。

**下一跳：** §3 继续看配置中的 Sub Agent 如何被转换成 Main Agent 可见的工具。

## 3. 调用链精读②：子 Agent 工具化

### 3.1 `expose_sub_agents_as_tools`：把配置项转换为工具定义

文件：`src/utils/tool_utils.py:87-105`

```python
def expose_sub_agents_as_tools(sub_agents_cfg: DictConfig):
    """Expose sub-agents as tools"""
    sub_agents_server_params = []
    for sub_agent in sub_agents_cfg.keys():
        if not sub_agent.startswith("agent-"):
            raise ValueError(
                f"Sub-agent name must start with 'agent-': {sub_agent}. Please check the sub-agent name in the agent's config file."
            )
        try:
            sub_agent_prompt_instance = _load_agent_prompt_class(
                sub_agents_cfg[sub_agent].prompt_class
            )
            sub_agent_tool_definition = sub_agent_prompt_instance.expose_agent_as_tool(
                subagent_name=sub_agent
            )
            sub_agents_server_params.append(sub_agent_tool_definition)
        except Exception as e:
            raise ValueError(f"Failed to expose sub-agent {sub_agent} as a tool: {e}")
    return sub_agents_server_params
```

旁注：函数遍历 Sub Agent 配置，按 `prompt_class` 动态加载 Prompt 类，再调用其 `expose_agent_as_tool` 生成工具定义。名称必须以 `agent-` 开头；这既是配置校验，也是后续执行阶段区分「普通 MCP 工具」与「子 Agent 工具」的协议约定。

### 3.2 `SubAgentWorkerPrompt.expose_agent_as_tool`：定义委派契约

文件：`config/agent_prompts/sub_worker.py:229-247`

```python
    def expose_agent_as_tool(self, subagent_name: str) -> dict:
        tool_definition = dict(
            name=subagent_name,
            tools=[
                dict(
                    name="execute_subtask",
                    description="This tool is an agent that performs various subtasks to collect information and execute specific actions. It can access the internet, read files, program, and process multimodal content, but is not specialized in complex reasoning or logical thinking. The tool returns processed summary reports rather than raw information - it analyzes, synthesizes, and presents findings in a structured format. The subtask should be clearly defined, include relevant background, and focus on a single, well-scoped objective. It does not perform vague or speculative subtasks. \nArgs: \n\tsubtask: the subtask to be performed. \nReturns: \n\tthe processed summary report of the subtask. ",
                    schema={
                        "type": "object",
                        "properties": {
                            "subtask": {"title": "Subtask", "type": "string"}
                        },
                        "required": ["subtask"],
                        "title": "execute_subtaskArguments",
                    },
                )
            ],
        )
        return tool_definition
```

旁注：

- 对 Main Agent 暴露的动作名是 `execute_subtask`，入参只有必填的 `subtask` 字符串；因此 Main 需要把背景、目标与范围写进这段委派指令。
- 描述明确承诺返回 **processed summary reports**，而不是原始搜索结果。也就是说，Sub Agent 先分析、综合并结构化表达，再把摘要作为工具结果交还 Main。
- 工具定义描述的是调用契约，不代表此刻已执行子 Agent；真正执行发生在主循环选择该工具之后。

### 3.3 主循环合并普通工具与子 Agent 工具

文件：`src/core/orchestrator.py:994-1000`

```python
        # 2. Get tool definitions
        tool_definitions = await self.main_agent_tool_manager.get_all_tool_definitions()
        if self.cfg.sub_agents is not None and self.cfg.sub_agents:
            tool_definitions += expose_sub_agents_as_tools(self.cfg.sub_agents)
        if self._human_feature_enabled("allow_ask_user"):
            tool_definitions.append(ASK_USER_TOOL_DEFINITION)
        if not tool_definitions:
```

旁注：`run_main_agent` 先取得 Main 自身的普通工具，再把 Sub Agent 的**伪工具**定义追加到同一份 `tool_definitions`。LLM 看到的是统一工具面，因而可以依据名称、描述和 schema 在运行时决定直接用普通 MCP 工具，还是调用 `agent-worker.execute_subtask`（入参 `subtask` = 任务描述字符串）；后者在主循环里会被 `agent-` 前缀识别并转交 `run_sub_agent`（§4）。

### 面试时怎么说

1. **子 Agent 是带 `agent-` 前缀的伪工具**——不是普通 MCP server，而是经 `expose_sub_agents_as_tools` 生成 tool 定义后并入主工具列表；主循环里若 `server_name.startswith("agent-")` 则拦截，转调 `run_sub_agent`（主循环拦截细节见 §4），而不是走 `ToolManager.execute` 的普通 MCP 路径。
2. **入参是任务描述**：工具 schema 字段名是 `subtask`，语义即一段任务描述字符串（背景、目标、范围写进这段委派指令）；Main 根据当前问题与工具描述决定是否委派，因此是 LLM 驱动的动态委派，不是写死「某类问题固定路由到某角色」的路由表。
3. Sub 完成后返回 processed summary report（非原始检索结果），Main 再继续推理和汇总。

### 易踩坑

- 不要把 expose 说成子 Agent 共享主 history：这里只是把子 Agent 的调用契约加入主工具列表；会话是否隔离要看后续 `run_sub_agent` 的新 `message_history` 与 session 实现。
- 不要漏掉 `agent-` 前缀，它是暴露阶段的硬校验，也是后续识别子 Agent 工具的约定。
- 不要把 `execute_subtask` 的返回说成原始网页、文件或工具日志；描述明确要求 processed summary reports。

**下一跳：** §4 将沿着 `run_main_agent` 主循环，继续追踪模型如何选择并执行这些工具。

## 4. 调用链精读③：主循环

### 4.1 循环骨架：每轮先问 LLM，再判断是否调用工具

文件：`src/core/orchestrator.py:1052-1108`

```python
        # 4. Main loop: LLM <-> Tools
        max_turns = self.cfg.main_agent.max_turns
        if max_turns < 0:
            max_turns = sys.maxsize
        turn_count = 0
        task_failed = False  # Track whether task failed
        while turn_count < max_turns:
            turn_count += 1
            logger.debug(f"\n--- Main Agent Turn {turn_count} ---")
            self.task_log.save()

            # Use unified LLM call handling
            (
                assistant_response_text,
                should_break,
                tool_calls,
            ) = await self._handle_llm_call_with_logging(
                system_prompt,
                message_history,
                tool_definitions,
                turn_count,
                f"Main agent turn {turn_count}",
                keep_tool_result=keep_tool_result,
                agent_type="main",
            )

            # Handle LLM response
            if assistant_response_text:
                if should_break:
                    break
            else:
                # LLM call failed, mark task as failed and end current turn
                if tool_calls == "context_limit":
                    # Context limit exceeded situation
                    self.task_log.log_step(
                        "main_agent_context_limit_reached",
                        "Main agent context limit reached, jumping to summary",
                        "warning",
                    )
                else:
                    # Other LLM call failure situations
                    self.task_log.log_step(
                        step_name="main_agent",
                        message="LLM call failed",
                        status="failed",
                    )
                task_failed = True  # Mark task as failed
                break

            if (
                tool_calls is None
                or len(tool_calls) < 2
                or (len(tool_calls[0]) == 0 and len(tool_calls[1]) == 0)
            ):
                # No tool calls, consider as final answer
                logger.debug("LLM did not request tool use, process ends.")
                break  # Exit loop
```

`_handle_llm_call_with_logging` 同时返回自然语言响应、是否应中止和解析后的工具调用。没有工具调用、LLM 主动结束、调用失败或达到 `max_turns`，都会结束 ReAct 式循环；本轮工具结果写回 history 后，下一轮 LLM 才能读取结果并继续决策。

### 4.2 完整工具执行段：普通工具与子 Agent 在同一个顺序循环中分流

文件：`src/core/orchestrator.py:1110-1225`

```python
            # 7. Execute tool calls (in sequence)
            tool_calls_data = []
            all_tool_results_content_with_id = []

            # Get maximum tool calls per turn from configuration
            max_tool_calls = self.cfg.main_agent.max_tool_calls_per_turn
            tool_calls_exceeded = (
                len(tool_calls) > 0 and len(tool_calls[0]) > max_tool_calls
            )
            if tool_calls_exceeded:
                logger.warning(
                    f"[ERROR] Single turn tool call count too high ({len(tool_calls[0])} calls), only processing first {max_tool_calls}"
                )

            for call in tool_calls[0][:max_tool_calls]:
                server_name = call["server_name"]
                tool_name = call["tool_name"]
                arguments = call["arguments"]
                call_id = call["id"]

                call_start_time = time.time()
                try:
                    if server_name == "human" and tool_name == "ask_user":
                        tool_result = await self._ask_user_tool(arguments)
                    elif server_name.startswith("agent-"):
                        sub_agent_result = await self.run_sub_agent(
                            server_name, str(arguments), keep_tool_result
                        )
                        tool_result = {
                            "server_name": server_name,
                            "tool_name": tool_name,
                            "result": sub_agent_result,
                        }
                    else:
                        tool_result = (
                            await self.main_agent_tool_manager.execute_tool_call(
                                server_name=server_name,
                                tool_name=tool_name,
                                arguments=arguments,
                            )
                        )

                    call_end_time = time.time()
                    call_duration_ms = int((call_end_time - call_start_time) * 1000)

                    tool_calls_data.append(
                        {
                            "server_name": server_name,
                            "tool_name": tool_name,
                            "arguments": arguments,
                            "result": tool_result,
                            "duration_ms": call_duration_ms,
                            "call_time": datetime.datetime.now(),
                        }
                    )
                    self._log_hybrid_observability(tool_result, "main")

                except Exception as e:
                    call_end_time = time.time()
                    call_duration_ms = int((call_end_time - call_start_time) * 1000)

                    # Handle empty error messages, especially for TimeoutError
                    error_msg = str(e) or (
                        "[ERROR]: Tool execution timeout"
                        if isinstance(e, TimeoutError)
                        else f"Tool execution failed: {type(e).__name__}"
                    )

                    tool_calls_data.append(
                        {
                            "server_name": server_name,
                            "tool_name": tool_name,
                            "arguments": arguments,
                            "error": error_msg,
                            "duration_ms": call_duration_ms,
                            "call_time": datetime.datetime.now(),
                        }
                    )
                    tool_result = {
                        "server_name": server_name,
                        "tool_name": tool_name,
                        "error": error_msg,
                    }

                # Format result for LLM feedback (more concise)
                tool_result_for_llm = self.output_formatter.format_tool_result_for_user(
                    tool_result
                )
                # all_tool_results_content.extend(tool_result_for_llm)  # Collect all tool results
                all_tool_results_content_with_id.append((call_id, tool_result_for_llm))

            if len(tool_calls) > 1 and len(tool_calls[1]) > 0:
                tool_result = {
                    "result": f"Your tool call format was incorrect, and the tool invocation failed, error_message: {tool_calls[1][0]['error']}; please review it carefully and try calling again.",
                    "server_name": "re-think",
                    "tool_name": "re-think",
                }
                tool_calls_data.append(
                    {
                        "server_name": "",
                        "tool_name": "",
                        "arguments": "",
                        "result": tool_result,
                        "duration_ms": 0,
                        "call_time": datetime.datetime.now(),
                    }
                )
                tool_result_for_llm = self.output_formatter.format_tool_result_for_user(
                    tool_result
                )
                all_tool_results_content_with_id.append(("FAILED", tool_result_for_llm))

            # Update message history with tool calls data (llm client specific)
            message_history = self.llm_client.update_message_history(
                message_history, all_tool_results_content_with_id, tool_calls_exceeded
            )
```

三条必须钉死的结论：

1. **顺序执行（Execute tool calls in sequence）**：注释已明确写出 `Execute tool calls (in sequence)`；`for` 循环体内直接 `await` 当前调用，完成后才进入下一次迭代。标本中没有 `asyncio.gather` 或并行调度这一组调用。
2. **`max_tool_calls_per_turn` 是截断上限，不是并发度**：切片 `tool_calls[0][:max_tool_calls]` 只处理前 N 个调用；超出部分通过 `tool_calls_exceeded` 告知 history 更新逻辑。
3. **只有 `server_name.startswith("agent-")` 才进入子 Agent**：`human.ask_user` 走人工反馈分支，`agent-*` 调用 `run_sub_agent`，其余服务都交给 `main_agent_tool_manager.execute_tool_call`。

子 Agent 的 `final_answer_text` 被包装为普通 `tool_result["result"]`，再与 `call_id` 一起写回 Main 的 `message_history`。因此从 Main 的视角看，委派与普通 MCP 调用遵循同一种「调用—结果—下一轮推理」协议。

### 面试时怎么说

> Main Agent 是一个有轮次上限的 LLM—Tool 闭环。每轮 LLM 可以提出多个工具调用，但实现用 `for` 加逐个 `await` 顺序执行，并由 `max_tool_calls_per_turn` 截断前 N 个；它不是并发参数。工具名以 `agent-` 开头时，编排器把这次调用拦截为子 Agent 委派，等待 `run_sub_agent` 返回摘要，再像普通工具结果一样写回 Main history，供下一轮继续推理。

### 易踩坑

- 不要因为 LLM 一轮生成多个 tool calls，就声称执行层已经并发；标本的证据恰好相反，是 `in sequence`。
- 不要把 `max_tool_calls_per_turn` 解释成「并发 worker 数」；它只是列表切片上限。
- 不要说所有工具都可能递归创建子 Agent；只有 `agent-` 前缀分支会调用 `run_sub_agent`。
- 不要声称标本已经使用 `gather`；若简历要描述并发，需要另行实现并发调度，并处理结果顺序、共享状态和异常隔离。

**下一跳：** §5 进入 `run_sub_agent`，查看子会话怎样建立独立 history、执行自己的 LLM—Tool 循环并只向 Main 回传摘要。

## 5. 调用链精读④：`run_sub_agent`

### 5.1 建立隔离单元：新 session、新 history、自己的工具集

文件：`src/core/orchestrator.py:577-623`

```python
    async def run_sub_agent(
        self, sub_agent_name, task_description, keep_tool_result: int = -1
    ):
        """
        Run sub agent
        """
        logger.debug(f"\n=== Starting Sub Agent {sub_agent_name} ===")
        task_description += "\n\nPlease provide the answer and detailed supporting information of the subtask given to you."
        logger.debug(f"Subtask: {task_description}")

        # Start new sub-agent session
        self.task_log.start_sub_agent_session(sub_agent_name, task_description)

        # Reset sub-agent usage stats for independent tracking
        self.sub_agent_llm_client.reset_usage_stats()

        # Simplified initial user content (no file attachments)
        initial_user_content = [{"type": "text", "text": task_description}]
        message_history = [{"role": "user", "content": initial_user_content}]

        # Get sub-agent tool definitions
        tool_definitions = await self._list_sub_agent_tools()
        tool_definitions = tool_definitions.get(sub_agent_name, [])
        self.task_log.log_step(
            f"get_sub_{sub_agent_name}_tool_definitions", f"{tool_definitions}"
        )

        if not tool_definitions:
            logger.debug(
                "Warning: Failed to get any tool definitions. LLM may not be able to use tools."
            )
            self.task_log.log_step(
                f"{sub_agent_name}_no_tools",
                f"No tool definitions available for {sub_agent_name}",
                "warning",
            )

        # Generate sub-agent system prompt
        if not self.cfg.sub_agents or sub_agent_name not in self.cfg.sub_agents:
            raise ValueError(f"Sub-agent {sub_agent_name} not found in configuration")
        sub_agent_prompt_instance = _load_agent_prompt_class(
            self.cfg.sub_agents[sub_agent_name].prompt_class
        )
        system_prompt = sub_agent_prompt_instance.generate_system_prompt_with_mcp_tools(
            mcp_servers=tool_definitions,
            chinese_context=self.chinese_context,
        )
```

这里的隔离不是只换一个名字，而是至少包含四层：调用 `start_sub_agent_session` 建立独立 session、重置 Sub LLM 用量统计、从任务描述新建 `message_history`、按 `sub_agent_name` 选择该角色自己的工具定义与 prompt。它没有把 Main 的完整 history 复制进来。

### 5.2 子循环：与 Main 同构，但工具执行器属于 Sub

文件：`src/core/orchestrator.py:625-804`

```python
        # Limit sub-agent turns
        max_turns = self.cfg.sub_agents[sub_agent_name].max_turns
        if max_turns < 0:
            max_turns = sys.maxsize
        turn_count = 0
        all_tool_results_content_with_id = []
        task_failed = False  # Track whether task failed

        while turn_count < max_turns:
            turn_count += 1
            logger.debug(f"\n--- Sub Agent {sub_agent_name} Turn {turn_count} ---")
            self.task_log.save()

            # Use unified LLM call handling
            (
                assistant_response_text,
                should_break,
                tool_calls,
            ) = await self._handle_llm_call_with_logging(
                system_prompt,
                message_history,
                tool_definitions,
                turn_count,
                f"Sub agent {sub_agent_name} turn {turn_count}",
                keep_tool_result=keep_tool_result,
                agent_type=sub_agent_name,
            )

            # Handle LLM response
            if assistant_response_text:
                if should_break:
                    self.task_log.log_step(
                        "sub_agent_early_termination",
                        f"Sub agent {sub_agent_name} terminated early on turn {turn_count}",
                    )
                    break
            else:
                # LLM call failed, mark task as failed and end current turn
                if tool_calls == "context_limit":
                    # Context limit exceeded situation
                    self.task_log.log_step(
                        "sub_agent_context_limit_reached",
                        f"Sub agent {sub_agent_name} context limit reached, jumping to summary",
                        "warning",
                    )
                else:
                    # Other LLM call failure situations
                    self.task_log.log_step(
                        "sub_agent_llm_call_failed",
                        "LLM call failed",
                        "failed",
                    )
                task_failed = True  # Mark task as failed
                break

            # Use tool calls parsed from LLM response
            if (
                tool_calls is None
                or len(tool_calls) < 2
                or (len(tool_calls[0]) == 0 and len(tool_calls[1]) == 0)
            ):
                logger.debug(
                    f"Sub Agent {sub_agent_name} did not request tool use, ending task."
                )
                self.task_log.log_step(
                    "sub_agent_no_tool_calls",
                    f"No tool calls found in sub agent {sub_agent_name}, ending on turn {turn_count}",
                )
                break

            # Execute tool calls
            tool_calls_data = []
            all_tool_results_content_with_id = []

            # Get maximum tool calls per turn from configuration
            max_tool_calls = self.cfg.sub_agents[sub_agent_name].max_tool_calls_per_turn
            tool_calls_exceeded = (
                len(tool_calls) > 0 and len(tool_calls[0]) > max_tool_calls
            )
            if tool_calls_exceeded:
                logger.warning(
                    f"[ERROR] Sub agent single turn tool call count too high ({len(tool_calls[0])} calls), only processing first {max_tool_calls}"
                )

            for call in tool_calls[0][:max_tool_calls]:
                # This place can be used to inject arguments of tools
                server_name = call["server_name"]
                tool_name = call["tool_name"]
                arguments = call["arguments"]
                call_id = call["id"]

                self.task_log.log_step(
                    "sub_agent_tool_call_start",
                    f"Executing {tool_name} on {server_name}",
                )

                call_start_time = time.time()
                try:
                    tool_result = await self.sub_agent_tool_managers[
                        sub_agent_name
                    ].execute_tool_call(server_name, tool_name, arguments)

                    call_end_time = time.time()
                    call_duration_ms = int((call_end_time - call_start_time) * 1000)

                    self.task_log.log_step(
                        "sub_agent_tool_call_success",
                        f"Tool {tool_name} executed successfully in {call_duration_ms}ms",
                    )

                    tool_calls_data.append(
                        {
                            "server_name": server_name,
                            "tool_name": tool_name,
                            "arguments": arguments,
                            "result": tool_result,
                            "duration_ms": call_duration_ms,
                            "call_time": datetime.datetime.now(),
                        }
                    )
                    self._log_hybrid_observability(tool_result, f"sub:{sub_agent_name}")

                except Exception as e:
                    call_end_time = time.time()
                    call_duration_ms = int((call_end_time - call_start_time) * 1000)

                    # Handle empty error messages, especially for TimeoutError
                    error_msg = str(e) or (
                        "[ERROR]: Tool execution timeout"
                        if isinstance(e, TimeoutError)
                        else f"Tool execution failed: {type(e).__name__}"
                    )

                    tool_calls_data.append(
                        {
                            "server_name": server_name,
                            "tool_name": tool_name,
                            "arguments": arguments,
                            "error": error_msg,
                            "duration_ms": call_duration_ms,
                            "call_time": datetime.datetime.now(),
                        }
                    )
                    tool_result = {
                        "error": f"Tool call failed: {error_msg}",
                        "server_name": server_name,
                        "tool_name": tool_name,
                    }

                tool_result_for_llm = self.output_formatter.format_tool_result_for_user(
                    tool_result
                )
                logger.debug(f"Tool result: {tool_result}")

                all_tool_results_content_with_id.append((call_id, tool_result_for_llm))

            if len(tool_calls) > 1 and len(tool_calls[1]) > 0:
                tool_result = {
                    "result": f"Your tool call format was incorrect, and the tool invocation failed, error_message: {tool_calls[1][0]['error']}; please review it carefully and try calling again.",
                    "server_name": "re-think",
                    "tool_name": "re-think",
                }
                tool_calls_data.append(
                    {
                        "server_name": "",
                        "tool_name": "",
                        "arguments": "",
                        "result": tool_result,
                        "duration_ms": 0,
                        "call_time": datetime.datetime.now(),
                    }
                )
                tool_result_for_llm = self.output_formatter.format_tool_result_for_user(
                    tool_result
                )
                all_tool_results_content_with_id.append(("FAILED", tool_result_for_llm))

            message_history = self.sub_agent_llm_client.update_message_history(
                message_history, all_tool_results_content_with_id, tool_calls_exceeded
            )
```

Sub 与 Main 的循环骨架同构：都有 `max_turns`、统一 LLM 调用、退出判断、工具调用截断、异常转工具结果和 history 回写。关键差异是工具集来自 `_list_sub_agent_tools()` 按名称筛选，执行则通过 `self.sub_agent_tool_managers[sub_agent_name]`，不会借用 Main 的 ToolManager。

### 5.3 即使失败或耗尽轮次，也尝试生成最终摘要

文件：`src/core/orchestrator.py:806-861`

```python
        # Continue execution
        logger.debug(
            f"\n=== Sub Agent {sub_agent_name} Completed ({turn_count} turns) ==="
        )

        # Record browser agent loop end
        if turn_count >= max_turns:
            if (
                not task_failed
            ):  # If not yet marked as failed and due to turn limit exceeded
                task_failed = True
            self.task_log.log_step(
                "sub_agent_max_turns_reached",
                f"Sub agent {sub_agent_name} reached maximum turns ({max_turns})",
                "warning",
            )

        else:
            self.task_log.log_step(
                "sub_agent_loop_completed",
                f"Sub agent {sub_agent_name} loop completed after {turn_count} turns",
            )

        # Final summary - following main agent process
        self.task_log.log_step(
            "sub_agent_final_summary",
            f"Generating sub agent {sub_agent_name} final summary",
        )

        # Use context limit retry logic to generate final summary
        final_answer_text = await self._handle_summary_with_context_limit_retry(
            system_prompt,
            sub_agent_prompt_instance,
            message_history,
            tool_definitions,
            f"Sub agent {sub_agent_name} final summary",
            task_description,
            task_failed,
            agent_type=sub_agent_name,
        )

        if final_answer_text:
            self.task_log.log_step(
                "sub_agent_final_answer",
                f"Sub agent {sub_agent_name} final answer generated successfully",
            )

        else:
            final_answer_text = (
                f"No final answer generated by sub agent {sub_agent_name}."
            )
            self.task_log.log_step(
                "sub_agent_final_answer",
                f"Failed to generate sub agent {sub_agent_name} final answer",
                "failed",
            )
```

`task_failed` 不是「立即跳过总结」开关。上下文超限、LLM 调用失败或 `max_turns` 耗尽会先结束子循环，但控制流仍进入 `sub_agent_final_summary`，调用 `_handle_summary_with_context_limit_retry`；该函数接收失败标记和现有 history，尽力把已经获得的信息压缩为可回传结果。

### 5.4 持久化隔离 history，结束 session，只返回摘要文本

文件：`src/core/orchestrator.py:863-884`

```python
        logger.debug(f"Sub Agent {sub_agent_name} Final Answer: {final_answer_text}")

        self.task_log.sub_agent_message_history_sessions[
            self.task_log.current_sub_agent_session_id
        ] = {"system_prompt": system_prompt, "message_history": message_history}  # type: ignore
        self.task_log.save()

        # Record sub-agent cumulative usage
        usage_log = self.sub_agent_llm_client.get_usage_log()
        self.task_log.log_step(
            "usage_calculation",
            usage_log,
            metadata={"session_id": self.task_log.current_sub_agent_session_id},
        )

        self.task_log.end_sub_agent_session(sub_agent_name)
        self.task_log.log_step(
            "sub_agent_completed", f"Sub agent {sub_agent_name} completed", "info"
        )

        # Return final answer instead of dialogue log, so main agent can use directly
        return final_answer_text
```

Sub 的完整对话保存在 `sub_agent_message_history_sessions[session_id]`，便于追踪和审计；函数边界却只 `return final_answer_text`。Main 收到的是 summary 文本，不是 Sub 的完整消息历史、原始工具日志或共享可变 history。

### 5.5 `session_id` 的生成规则

文件：`src/logging/task_tracer.py:68-84`

```python
    def start_sub_agent_session(
        self, sub_agent_name: str, subtask_description: str
    ) -> str:
        """Start a new sub-agent session"""
        self.sub_agent_counter += 1
        session_id = f"{sub_agent_name}_{self.sub_agent_counter}"
        self.current_sub_agent_session_id = session_id

        # record sub-agent session start
        self.log_step(
            f"sub_{sub_agent_name}_session_start",
            f"Starting {session_id} for subtask: {subtask_description[:100]}{'...' if len(subtask_description) > 100 else ''}",
            "info",
            metadata={"session_id": session_id, "subtask": subtask_description},
        )

        return session_id
```

规则是「`sub_agent_name` + 下划线 + 任务内递增计数器」，例如 `agent-worker_1`、`agent-worker_2`。计数器先自增，再更新 `current_sub_agent_session_id`，并把 session ID 与完整 subtask 写入日志 metadata。

### 隔离与信息传递的边界

1. **隔离单元**：每次委派都有独立 session、从零创建的 Sub `message_history`、角色专属 prompt/tool definitions、独立用量统计；完整记录按 session 保存。
2. **回传契约**：`run_sub_agent` 返回的是 `final_answer_text` 摘要，Main 把它当成一次普通工具调用结果写回自己的 history。
3. **信息缺失的解决方式**：因为 Sub 不继承 Main 全历史，Main 必须在 `subtask` 中写全必要背景、目标、输入、约束和期望输出；正确方向不是把 Main 的全部 history 无差别塞给 Sub，否则会破坏隔离、扩大上下文并引入无关信息。

### 面试时怎么说

> `run_sub_agent` 是一个完整但隔离的 Agent 运行时：它新建 session 和 message history，加载角色专属 prompt 与工具集，再运行与 Main 同构的 LLM—Tool 循环。即使达到轮次上限或中途失败，也会基于已有 history 尝试做 final summary。完整子对话按 session 落盘用于审计，但回给 Main 的只有摘要文本，所以委派边界清晰、上下文可控。

### 易踩坑

- 不要说 Sub 继承 Main 全部 history；源码从 `task_description` 新建单条 user message。
- 不要把 `sub_agent_message_history_sessions` 说成 Main 的推理输入；它是按 session 持久化的追踪记录。
- 不要说失败就没有输出；失败标记会传给 summary 逻辑，仍会尝试整理已有结果。
- 不要把摘要回传误说成原始工具结果透传；函数注释明确写着返回 final answer，而不是 dialogue log。

## 6. 调用链精读⑤：主 Agent final summary

### 6.1 主循环结束后统一进入总结阶段

文件：`src/core/orchestrator.py:1227-1258`

```python
        # Record main loop end
        if turn_count >= max_turns:
            if (
                not task_failed
            ):  # If not yet marked as failed and due to turn limit exceeded
                task_failed = True
            self.task_log.log_step(
                "max_turns_reached",
                f"Reached maximum turns ({max_turns})",
                "warning",
            )

        else:
            self.task_log.log_step(
                "main_loop_completed", f"Main loop completed after {turn_count} turns"
            )

        # Final summary
        self.task_log.log_step("final_summary", "Generating final summary")

        # Use context limit retry logic to generate final summary
        final_answer_text = await self._handle_summary_with_context_limit_retry(
            system_prompt,
            main_agent_prompt_instance,
            message_history,
            tool_definitions,
            "Final summary generation",
            task_description,
            task_failed,
            agent_type="main",
            task_guidence=task_guidence,
        )
```

主循环可能因为模型主动停止、无工具调用、LLM 调用失败、上下文超限或达到 `max_turns` 而结束，但这些出口最终都会汇合到 `_handle_summary_with_context_limit_retry`。如果达到轮次上限，代码先把 `task_failed` 置为 `True`；如果循环内 LLM 调用失败，也已设置该标记。它不是「失败后跳过 summary」的开关，而是传入总结 Prompt 的状态，使模型基于已有 `message_history` 尽力给出带失败语境的最终答案。这与 §5.3 的 Sub Agent 处理方式对称。

### 6.2 输出契约：自然语言报告，而非已强校验的 JSON

标本中的 `final_answer_text` 是 LLM 生成的**自然语言 summary**。工程上希望最终报告具备「结论、证据、缺口、不确定性」等逻辑结构，方便 Main 把多个 Sub Agent 的结果综合为可解释答案；但这是一项输出质量关注点，不等于代码已经落地 JSON schema 强校验。

因此，遇到 summary 质量不足时，合理的编排动作是：

1. **重派**：原子任务定义不清或执行方向错误时，改写 `subtask` 后重新委派。
2. **补证**：结论缺少来源或证据冲突时，追加定向检索、阅读或验证任务。
3. **降置信**：预算耗尽、关键证据缺失或冲突无法消解时，在最终答案中显式保留缺口与不确定性。

标本未展示一个对 summary 自动打分并据分数触发上述动作的质量评估器；这些动作应由 Main 根据任务状态、证据完整性和预算作出决策，不能说成已有自动评分闭环。

### 面试时怎么说

> Main Agent 不直接把最后一轮回复当最终答案，而是在主循环结束后统一调用 `_handle_summary_with_context_limit_retry`，优先基于完整主 history 生成 summary；若触发上下文超限重试，则会裁剪近期对话后再生成，并不保证始终保留完整 history。即使 LLM 调用失败或达到 `max_turns`，也会把 `task_failed` 传入总结逻辑，尽量保留已有成果。我们关注结论、证据、缺口和不确定性的逻辑结构，但标本没有 JSON schema 强校验或自动质量打分器；质量不足时采用重派、补证或降置信。

### 易踩坑

- 不要说 `task_failed=True` 就直接返回错误；控制流仍会进入 final summary。
- 不要把「结构化表达」等同于「返回 JSON」；标本产物是自然语言文本。
- 不要声称已有自动 summary 打分器；能确认的是总结生成与上下文超限重试路径。
- 不要把 Main summary 与 Sub summary 混为一次调用：Sub 先返回摘要作为工具结果，Main 再基于主 history 做总汇总。

## 7. 预算与熔断

### 7.1 标本配置：Main 20/10，Sub worker 50/10

以下数字来自 `config/agent_llm_qwen37plus.yaml`，用于复习标本控制流，不代表未经实测即可照搬的线上最优参数。

| Agent | `max_turns` | `max_tool_calls_per_turn` | 标本含义 |
|------|------------:|--------------------------:|----------|
| Main Agent | 20 | 10 | 最多进行 20 轮主决策；每轮最多执行前 10 个工具调用 |
| Sub `agent-worker` | 50 | 10 | 最多进行 50 轮子任务决策；每轮最多执行前 10 个工具调用 |

### 7.2 第一层预算：`max_turns` 限制循环深度

Main 与 Sub 使用同一种循环条件；区别只是从各自配置读取上限。以 Main 为例：

```python
        max_turns = self.cfg.main_agent.max_turns
        if max_turns < 0:
            max_turns = sys.maxsize
        turn_count = 0
        task_failed = False  # Track whether task failed
        while turn_count < max_turns:
            turn_count += 1
```

当 `turn_count` 达到上限后，不再进入下一轮 LLM—Tool 决策。循环结束处会记录告警、设置 `task_failed`，随后仍进入 §6 的 final summary。它限制的是会话纵向推进深度，避免 Agent 无休止地「思考—调用—再思考」。

### 7.3 第二层预算：`tool_calls_exceeded` 截断单轮调用数

Main 与 Sub 也都按自己的 `max_tool_calls_per_turn` 对本轮工具调用切片。以 Main 为例：

```python
            max_tool_calls = self.cfg.main_agent.max_tool_calls_per_turn
            tool_calls_exceeded = (
                len(tool_calls) > 0 and len(tool_calls[0]) > max_tool_calls
            )
            if tool_calls_exceeded:
                logger.warning(
                    f"[ERROR] Single turn tool call count too high ({len(tool_calls[0])} calls), only processing first {max_tool_calls}"
                )

            for call in tool_calls[0][:max_tool_calls]:
                # Execute only the first max_tool_calls entries
                ...

            message_history = self.llm_client.update_message_history(
                message_history, all_tool_results_content_with_id, tool_calls_exceeded
            )
```

这里不是先执行全部调用再统计，而是只处理 `[:max_tool_calls]` 的前 N 个，并把 `tool_calls_exceeded` 传给 history 更新逻辑，让后续推理知道本轮发生了截断。

### 7.4 两道预算的含义不能混用

| 维度 | `max_turns` | `max_tool_calls_per_turn` |
|------|-------------|---------------------------|
| 控制对象 | 整个 Agent 会话的循环轮数 | 单轮 LLM 响应中的工具调用数量 |
| 防护风险 | 无限循环、上下文持续膨胀、累计成本失控 | 单轮调用爆炸、瞬时成本和延迟过高 |
| 触发结果 | 停止循环，标记失败语境，再尝试 summary | 截断为前 N 个，记录超限并继续后续轮次 |
| 不代表 | 工具调用总量的精确硬上限 | 并发数、worker 数或全任务总调用数 |

两层约束组合后，理论执行量仍不能简单当作严格的 `max_turns × max_tool_calls_per_turn` 成本承诺：每轮可能提前结束，Sub Agent 内还有自己的循环与工具调用，LLM 重试、summary 和人工交互也会产生额外开销。线上还应结合 token、金额、墙钟时间、重试次数和全链路调用总数设置更完整的预算熔断。

完整的预算追问 G23 仍见 [`02-面试问答.md`](./02-面试问答.md)；本文只解释 Main–Sub 编排直接相关的轮次与单轮工具调用限制。

### 面试时怎么说

> 这套编排有两道基础预算：`max_turns` 控制 Agent 循环深度，`max_tool_calls_per_turn` 控制单轮工具调用数，超出的调用只取前 N 个。标本配置是 Main 20/10、Sub worker 50/10，但这是 GAIA 复习标本参数，不是未经压测就能宣称的线上最优；生产值要根据任务完成率、P95 延迟、token 与工具成本、超限率共同调优，并补充全链路预算。

### 易踩坑

- 不要把 `10` 说成「同时并发 10 个子 Agent」；标本工具循环仍是顺序执行。
- 不要把 `20 × 10` 说成整个任务绝不会超过 200 次工具调用；一次 Main 委派会进入 Sub 自己的预算域。
- 不要说达到 `max_turns` 后完全无输出；实现仍尝试 final summary。
- 不要把标本参数包装成线上最佳实践；缺少业务压测和成本数据时，只能称为配置示例。

## 8. 专节：顺序执行 vs 简历「并发」

### 8.1 标本证据：单题内顺序调度

`src/core/orchestrator.py:1110-1150` 对 Main Agent 一轮内的 tool call 调度写得很直接：

```python
            # 7. Execute tool calls (in sequence)
            tool_calls_data = []
            all_tool_results_content_with_id = []

            max_tool_calls = self.cfg.main_agent.max_tool_calls_per_turn
            tool_calls_exceeded = (
                len(tool_calls) > 0 and len(tool_calls[0]) > max_tool_calls
            )

            for call in tool_calls[0][:max_tool_calls]:
                server_name = call["server_name"]
                tool_name = call["tool_name"]
                arguments = call["arguments"]

                if server_name == "human" and tool_name == "ask_user":
                    tool_result = await self._ask_user_tool(arguments)
                elif server_name.startswith("agent-"):
                    sub_agent_result = await self.run_sub_agent(
                        server_name, str(arguments), keep_tool_result
                    )
                else:
                    tool_result = (
                        await self.main_agent_tool_manager.execute_tool_call(
                            server_name=server_name,
                            tool_name=tool_name,
                            arguments=arguments,
                        )
                    )
```

这里要区分「生成」和「执行」：LLM 一轮可以提出多个 tool call，但执行器进入 `for` 循环后，会对当前调用直接 `await`；当前工具或子 Agent 返回后，才进入下一次迭代。因此，当前可核对标本的**单题内调用是顺序调度**，`max_tool_calls_per_turn` 也只是截断上限，不是并发度。

### 8.2 对比：多题并行不是单题内并行

`common_benchmark.py:369-393` 的 `run_parallel_inference` 确实使用了 `Semaphore + gather(return_exceptions=True)`：

```python
    async def run_parallel_inference(
        self, tasks: List[BenchmarkTask], max_concurrent: int = 3
    ) -> List[BenchmarkResult]:
        """Run inference on multiple tasks in parallel"""
        print(
            f"Running inference on {len(tasks)} tasks with max_concurrent={max_concurrent}"
        )

        semaphore = asyncio.Semaphore(max_concurrent)

        async def run_with_semaphore(task):
            async with semaphore:
                with task_logging_context(task.task_id, self.get_log_dir()):
                    result = await self.run_single_task(task)
                return result

        shuffled_tasks = tasks.copy()
        random.shuffle(shuffled_tasks)

        results = await asyncio.gather(
            *[run_with_semaphore(task) for task in shuffled_tasks],
            return_exceptions=True,
        )
```

但并行单元是 `tasks` 列表中的**多道 benchmark 题目**：每道题调用一次 `run_single_task`，`max_concurrent` 限制同时运行的题目数，`return_exceptions=True` 防止一道题异常直接取消整批任务。它不能证明某一道题内部同时运行了多个子 Agent。

换句话说，两处代码控制的是不同层级：

- **单题内：** `orchestrator.py` 对一轮 tool call / 子 Agent 调用逐个 `await`，当前是顺序调度。
- **多题间：** `common_benchmark.py` 用 `Semaphore` 控制题目级并发，再用 `gather` 汇总结果。

并发追问 G22 的详答仍放在 [`02-面试问答.md`](./02-面试问答.md)；未来若补 G 专项，也应继续保持「单题内调度」与「评测多题吞吐」两个层级的区分。

### 8.3 简历口径模板（可背）

> 主 Agent 动态拆子任务；子任务在独立会话执行并回传摘要。当前可核对实现里，单题内 tool call / 子 Agent 调用是顺序调度；架构上可以把无依赖子任务并行化，但需要单独配置全局并发、超时和异常隔离。评测里的 `max_concurrent` 是多题并行，不是单题内同时跑 N 个子 Agent。

如果面试官继续追问「简历为什么写并发」，可以补一句：

> 我描述的是 Main–Sub 架构对无依赖子任务的并行化能力与演进方向，不是把当前标本的顺序 `for + await` 说成已并行落地；已落地的 `Semaphore + gather` 位于 benchmark 多题执行层。

### 8.4 可选演进（未在标本落地）

下面只是单题内无依赖调用并行化的伪代码草图，**未在标本落地，本准备文档也不修改业务代码**：

```python
async def execute_independent_calls(calls, max_concurrent):
    semaphore = asyncio.Semaphore(max_concurrent)

    async def run_one(call):
        async with semaphore:
            try:
                return await asyncio.wait_for(
                    dispatch_tool_or_sub_agent(call),
                    timeout=PER_CALL_TIMEOUT,
                )
            except Exception as exc:
                return ToolCallFailure(call_id=call["id"], error=str(exc))

    results = await asyncio.gather(
        *(run_one(call) for call in calls),
        return_exceptions=False,
    )
    return reorder_by_original_call_id(results)
```

真正落地前还要先做依赖分析：只有无依赖、无共享可变状态冲突的调用才能进入同一批次；同时要补全全局并发上限、单调用超时、异常隔离、结果顺序恢复、取消传播、日志关联和预算统计。否则，机械地把现有循环替换成 `asyncio.gather`，可能造成限流失效、历史顺序错乱或一个失败拖累整批调用。

## 9. 面试题索引（E13–E16）

（任务 6 填充）

## 10. 回看清单

（任务 6 填充）
