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

**配置挂载：** Agent YAML（Main 或 Sub）的 `tool_config` 列表引用 `config/tool/{name}.yaml`；`create_mcp_server_parameters` 逐条加载并**只**转成 `StdioServerParameters`（读 `tool_command` + `args`），供 `ToolManager` 初始化——标本 yaml 装配链走 **stdio 子进程**，不读 `url` 字段。

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
    router:                    # 文档/对齐用；装配链未注入子进程
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

- **一条 yaml = 一个 MCP Server 注册项**：Agent `tool_config` 引用后，由 `create_mcp_server_parameters` 加载，`ToolManager` 按配置拉起 stdio 子进程。`name` 即 LLM 调用时的 `server_name`。
- **SSE / URL 诚实边界**：`ToolManager` 类本身在 `execute_tool_call` / `get_all_tool_definitions` 里**能**接受 `http(s)://...` 字符串并走 `sse_client`；但当前 Hydra `tool-*.yaml` → `create_mcp_server_parameters` 路径**未接 URL/SSE**——只产出 `StdioServerParameters`。面试不要说「tool yaml 可配 URL/SSE」；若需远程 MCP，得改装配代码或手工注入 URL 型 `params`。
- Hybrid Search 额外把 Agent 级 `retrieval.mode` 注入子进程环境（`RETRIEVAL_MODE`），与 §3 路由对齐。**权重不走这条链**：`retrieval.router.local_weight` / `web_weight` 在 `create_mcp_server_parameters` 中**未被读取**；MCP 子进程启动时读的是 `tool-hybrid-search.yaml` 的 `env.RETRIEVAL_LOCAL_WEIGHT` / `RETRIEVAL_WEB_WEIGHT`（默认 0.6 / 0.4）。Agent YAML 里的 router 权重仅作配置对齐参考，改它**不会**自动覆盖融合权重，除非同步改 tool yaml 或 OS 环境变量。
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

    # playwright 特例（L327–357）；yaml 装配产出 stdio；类内另有 http(s) URL → sse_client 分支（L404–446），但 yaml 未接通
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
- **`@with_timeout(900)`** 在装饰器外层用 `asyncio.wait_for` 包住整个 `execute_tool_call`；**超时抛出的 `asyncio.TimeoutError` 不会进入函数内 `except`**，而是向上冒泡到 Orchestrator（Main ~L1167、Sub ~L747）。与任务级 14min `wait_for`、预算熔断（见 `05`）是不同层级。

### 2.5 降级分支（关键路径）

| 场景 | 代码锚点 | 行为 |
|------|----------|------|
| **调用超时** | L254 `@with_timeout(900)`；Orchestrator ~L1167 / ~L747 | `asyncio.wait_for` 超时 → `TimeoutError` **逸出** `execute_tool_call` → Orchestrator `except` 捕获 → 构造 `{"error": "[ERROR]: Tool execution timeout"}`（Main）或 `{"error": "Tool call failed: [ERROR]: Tool execution timeout"}`（Sub）→ `format_tool_result_for_user` 写回 message history |
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

1. 工具进系统靠 **YAML 声明式注册**：`tool_config` 列表 → `create_mcp_server_parameters` → 只装配 **stdio 子进程**（`tool_command` + `args`）→ `ToolManager` 持有 Server 字典。`ToolManager` 类能接 URL/SSE，但当前 yaml 路径没接通——别暗示现成可配。
2. **发现**是运行时 `list_tools`，不是写死工具表；**调用**统一走 `execute_tool_call`，Main 和 Sub 各自 Manager，和 `03` 主循环分流一致。
3. **98%** 我讲的是 **单次工具调用的有效结果率**——返回能接着推理的非空内容；不是任务做完的比例，更不是 GAIA 53%。
4. 降级分两层：**工具层**是名纠错、空结果显式反馈、scrape 走 MarkItDown、LLM 换参再调；**900s 工具超时**不在 `execute_tool_call` 内转成 `{"error":...}`，而是 Orchestrator 捕获 `TimeoutError` 后写回 message history。**产品层**才是最终报告不可用或总超时后的静默回退（[`02` D10–D11](./02-面试问答.md#d10-怎么定义失败中间一步失败就整单失败吗)）。
5. Hybrid Search 是 **众多 MCP 之一**（`tool-hybrid-search`），下一章再讲路由与融合；本章先把通用工具链讲清楚。

### 易踩坑

- 把 **98% 说成任务成功率、答案准确率或 GAIA 通过率**——必须拆开定义。
- 把 **MCP 进程启动成功** 等同于调用成功——应以返回内容是否可消费为准。
- 把 **`max_tool_calls_per_turn: 10`** 说成工具并发度——与 [`03`](./03-Main-Sub-Agent编排.md) 相同，是单轮顺序执行上限。
- 把 **MarkItDown 降级** 说成 Hybrid Search 内置——它是 scrape/reading 链的备用，别张冠李戴。
- 把 **0.6 / 0.4** 说成线上最优权重——只是标本基线，§3 再讲。
- 宣称 **生产向量库已落地**——`VectorBackend` 当前回退本地索引，§3 详述。
- 把 **引用质量** 说成代码级 schema 校验——实际是 hit 字段 + Prompt 约束，§3.末再钉。

**下一跳：** [§3 Hybrid Search：路由 → 召回 → 融合 → 证据链](./04-Hybrid-Search-MCP.md#3-hybrid-search路由--召回--融合--mcp-返回--证据链与引用)

---

## 3. Hybrid Search：路由 → 召回 → 融合 → MCP 返回 → 证据链与引用

### 3.1 前置条件

读到这里应已知（来自 §2）：

1. `tool-hybrid-search` 经 YAML 注册为 stdio MCP Server，`ToolManager.execute_tool_call` 统一调 `hybrid_search`。
2. Agent 级 `retrieval.mode` 经 `create_mcp_server_parameters` 注入 `RETRIEVAL_MODE`；融合权重由 tool yaml 环境变量 `RETRIEVAL_LOCAL_WEIGHT` / `RETRIEVAL_WEB_WEIGHT` 提供（§3.5），Agent `retrieval.router` **不覆盖**。
3. **98%** 指单次工具调用返回可消费内容；Hybrid 一路失败时仍可用另一路或已有证据部分完成（§2.6 三级降级）。

本章从 MCP 入口 `hybrid_search` 往下钻：**路由决策 → 本地 / Web 召回 → 加权融合 → JSON 返回 → Agent 如何把 hit 变成可引用结论**。

标本锚点：`src/retrieval/router.py` · `ingest.py` · `local_index.py` · `vector_backend.py` · `web_retriever.py` · `fusion.py` · `schemas.py` · `src/tool/mcp_servers/hybrid_search_mcp_server.py`

### 3.2 路由：`route_query`

**入口参数：** `query`、`has_local_index`（由 `LocalIndexStore.has_index(task_id)` 判定）、`mode`（`auto` / `local` / `web` / `hybrid`）、默认权重 `local_weight=0.6` / `web_weight=0.4`。

**决策顺序（钉死）：**

| 优先级 | 条件 | 选中 mode | reason |
|--------|------|-----------|--------|
| 1 | `mode` 显式为 `local` / `web` / `hybrid` | 强制该 mode | `forced_by_mode` |
| 2 | 无本地索引 | `web` | `no_local_index` |
| 3 | 仅命中 LOCAL_HINTS | `local` | `local_keywords` |
| 4 | 仅命中 WEB_HINTS | `web` | `web_keywords` |
| 5 | 双命中或都未命中 | `hybrid` | `default_hybrid` |

LOCAL_HINTS 示例：`附件`、`上传`、`文档`、`pdf`、`内部`、`第`、`页` …  
WEB_HINTS 示例：`最新`、`今天`、`新闻`、`公告`、`政策`、`官网`、`实时` …

**权重归一：** `local` → `(1.0, 0.0)`；`web` → `(0.0, 1.0)`；`hybrid` → 保留配置权重并按 `local+web` 归一（防无效输入）。

```python
# src/retrieval/router.py · route_query（L31–73，近全文）
def route_query(
    query: str,
    has_local_index: bool,
    mode: str = "auto",
    local_weight: float = 0.6,
    web_weight: float = 0.4,
) -> RoutePlan:
    normalized_mode = (mode or "auto").strip().lower()
    if normalized_mode in ("local", "web", "hybrid"):
        selected = normalized_mode
        reason = "forced_by_mode"
    else:
        lowered = query.lower()
        local_hit = any(hint in lowered for hint in LOCAL_HINTS)
        web_hit = any(hint in lowered for hint in WEB_HINTS)
        if not has_local_index:
            selected = "web"
            reason = "no_local_index"
        elif local_hit and not web_hit:
            selected = "local"
            reason = "local_keywords"
        elif web_hit and not local_hit:
            selected = "web"
            reason = "web_keywords"
        else:
            selected = "hybrid"
            reason = "default_hybrid"

    if selected == "local":
        local_weight, web_weight = 1.0, 0.0
    elif selected == "web":
        local_weight, web_weight = 0.0, 1.0
    else:
        total = max(local_weight + web_weight, 1e-6)
        local_weight, web_weight = local_weight / total, web_weight / total

    return RoutePlan(mode=selected, reason=reason, local_weight=local_weight, web_weight=web_weight)
```

旁注：

- **不是语义路由**——关键词 hints + 强制 mode + 无索引降级；面试别说「已上线学习型路由」。
- `query_mode` 参数非 `auto` 时走强制分支；`auto` 则读环境变量 `RETRIEVAL_MODE`（§2.2 注入）。

### 3.3 本地召回：ingest → chunk → LocalIndexStore

**写入链（索引构建）：**

```python
# ingest.py · build_task_index（签名）
def build_task_index(task_id, file_path, index_dir, backend="local_index", chunk_size=800, chunk_overlap=120) -> dict
```

1. `_convert_file_to_text`：文本直读 / MarkItDown 转 PDF·Office / 兜底 decode。
2. `VectorBackend.upsert_document` → 当前**回退** `LocalIndexStore.write_index`。
3. `chunk_text(text, chunk_size=800, chunk_overlap=120)` 滑窗分块；每块写入 `{task_id}.json`，含 `chunk_id`、`title`、`url`（source_uri）、`text`、`tokens`（`tokenize` 分词）。

**检索链：**

```python
# local_index.py · LocalIndexStore.search（签名）
def search(self, task_id: str, query: str, top_k: int = 5) -> list[SearchHit]
```

- 读 `{index_dir}/{task_id}.json`；query 与 chunk **token 交集 / |query_tokens|** 作 score。
- 返回 `SearchHit(source="local", ..., snippet=text[:500], metadata={"overlap_terms": ...})`。

**VectorBackend 诚实边界：**

```python
# vector_backend.py · 类 docstring + upsert/search
class VectorBackend:
    """Production vector DB adapter placeholder. Current implementation falls back to the local index."""
    # TODO: connect Milvus/PGVector in production mode.
    def upsert_document(...) -> dict:
        return self.local_store.write_index(...)
    def search(...) -> list[SearchHit]:
        return self.local_store.search(...)
```

旁注：接口预留 Milvus/PGVector，**当前全部走本地 JSON 索引**——不要说「生产向量库已完整落地」。

### 3.4 Web 召回：`search_web`

```python
# web_retriever.py · search_web（签名）
async def search_web(query: str, top_k: int = 5) -> list[SearchHit]
```

- 依赖 `SERPER_API_KEY`；无 key 或 HTTP 异常 → **返回空列表**（不抛到 MCP 外层）。
- Serper `organic` 结果映射为 `SearchHit(source="web", ...)`；score 按排名递减 `1.0 - index * 0.05`；`chunk_id=f"web_{index}"`。

旁注：

- Web 空召回**不等于**整次 Hybrid 失败——若路由为 `hybrid` 或 `local`，仍只交本地侧 fused 结果；Agent 应在报告中声明 Web 缺口（§3.7）。

### 3.5 融合：`weighted_fusion` + `_dedupe`

**流程：** 本地 hit × `local_weight`、Web hit × `web_weight` → 合并 → 按 score 降序 → 去重 → 取 Top K（默认 8）。

**去重键（优先级钉死）：**

1. **`hit.url` 非空** → 以 URL 为 key。列表已按 score 降序，故**同一 URL 只保留最高分那条**；其余 chunk 直接丢弃。本地 ingest 时各 chunk 的 `url` 均设为同一 `source_uri`，因此**同一文档的多 chunk 会撞车**，不会并存。
2. **`hit.url` 为空** → 退化为 `f"{hit.source}:{hit.chunk_id}"`，不同 chunk 可并存。

```python
# src/retrieval/fusion.py · _dedupe + weighted_fusion（L4–31，近全文）
def _dedupe(hits: list[SearchHit]) -> list[SearchHit]:
    seen: set[str] = set()
    result: list[SearchHit] = []
    for hit in hits:
        key = hit.url or f"{hit.source}:{hit.chunk_id}"
        if key in seen:
            continue
        seen.add(key)
        result.append(hit)
    return result

def weighted_fusion(
    local_hits: list[SearchHit],
    web_hits: list[SearchHit],
    local_weight: float,
    web_weight: float,
    top_k: int = 8,
) -> list[SearchHit]:
    mixed: list[SearchHit] = []
    for hit in local_hits:
        hit.score = hit.score * local_weight
        mixed.append(hit)
    for hit in web_hits:
        hit.score = hit.score * web_weight
        mixed.append(hit)
    mixed.sort(key=lambda item: item.score, reverse=True)
    return _dedupe(mixed)[:top_k]
```

旁注：

- **权重来源（钉死）：** `hybrid_search_mcp_server.py` 模块加载时读 `RETRIEVAL_LOCAL_WEIGHT` / `RETRIEVAL_WEB_WEIGHT`（来自 `tool-hybrid-search.yaml` 的 `env`，默认 0.6 / 0.4）。`create_mcp_server_parameters` **只覆盖** `RETRIEVAL_MODE`，**不**把 Agent `retrieval.router` 写进子进程 env——面试别说「Agent 配置覆盖了融合权重」。
- **0.6 / 0.4** 是标本默认基线，归一后加权——不是业务最优参数。
- 融合**原地修改** `hit.score`；去重在 score 降序之后执行，保留**先遇到**（即分更高）条目。
- 本地 token 重叠分与 Web 排名分**量纲不同**，加权是工程折中，不是信息检索理论最优。

### 3.6 MCP 返回：`hybrid_search`

```python
# hybrid_search_mcp_server.py · hybrid_search 主流程 + 返回 dict（L22–78，关键段）
@mcp.tool()
async def hybrid_search(query: str, top_k: int = 8, query_mode: str = "auto") -> str:
    task_id = os.environ.get("TASK_ID", "").strip()
    if not task_id:
        return json.dumps({"error": "...", "route": "web"}, ...)

    store = LocalIndexStore(index_dir=INDEX_DIR)
    has_local_index = store.has_index(task_id)
    route = route_query(query=query, has_local_index=has_local_index, mode=..., ...)

    local_hits = store.search(...) if route.mode in ("local", "hybrid") else []
    web_hits = await search_web(...) if route.mode in ("web", "hybrid") else []
    fused_hits = weighted_fusion(local_hits, web_hits, route.local_weight, route.web_weight, top_k)

    return json.dumps({
        "route": route.mode,
        "reason": route.reason,
        "mix": {"local_weight": route.local_weight, "web_weight": route.web_weight},
        "local_hits": len(local_hits),
        "web_hits": len(web_hits),
        "results": [item.to_dict() for item in fused_hits],
    }, ensure_ascii=False, indent=2)
```

**返回 JSON 字段（钉死）：**

| 字段 | 含义 |
|------|------|
| `route` | 最终 mode：`local` / `web` / `hybrid` |
| `reason` | 路由原因码（见 §3.2 表） |
| `mix` | 归一后 `{local_weight, web_weight}` |
| `local_hits` | 本地召回条数（融合前） |
| `web_hits` | Web 召回条数（融合前） |
| `results` | 融合后 `SearchHit.to_dict()` 列表 |

旁注：

- 缺 `TASK_ID` 时直接 error JSON，**无法定位任务索引**——索引按 `task_id` 隔离文件。
- 返回值是 **JSON 字符串**（MCP text content），Orchestrator 写回 message history 供 LLM 消费；无 Pydantic 二次校验。

### 3.7 证据链与引用

Hybrid 的价值不止「搜到东西」——而是先产出**可追溯 hit 列表**，再让 Agent 按出处写结论并标缺口。

#### 3.7.1 工具层：`SearchHit` 字段

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

#### 3.7.2 报告层：Prompt + ResearchDirective

**Sub / Main Prompt（标本可核对）：** `sub_worker.py` 工作阶段要求：

- **Prefer quoting or excerpting original source text**，并 **provide the URL if available**；
- 来源可信度不确定要 **clearly flag**；冲突信息全部保留并标不一致；
- 信息不完整仍交 **partial excerpts** 并标 **uncertainty**；
- **Never assume or guess — if an exact answer cannot be found, say so clearly**（工作阶段口径：有证据优先、缺口明示，而非硬编）。

**Prompt 张力（面试可主动点出）：** 同一文件里，**summarize 阶段**在任务耗尽上下文时会写 *make a well-informed educated guess*——与工作阶段的 *never assume or guess* 并存。面试口径取中间层：**有 hit / 原文就摘录+URL；无证据就声明缺口，不把推测包装成事实**；仅在 summarize 兜底且证据已穷尽时，才允许带标注的推断。

**业务 ResearchDirective（见 [`01` §7.5](./01-集成设计.md#75-researchdirective-type-specific-研究指导-prompt)，交叉引用不整篇复制）：**

| 增强类型 | 引用相关约束（摘要） |
|----------|----------------------|
| `financial_analyst` | 归因须标 **证据强度** `[已验证]` / `[推断]` / `[推测]`；禁止编造未披露数字 |
| `academic` | **严禁编造引用**；预印本须标注；文内 `[作者, 年份]` + 文末清单含 DOI/URL |
| `default` | 通用研究指导 + 声明缺口 |

Directive 是 **prepend 进 task 的 Markdown 指导**，不是编译期 schema——与 Hybrid JSON 返回并行约束 Agent 行为。

#### 3.7.3 诚实边界：无代码级引用强校验

**当前没有：**

- 强制 JSON 引用列表 / 脚注 schema 的 post-processor；
- 对最终报告逐条核对 `chunk_id` 是否存在于 `results` 的编译期保证；
- 分高覆盖原始访谈/研报的自动仲裁——冲突时应**保留双出处 + 不确定性**。

引用质量靠 **结构化 `SearchHit` + Prompt / Directive 软约束**，不是类型系统或 JSON Schema 强校验。面试一句话：

> Hybrid 先产出可追溯 hit 列表；Agent 按出处摘录并标强度/缺口；**不假装**引用未召回材料，也**不说**代码已做脚注 schema 校验。

**可背流程：** 先产出可追溯 hit → 按出处写结论并标证据强度与缺口 → 一路失败仍交已验证部分。

### 面试时怎么说

1. Hybrid 是 **一把 MCP 工具**：`hybrid_search` 里先 `route_query`——强制 mode 优先；没本地索引就 web；关键词 hints 分流；默认 hybrid；权重按 mode 归一。
2. 本地侧 **ingest → chunk → JSON 索引**；`VectorBackend` 只是占位，**现在全回退 LocalIndexStore**，别说生产向量库已上线。
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
2. 路由、融合、去重与 Top K 已在 §3.2–§3.5 钉死；默认权重 **0.6 / 0.4** 仅是标本基线。
3. 报告层引用靠 `SearchHit` 字段 + Prompt / ResearchDirective，**无**代码级 schema 强校验（§3.7）。

本章回答：**业务知识库实际存什么、怎么维护、与联网结果如何协同**——再用两个 F19 案例把 §3 机制讲成可背故事。

### 4.2 存什么（主口径）

**经授权入库的主内容（钉死）：**

| 类型 | 说明 | 检索侧体现 |
|------|------|------------|
| **访谈材料** | 经授权的研究访谈记录、纪要或转写文本；保留来源与采集上下文 | `SearchHit.source="local"`，`title` / `url`（source_uri）/ `chunk_id` 可回溯 |
| **清洗后的研报** | 经抽取、去噪、结构化后的行业 / 公司研报文本；保留可追溯的来源、版本或更新时间等元数据（以业务可讲为准） | 同上；`snippet` 为 chunk 原文截断，供 Agent 摘录 |

**每个分块至少保留：** 来源标识、标题、`chunk_id`——与 §3.7.1 `SearchHit` 字段对齐，便于回答时回溯「这句话来自哪份材料哪一块」。

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

1. **上传：** 任务上下文绑定 `task_id`；文件进入 ingest 入口（§3.3 `build_task_index`）。
2. **抽取：** 纯文本直接读；PDF / Office 等走 MarkItDown 转换（与 §2.5 scrape→MarkItDown **不同链**——这里是**建库**抽取，不是运行时降级）。
3. **分块：** 默认 `chunk_size=800`、`chunk_overlap=120` 滑窗；每块带 `chunk_id`、标题、`source_uri`。
4. **索引写入：** 当前经 `VectorBackend` **回退** `LocalIndexStore` 写 `{task_id}.json`（§3.3）；不是生产 Milvus/PGVector。
5. **修订：** 新增或更新文档 → **upsert / 重建** 对应任务索引后检索才生效；业务上还应维护来源、版本、更新时间、权限与失效状态——**标本可核对的是抽取与索引写入**，不宣称版本治理或向量库已完整生产落地。

### 4.4 与联网结果融合（链回 §3）

本地知识库**不替代**联网检索，而是与 Web 召回在同一 MCP 工具内按路由协同：

| 步骤 | 机制 | 详见 |
|------|------|------|
| 路由 | 强制 `mode` 优先；无本地索引 → web；hints 分流；默认 hybrid | [§3.2](./04-Hybrid-Search-MCP.md#32-路由route_query) |
| 召回 | local：`LocalIndexStore.search`；web：Serper | [§3.3–§3.4](./04-Hybrid-Search-MCP.md#33-本地召回ingest--chunk--localindexstore) |
| 融合 | `local_weight` / `web_weight` 加权 → 降序 → URL 或 `source:chunk_id` 去重 → Top K | [§3.5](./04-Hybrid-Search-MCP.md#35-融合weighted_fusion--_dedupe) |
| 报告 | 本地守口径与内部背景；Web 补时效与外部交叉验证；冲突保留双出处 | [§3.7](./04-Hybrid-Search-MCP.md#37-证据链与引用) |

**权重：** 默认 **0.6 / 0.4** 来自 `tool-hybrid-search.yaml` 环境变量，是标本基线，不是业务调优最优值（§3.5 旁注）。

**证据质量（融合后仍须 Agent 判断）：** 排序分高 **≠** 事实更可信；访谈 / 研报原文优先于二手摘要；来源冲突时保留出处与不确定性，不因 Web 分高覆盖经授权的本地材料。

### 4.5 F19 案例一：金融 — 研报与政策归因

<a id="f19-financial"></a>

**场景一句话：** 结合**上传/入库的清洗研报与相关访谈材料**与**近期公开政策**，解释某业务指标为何变化——本地守经授权的内部披露口径（研报与访谈），联网核政策时间与适用范围，只输出两边都能支撑的归因。

**案例骨架（示例问句，可换成真实项目名）：**

1. **问句与路由：** 「结合上传的季度研报与访谈材料，解释本季度毛利率变化；近期行业政策是否有影响？」——含「上传」（local hint）与「近期」「政策」（web hint）→ `route_query` 选 **hybrid**（§3.2）；若该 `task_id` 无本地索引，则降级 web 并在 `reason` 中保留 `no_local_index`。
2. **local 侧：** 从入库的**清洗研报**与**相关访谈材料**抽取毛利率、销量、售价、成本及管理层/受访者表述；经营数据以研报披露或访谈口径为准，**不把未入库的「经营分析表」当作本地主库默认内容**；`SearchHit` 带回 `chunk_id` / `source_uri`；**有页码则引用，无则不强编**。
3. **web 侧：** 查监管部门官网、政策原文、公司公告；核对发布日期、生效范围、适用对象——补时效与外部交叉验证。
4. **融合与归因：** `weighted_fusion` 合并两路（§3.5）；`financial_analyst` Directive 要求归因标 **证据强度** `[已验证]` / `[推断]` / `[推测]`（§3.7.2）。组织顺序：**指标事实 → 内部经营因素（来自研报/访谈披露）→ 外部政策因素 → 证据强弱**；**时间相邻 ≠ 因果**。
5. **缺口处理：** 政策原文适用该行业但研报/访谈未披露量化影响 → 「可能的外部因素，当前证据不足以量化贡献」；Web 一路失败 → 仍交付基于本地研报与访谈的经营归因，**声明政策部分未完成**（§2.6 三级降级 + §3.7）。

### 4.6 F19 案例二：行为科学 — 相似研究检索与结论校验

<a id="f19-behavioral"></a>

**场景一句话：** 拿**上传/入库的访谈材料**和/或**清洗后的研报**（如关于提醒频率与完成率的访谈纪要 + 清洗后的行为研究类研报），检索公开的相似行为科学研究，判断结论能否迁移——比较机制与边界条件，不是只找标题相似的文章。

**案例骨架（示例问句，可换成真实项目名）：**

1. **问句与路由：** 「结合上传的访谈材料，查找近期相似行为科学研究并评估能否用于产品策略？」——「上传」+「近期」→ **hybrid**。
2. **local 侧：** 从**访谈材料**与**清洗后的研报**抽取样本、对照、干预方式、观察周期、指标定义与局限；主路径仍是访谈 + 清洗研报口径。若问句含「实验报告」，须说明那是**扩展场景、非主库存量**（未入库的原始实验报告不是本地主库默认内容）；不依赖数据库里的量表原始分（那是问数链路，不是本 Hybrid 本地索引主口径）。
3. **web 侧：** 围绕提醒、注意力、习惯形成等**机制**检索高校 / 期刊 / 研究机构**公开页面**；**严禁编造论文标题、作者、页码或 p 值**——`academic` Directive 与 §3.7.2 一致。
4. **可比性三档：** 比较干预机制、目标行为、样本人群、实验环境、指标口径 → 分成 **直接可比 / 机制相似但场景不同 / 仅作背景**；关键词相似 **≠** 实验可比。
5. **边界：** 公开研究与内部实验方向一致，也只说明外部证据增强可解释性，**不能替代**本业务人群上的复验；弱相关材料 → 输出本地结论 + 迁移风险，不强行给推广建议；任一路失败仍交已验证部分并声明缺口。

### 面试时怎么说

1. 知识库主口径是 **经授权的访谈材料 + 清洗后的研报**；每块有来源、标题、`chunk_id`，回答能回溯，**不吹库规模**。
2. 维护走 **上传 → 抽取（直读 / MarkItDown）→ 分块 → 按 task_id 写索引**；改文档就 upsert / 重建；审批 / 权限讲原则，不说标本已全落地。
3. 和联网不是二选一：`hybrid_search` 里先 **route**，再 **local + web 召回**，**0.6/0.4 加权去重**（§3）；本地守口径，Web 补时效。
4. **金融案例**讲清洗研报 + 访谈 + 政策 hybrid 归因，标证据强度，**先后 ≠ 因果**；**行为案例**以访谈材料 + 清洗研报为主路径讲机制与人群边界，**不编论文**。
5. 引用质量靠 hit + Prompt，不说代码做了脚注 schema 校验（§3.7.3）。

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
- **回看标本 + 详见：** `miro-flow-solution/src/retrieval/router.py` 的 `route_query()`；`miro-flow-solution/src/retrieval/fusion.py` 的 `weighted_fusion()` / `_dedupe()`。详见本文 [§3.2 路由](./04-Hybrid-Search-MCP.md#32-路由route_query)、[§3.5 融合](./04-Hybrid-Search-MCP.md#35-融合weighted_fusion--_dedupe)。

<a id="f18-mcp-工具调用成功率-98-是怎么定义的失败后怎么降级"></a>
### F18. MCP 工具调用成功率 98% 是怎么定义的？失败后怎么降级？

- **第一句：** 98% 指单次 MCP 工具调用返回了可解析、非空且可被 Agent 继续消费的有效结果，不是深度研究任务成功率，更不代表最终结论准确率。
- **要点：**
  - 统计口径以**单次工具调用**为分母：成功 = 未超时 + 协议正常 + 结果非空 + 结构可解析 + Agent 可继续消费；连接成功但空召回、错误文本或不可解析 JSON 不算成功。
  - 常见失败：超时、无有效召回、结构异常；Server 名唯一命中时可自动纠错；scrape 失败可切 MarkItDown 备用读取。
  - **工具层降级顺序（可背）：** 同工具限次重试或名纠错 → 备选工具 / 来源 → 基于已有证据部分完成；部分完成仍输出已验证结论并声明缺口。
  - **产品层回退**（分开记）：最终报告不可用或总超时才静默回退描述性解读（[`02` D10–D11](./02-面试问答.md#d10-怎么定义失败中间一步失败就整单失败吗)）。
  - 工具成功率与任务成功率必须分开统计——多跳规划、证据冲突、归纳阶段仍可能失败。
- **易踩坑：** 把 98% 说成 GAIA 通过率或答案准确率；把进程启动成功当调用成功；单步失败丢弃全部已有证据；把 MarkItDown 说成 Hybrid 内置能力。
- **回看标本 + 详见：** `miro-flow-solution/src/tool/manager.py` 的 `execute_tool_call()`；`miro-flow-solution/src/tool/mcp_servers/hybrid_search_mcp_server.py`；`miro-flow-solution/config/tool/tool-hybrid-search.yaml`。详见本文 [§2.4–§2.6](./04-Hybrid-Search-MCP.md#24-调用execute_tool_call-统一入口)、[§3.6 MCP 返回](./04-Hybrid-Search-MCP.md#36-mcp-返回hybrid_search)。

<a id="f19-cases"></a>
<a id="f19-金融--行为科学两类-hybrid-search-案例"></a>
### F19. 金融 + 行为科学两类 Hybrid Search 案例

**金融：研报与政策归因**

- **第一句：** 我会用「结合上传/入库的清洗研报与相关访谈材料，以及近期公开政策，解释某业务指标为什么变化」作案例：本地守经授权的内部披露口径，联网补政策发布时间与适用范围，只输出两边都能支撑的归因。
- **要点：**
  - 问句同时含 local / web hints → hybrid；local 从**清洗研报 + 访谈材料**抽指标与管理层/受访者表述；经营数据来自研报/访谈披露，**不把未入库经营分析表当主库默认**；web 核政策原文、公告与适用范围。
  - 融合后按「指标事实 → 经营因素 → 政策因素 → 证据强弱」组织；Directive 标 `[已验证]` / `[推断]` / `[推测]`。
  - **时间相邻 ≠ 因果**；政策适用但无量化披露 → 标「可能外部因素，证据不足以量化」。
  - Web 失败 → 仍交付本地研报与访谈归因并声明政策缺口。
- **易踩坑：** 虚构内部数据或政策效果；把发布时间先后当因果；临场编造研报名称与页码。
- **回看标本 + 详见：** `router.py` / `fusion.py` / `hybrid_search_mcp_server.py`。详见本文 [§4.5 金融案例](./04-Hybrid-Search-MCP.md#45-f19-案例一金融--研报与政策归因)、[§3.7 证据链](./04-Hybrid-Search-MCP.md#37-证据链与引用)。

**行为科学：相似研究检索与结论校验**

- **第一句：** 我会用「拿上传/入库的访谈材料与清洗后的研报（如关于提醒频率与完成率的访谈纪要 + 行为研究类清洗研报），找公开相似行为科学研究，判断结论能否迁移」作案例：比较机制、人群与指标口径，不是只找标题相似的文章。
- **要点：**
  - local 主路径从**访谈材料**与**清洗后的研报**还原实验设计；「实验报告」若出现须标**扩展场景、非主库存量**；web 按**机制**检索公开来源，**不编造论文标题或页码**。
  - 可比性分三档：直接可比 / 机制相似场景不同 / 仅作背景；关键词相似 ≠ 实验可比。
  - 外部证据增强可解释性，**不能替代**本业务人群复验；弱材料 → 本地结论 + 迁移风险。
  - 任一路失败仍交已验证部分并声明缺口。
- **易踩坑：** 编造论文标题、作者或 p 值；忽略样本人群与指标口径差异；把学术结论直接外推到产品用户。
- **回看标本 + 详见：** 同上 + `config/tool/tool-hybrid-search.yaml`（路由 env）。详见本文 [§4.6 行为科学案例](./04-Hybrid-Search-MCP.md#46-f19-案例二行为科学--相似研究检索与结论校验)、[§3.7.2 Directive](./04-Hybrid-Search-MCP.md#372-报告层prompt--researchdirective)。

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
- **回看标本 + 详见：** `miro-flow-solution/src/retrieval/ingest.py`；`local_index.py`；`vector_backend.py`；`router.py`；`fusion.py`。详见本文 [§4.2 存什么](./04-Hybrid-Search-MCP.md#42-存什么主口径)、[§4.3 维护](./04-Hybrid-Search-MCP.md#43-怎么维护)、[§4.4 与联网融合](./04-Hybrid-Search-MCP.md#44-与联网结果融合链回-3)、[§3.5 融合](./04-Hybrid-Search-MCP.md#35-融合weighted_fusion--_dedupe)。

### 回看清单

按以下顺序回看，先通用工具链，再 Hybrid 特例，最后业务库与案例：

0. 本文 [§1 地图与诚实边界](./04-Hybrid-Search-MCP.md#1-与上一章的关系--本章地图--诚实边界)：98% / 向量 / 知识库 / 引用口径总表。
1. `config/tool/tool-hybrid-search.yaml` + `config/agent_server.yaml`：工具注册与 `RETRIEVAL_MODE` 注入（§2.2）。
2. `src/tool/manager.py`：`execute_tool_call` 超时、纠错、空内容、MarkItDown（§2.4–§2.5）。
3. `src/retrieval/router.py` → `local_index.py` / `web_retriever.py` → `fusion.py` → `hybrid_search_mcp_server.py`（§3 全链）。
4. `src/retrieval/ingest.py`：上传、抽取、分块、索引入口（§4.3）。
5. `config/agent_prompts/sub_worker.py` + [`01` §7.5 ResearchDirective](./01-集成设计.md#75-researchdirective-type-specific-研究指导-prompt)：摘录、URL、证据强度、禁编造引用（§3.7.2）。
6. 对照本文 [§4.5–§4.6](./04-Hybrid-Search-MCP.md#45-f19-案例一金融--研报与政策归因)：金融 / 行为两案例可背骨架。
7. 工程化（追踪 / 熔断 / 断点续跑）→ [`05-工程化能力.md`](./05-工程化能力.md)；编排主线 → [`03`](./03-Main-Sub-Agent编排.md)。
