# Hybrid Search + MCP — 代码精读与面试深挖

> 对应简历：问数结果深度研究 · Hybrid Search / MCP
> 题纲：[`../面试题纲.md`](../面试题纲.md) § 三 F17–F20
> 索引本：[`02-面试问答.md`](./02-面试问答.md)（F 节已迁出至本文）
> 上一章：[`03-Main-Sub-Agent编排.md`](./03-Main-Sub-Agent编排.md)
> 设计规格：[`../../superpowers/specs/2026-08-06-hybrid-search-and-engineering-interview-prep-design.md`](../../superpowers/specs/2026-08-06-hybrid-search-and-engineering-interview-prep-design.md)
> 复习标本：`miro-flow-solution`（对齐工程细节；面试不主动对比 MiroFlow，不宣称「我发明框架」）

---

## 1. 与上一章的关系 + 本章地图 + 诚实边界

### 1.1 与 `03` 的衔接

[`03`](./03-Main-Sub-Agent编排.md) 已讲 Main–Sub 编排主循环：LLM 产出 tool call 后，**普通 MCP** 走 `ToolManager.execute_tool_call`；**`agent-*` 伪工具** 走 `run_sub_agent`，Sub 内部再用各自的 `sub_agent_tool_managers[name]` 调真 MCP。

本章从 **`03` 第 ⑥a 步往下钻**：工具怎么注册进系统、怎么被 LLM 发现、怎么执行、失败怎么降级——然后再讲 **Hybrid Search 这一把 MCP 工具**的特点（§3）、业务知识库与案例（§4）。

**不在本章展开：**

- `agent-*` 伪工具的 expose / 委派 / 子会话隔离（归 [`03` §2–§3](./03-Main-Sub-Agent编排.md#2-配置与装配入口)）
- 全链路追踪、预算熔断、断点续跑（归 [`05-工程化能力.md`](./05-工程化能力.md)）

### 1.2 本章地图

| 章 | 内容 | 题纲 |
|----|------|------|
| **§1** | 与 `03` 衔接 + 诚实边界 | — |
| **§2** | 工具注册 / 发现 / 调用 / 降级；98% 定义 | F18（部分） |
| **§3** | Hybrid Search：路由 → 召回 → 融合 → MCP 返回 → 证据链与引用 | F17、F18（检索侧） |
| **§4** | 业务知识库（访谈 + 清洗研报）+ 金融 / 行为科学案例 | F19、F20 |
| **§5** | 面试题索引 F17–F20 + 回看清单 | F17–F20 |

阅读顺序：**先 §2 通用 harness，再 §3 Hybrid 特例**——面试被追问「98% 怎么来的」时，先答工具层定义与降级，再落到 Hybrid 路由与融合。

### 1.3 诚实边界总表

| 说法 | 可讲 | 不可讲 |
|------|------|--------|
| **98%** | 单次 MCP 工具调用返回可解析、非空、可被 Agent 继续消费的有效结果 | 任务成功率 / 答案准确率 / GAIA 通过率 |
| **路由** | 关键词 hints + 强制 `mode` + 无本地索引时降级 web | 「已是语义理解路由 / 已上线学习型路由」（无依据时） |
| **权重 0.6 / 0.4** | 标本默认基线，归一化后加权排序 | 业务最优参数 |
| **向量** | `VectorBackend` 接口存在，当前回退本地索引 | 生产向量库已完整落地 |
| **知识库** | 经授权的访谈材料 + 清洗后的研报；每块保留来源 / chunk id | 虚构库规模 / 向量条数 |
| **引用** | `SearchHit` 字段 + Prompt / ResearchDirective 约束摘录与标强度 | 代码级引用 schema 强校验已落地 |
| **归属** | 工程 harness owner；标本对齐细节 | 「我发明了这套 MCP / 检索框架」 |

---

## 2. 工具如何注册、发现、调用与降级

### 2.1 前置条件

读到这里应已知（来自 [`03` §1–§2](./03-Main-Sub-Agent编排.md#1-架构总览)）：

1. `create_pipeline_components` 为 Main / 各 Sub 各建独立 `ToolManager`（真 MCP 执行器）。
2. `run_main_agent` 主循环里，LLM 选普通 MCP → `main_agent_tool_manager.execute_tool_call(...)`；选 `agent-*` → `run_sub_agent`，Sub 内走 `sub_agent_tool_managers[...].execute_tool_call(...)`。
3. `get_all_tool_definitions()` 在主循环**之前**拉真 MCP 工具目录，再与 `agent-*` 假工具合并成 `tool_definitions`。

### 2.2 注册：`tool-*.yaml` → Agent `tool_config`

**配置挂载：** Agent YAML（Main 或 Sub）的 `tool_config` 列表引用 `config/tool/{name}.yaml`；`create_mcp_server_parameters` 逐条加载并转成 `StdioServerParameters`（或 SSE URL），供 `ToolManager` 初始化。

```yaml
# config/tool/tool-hybrid-search.yaml（关键字段）
name: "tool-hybrid-search"
tool_command: "python"
args:
  - "-m"
  - "src.tool.mcp_servers.hybrid_search_mcp_server"
env:
  SERPER_API_KEY: "${oc.env:SERPER_API_KEY,}"
  RETRIEVAL_INDEX_DIR: "${oc.env:RETRIEVAL_INDEX_DIR,./data/retrieval_indexes}"
  RETRIEVAL_MODE: "${oc.env:RETRIEVAL_MODE,auto}"
  RETRIEVAL_LOCAL_WEIGHT: "${oc.env:RETRIEVAL_LOCAL_WEIGHT,0.6}"
  RETRIEVAL_WEB_WEIGHT: "${oc.env:RETRIEVAL_WEB_WEIGHT,0.4}"
```

```yaml
# config/agent_server.yaml（业务侧 Main 挂载示例）
main_agent:
  tool_config:
    - tool-reading
    - tool-hybrid-search
    - tool-searching
  retrieval:
    mode: "${oc.env:RETRIEVAL_MODE,auto}"
    router:
      local_weight: 0.6
      web_weight: 0.4
```

```python
# src/utils/tool_utils.py · create_mcp_server_parameters（L21–57，节选）
for tool in agent_cfg["tool_config"]:
    config_path = ... / "config" / "tool" / f"{tool}.yaml"
    tool_cfg = OmegaConf.load(config_path)
    tool_env = OmegaConf.to_container(tool_cfg.get("env", {}), resolve=True) or {}
    if tool_cfg.get("name", tool) == "tool-hybrid-search":
        retrieval_cfg = agent_cfg.get("retrieval", {})
        tool_env["RETRIEVAL_MODE"] = str(retrieval_cfg.get("mode", "auto"))
    configs.append({
        "name": tool_cfg.get("name", tool),
        "params": StdioServerParameters(command=..., args=..., env=tool_env),
    })
```

旁注：

- **一条 yaml = 一个 MCP Server 注册项**：Agent `tool_config` 引用后，由 `create_mcp_server_parameters` 加载，`ToolManager` 按配置拉起或连接对应 MCP。**stdio 子进程**是标本常见形态（如 `tool-hybrid-search.yaml` 的 `tool_command` + `args`）；若 yaml 配的是远程 URL / SSE，则走网络连接而非本地 stdio 进程——面试以实际 tool yaml 的 `command` / `url` 字段为准。`name` 即 LLM 调用时的 `server_name`。
- Hybrid Search 额外把 Agent 级 `retrieval.mode` 注入子进程环境，与 §3 路由对齐。
- Main / Sub **各自** `tool_config` + `tool_blacklist` → 各自 `ToolManager`，工具面可不同（GAIA 标本 Sub 挂 searching/reading/code，业务 `agent_server` Main 挂 hybrid-search）。

### 2.3 发现：`get_all_tool_definitions`

```python
# src/tool/manager.py · get_all_tool_definitions（L171–252，骨架）
async def get_all_tool_definitions(self):
    for config in self.server_configs:
        server_name, server_params = config["name"], config["params"]
        async with stdio_client(...) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_response = await session.list_tools()
                for tool in tools_response.tools:
                    if (server_name, tool.name) in self.tool_blacklist:
                        continue
                    one_server_for_prompt["tools"].append({
                        "name": tool.name,
                        "description": tool.description,
                        "schema": tool.inputSchema,
                    })
    return all_servers_for_prompt
```

旁注：

- **发现 = 连上每个已注册 Server，调 MCP `list_tools`**，不是静态读 yaml。
- 某 Server 连不上时仍占位，tools 里写 `{"error": "Failed to fetch tools: ..."}`（L242–250），避免整表缺失。
- 调用点：`orchestrator.py` L995（Main 主循环前）；Sub 侧在 `run_sub_agent` 内对对应 `ToolManager` 同样拉目录。

### 2.4 调用：`execute_tool_call` 统一入口

```python
# src/tool/manager.py
@with_timeout(900)                                    # L254：单次调用 asyncio 超时 900s
async def execute_tool_call(self, server_name, tool_name, arguments) -> Any:  # L255
    server_params = self.get_server_params(server_name)
    if not server_params:
        suggested_servers = await self._find_servers_with_tool(tool_name)  # L272
        if len(suggested_servers) == 1:
            # ↓ Server 名纠错（L276–307）
            return await self.execute_tool_call(correct_server, tool_name, arguments)
        return {"error": error_message, ...}

    # playwright 特例（L327–357）；其余 stdio / SSE：
    async with stdio_client(...) as ...:
        tool_result = await session.call_tool(tool_name, arguments=arguments)  # L370
        # ↓ 空内容处理（L374–392）
        ...
    if "Unknown tool:" in result_content:               # L456–467：tool 名纠错
        if len(suggested_servers) == 1:
            return await self.execute_tool_call(suggested_servers[0], tool_name, arguments)
    return {"server_name": ..., "tool_name": ..., "result": result_content}
```

**Orchestrator 调用点（Main 侧）：**

```python
# src/core/orchestrator.py · run_main_agent 主循环内（约 L1143–1149）
tool_result = await self.main_agent_tool_manager.execute_tool_call(
    server_name=server_name,
    tool_name=tool_name,
    arguments=arguments,
)
```

旁注：

- 返回值统一为 `dict`，含 `result` 或 `error`；Orchestrator 写回 message history 供下一轮 LLM 消费。
- **`@with_timeout(900)`** 是工具层硬超时；与任务级 14min `wait_for`、预算熔断（见 `05`）是不同层级。

### 2.5 降级分支（关键路径）

| 场景 | 代码锚点 | 行为 |
|------|----------|------|
| **调用超时** | L254 `@with_timeout(900)` | `asyncio.wait_for` 超时 → 外层 `except` → 返回 `{"error": "Tool call failed: ..."}` |
| **Server 名写错、全局唯一** | L276–307 | `_find_servers_with_tool` 只命中 1 个 Server → 递归 `execute_tool_call` 并附 `[Auto-corrected: ...]` 注记 |
| **Tool 名在该 Server 不存在、全局唯一** | L456–467 | 响应含 `Unknown tool:` → 换唯一正确 Server 重试 |
| **返回空 / 无 text** | L336–345（playwright）；L374–392、L417–435（stdio/SSE） | 不抛异常；返回说明性 `result` 字符串，让 LLM 决定换工具或继续 |
| **scrape 失败 → MarkItDown** | L485–510 | `tool_name == "scrape"` 且错误含 `unhandled errors` → `MarkItDown.convert(url)` 备用读取 |

```python
# 空内容（stdio，L374–386）
if tool_result.content and len(tool_result.content) > 0:
    text_content = tool_result.content[-1].text
    if text_content is not None and text_content.strip():
        result_content = text_content
    else:
        result_content = f"Tool '{tool_name}' completed but returned empty text - ..."
else:
    result_content = f"Tool '{tool_name}' completed but returned no content - ..."
```

```python
# MarkItDown 备用读取（L485–504）
if tool_name == "scrape" and "unhandled errors" in error_message and arguments.get("url"):
    from markitdown import MarkItDown
    result = MarkItDown(...).convert(arguments["url"])
    return {"result": result.text_content, ...}
```

旁注：

- Server / Tool **名纠错**只在「全局唯一命中」时自动改；多 Server 同名 tool 时只提示、不猜。
- 空结果**不等于**调用失败——对 delete 类工具可能正常；98% 统计时通常不把「可解析但空且 LLM 无法继续」算作有效成功。
- MarkItDown 是 **reading/scrape 链** 的备用，不是 Hybrid Search 主路径；面试可举例说明「多源读取降级」，勿说成 Hybrid 内置能力。

### 2.6 MCP 成功率 98%：定义与可背降级顺序

**定义（钉死）：**

> **98%** = 单次 MCP 工具调用返回 **可解析、非空、可被 Agent 继续消费** 的有效结果。  
> ≠ 深度研究任务成功率 ≠ 最终答案准确率 ≠ GAIA 通过率。

口径来源：[`02` L0](./02-面试问答.md#03-硬指标) + 规格 §5.2；实现侧以 `execute_tool_call` 返回的 `result` 能否进入下一轮 LLM 为准，而非「子进程启动成功」。

**工具层降级顺序（可背三级）：**

1. **同工具限次重试或名纠错** — Server/Tool 唯一命中时 harness 自动纠正（§2.5）；超时 / 空结果 / 异常返回会显式写回 message history，由 LLM 换参数再调。**标本未见单独配置成固定 `retry=N` 的计数器**——「限次」是 harness 纠错 + LLM 再调的组合口径，不要暗示硬编码重试次数。
2. **备选工具 / 来源** — 如 scrape 失败走 MarkItDown；Hybrid 一路失败仍可用另一路（§3）。
3. **基于已有证据部分完成** — Sub/Main Prompt 要求声明缺口；不因单步失败丢弃已验证片段。

**产品层回退（与工具层分开记）：** 工具层部分完成后，若最终报告仍不可用或达到总超时，才进入产品静默回退描述性解读——见 [`02` D10–D11](./02-面试问答.md#d10-怎么定义失败中间一步失败就整单失败吗)；不阻断问数主链路。

### 面试时怎么说

1. 工具进系统靠 **YAML 声明式注册**：`tool_config` 列表 → `create_mcp_server_parameters` → `ToolManager` 按 yaml 拉起或连接 MCP（标本常见 stdio 子进程，远程 / SSE 则看 `url`），持有 Server 字典。
2. **发现**是运行时 `list_tools`，不是写死工具表；**调用**统一走 `execute_tool_call`，Main 和 Sub 各自 Manager，和 `03` 主循环分流一致。
3. **98%** 我讲的是 **单次工具调用的有效结果率**——返回能接着推理的非空内容；不是任务做完的比例，更不是 GAIA 53%。
4. 降级分两层：**工具层**是名纠错、空结果显式反馈、scrape 走 MarkItDown、LLM 换参再调；**产品层**才是最终报告不可用或总超时后的静默回退（[`02` D10–D11](./02-面试问答.md#d10-怎么定义失败中间一步失败就整单失败吗)）。
5. Hybrid Search 是 **众多 MCP 之一**（`tool-hybrid-search`），下一章再讲路由与融合；本章先把通用工具链讲清楚。

### 易踩坑

- 把 **98% 说成任务成功率、答案准确率或 GAIA 通过率**——必须拆开定义。
- 把 **MCP 进程启动成功** 等同于调用成功——应以返回内容是否可消费为准。
- 把 **`max_tool_calls_per_turn: 10`** 说成工具并发度——与 [`03`](./03-Main-Sub-Agent编排.md) 相同，是单轮顺序执行上限。
- 把 **MarkItDown 降级** 说成 Hybrid Search 内置——它是 scrape/reading 链的备用，别张冠李戴。
- 把 **0.6 / 0.4** 说成线上最优权重——只是标本基线，§3 再讲。
- 宣称 **生产向量库已落地**——`VectorBackend` 当前回退本地索引，§3 详述。
- 把 **引用质量** 说成代码级 schema 校验——实际是 hit 字段 + Prompt 约束，§3.末再钉。

**下一跳：** [§3 Hybrid Search：路由 → 召回 → 融合 → 证据链](./04-Hybrid-Search-MCP.md#3-hybrid-search路由--召回--融合--mcp-返回--证据链与引用)（待写）
