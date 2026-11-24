# Hybrid Search + MCP — 代码精读与面试深挖

> 对应简历：问数结果深度研究 · Hybrid Search / MCP
> 题纲：[`../面试题纲.md`](../面试题纲.md) § 三 F17–F20
> 指标 / 问题 / 改进：[`01-通用问答.md`](./01-通用问答.md)（F 节详解在本文）
> 上一章：[`03-Main-Sub-Agent编排.md`](./03-Main-Sub-Agent编排.md)
> 设计规格：[`../../../superpowers/specs/2026-08-06-hybrid-search-and-engineering-interview-prep-design.md`](../../../superpowers/specs/2026-08-06-hybrid-search-and-engineering-interview-prep-design.md)
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
| **§2** | 工具五步注册 / 发现 / 调用 / 降级；98% 定义 | F18（部分） |
| **§3** | Hybrid Search：路由 → 召回 → 融合 → MCP 返回 → 证据链与引用 | F17、F18（检索侧） |
| **§4** | 业务知识库（访谈 + 清洗研报）+ 金融 / 行为科学案例 | F19、F20 |
| **§5** | 面试题索引 F17–F20 + 回看清单 | F17–F20 |

阅读顺序：**先 §2 通用 harness，再 §3 Hybrid 特例**——面试被追问「98% 怎么来的」时，先答工具层定义与降级，再落到 Hybrid 路由与融合。

### 1.3 诚实边界总表

| 说法 | 可讲 | 不可讲 |
|------|------|--------|
| **98%** | 工具调用成功率（对齐投顾话术）：单次 MCP 返回可解析、非空、可继续消费的有效结果 | 任务成功率 / 答案准确率 / GAIA 通过率 |
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

### 2.2 注册：以「新挂 `tool-hybrid-search`」为例走完步骤

面试官若问「工具怎么注册」，不要只背「有个 yaml」。按**新加一把 MCP 工具**的视角，逐步说明；下面用 Hybrid Search 当完整样例，其他工具（如 `tool-reading`）少做 Step 4 特例即可。

#### Step 1：实现 MCP Server（工具本体）

写一个 FastMCP 进程模块，用 `@mcp.tool()` 暴露可调用函数；函数 docstring / 参数会成为 LLM 看到的 description 与 schema。

标本：`src/tool/mcp_servers/hybrid_search_mcp_server.py`

```python
mcp = FastMCP("hybrid-search-mcp-server")

@mcp.tool()
async def hybrid_search(query: str, top_k: int = 8, query_mode: str = "auto") -> str:
    """Hybrid retrieval combining uploaded-file index and web search. ..."""
    # 读 env、路由、召回、融合，返回 JSON 字符串
    ...
```

要点：

- **一个 Server 进程里可以挂多个 `@mcp.tool()`**；Hybrid 这把目前只有 `hybrid_search`。
- 运行时由 `ToolManager` 以 **stdio 子进程**拉起本模块（见 Step 5），不是 import 进主进程直接调。

#### Step 2：写 `config/tool/tool-*.yaml`（注册清单）

新建 `config/tool/tool-hybrid-search.yaml`，声明 **Server 名、怎么启动、环境变量**：

```yaml
name: "tool-hybrid-search"          # ← 之后 LLM 调用时的 server_name
tool_command: "python"              # ← 启动命令（python 会换成当前解释器）
args:
  - "-m"
  - "src.tool.mcp_servers.hybrid_search_mcp_server"   # ← Step 1 的模块
env:                                # ← 注入子进程的环境变量
  SERPER_API_KEY: "${oc.env:SERPER_API_KEY,}"
  RETRIEVAL_INDEX_DIR: "${oc.env:RETRIEVAL_INDEX_DIR,./data/retrieval_indexes}"
  RETRIEVAL_MODE: "${oc.env:RETRIEVAL_MODE,auto}"
  RETRIEVAL_LOCAL_WEIGHT: "${oc.env:RETRIEVAL_LOCAL_WEIGHT,0.6}"
  RETRIEVAL_WEB_WEIGHT: "${oc.env:RETRIEVAL_WEB_WEIGHT,0.4}"
```

要点：

- **一条 yaml = 一个 MCP Server 注册项**；文件名（去掉 `.yaml`）要和 Agent `tool_config` 里写的字符串一致。
- 当前装配**只认** `tool_command` + `args` + `env` → `StdioServerParameters`；**不读 url**。别说「yaml 里配个 URL 就能 SSE」。

#### Step 3：在 Agent 配置里挂上（谁能用这把工具）

在对应 Agent 的 `tool_config` 列表加一行。业务侧 Main 示例（`config/agent_server.yaml`）：

```yaml
main_agent:
  tool_config:
    - tool-reading
    - tool-hybrid-search    # ← 挂上 Step 2 的注册名
    - tool-searching
  retrieval:
    mode: "${oc.env:RETRIEVAL_MODE,auto}"
    router:                 # 对齐用；默认不会自动注入权重（见 Step 4）
      local_weight: 0.6
      web_weight: 0.4
```

要点：

- Main / Sub **各自一份** `tool_config`（+ 可选 `tool_blacklist`）→ **各自一个** `ToolManager`，工具面可以不同。
- GAIA 标本常把 searching/reading 挂在 Sub；业务 `agent_server` 把 hybrid-search 挂在 Main——面试讲清「挂在谁身上」，不要混成全局一张表。

#### Step 4：大多数工具可以跳过——只有 Hybrid 多抄了一行「默认检索模式」

**先把「装配」说清楚：** Step 2 / 3 写完后，框架会调 `create_mcp_server_parameters`：按 `tool_config` 逐个打开 yaml，拼出「怎么启动这个 MCP 子进程」（命令 + args + **环境变量 env**）。对 `tool-reading`、`tool-searching` 等，**读完 yaml 就结束**，没有额外逻辑。

**Hybrid 为什么特殊？** 路由默认模式有两处可能写：

1. Agent 配置里：`main_agent.retrieval.mode`（例如 `auto`）
2. 工具 yaml 的 env：`RETRIEVAL_MODE`

MCP 子进程**读不到** Agent YAML 全文，它只能读自己启动时带上的 **env**。所以代码里加了一段 **if 名字是 tool-hybrid-search**：把 Agent 上的 `retrieval.mode` **再写进**即将启动的子进程环境变量 `RETRIEVAL_MODE`，避免「Agent 配了 auto，子进程却不知道」。

```python
# src/utils/tool_utils.py · create_mcp_server_parameters（L42–45 意思）
# 伪代码：
env = 从 tool-hybrid-search.yaml 读出来的 env          # Step 2 已有
if 工具名 == "tool-hybrid-search":
    env["RETRIEVAL_MODE"] = Agent配置.retrieval.mode   # ← 多抄这一行
# 其他工具：没有这个 if，直接用 yaml 里的 env
```

**你注册普通新工具时：** 一般 **不用改这段 Python**；只要 Step 1–3（+ Step 5）就够。只有当你也想像 Hybrid 一样「让 Agent YAML 里某个字段自动变成子进程环境变量」时，才需要加类似 if。

**别和权重搞混（常考）：**

| 你想改什么 | 改哪里才生效 |
|------------|--------------|
| 默认路由模式 `auto/local/web/hybrid` | Agent `retrieval.mode`（靠上面这段抄进 `RETRIEVAL_MODE`）或直接改 tool yaml / OS 的 `RETRIEVAL_MODE` |
| 融合权重 0.6 / 0.4 | **只看** tool yaml 的 `RETRIEVAL_LOCAL_WEIGHT` / `RETRIEVAL_WEB_WEIGHT`（或 OS 环境变量）。Agent 里的 `retrieval.router.local_weight` **不会被这段代码读取**——改了也白改，除非同步改 tool yaml |

另：`ToolManager` 类理论上能接 URL/SSE，但当前「从 yaml 装配」只走 stdio，面试别说 yaml 配 URL 就能用。

#### Step 5：Pipeline 把 yaml 装配结果装进 `ToolManager`（可再挖一层）

Step 1–4 只是「配置写好了」。真正把配置变成**可执行句柄**的是：

```
Agent YAML (tool_config)
        │
        ▼
create_mcp_server_parameters(cfg, agent_cfg, logs_dir)
        │  读 config/tool/*.yaml → StdioServerParameters
        │  返回 (configs: list[dict], blacklist: set)
        ▼
ToolManager(server_configs=configs, tool_blacklist=blacklist)
        │  建成 server_dict[name] = params
        ▼
交给 Orchestrator（Main 一个 Manager；每个 Sub 各一个）
```

**注意：** 这里装配的是「**怎么启动**」的参数，**还不会立刻把所有 MCP 子进程拉起来**。真正 `stdio_client` 起进程，发生在后面的 **发现**（`get_all_tool_definitions` → `list_tools`）和 **调用**（`execute_tool_call` → `call_tool`）。

##### 5.1 yaml → 参数列表：`create_mcp_server_parameters`

```python
# src/utils/tool_utils.py
def create_mcp_server_parameters(
    cfg: DictConfig,          # 全局 Hydra 配置（本函数里几乎不用，留给扩展）
    agent_cfg: DictConfig,    # 某一个 Agent：cfg.main_agent 或 cfg.sub_agents["agent-worker"]
    logs_dir: str | None = None,
) -> tuple[list[dict], set]:
    """
    返回:
      configs: [
        {
          "name": "tool-hybrid-search",           # server_name
          "params": StdioServerParameters(        # MCP stdio 启动参数
              command=...,                        # 如当前 python
              args=["-m", "src.tool.mcp_servers.hybrid_search_mcp_server"],
              env={...},                          # 含 RETRIEVAL_* 等
          ),
        },
        ...
      ]
      blacklist: set[(server_name, tool_name), ...]  # 来自 agent_cfg.tool_blacklist
    """
```

关键循环（与 Step 2–4 衔接）：

1. `for tool in agent_cfg["tool_config"]` —— 字符串如 `"tool-hybrid-search"`
2. 打开 `config/tool/{tool}.yaml`
3. 拼 `env`（Hybrid 时再抄 `RETRIEVAL_MODE`，见 Step 4）
4. `configs.append({"name": ..., "params": StdioServerParameters(...)})`
5. 再读 `tool_blacklist`，变成 `(server, tool)` 二元组集合后一并返回

某一个 tool yaml 坏了：打 error 日志后 `continue`，**不拖死整次装配**。

##### 5.2 谁调用装配：`create_pipeline_components`

入口（评测 / server bridge / trace 都会先走这里）：

```python
# src/core/pipeline.py
def create_pipeline_components(
    cfg: DictConfig,
    logs_dir: str | None = None,
) -> tuple[ToolManager, dict[str, ToolManager], OutputFormatter]:
    """
    返回:
      main_agent_tool_manager: ToolManager
      sub_agent_tool_managers: dict[sub_agent_name, ToolManager]   # 如 "agent-worker" → Manager
      output_formatter: OutputFormatter
    """
```

正文逻辑（Main + 每个 Sub **各装一次**）：

```python
# Main
main_configs, main_blacklist = create_mcp_server_parameters(cfg, cfg.main_agent, logs_dir)
main_agent_tool_manager = ToolManager(main_configs, tool_blacklist=main_blacklist)

# 每个 Sub 独立 tool_config → 独立 ToolManager
sub_agent_tool_managers = {}
for sub_agent in cfg.sub_agents:          # 键名如 "agent-worker"
    sub_configs, sub_blacklist = create_mcp_server_parameters(
        cfg, cfg.sub_agents[sub_agent], logs_dir
    )
    sub_agent_tool_managers[sub_agent] = ToolManager(
        sub_configs, tool_blacklist=sub_blacklist
    )

return main_agent_tool_manager, sub_agent_tool_managers, output_formatter
```

面试要点：**挂在 Main 的 hybrid-search，只进 Main 的 Manager；Sub 列表里没有就不会被 Sub 发现/调用。** 这就是 Step 3「挂在谁身上」在运行时的落地。

##### 5.3 `ToolManager` 构造与关键方法

```python
# src/tool/manager.py
class ToolManager:
    def __init__(self, server_configs, tool_blacklist=None):
        """
        server_configs: create_mcp_server_parameters 返回的 configs 列表
        tool_blacklist: set[(server_name, tool_name)]
        """
        self.server_configs = server_configs
        self.server_dict = {
            config["name"]: config["params"] for config in server_configs
        }   # "tool-hybrid-search" → StdioServerParameters
        self.tool_blacklist = tool_blacklist if tool_blacklist else set()
```

装好之后，后面章节会用到的方法（先记签名，细节在 §2.3 / §2.4）：

| 方法 | 签名（要点） | 作用 |
|------|----------------|------|
| `get_server_params` | `get_server_params(self, server_name) -> StdioServerParameters \| None` | 按 `server_name` 取启动参数 |
| `get_all_tool_definitions` | `async def get_all_tool_definitions(self) -> list` | 对每个 Server `stdio_client` + `list_tools`，拼 LLM 可见工具目录（§2.3） |
| `execute_tool_call` | `async def execute_tool_call(self, server_name, tool_name, arguments) -> Any` | 起子进程 / 调 `call_tool`，含纠错与空结果处理（§2.4） |
| `_find_servers_with_tool` | `async def _find_servers_with_tool(self, tool_name) -> list[str]` | Server 名纠错时用：扫谁拥有该 tool |

辅助函数（调用前会跑）：

```python
# 把当前任务的 TASK_ID 写进 StdioServerParameters.env
# Hybrid 本地索引按 task_id 找文件，依赖这一步
def update_server_params_with_context_var(
    server_params: StdioServerParameters,
) -> StdioServerParameters: ...
```

##### 5.4 和 `execute_task_pipeline` 的衔接（一眼看清）

```python
# pipeline 先装配组件，再跑任务（示意）
main_tm, sub_tms, formatter = create_pipeline_components(cfg, logs_dir=...)
# ...
await execute_task_pipeline(
    cfg,
    ...,
    main_agent_tool_manager=main_tm,
    sub_agent_tool_managers=sub_tms,
    ...
)
# Orchestrator 内：main_tm.get_all_tool_definitions() → 主循环
#               main_tm.execute_tool_call("tool-hybrid-search", "hybrid_search", {...})
```

至此：**注册链路闭环**（配置 → 参数列表 → Manager 字典）。下一步不是再写静态工具表，而是运行时 **发现**（§2.3）与 **调用**（§2.4）。

#### 注册步骤一览（可背）

| Step | 做什么 | Hybrid 对应物 |
|------|--------|----------------|
| 1 | 实现 MCP Server + `@mcp.tool()` | `hybrid_search_mcp_server.py` → `hybrid_search` |
| 2 | 新增 `config/tool/tool-xxx.yaml` | `tool-hybrid-search.yaml` |
| 3 | Agent `tool_config` 挂上名字 | `agent_server.yaml` Main 列表 |
| 4 | （多数可跳过）把 Agent 的检索 mode 抄进子进程 env | 仅 Hybrid：`retrieval.mode` → `RETRIEVAL_MODE` |
| 5 | `create_mcp_server_parameters` → `ToolManager`；Main/Sub 各装一份 | `create_pipeline_components`；进程延后到 list/call 才拉起 |

调用链口诀：**写 Server → 写 tool yaml → 挂 tool_config →（Hybrid 才多抄一行 mode）→ create_mcp_server_parameters 产出 Stdio 参数 → ToolManager.server_dict → 运行时 list/call。**

### 2.3 发现：`get_all_tool_definitions`

#### 什么时候触发？

**不是** Step 5 装配时——那时只有 `server_dict` 启动参数。发现发生在 **Agent 会话开跑、主循环之前**：拉真 MCP 工具目录 → 拼进 system prompt。

| 角色 | 触发点 | 标本 |
|------|--------|------|
| Main | `run_main_agent`：初始 message 之后、`while turn` 之前，每任务一次 | ~L994–1016 |
| Sub | `run_sub_agent` 开头经 `_list_sub_agent_tools()`（带 cache） | ~L597–599 |

首次出现（也是结果怎么用）就在这里：

```python
# orchestrator.py · run_main_agent ~L994–1016
tool_definitions = await self.main_agent_tool_manager.get_all_tool_definitions()
if self.cfg.sub_agents is not None and self.cfg.sub_agents:
    tool_definitions += expose_sub_agents_as_tools(self.cfg.sub_agents)  # 假工具，非 MCP list
system_prompt = main_agent_prompt_instance.generate_system_prompt_with_mcp_tools(
    mcp_servers=tool_definitions, ...
)
# 进入 max_turns；turn 内复用，不再每轮重拉
# 之后某 turn 的 execute_tool_call 会再起进程做 call_tool（发现 ≠ 调用）
```

```
create_pipeline_components          ← 只装配参数，无 list_tools
        │
run_main_agent
        ├─ ★ get_all_tool_definitions()     ← 上面这段
        ├─ + expose_sub_agents_as_tools()
        ├─ generate_system_prompt_with_mcp_tools(...)
        └─ while turn → execute_tool_call / run_sub_agent
```

发现 = `list_tools`（问有哪些工具）；调用 = `call_tool`（§2.4，真正执行）。  
旁注：Sub 经 `_list_sub_agent_tools` cache，避免每个子任务重复扫全量 MCP。

**白话（先消掉「是不是每个工具都起进程」的误解）：**

Agent yaml 里写的：

```yaml
tool_config:
  - tool-reading
  - tool-hybrid-search
  - tool-searching
```

这里每一项名字带 `tool-`，**其实是 MCP Server 配置名**（对应 `config/tool/tool-*.yaml` → 一个 `*_mcp_server.py` 进程入口），**不是** `@mcp.tool` 函数名。

| 层级 | 例子 | 发现时起几个子进程 |
|------|------|-------------------|
| Agent 配的一项 | `tool-searching` | **1**（`python -m ...searching_mcp_server`） |
| 该 Server 文件里的多个函数 | `google_search` / `wiki_get_page_content` / … | **0 额外**——同一次 `list_tools` 一次吐出 |

所以：Main 配了 3 项 → 发现时先后短暂起 **3** 个子进程（问完就灭）。  
`tool-searching` 里哪怕有 5 个 `@mcp.tool`，也只算 **1** 次起停，不会「每个函数一个进程」。

**那最终有多少「工具」？** 进程数 ≠ 工具数。工具数 = 各 Server `list_tools` 结果之和（再扣 blacklist）：

| Server（`tool_config` 一项） | 该进程里的 `@mcp.tool` | 个数 |
|------------------------------|------------------------|------|
| `tool-reading` | `read_file` | 1 |
| `tool-hybrid-search` | `hybrid_search` | 1 |
| `tool-searching` | `google_search` / `wiki_get_page_content` / `search_wiki_revision` / `search_archived_webpage` / `scrape_website` | 5 |
| **合计** | | **7** |

即：发现后 `get_all_tool_definitions` 返回 **3 个 Server 条目**，tools 数组里一共约 **7 个**可调函数（未 blacklist 时）。之后 `expose_sub_agents_as_tools` 再往同一列表里塞假工具，那是编排层，不算 MCP `list_tools`。

- 起进程单位 = **Server 配置项**（`tool_config` 的一行）→ 本例 3  
- 工具个数 = 各 Server 内 `@mcp.tool` 之和 → 本例 7  
- 调用时：`execute_tool_call(server_name=..., tool_name=...)` 按 **Server** 起进程，在该进程里调某个 `tool_name`

#### 签名与返回值

```python
# src/tool/manager.py
class ToolManager:
    async def get_all_tool_definitions(self) -> list[dict]:
        """
        连接本 Manager 已配置的每个 MCP Server，拉取 tool 元数据，
        压成 Prompt 可用的列表。

        返回形如:
          [
            {
              "name": "tool-hybrid-search",   # server_name
              "tools": [
                {
                  "name": "hybrid_search",
                  "description": "...",       # 来自 @mcp.tool docstring
                  "schema": {...},            # 即 Tool.inputSchema
                },
                ...
              ],
            },
            ...
          ]
        某 Server 连失败时 tools 可能是:
          [{"error": "Failed to fetch tools: ..."}]
        """
```

#### 方法正文（外层 + try 在干什么）

```python
# manager.py ~L171–252
async def get_all_tool_definitions(self):
    all_servers_for_prompt = []

    # 遍历单位是 Server（tool_config 的一项），不是 @mcp.tool 函数
    for config in self.server_configs:  # Step 5 装进 ToolManager 的列表
        server_name = config["name"]
        server_params = config["params"]  # 通常 StdioServerParameters
        one_server_for_prompt = {"name": server_name, "tools": []}

        try:
            if isinstance(server_params, StdioServerParameters):
                async with stdio_client(
                    update_server_params_with_context_var(server_params)
                ) as (read, write):
                    async with ClientSession(
                        read, write, sampling_callback=None
                    ) as session:
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
            elif isinstance(server_params, str) and server_params.startswith(
                ("http://", "https://")
            ):
                async with sse_client(server_params) as (read, write):
                    ...  # 同构：initialize + list_tools
            else:
                raise TypeError(...)

            all_servers_for_prompt.append(one_server_for_prompt)

        except Exception as e:
            one_server_for_prompt["tools"] = [
                {"error": f"Failed to fetch tools: {e}"}
            ]
            all_servers_for_prompt.append(one_server_for_prompt)

    return all_servers_for_prompt
```

**`try` 在干什么（结合上下文概括，不必逐行抠）：**

对当前这个 Server，临时连上去问一句「你有哪些工具」，把目录收成 Prompt 用的 `{name, description, schema}`，然后断开。标本默认走 stdio：起该 Server 对应的那一个子进程 → MCP 握手 → `list_tools` → 把结果写进 `one_server_for_prompt` → 退出上下文即灭进程。SSE 分支类里有、当前 yaml 装配基本走不到。连失败也不让整个 Server 从列表里消失，而是塞一条 error 占位再 append——后面拼 system prompt 时仍知道配过这个名字。整段只做**发现/列目录**，不会在这里执行 `hybrid_search` 或任何业务检索。

### 2.4 调用：`execute_tool_call` 统一入口

#### 什么时候触发？（调用点）

发现（§2.3）在主循环**之前**只做一次；真正执行工具发生在 **turn 内**：LLM 吐出 tool_calls 之后。

```python
# orchestrator.py · run_main_agent 主循环内 ~L1110–1150
# 上一轮 LLM 已返回 tool_calls；本 turn 按顺序执行（受 max_tool_calls_per_turn 截断）
for call in tool_calls[0][:max_tool_calls]:
    server_name = call["server_name"]   # 如 "tool-hybrid-search"
    tool_name = call["tool_name"]       # 如 "hybrid_search"
    arguments = call["arguments"]
    call_id = call["id"]

    try:
        if server_name == "human" and tool_name == "ask_user":
            tool_result = await self._ask_user_tool(arguments)
        elif server_name.startswith("agent-"):
            # 假工具：走 run_sub_agent，不进 ToolManager
            tool_result = {
                "server_name": server_name,
                "tool_name": tool_name,
                "result": await self.run_sub_agent(...),
            }
        else:
            # ★ 真 MCP：Hybrid / searching / reading 都走这里
            tool_result = await self.main_agent_tool_manager.execute_tool_call(
                server_name=server_name,
                tool_name=tool_name,
                arguments=arguments,
            )
        # 成功：写入 tool_calls_data，再 format 进 message history 供下一轮 LLM
    except Exception as e:
        # 含 @with_timeout(900) 冒出的 TimeoutError → 构造成 {"error": ...} 写回
        ...
```

Sub 侧同构：`sub_agent_tool_managers[name].execute_tool_call(...)`（~L723）。  
`human` / `agent-*` 不进本节；Hybrid 的 `hybrid_search` 一定落在 `else` 这条 MCP 支路。

#### 方法正文（主分支在干什么）

```python
# manager.py ~L254–517
@with_timeout(900)
async def execute_tool_call(self, server_name, tool_name, arguments) -> Any:
    server_params = self.get_server_params(server_name)

    if not server_params:
        # 分支 A：Server 名对不上
        ...
    if server_name == "playwright":
        # 分支 B：浏览器特例
        ...
    else:
        # 分支 C：普通 MCP（Hybrid / searching / reading 走这里）
        try:
            if isinstance(server_params, StdioServerParameters):
                ...  # C1 stdio
            elif ... http(s) ...:
                ...  # C2 SSE（当前 yaml 基本走不到）
            # 成功后可能再走「Unknown tool」纠错，然后 return {"result": ...}
        except Exception:
            ...  # 分支 D：调用异常（含 scrape→MarkItDown）
```

| 分支 | 条件 | 在干什么 |
|------|------|----------|
| **A** | `server_params` 找不到 | Server 名写错。用 `_find_servers_with_tool` 扫一遍：全局只命中 1 个就递归纠错重调；否则返回 `{"error": ...}` 提示 LLM |
| **B** | `server_name == "playwright"` | 不走短连接 stdio，复用常驻 `PlaywrightSession` 调浏览器工具 |
| **C1** | 默认 stdio（标本主路径） | 再起该 Server 子进程 → `initialize` → **`call_tool`**（发现是 `list_tools`）→ 抽出文本；空内容写成说明性 `result`，不抛异常 |
| **C2** | params 是 http(s) URL | SSE 同构调用；当前 yaml 装配基本进不来 |
| **C 成功后** | 返回里带 `Unknown tool:` | Tool 名在该 Server 不存在、但全局唯一 → 换正确 Server 再调一次 |
| **D** | `call_tool` 等抛异常 | 一般返回 `{"error": ...}`；若是 `scrape` + `unhandled errors`，再试 MarkItDown 读 URL（非 Hybrid 主路径） |

统一出口：`{"server_name", "tool_name", "result"|"error"}`，Orchestrator 写回 history。超时由 `@with_timeout(900)` 抛 `TimeoutError` 冒到 Orchestrator（见下节）。

### 2.5 降级、备选工具与 98% 成功率

#### 98% 怎么说（对齐投顾话术）

对标股票智能投顾那句「工具调用成功率稳在 98%」（`agent_project/interview/tell/股票智能投顾_叙述脚本.md`、补充题「工具调用失败 2%」）。  
两边都是 **MCP 单次调用** 口径：**未超时 + 有可解析、非空、能进下一轮 LLM 的内容**。  
≠ 任务做完率、答案准不准、GAIA 通过率。连接成功但结果不可用，也不算成功。

**约 2% 失败：** ① 外部源偶发（联网 / scrape / 索引超时异常）；② 模型写错 `server_name` / `tool_name` 或参数（纠错吃不掉的部分）。

开口可压成三层：入口兜错 → 失败可降级（含备选工具）→ 调用链路可追踪（`05`）。别照搬投顾的「股票代码强校验 / 固定 3 次指数退避」——标本没有硬编码 `retry=N`，超时错误写回 history 后由 LLM 换参再调。

#### 常见兜底（举例）

1. **超时** — 单次调用 >900s → Orchestrator 写成 timeout error 塞回对话。  

2. **Server / Tool 名写错（举例）**
   - **Server 名写错、工具全局唯一 → 自动改：** LLM 写成 `server_name=tool-search`（少了 ing），`tool_name=google_search`。字典里没有 `tool-search`，但扫一遍发现只有 `tool-searching` 提供 `google_search` → harness 改成正确 Server **再调一次**，结果里带 Auto-corrected 注记。
   - **Tool 挂错 Server、全局唯一 → 也自动改：** 调 `tool-reading` + `google_search`。reading 里没有这个 tool，返回 `Unknown tool:`；全局只有 searching 有 → 换到 `tool-searching` 再调。
   - **多处都能提供同名 tool → 不猜：** 假设两个 Server 都暴露了同名 `search`（标本默认配置一般碰不到，但逻辑如此）→ harness **不会**随便挑一个，只返回 error，列出候选 Server，让 LLM 下一轮自己选对的。

3. **返回空（举例）**
   - 调 `hybrid_search` / `scrape_website` **协议成功**（子进程起来了、`call_tool` 没抛异常），但 MCP `content` 没字或只有空白 → **不抛异常、不重试**，直接返回类似  
     `Tool 'hybrid_search' completed but returned empty text - this may be expected or indicate an issue`  
     写进 message history。
   - 下一轮由 LLM 决定：换 query、换工具，或认定「这次本来就该空」（个别 delete 类操作空结果可能正常）。  
   - **和失败的区别：** 这里没有 `{"error": ...}`，是带说明的 `{"result": "..."}`——所以 98% 统计里通常**不算成功**（内容不可继续推理），但也不会把整次调用当硬崩溃。

#### 备选工具机制：怎么切？要事先配置吗？

**先钉死一句：没有「备选工具注册表 / fallback yaml」。**  
`tool_config` 只声明 Agent **能用哪些 Server**；真正怎么切换，是 **代码里写死的 if / 链式尝试**，或 **LLM 自己换下一个已发现的工具**——不是再配一张「失败后改调谁」的表。

| 层级 | 怎么切换 | 事先要配什么 |
|------|----------|--------------|
| **① Harness 内** | `manager.py` 里写死：`tool_name=="scrape"` 且错误含 `unhandled errors` → 直接 `MarkItDown.convert(url)`，**不**再起一个 MCP、也**不**改 `tool_config` | 无独立配置；MarkItDown 是库调用，条件写在代码里 |
| **② Server 内** | Server 自己的函数里写死顺序，例如 `read_file` 下载失败 → 调 `smart_request`；`smart_request` 再按 Jina → Serper → requests 依次试 | 一般只要相关 **API Key 在 env**（如 `JINA_API_KEY` / `SERPER_API_KEY`）；不是「备选工具列表」 |
| **③ 跨工具（LLM）** | 本次返回 `error` / 空说明写回对话 → **下一轮** LLM 从已发现的工具目录里再挑（如改调 `hybrid_search`） | 目标工具必须已在该 Agent 的 `tool_config` 里（否则发现阶段就没有）；**切换动作本身不配**，靠 Prompt + 模型决策 |
| **Hybrid 一路切另一路** | `hybrid_search` / `route_query` 代码内按 mode 决定 local/web（详 §3） | `RETRIEVAL_MODE` 等 env；仍不是「备选 MCP 表」 |

**面试怎么答「怎么切换」：**

1. **自动切（①②）**：失败条件命中 → 同一次调用内走备用路径，调用方只看到一次 tool call 的成功/失败结果。  
2. **模型切（③）**：没有自动备用时，把失败信息喂回 LLM，由它选下一个**已经注册并 list 过的**工具——所以「备选」的前提是工具早就挂在 `tool_config` 里，而不是失败时动态注册。  
3. **不要说成**：配了 `fallback: markitdown` 之类；标本没有这层配置抽象。

**下一跳：** [§3 Hybrid Search：路由 → 召回 → 融合 → 证据链](./04-Hybrid-Search-MCP.md#3-hybrid-search路由--召回--融合--mcp-返回--证据链与引用)

---

## 3. Hybrid Search：路由 → 召回 → 融合 → MCP 返回 → 证据链与引用

### 3.1 前置条件

读到这里应已知（来自 §2）：

1. `tool-hybrid-search` 经 YAML 注册为 stdio MCP Server，`ToolManager.execute_tool_call` 统一调 `hybrid_search`。
2. Agent 级 `retrieval.mode` 经 `create_mcp_server_parameters` 注入 `RETRIEVAL_MODE`；融合权重由 tool yaml 环境变量 `RETRIEVAL_LOCAL_WEIGHT` / `RETRIEVAL_WEB_WEIGHT` 提供（§3.6），Agent `retrieval.router` **不覆盖**。
3. **98%** 指单次工具调用返回可消费内容；Hybrid 一路失败时仍可用另一路或已有证据部分完成（§2.5）。

本章从 MCP 入口 `hybrid_search` 往下钻：先看 **Server 里怎么串起来**，再按调用顺序拆路由 / 召回 / 融合 / 返回 / 证据链。

### 3.2 入口骨架：`hybrid_search` 编排全貌

业务主体逻辑就在这一份 MCP Server 里编排——`ToolManager` 只负责起进程 + `call_tool`；**路由、召回、融合、拼 JSON 都在 `hybrid_search` 函数内完成**。

```python
# src/tool/mcp_servers/hybrid_search_mcp_server.py（逻辑骨架）
INDEX_DIR = env RETRIEVAL_INDEX_DIR
DEFAULT_MODE = env RETRIEVAL_MODE          # §2 装配注入；可被参数 query_mode 覆盖
LOCAL_WEIGHT / WEB_WEIGHT = env ...        # tool yaml 默认 0.6 / 0.4

@mcp.tool()
async def hybrid_search(query, top_k=8, query_mode="auto") -> str:
    task_id = env TASK_ID
    if not task_id:
        return JSON{error, route:"web"}     # 无任务 ID 则无法定位本地索引

    # 文件：src/retrieval/local_index.py · LocalIndexStore
    # 作用：按 task_id 判断本地是否已有索引；后面按需 search
    store = LocalIndexStore(INDEX_DIR)
    has_local = store.has_index(task_id)

    # 文件：src/retrieval/router.py · route_query → schemas.RoutePlan（详 §3.3）
    # 作用：决定走 local / web / hybrid，并给出归一后的融合权重
    route = route_query(
        query, has_local,
        mode=query_mode if != "auto" else DEFAULT_MODE,
        local_weight=LOCAL_WEIGHT, web_weight=WEB_WEIGHT,
    )

    # 文件：src/retrieval/local_index.py · LocalIndexStore.search → schemas.SearchHit（详 §3.4）
    # 作用：在本地 chunk 上做 token 交集打分召回（仅 local/hybrid）
    local_hits = store.search(...) if route.mode in ("local","hybrid") else []

    # 文件：src/retrieval/web_retriever.py · search_web（详 §3.5）
    # 作用：联网检索（Serper 等），产出 Web 侧 SearchHit（仅 web/hybrid）
    web_hits = await search_web(...) if route.mode in ("web","hybrid") else []

    # 文件：src/retrieval/fusion.py · weighted_fusion / _dedupe（详 §3.6）
    # 作用：两路加权排序、去重，截断到 top_k
    fused = weighted_fusion(local_hits, web_hits, route.weights, top_k)

    # 字段见 §3.7；SearchHit / 引用见 schemas.py + §3.8
    # 作用：把路由信息与融合结果打成 JSON 字符串返回给 Agent
    return JSON{
        route, reason, mix, local_hits, web_hits,
        results: [hit.to_dict() for hit in fused],
    }
```

一次调用 = 读 env → 判索引 → 路由 →（按需）本地/Web 召回 → 融合 → JSON；**不是** Orchestrator 分别调三个工具。  
建库不在这条热路径：`ingest.py` 的 `build_task_index`（经 `vector_backend.py` 回退写本地索引）只在上传后跑，讲「索引哪来的」时回看 §3.4。

### 3.3 路由：`route_query`

```python
# 文件：src/retrieval/router.py · route_query → schemas.RoutePlan
# 作用：关键词 hints + 强制 mode + 无索引降级 —— 不是语义/学习型路由

LOCAL_HINTS = ("附件", "上传", "文档", "pdf", "内部", "第", "页", ...)
WEB_HINTS   = ("最新", "今天", "新闻", "公告", "政策", "官网", "实时", ...)

def route_query(
    query: str,
    has_local_index: bool,   # 来自 LocalIndexStore.has_index(task_id)
    mode: str = "auto",      # 非 auto 时强制；hybrid_search 里 auto → 读 RETRIEVAL_MODE（§2 注入）
    local_weight: float = 0.6,
    web_weight: float = 0.4,
) -> RoutePlan:

    # —— 决策（按优先级，命中即定）——
    normalized_mode = (mode or "auto").strip().lower()
    if normalized_mode in ("local", "web", "hybrid"):
        # 1) 显式 mode：强制该路，reason=forced_by_mode
        selected, reason = normalized_mode, "forced_by_mode"
    else:
        local_hit = any(h in query.lower() for h in LOCAL_HINTS)
        web_hit   = any(h in query.lower() for h in WEB_HINTS)
        if not has_local_index:
            # 2) 本地无索引：只能 web，reason=no_local_index
            selected, reason = "web", "no_local_index"
        elif local_hit and not web_hit:
            # 3) 只命中本地 hint：走 local
            selected, reason = "local", "local_keywords"
        elif web_hit and not local_hit:
            # 4) 只命中联网 hint：走 web
            selected, reason = "web", "web_keywords"
        else:
            # 5) 双命中或都未命中：默认 hybrid
            selected, reason = "hybrid", "default_hybrid"

    # —— 权重归一（供后续 weighted_fusion）——
    if selected == "local":
        local_weight, web_weight = 1.0, 0.0      # 纯本地
    elif selected == "web":
        local_weight, web_weight = 0.0, 1.0      # 纯联网
    else:
        total = max(local_weight + web_weight, 1e-6)
        local_weight, web_weight = local_weight / total, web_weight / total  # hybrid：保留配置比并归一

    return RoutePlan(mode=selected, reason=reason,
                     local_weight=local_weight, web_weight=web_weight)
```

### 3.4 本地：建库一条链、检索一条链

本地相关**不是** `hybrid_search` 里一口气跑完 `ingest → chunk → search`。  
两条时间线、两次调用：

```
上传 / 任务开始（pipeline）          hybrid_search 热路径（§3.2）
─────────────────────────          ─────────────────────────
build_task_index                   LocalIndexStore.has_index / search
        │                                    │
        ▼                                    ▼
   写出 {task_id}.json  ←──── 同一份文件 ────  读入打分召回
```

#### A. 建库链（检索之前，不在 `hybrid_search` 里）

**调用证据（pipeline，任务开跑、Main Agent 之前）：**

```python
# 文件：src/core/pipeline.py · execute_task_pipeline 内（~L88–103）
# 作用：满足开关时先建索引，再往后跑 Agent / 工具

retrieval_cfg = cfg.main_agent.get("retrieval", {})
if retrieval_enabled and auto_index_on_start and task_file_name:
    index_info = build_task_index(          # ← 建库入口就在这里
        task_id=task_id,
        file_path=task_file_name,
        index_dir=..., backend=..., chunk_size=..., chunk_overlap=...,
    )
    # 记入 task_log；之后才初始化 LLM / 进 orchestrator
```

配置开关示例：`config/agent_server.yaml` 里 `retrieval.enabled` / `auto_index_on_start: true`。

**建库内部（被上面那一次调用拉起）：**

```python
# 文件：src/retrieval/ingest.py · build_task_index
# 作用：把上传文件变成可检索的本地索引文件

content = _convert_file_to_text(path)
#   文本类直读；PDF/Office 走 MarkItDown；否则尽力 decode

# 文件：src/retrieval/vector_backend.py · VectorBackend.upsert_document
# 作用：本应接向量库；当前直接回退本地 JSON（未接 Milvus/PGVector）
store = VectorBackend(index_dir, backend="local_index")
store.upsert_document(task_id, source_uri, content, chunk_size=800, overlap=120)
#   └── 内部调用 ↓

# 文件：src/retrieval/local_index.py · LocalIndexStore.write_index / chunk_text
# 作用：滑窗分块 → 每块 tokenize → 写入 {index_dir}/{task_id}.json
chunks = chunk_text(content, 800, 120)   # 滑窗，默认 size=800 overlap=120
# 每块字段：chunk_id / title / url(=source_uri) / text / tokens
# 落盘：{task_id}.json
```

#### B. 检索链（`hybrid_search` 热路径，§3.2 已点名）

```python
# 文件：src/retrieval/local_index.py · LocalIndexStore
# 作用：hybrid_search 里只用 has_index + search，不再走 ingest

has_local = store.has_index(task_id)     # 有没有 {task_id}.json → 交给 route_query
local_hits = store.search(task_id, query, top_k)
#   读 JSON → query/chunk 做 token 交集分：|overlap| / |query_tokens|
#   → list[SearchHit(source="local", snippet=text[:500], ...)]
```

要点：建库一次、检索多次；`hybrid_search` **只读**已有索引。没建过库 → `has_index=False` → 路由常落到 web（§3.3）。

#### C. 追问：接远端向量库（Milvus / Mongo）装研报 + 访谈，怎么办？

标本**还没接上**——`VectorBackend` 只是占位，且 `hybrid_search` 热路径目前**直接** `LocalIndexStore`，连 `VectorBackend.search` 都没走。面试要说清「改哪里」，别说「配个 URI 就自动用向量库」。

**目标形态：** 清洗后的研报 + 经授权访谈 → 分块 embedding → 写入远端库；检索时向量召回（可再加关键词），仍吐出统一的 `SearchHit`，后面路由/融合/引用不用大改。

```python
# 1) 实现 VectorBackend 的真实分支（vector_backend.py）
#    文件：仍走 upsert_document / search 两个口子，对上 ingest 与检索
class VectorBackend:
    def __init__(..., backend="milvus"|"mongodb"|"local_index"):
        if backend == "milvus":
            # 连远端：uri / token / collection；embedding 模型从配置读
            ...
        elif backend == "mongodb":
            # 一般是 MongoDB Atlas Vector Search（或自管库 + 向量字段）
            # 纯文档 Mongo 不够，必须有向量索引能力
            ...

    def upsert_document(task_id, source_uri, content, ...):
        chunks = chunk_text(content, ...)           # 可复用 local_index.chunk_text
        vectors = embed([c for c in chunks])        # 新增：调用 embedding API/本地模型
        # 每条至少写入：vector + text + 业务元数据（见下）
        milvus.insert(...) / mongo.collection.insert_many(...)

    def search(task_id_or_filter, query, top_k) -> list[SearchHit]:
        qvec = embed([query])[0]
        rows = milvus.search(...) / atlas.vectorSearch(...)
        return [SearchHit(source="local", title=..., url=..., snippet=...,
                          score=..., chunk_id=..., metadata=...) for ...]
```

**研报 / 访谈怎么「带进去」：**

| 步骤 | 做法 |
|------|------|
| 解析与清洗 | 沿用现有抽取（MarkItDown / 业务清洗流水线），得到纯文本 + 来源元数据 |
| 元数据（建议必带） | `doc_type`=`interview`\|`research_report`、`source_uri`、标题、版本/更新时间、权限标签、`chunk_id` |
| 入库时机 | **离线批量**：实验室知识库全量/增量 upsert（主路径）；**在线**：任务上传附件仍可走 `build_task_index`，只是 `backend=milvus` |
| 过滤 | 检索加 filter：权限 + 可选 `doc_type`；任务附件可用 `task_id` 字段隔离 |

**还要改热路径（否则接了库也搜不到）：**

```python
# hybrid_search_mcp_server.py 今天：
store = LocalIndexStore(...)          # ← 写死本地
has_local = store.has_index(task_id)
local_hits = store.search(...)

# 接向量库后应改为（示意）：
store = VectorBackend(..., backend=cfg.backend)   # milvus / mongodb / local_index
has_local = store.has_corpus(...)                 # 按 filter 判断是否有可检数据
local_hits = store.search(filter=..., query, top_k)
```

配置侧（示意，标本未落地）：`retrieval.backend: milvus`，以及 `MILVUS_URI` / `MONGO_URI`、collection 名、embedding 模型名写入 tool/agent yaml env。

**诚实边界：** 这是**扩展设计**，不是当前运行时行为；Mongo 要讲清是「向量检索能力」而非普通文档查询；接上后 Hybrid 的 web 路、融合、证据链字段约定可不变，变的是 **local 路的存储与打分**。

```python
# web_retriever.py · search_web（签名）
async def search_web(query: str, top_k: int = 5) -> list[SearchHit]
```

- 依赖 `SERPER_API_KEY`；无 key 或 HTTP 异常 → **返回空列表**（不抛到 MCP 外层）。
- Serper `organic` 结果映射为 `SearchHit(source="web", ...)`；score 按排名递减 `1.0 - index * 0.05`；`chunk_id=f"web_{index}"`。

旁注：

- Web 空召回**不等于**整次 Hybrid 失败——若路由为 `hybrid` 或 `local`，仍只交本地侧 fused 结果；Agent 应在报告中声明 Web 缺口（§3.8）。

### 3.6 融合：`weighted_fusion` + `_dedupe`

**先消歧义：「hit × weight」不是只留一条。**

- 召回阶段两边都可以是**多条**：`local_hits` 最多约 `top_k` 条 chunk，`web_hits` 最多约 `top_k` 条网页结果。
- 「× `local_weight` / `web_weight`」只是给**每一条**已有 hit 的 `score` 乘上该路权重，用来在合并排序时偏袒某一侧——**不删条数、不合成一条摘要**。
- 例：默认 0.6 / 0.4 时，本地一条原始分 0.8 → 融合分 `0.8×0.6=0.48`；Web 一条原始分 0.9 → `0.9×0.4=0.36`；然后两边所有条扔进同一个列表比高低。

**流程：** 两路多条 hit 各自改 score → 拼成一个大列表 → 按 score 降序 → `_dedupe` → 截断 Top K（默认 8）交给 Agent。

**去重键（优先级钉死）：**

1. **`hit.url` 非空** → 以 URL 为 key。列表已按 score 降序，故**同一 URL 只保留最高分那条**；其余 chunk 直接丢弃。本地 ingest 时各 chunk 的 `url` 均设为同一 `source_uri`，因此**同一文档的多 chunk 会撞车**，不会并存。
2. **`hit.url` 为空** → 退化为 `f"{hit.source}:{hit.chunk_id}"`，不同 chunk 可并存。

```python
# 文件：src/retrieval/fusion.py · weighted_fusion / _dedupe
# 作用：两路多条结果加权排序后去重截断，不是「每路合成一条」

def weighted_fusion(local_hits, web_hits, local_weight, web_weight, top_k=8):
    mixed = []
    for hit in local_hits:                 # 多条本地
        hit.score = hit.score * local_weight   # 只改分，不删条
        mixed.append(hit)
    for hit in web_hits:                   # 多条 Web
        hit.score = hit.score * web_weight
        mixed.append(hit)
    mixed.sort(key=lambda item: item.score, reverse=True)
    return _dedupe(mixed)[:top_k]          # 去重后再取前 K 条
```

旁注：

- **权重来源（钉死）：** `hybrid_search_mcp_server.py` 读 `RETRIEVAL_LOCAL_WEIGHT` / `RETRIEVAL_WEB_WEIGHT`（tool yaml，默认 0.6 / 0.4）。装配**只覆盖** `RETRIEVAL_MODE`，不覆盖融合权重。
- **0.6 / 0.4** 是标本基线，不是业务最优。
- 本地 token 分与 Web 排名分**量纲不同**，乘权重只是工程折中。
- 因 url 去重，本地多 chunk 若共用同一 `source_uri`，融合后同一文档往往只剩 1 条——这是去重副作用，不是「每路只召回 1 条」。

### 3.7 MCP 返回：返回 JSON 长什么样

编排流程见 §3.2；这里只钉 **返回给 Agent 的 payload**。

```python
# hybrid_search 末尾（成功路径）
return json.dumps({
    "route": route.mode,
    "reason": route.reason,
    "mix": {"local_weight": route.local_weight, "web_weight": route.web_weight},
    "local_hits": len(local_hits),
    "web_hits": len(web_hits),
    "results": [item.to_dict() for item in fused_hits],
}, ensure_ascii=False, indent=2)
```

| 字段 | 含义 |
|------|------|
| `route` | 最终 mode：`local` / `web` / `hybrid` |
| `reason` | 路由原因码（见 §3.3 表） |
| `mix` | 归一后 `{local_weight, web_weight}` |
| `local_hits` | 本地召回条数（融合前） |
| `web_hits` | Web 召回条数（融合前） |
| `results` | 融合后 `SearchHit.to_dict()` 列表 |

旁注：缺 `TASK_ID` 时直接 error JSON（无法定位任务索引）。返回值是 **JSON 字符串**（MCP text），写回 message history；无 Pydantic 二次校验。

### 3.8 证据链与引用

Hybrid 的价值不止「搜到东西」——而是先产出**可追溯 hit 列表**，再让 Agent 按出处写结论并标缺口。

#### 3.8.1 工具层：`SearchHit` 字段

```python
# schemas.py · SearchHit dataclass（L8–19）
@dataclass
class SearchHit:
    source: SourceType          # "local" | "web"
    title: str
    url: str
    snippet: str                # 可摘录原文片段（本地为 chunk 前 500 字）
    score: float                # 召回/融合分（非置信度）
    chunk_id: str               # 本地 "{task_id}_{i}"；Web "web_{index}"
    metadata: dict[str, Any] = field(default_factory=dict)
```

| 字段 | 本地典型值 | Web 典型值 | 报告层用途 |
|------|------------|------------|------------|
| `source` | `"local"` | `"web"` | 区分访谈/研报 vs 公网 |
| `title` | 文件名 | 搜索结果标题 | 引用标题 |
| `url` | `source_uri` | Serper link | **必须尽量带回** |
| `snippet` | chunk 文本截断 | Serper snippet | **优先摘录原文** |
| `score` | token 重叠比 × 权重 | 排名分 × 权重 | 排序参考，**≠ 事实置信度** |
| `chunk_id` | `{task_id}_{i}` | `web_{n}` | 回溯具体块；**仅 url 为空时**参与去重键 |
| `metadata` | `overlap_terms` 等 | `position` 等 | 调试 / 交叉验证辅助 |

MCP 外层另含 `route` / `reason` / `mix` / 两路召回计数——Agent 可据此说明「本次 mainly local / 为何 hybrid / Web 是否为空」。

#### 3.8.2 报告层：Prompt + ResearchDirective

**Sub / Main Prompt（标本可核对）：** `sub_worker.py` 工作阶段要求：

- **Prefer quoting or excerpting original source text**，并 **provide the URL if available**；
- 来源可信度不确定要 **clearly flag**；冲突信息全部保留并标不一致；
- 信息不完整仍交 **partial excerpts** 并标 **uncertainty**；
- **Never assume or guess — if an exact answer cannot be found, say so clearly**（工作阶段口径：有证据优先、缺口明示，而非硬编）。

**Prompt 张力（面试可主动点出）：** 同一文件里，**summarize 阶段**在任务耗尽上下文时会写 *make a well-informed educated guess*——与工作阶段的 *never assume or guess* 并存。面试口径取中间层：**有 hit / 原文就摘录+URL；无证据就声明缺口，不把推测包装成事实**；仅在 summarize 兜底且证据已穷尽时，才允许带标注的推断。

**业务 ResearchDirective（见 [`02` §7.5](./02-集成设计.md#75-researchdirective-type-specific-研究指导-prompt)，交叉引用不整篇复制）：**

| 增强类型 | 引用相关约束（摘要） |
|----------|----------------------|
| `financial_analyst` | 归因须标 **证据强度** `[已验证]` / `[推断]` / `[推测]`；禁止编造未披露数字 |
| `academic` | **严禁编造引用**；预印本须标注；文内 `[作者, 年份]` + 文末清单含 DOI/URL |
| `default` | 通用研究指导 + 声明缺口 |

Directive 是 **prepend 进 task 的 Markdown 指导**，不是编译期 schema——与 Hybrid JSON 返回并行约束 Agent 行为。

#### 3.8.3 诚实边界：无代码级引用强校验

**当前没有：**

- 强制 JSON 引用列表 / 脚注 schema 的 post-processor；
- 对最终报告逐条核对 `chunk_id` 是否存在于 `results` 的编译期保证；
- 分高覆盖原始访谈/研报的自动仲裁——冲突时应**保留双出处 + 不确定性**。

引用质量靠 **结构化 `SearchHit` + Prompt / Directive 软约束**，不是类型系统或 JSON Schema 强校验。面试一句话：

> Hybrid 先产出可追溯 hit 列表；Agent 按出处摘录并标强度/缺口；**不假装**引用未召回材料，也**不说**代码已做脚注 schema 校验。

**可背流程：** 先产出可追溯 hit → 按出处写结论并标证据强度与缺口 → 一路失败仍交已验证部分。

### 面试时怎么说

1. Hybrid 是 **一把 MCP 工具**：`hybrid_search` 里先 `route_query`——强制 mode 优先；没本地索引就 web；关键词 hints 分流；默认 hybrid；权重按 mode 归一。
2. 本地侧分两条时间线：pipeline **建库**写出 `{task_id}.json`；`hybrid_search` **只检索**。`VectorBackend` 当前回退 LocalIndexStore，别说生产向量库已上线。
3. Web 走 Serper；**空 Web 仍可只交本地 fused**；API 挂了返回 `[]`，由 LLM 声明缺口。
4. 融合权重来自 **tool yaml 环境变量**（默认 0.6/0.4），Agent `retrieval.router` 不自动覆盖；加权排序后 **有 url 则按 url 去重（同文档多 chunk 只留最高分）**，url 空才用 `source:chunk_id`，再取 Top K。
5. 返回 JSON 带 **route/reason/mix/两路计数/results**——LLM 据此写报告；引用靠 hit 字段 + Prompt/Directive，**没有**代码级 schema 强校验。

### 易踩坑

- 把 **关键词 hints** 说成语义理解 / 学习型路由。
- 把 **score** 说成置信度或因果强度——只是召回+融合排序分。
- 把 **0.6/0.4** 说成线上调优最优值。
- 把 **`VectorBackend`** 说成 Milvus/PGVector 已生产落地。
- Web **空列表** 就说 Hybrid 整体失败——local 路可能仍有结果。
- 把 **自然语言报告里的引用格式** 说成「JSON schema / 脚注校验已落地」——规格与 §1.3 诚实表已钉：无强校验。
- 把 **同一 source_uri 的多 chunk** 说成融合后会并存——有 url 时去重键是 URL，只留最高分那条。
- 把 **Agent `retrieval.router` 权重** 说成会注入 MCP 子进程——装配链只覆盖 `RETRIEVAL_MODE`。
- **引用未召回材料** 或把推测当事实——工作 Prompt 要求摘录+URL、缺口明示；面试主动划界，别说「绝对禁止编造」这种过度绝对口径。

**下一跳：** [§4 业务知识库与案例](./04-Hybrid-Search-MCP.md#4-业务落地知识库访谈--清洗研报--f19-金融--行为科学两案例)

---

## 4. 业务落地：知识库（访谈 + 清洗研报）+ F19 金融 / 行为科学两案例

### 4.1 前置条件

读到这里应已知（来自 §3）：

1. 本地侧按 `task_id` 隔离索引：`ingest` → `chunk` → `LocalIndexStore` 写入；检索走 `hybrid_search` MCP。
2. 路由、融合、去重与 Top K 已在 §3.3–§3.6 钉死；默认权重 **0.6 / 0.4** 仅是标本基线。
3. 报告层引用靠 `SearchHit` 字段 + Prompt / ResearchDirective，**无**代码级 schema 强校验（§3.8）。

本章回答：**业务知识库实际存什么、怎么维护、与联网结果如何协同**——再用两个 F19 案例把 §3 机制讲成可背故事。

### 4.2 存什么（主口径）

**经授权入库的主内容（钉死）：**

| 类型 | 说明 | 检索侧体现 |
|------|------|------------|
| **访谈材料** | 经授权的研究访谈记录、纪要或转写文本；保留来源与采集上下文 | `SearchHit.source="local"`，`title` / `url`（source_uri）/ `chunk_id` 可回溯 |
| **清洗后的研报** | 经抽取、去噪、结构化后的行业 / 公司研报文本；保留可追溯的来源、版本或更新时间等元数据（以业务可讲为准） | 同上；`snippet` 为 chunk 原文截断，供 Agent 摘录 |

**每个分块至少保留：** 来源标识、标题、`chunk_id`——与 §3.8.1 `SearchHit` 字段对齐，便于回答时回溯「这句话来自哪份材料哪一块」。

**授权与边界（可讲原则，不虚构治理落地细节）：**

- 入库前须有**业务授权**；对外引用时遵守来源与脱敏要求。
- 可讲来源 / 版本 / 更新时间等元数据字段的设计意图；**不宣称**标本已完整落地审批流、权限矩阵或失效自动下架。

**非主库存量（无额外依据时不写成「库里主要有什么」）：**

- 泛化清单如「实验方案大全 / 制度文档全集 / 指标口径百科」等——若面试被追问，应说明**本 Hybrid 本地索引的主口径是访谈 + 清洗研报**；其他材料类型若有，属于扩展场景而非当前主叙述。
- **不虚构**文档条数、向量规模、索引文件大小或「库里有 X 万份研报」类数字。

### 4.3 怎么维护

**标本可核对链路（上传 → 索引）：**

```
上传文件 → 文本抽取 → 分块 → 写入任务索引（按 task_id 隔离）
                ↑
    文本直读 / MarkItDown（PDF·Office 等）
```

1. **上传：** 任务上下文绑定 `task_id`；文件进入 ingest 入口（§3.4 `build_task_index`）。
2. **抽取：** 纯文本直接读；PDF / Office 等走 MarkItDown 转换（与 §2.5 harness 内 scrape→MarkItDown **不同链**——这里是**建库**抽取，不是运行时降级）。
3. **分块：** 默认 `chunk_size=800`、`chunk_overlap=120` 滑窗；每块带 `chunk_id`、标题、`source_uri`。
4. **索引写入：** 当前经 `VectorBackend` **回退** `LocalIndexStore` 写 `{task_id}.json`（§3.4）；不是生产 Milvus/PGVector。
5. **修订：** 新增或更新文档 → **upsert / 重建** 对应任务索引后检索才生效；业务上还应维护来源、版本、更新时间、权限与失效状态——**标本可核对的是抽取与索引写入**，不宣称版本治理或向量库已完整生产落地。

### 4.4 与联网结果融合（链回 §3）

本地知识库**不替代**联网检索，而是与 Web 召回在同一 MCP 工具内按路由协同：

| 步骤 | 机制 | 详见 |
|------|------|------|
| 路由 | 强制 `mode` 优先；无本地索引 → web；hints 分流；默认 hybrid | [§3.3](./04-Hybrid-Search-MCP.md#33-路由route_query) |
| 召回 | local：`LocalIndexStore.search`；web：Serper | [§3.4–§3.5](./04-Hybrid-Search-MCP.md#34-本地建库一条链检索一条链) |
| 融合 | `local_weight` / `web_weight` 加权 → 降序 → URL 或 `source:chunk_id` 去重 → Top K | [§3.6](./04-Hybrid-Search-MCP.md#36-融合weighted_fusion--_dedupe) |
| 报告 | 本地守口径与内部背景；Web 补时效与外部交叉验证；冲突保留双出处 | [§3.8](./04-Hybrid-Search-MCP.md#38-证据链与引用) |

**权重：** 默认 **0.6 / 0.4** 来自 `tool-hybrid-search.yaml` 环境变量，是标本基线，不是业务调优最优值（§3.6 旁注）。

**证据质量（融合后仍须 Agent 判断）：** 排序分高 **≠** 事实更可信；访谈 / 研报原文优先于二手摘要；来源冲突时保留出处与不确定性，不因 Web 分高覆盖经授权的本地材料。

### 4.5 F19 案例一：金融 — 研报与政策归因

<a id="f19-financial"></a>

**场景一句话：** 结合**上传/入库的清洗研报与相关访谈材料**与**近期公开政策**，解释某业务指标为何变化——本地守经授权的内部披露口径（研报与访谈），联网核政策时间与适用范围，只输出两边都能支撑的归因。

**案例骨架（示例问句，可换成真实项目名）：**

1. **问句与路由：** 「结合上传的季度研报与访谈材料，解释本季度毛利率变化；近期行业政策是否有影响？」——含「上传」（local hint）与「近期」「政策」（web hint）→ `route_query` 选 **hybrid**（§3.3）；若该 `task_id` 无本地索引，则降级 web 并在 `reason` 中保留 `no_local_index`。
2. **local 侧：** 从入库的**清洗研报**与**相关访谈材料**抽取毛利率、销量、售价、成本及管理层/受访者表述；经营数据以研报披露或访谈口径为准，**不把未入库的「经营分析表」当作本地主库默认内容**；`SearchHit` 带回 `chunk_id` / `source_uri`；**有页码则引用，无则不强编**。
3. **web 侧：** 查监管部门官网、政策原文、公司公告；核对发布日期、生效范围、适用对象——补时效与外部交叉验证。
4. **融合与归因：** `weighted_fusion` 合并两路（§3.6）；`financial_analyst` Directive 要求归因标 **证据强度** `[已验证]` / `[推断]` / `[推测]`（§3.8.2）。组织顺序：**指标事实 → 内部经营因素（来自研报/访谈披露）→ 外部政策因素 → 证据强弱**；**时间相邻 ≠ 因果**。
5. **缺口处理：** 政策原文适用该行业但研报/访谈未披露量化影响 → 「可能的外部因素，当前证据不足以量化贡献」；Web 一路失败 → 仍交付基于本地研报与访谈的经营归因，**声明政策部分未完成**（§2.5 + §3.8）。

### 4.6 F19 案例二：行为科学 — 相似研究检索与结论校验

<a id="f19-behavioral"></a>

**场景一句话：** 拿**上传/入库的访谈材料**和/或**清洗后的研报**（如关于提醒频率与完成率的访谈纪要 + 清洗后的行为研究类研报），检索公开的相似行为科学研究，判断结论能否迁移——比较机制与边界条件，不是只找标题相似的文章。

**案例骨架（示例问句，可换成真实项目名）：**

1. **问句与路由：** 「结合上传的访谈材料，查找近期相似行为科学研究并评估能否用于产品策略？」——「上传」+「近期」→ **hybrid**。
2. **local 侧：** 从**访谈材料**与**清洗后的研报**抽取样本、对照、干预方式、观察周期、指标定义与局限；主路径仍是访谈 + 清洗研报口径。若问句含「实验报告」，须说明那是**扩展场景、非主库存量**（未入库的原始实验报告不是本地主库默认内容）；不依赖数据库里的量表原始分（那是问数链路，不是本 Hybrid 本地索引主口径）。
3. **web 侧：** 围绕提醒、注意力、习惯形成等**机制**检索高校 / 期刊 / 研究机构**公开页面**；**严禁编造论文标题、作者、页码或 p 值**——`academic` Directive 与 §3.8.2 一致。
4. **可比性三档：** 比较干预机制、目标行为、样本人群、实验环境、指标口径 → 分成 **直接可比 / 机制相似但场景不同 / 仅作背景**；关键词相似 **≠** 实验可比。
5. **边界：** 公开研究与内部实验方向一致，也只说明外部证据增强可解释性，**不能替代**本业务人群上的复验；弱相关材料 → 输出本地结论 + 迁移风险，不强行给推广建议；任一路失败仍交已验证部分并声明缺口。

### 面试时怎么说

1. 知识库主口径是 **经授权的访谈材料 + 清洗后的研报**；每块有来源、标题、`chunk_id`，回答能回溯，**不吹库规模**。
2. 维护走 **上传 → 抽取（直读 / MarkItDown）→ 分块 → 按 task_id 写索引**；改文档就 upsert / 重建；审批 / 权限讲原则，不说标本已全落地。
3. 和联网不是二选一：`hybrid_search` 里先 **route**，再 **local + web 召回**，**0.6/0.4 加权去重**（§3）；本地守口径，Web 补时效。
4. **金融案例**讲清洗研报 + 访谈 + 政策 hybrid 归因，标证据强度，**先后 ≠ 因果**；**行为案例**以访谈材料 + 清洗研报为主路径讲机制与人群边界，**不编论文**。
5. 引用质量靠 hit + Prompt，不说代码做了脚注 schema 校验（§3.8.3）。

### 易踩坑

- 把主库存成 **实验方案 / 制度文档大全**——与业务主口径（访谈 + 清洗研报）不符。
- **虚构**库规模、向量条数、文档数量。
- 把 **LocalIndexStore** 说成生产向量库已上线。
- **编造**研报名称、页码、论文标题或显著性数字。
- 把 **政策发布时间与指标变化先后** 写成确定因果。
- 把 **关键词相似** 等同于实验设计可比。
- 只讲召回 **不讲** 来源、版本、授权与缺口声明。
- 把 **0.6/0.4** 说成业务最优权重。

**下一跳：** [§5 面试题索引 F17–F20](./04-Hybrid-Search-MCP.md#5-面试题索引-f17f20--回看清单)

---

## 5. 面试题索引 F17–F20 + 回看清单

<a id="f17-什么情况走本地检索联网检索或混合检索"></a>
### F17. 什么情况走本地检索、联网检索或混合检索？

- **第一句：** 用户明确指定范围时服从指定；没有指定时，问附件、上传文档或具体页码就优先查本地，问最新新闻、公告、政策或官网就优先联网，两类线索同时出现或意图不明确时默认混合检索。
- **要点：**
  - 当前任务**没有可用本地索引**时，即使提到附件也不能假装查到文件，直接转 web，并在返回 JSON 的 `reason` 中保留路由原因（如 `no_local_index`）。
  - 纯附件 → local；纯时效 → web；例：「总结上传 PDF 第 5 页」→ local，「今天发布了什么行业政策」→ web，「结合附件研报和最新政策解释原因」→ hybrid。`route_query()` 看 query 文本：须**同时**命中 local / web 两类 hint 才因关键词走 hybrid；仅 web hint → web；都未命中 → 默认 hybrid。
  - 混合模式对两路 hit 按配置权重加权（默认 **0.6 / 0.4**），归一后降序排序，按 URL 或 `source:chunk_id` 去重并截 Top K——该数字是标本基线，不是业务最优。
  - 强制 `mode`（`local` / `web` / `hybrid`）优先于 hints；`local` / `web` 模式下对应一路权重归一为 1.0 / 0.0。
- **易踩坑：** 只背 `route_query()` 分支不用业务语言；附件与最新政策同时出现只搜一边；无本地索引仍声称引用了附件；把 hints 说成语义路由。
- **回看标本 + 详见：** `miro-flow-solution/src/retrieval/router.py` 的 `route_query()`；`miro-flow-solution/src/retrieval/fusion.py` 的 `weighted_fusion()` / `_dedupe()`。详见本文 [§3.3 路由](./04-Hybrid-Search-MCP.md#33-路由route_query)、[§3.6 融合](./04-Hybrid-Search-MCP.md#36-融合weighted_fusion--_dedupe)。

<a id="f18-mcp-工具调用成功率-98-是怎么定义的失败后怎么降级"></a>
### F18. MCP 工具调用成功率 98% 是怎么定义的？失败后怎么降级？

- **第一句：** 对齐投顾「工具调用成功率约 98%」——单次 MCP 返回可解析、非空、可继续消费的结果；不是任务成功率 / 答案准确率 / GAIA。
- **要点：** 入口兜错（名纠错、空结果写回）→ **备选工具三层**（harness 内 scrape→MarkItDown；Server 内多路；跨工具/Hybrid 另一路）→ 链路可追踪（`05`）。2% ≈ 外部源偶发 + 模型写错名/参。产品层回退与工具层分开（[`02` 静默回退](./02-集成设计.md) · [`01` P8](./01-通用问答.md#3-遇到的问题汇总)）。
- **易踩坑：** 98% 说成 GAIA；把投顾退避原样安过来；把 MarkItDown 说成 Hybrid 内置；混淆「同一次调用内自动切」与「下一轮 LLM 换工具」。
- **详见：** [§2.5](./04-Hybrid-Search-MCP.md#25-降级备选工具与-98-成功率)；投顾话术见 `agent_project/interview/tell/股票智能投顾_叙述脚本.md`。

### F19. 金融 + 行为科学两类 Hybrid Search 案例

**金融：研报与政策归因**

- **第一句：** 我会用「结合上传/入库的清洗研报与相关访谈材料，以及近期公开政策，解释某业务指标为什么变化」作案例：本地守经授权的内部披露口径，联网补政策发布时间与适用范围，只输出两边都能支撑的归因。
- **要点：**
  - 问句同时含 local / web hints → hybrid；local 从**清洗研报 + 访谈材料**抽指标与管理层/受访者表述；经营数据来自研报/访谈披露，**不把未入库经营分析表当主库默认**；web 核政策原文、公告与适用范围。
  - 融合后按「指标事实 → 经营因素 → 政策因素 → 证据强弱」组织；Directive 标 `[已验证]` / `[推断]` / `[推测]`。
  - **时间相邻 ≠ 因果**；政策适用但无量化披露 → 标「可能外部因素，证据不足以量化」。
  - Web 失败 → 仍交付本地研报与访谈归因并声明政策缺口。
- **易踩坑：** 虚构内部数据或政策效果；把发布时间先后当因果；临场编造研报名称与页码。
- **回看标本 + 详见：** `router.py` / `fusion.py` / `hybrid_search_mcp_server.py`。详见本文 [§4.5 金融案例](./04-Hybrid-Search-MCP.md#45-f19-案例一金融--研报与政策归因)、[§3.8 证据链](./04-Hybrid-Search-MCP.md#38-证据链与引用)。

**行为科学：相似研究检索与结论校验**

- **第一句：** 我会用「拿上传/入库的访谈材料与清洗后的研报（如关于提醒频率与完成率的访谈纪要 + 行为研究类清洗研报），找公开相似行为科学研究，判断结论能否迁移」作案例：比较机制、人群与指标口径，不是只找标题相似的文章。
- **要点：**
  - local 主路径从**访谈材料**与**清洗后的研报**还原实验设计；「实验报告」若出现须标**扩展场景、非主库存量**；web 按**机制**检索公开来源，**不编造论文标题或页码**。
  - 可比性分三档：直接可比 / 机制相似场景不同 / 仅作背景；关键词相似 ≠ 实验可比。
  - 外部证据增强可解释性，**不能替代**本业务人群复验；弱材料 → 本地结论 + 迁移风险。
  - 任一路失败仍交已验证部分并声明缺口。
- **易踩坑：** 编造论文标题、作者或 p 值；忽略样本人群与指标口径差异；把学术结论直接外推到产品用户。
- **回看标本 + 详见：** 同上 + `config/tool/tool-hybrid-search.yaml`（路由 env）。详见本文 [§4.6 行为科学案例](./04-Hybrid-Search-MCP.md#46-f19-案例二行为科学--相似研究检索与结论校验)、[§3.8.2 Directive](./04-Hybrid-Search-MCP.md#382-报告层prompt--researchdirective)。

<a id="f20-knowledge-base"></a>
<a id="f20-知识库存什么怎么维护与联网结果怎么融合排序"></a>
### F20. 知识库存什么、怎么维护、与联网结果怎么融合排序？

- **第一句：** 知识库主内容是经授权的**访谈材料**和**清洗后的研报**；维护走「上传 → 文本抽取 → 分块 → 建索引 → 更新或重建」，检索时按路由把本地召回与联网结果加权、去重后统一排序。
- **要点：**
  - **存什么：** 访谈材料 + 清洗研报；每块保留来源、标题、`chunk_id` 便于回溯；可讲授权与来源 / 版本 / 更新时间元数据；**不虚构**库规模或向量条数。泛化「实验方案 / 制度文档大全」**不是**本库主口径（无额外依据时不写成主存量）。
  - **怎么维护：** 上传 → 直读或 MarkItDown 抽取 → chunk（默认 800 / overlap 120）→ 按 `task_id` 写本地 JSON 索引；修订 upsert / 重建；业务上还应有权限与失效治理——标本可核对抽取与索引，不宣称审批流或生产向量库已完整落地。
  - **怎么融合：** `route_query` 选 local / web / hybrid → 两路召回 → `weighted_fusion`（默认 **0.6 / 0.4** 标本基线）→ 去重 Top K；本地守口径与内部背景，Web 补时效；冲突保留双出处，不因分高覆盖原始材料。
  - `VectorBackend` 当前回退本地索引，别说 Milvus/PGVector 已生产上线。
- **易踩坑：** 把主库存成实验材料 / 制度文档大全；虚构规模；把关键词索引说成生产向量库；只讲召回不讲来源追溯与版本；把默认权重说成调优最优。
- **回看标本 + 详见：** `miro-flow-solution/src/retrieval/ingest.py`；`local_index.py`；`vector_backend.py`；`router.py`；`fusion.py`。详见本文 [§4.2 存什么](./04-Hybrid-Search-MCP.md#42-存什么主口径)、[§4.3 维护](./04-Hybrid-Search-MCP.md#43-怎么维护)、[§4.4 与联网融合](./04-Hybrid-Search-MCP.md#44-与联网结果融合链回-3)、[§3.6 融合](./04-Hybrid-Search-MCP.md#36-融合weighted_fusion--_dedupe)。

### 回看清单

按以下顺序回看，先通用工具链，再 Hybrid 特例，最后业务库与案例：

0. 本文 [§1 地图与诚实边界](./04-Hybrid-Search-MCP.md#1-与上一章的关系--本章地图--诚实边界)：98% / 向量 / 知识库 / 引用口径总表。
1. 注册 Step 1–4：`hybrid_search_mcp_server.py` → `tool-hybrid-search.yaml` → Agent `tool_config` →（可选）`RETRIEVAL_MODE` 注入（§2.2）。
2. 注册 Step 5：`create_mcp_server_parameters` → `ToolManager.__init__` / `server_dict`；进程延后到 list/call（§2.2）。
3. `src/tool/manager.py`：`get_all_tool_definitions` / `execute_tool_call` 超时、纠错、空内容、MarkItDown（§2.3–§2.5）。
4. `src/retrieval/router.py` → `local_index.py` / `web_retriever.py` → `fusion.py` → `hybrid_search_mcp_server.py`（§3 全链）。
5. `src/retrieval/ingest.py`：上传、抽取、分块、索引入口（§4.3）。
6. `config/agent_prompts/sub_worker.py` + [`02` §7.5 ResearchDirective](./02-集成设计.md#75-researchdirective-type-specific-研究指导-prompt)：摘录、URL、证据强度、禁编造引用（§3.8.2）。
7. 对照本文 [§4.5–§4.6](./04-Hybrid-Search-MCP.md#45-f19-案例一金融--研报与政策归因)：金融 / 行为两案例可背骨架。
8. 工程化（追踪 / 熔断 / 断点续跑）→ [`05-工程化能力.md`](./05-工程化能力.md)；编排主线 → [`03`](./03-Main-Sub-Agent编排.md)。
