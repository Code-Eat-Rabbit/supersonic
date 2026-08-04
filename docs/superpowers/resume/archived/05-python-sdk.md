# SuperSonic Python SDK — 简历文案 + 面试预案

> 三层架构（SDK + CLI + MCP 规划）· 对标 open-metadata/ai-sdk · pydantic v2 + httpx + typer · 230 测试 94% 覆盖率

---

## 简历文案（终版）

> 开发 SuperSonic Python SDK（对标 open-metadata/ai-sdk），覆盖语义层建模（domain/model/dimension/metric CRUD）与多范式查询（S2SQL / 自然语言 / 结构化指标）全闭环；设计三层架构（SDK + CLI + MCP 规划），SDK 层 37 方法 + 154 单元测试 + 95% 覆盖率，CLI 层 38 命令 + typer + rich 表格双格式输出 + 5 类语义化退出码（Agent 友好），全流程 TDD + 两阶段代码审查（规格合规 + 代码质量）。

---

## ① 30 秒概括

> "SuperSonic 是腾讯开源的 Chat BI + Headless BI 平台，之前只有 Java SDK，缺 Python 生态接入。我做了三件事：第一，**Python SDK**——37 个方法（5 查询 + 32 元数据 CRUD），pydantic v2 模型 + httpx 双栈（同步 + opt-in 异步）+ 资源特化异常树（`MetricNotFoundError` 这种），154 个单元测试，95% 覆盖率。第二，**CLI 子包**——38 个命令镜像 SDK 命名空间，typer + rich，支持 TOML/dotenv 双配置 + 6 层优先级链 + 5 类语义化退出码，让 bash Agent（Claude Code / Cursor）能直接调用。第三，**MCP Server 经评估后主动跳过**——YAGNI 原则，CLI 已覆盖 Agent 调用场景，MCP 仅对 Claude Desktop（无 bash）有增量价值。
>
> 全流程对标 open-metadata/ai-sdk 的设计模式：门面 + 资源命名空间、opt-in async、资源特化异常、pytest-httpx mock、src layout + hatchling。工程上走完整闭环：规格 → 评审 → 计划 → 评审 → TDD 实现 → 两阶段审查。"

---

## ② 背景与动机

### 场景设定

SuperSonic 作为 Headless BI 平台，对外只有 Java SDK（`SemanticLayerService` 接口）。Python 是数据科学、AI Agent、自动化测试的主语言，缺 Python SDK 等于堵死这些场景。

### 痛点 1：Python 生态接入门槛高

数据科学家想在 Jupyter 里查指标，运维想在 CI/CD 里做 schema 巡检，AI Agent 想通过 bash 调用 SuperSonic——这些都需要 Python 接入。没有 Python SDK，用户只能手写 `requests.post(...)` 拼 REST 调用，没有类型提示、没有异常映射、没有重试。

### 痛点 2：CLI / Agent 工具链缺失

2026 年的 AI Agent 生态（Claude Code / Cursor / Aider）依赖命令行接口。仅靠 REST API 不够——需要稳定的 stdout 格式、语义化退出码、配置文件支持，才能让 Agent 程序化调用。

### 痛点 3：简历需要差异化

"做了一个 HTTP wrapper" 在 2026 年的简历池里是 commodity。需要对标业界成熟项目（open-metadata/ai-sdk）的设计深度，才能在面试中讲出工程决策。

---

## ③ 技术方案

### 整体架构：三层

```
┌──────────────────────────────────────────────────┐
│  Phase 3: MCP Server（规划，经评估主动跳过）      │  Agent 协议层
│  YAGNI：CLI 已覆盖 Claude Code/Cursor 场景        │  Claude Desktop 才需要
├──────────────────────────────────────────────────┤
│  Phase 2: CLI（38 命令）                         │  人 + Agent 通用入口
│  typer + rich · TOML/dotenv 配置 · 5 类退出码    │  bash 调用，稳定 stdout
├──────────────────────────────────────────────────┤
│  Phase 1: Python SDK（37 方法）                  │  编程接入
│  门面 + 资源命名空间 · pydantic v2 · httpx       │  Python 开发者/数据科学家
├──────────────────────────────────────────────────┤
│  SuperSonic Headless REST API (/api/semantic/*)  │  源
└──────────────────────────────────────────────────┘
```

### SDK 层核心设计（Phase 1）

#### 门面 + 资源命名空间（对标 ai-sdk 的 `AISdk` + `AgentsAPI`）

```python
from supersonic import SupersonicClient

with SupersonicClient.from_env() as client:
    # 7 个资源命名空间，懒加载 property
    result = client.query.sql("SELECT 销售额 FROM 销售表")
    page = client.metrics.list(model_id=10, page=1, page_size=20)
    metric = client.metrics.create(MetricCreateReq(
        model_id=10, name="销售额", biz_name="sales_amt",
        define_type="MEASURE", expression="pay_amt",
    ))
```

**关键决策**：
- `SupersonicClient` **只装配不请求**——业务调用走 `client.metrics.list()` 等命名空间
- 每个资源类（`MetricsAPI`）**不持有 host/token**——只持有注入的 HTTPClient
- 调用 HTTP 时显式传 `resource_type="metric"`，让 HTTP 层能抛出 `MetricNotFoundError` 而非通用 `NotFoundError`

#### 双栈 HTTP 层（同步 + opt-in 异步）

```python
# 默认同步（CLI/脚本/Jupyter 场景）
client = SupersonicClient(host=..., token=...)

# 显式开启异步（FastAPI/MCP Server 场景）
client = SupersonicClient(host=..., token=..., enable_async=True)
result = await client.query.asql("SELECT ...")
```

**关键决策**：Opt-in async（对标 ai-sdk）而非默认 async。
- 默认 sync 满足 CLI、脚本、Jupyter
- async client 懒加载（不在 `__init__` 创建 `AsyncClient`，避免事件循环绑定问题）
- Phase 1 仅 QueryAPI 有 `asql()`，元数据 CRUD 的 async 留作 v0.2（YAGNI）

#### 资源特化异常树

```
SupersonicError                    # 根
├── AuthenticationError            # 401
├── ValidationError                # 400（携带 field_errors: list[FieldError]）
├── RateLimitError                 # 429（携带 retry_after）
├── ServerError                    # 5xx
├── AsyncNotEnabledError           # 调用 async 方法但未启用
└── ResourceNotFoundError          # 404 基类
    ├── MetricNotFoundError        # 含 .resource_id
    ├── DatasetNotFoundError
    └── ...（6 个资源特化）
```

**价值**：用户可以 `except MetricNotFoundError:` 精准 catch，而不是 catch 一个模糊的 `NotFoundError` 后还要解析 message。

#### ChatQueryResult 的 detailed 双模式

```python
# 完整模式（默认）：开发者调试用，看解析过程
full = client.query.chat("销售额最高的产品")
print(full.selected_parse.sql)      # 看 LLM 生成的 S2SQL
print(full.candidate_parses)         # 看候选解析
print(full.time_cost.parse_time)     # 看各阶段耗时

# 简洁模式：数据分析师用，只要结果
result = client.query.chat("...", detailed=False)
print(result.result_rows)            # 直接拿数据
```

用 `@overload` + `Literal[True/False]` 实现类型收窄，mypy/pyright 能根据 `detailed` 值推断返回类型。

### CLI 层核心设计（Phase 2）

#### 命令镜像 SDK 命名空间

```bash
# SDK: client.metrics.list(model_id=10)
# CLI: supersonic metric list --model-id 10

# SDK: client.query.chat("...", detailed=False)
# CLI: supersonic query chat --text "..." --concise

# SDK: client.metrics.publish([1, 2, 3])
# CLI: supersonic metric publish --ids 1,2,3
```

学习成本最低——学会 SDK 即会用 CLI，反之亦然。

#### 6 层配置优先级链

```
1. CLI 参数（--host/--token）           ← 最高
2. 环境变量（SUPERSONIC_HOST）
3. --config FILE（TOML）
4. --env-file FILE（dotenv）
5. ~/.supersonic/config.toml（默认路径）
6. 代码默认值                            ← 最低
```

覆盖开发/测试/生产切换场景，CI 临时覆盖环境变量优于配置文件。

#### 5 类语义化退出码（Agent 友好）

| Code | 含义 | Agent 行为 |
|---|---|---|
| 0 | 成功 | 解析 stdout |
| 1 | 通用客户端错误 | 报告给用户 |
| 2 | 认证错误（401） | 重新获取 token 后重试 |
| 3 | 未找到（404） | 报告资源缺失，不重试 |
| 4 | 校验错误（400） | 展开字段级错误给用户修正 |
| 5 | 服务器错误（5xx） | 等待后重试或切换实例 |

稳定的退出码让 Agent 可程序化处理失败。

### 工程流程（完整闭环）

```
规格设计 → 规格评审（14 问题）→ 规格修订
    ↓
实现计划 → 计划评审（10 问题）→ 计划修订
    ↓
TDD 实现（26 任务，每任务：编写测试 → 验证失败 → 实现 → 验证通过 → commit）
    ↓
两阶段审查（规格合规 + 代码质量）
    ↓
最终审查 → 修复 → READY_FOR_RELEASE
```

**关键数字**：

| 维度 | 数据 |
|---|---|
| SDK 方法数 | 37（5 query + 32 元数据 CRUD） |
| CLI 命令数 | 38（镜像 SDK 命名空间） |
| 单元测试 | 230（154 SDK + 76 CLI） |
| 覆盖率 | 94% |
| ruff/mypy | 0 error（strict 模式） |
| 规格评审问题 | 14（全部修复） |
| 计划评审问题 | 10（全部修复） |

---

## ④ 面试追问 Q&A

### Q1：为什么对标 open-metadata/ai-sdk？它有什么设计值得学？

**A：** ai-sdk 是 OpenMetadata 平台的 Python SDK，把元数据能力暴露给 LLM Agent。我学了它 5 个核心模式：

1. **门面 + 资源命名空间**：`AISdk` 只装配不请求，`.agents` / `.memories` 等命名空间各管一摊
2. **Opt-in async**：同类双方法 `call/acall`，`enable_async=True` 才实例化 async client
3. **资源特化异常**：`AgentNotFoundError(.agent_name)` 比通用 `NotFoundError` 更可调试
4. **pytest-httpx mock**：单元测试零真实网络，`httpx_mock.add_response(url=...)`
5. **extras 模式**：核心包仅 2 依赖（httpx + pydantic），重集成走 `[langchain]`

但我也做了**不同于 ai-sdk 的改进**：
- ai-sdk 的分页用 `mapper: Callable[[dict], T]`，我改用 `Page.from_response(item_model=T)` 直接复用 pydantic 的 `model_validate`，少传一个函数
- ai-sdk 的 `models.py` 单文件 647 行，我按资源拆分到 `models/` 子包，每个文件 50-150 行

---

### Q2：为什么 CLI 命令要镜像 SDK 命名空间？这不是机械重复吗？

**A：** 不是机械重复，是**有意的设计决策**。三个理由：

1. **学习成本最低**：用户学会 SDK 即会用 CLI（`client.metrics.list()` ↔ `supersonic metric list`），反之亦然。CLI 文件是薄包装（700-900 行），所有业务逻辑在 SDK
2. **Agent 友好**：稳定的命令结构 = 稳定的工具调用。Claude Code 学会 `supersonic metric list` 后，看到 `supersonic dimension list` 也能举一反三
3. **维护成本低**：SDK 改了方法签名，CLI 只改对应命令的参数映射，不需要重新设计命令结构

**代价**：命令数多（38 个），但每个都很简单（平均 30-50 行）。如果按"用户场景"重组（如方案 ②），用户要记两套概念（SDK 的命名空间 + CLI 的场景分类），反而更混乱。

---

### Q3：为什么用 typer 而不是 click？

**A：** typer 是 click 的超集（typer 内部 import click），但用类型注解定义命令，样板代码减半。对比：

```python
# click（样板多）
@click.command()
@click.option("--model-id", type=int, required=True)
@click.option("--page", type=int, default=1)
def list_metrics(model_id, page):
    ...

# typer（类型注解即定义）
@app.command()
def list_cmd(model_id: int = typer.Option(...), page: int = typer.Option(1)):
    ...
```

typer 还自带 rich 集成（彩色表格输出）、自动生成 help、`--install-completion`。代价是多一层抽象，但 typer 0.9+ 已稳定。

**实际踩坑**：typer 0.24 的 `no_args_is_help=True` + callback 的 `--version` 选项有冲突——`--version` 被"无子命令"逻辑拦截。解决方案是把 `--version` 改为独立的 `supersonic version` 命令（typer 0.24+ 推荐做法）。

---

### Q4：为什么 chat 查询要做 detailed 双模式？

**A：** Chat BI 的查询结果与普通查询不同——它包含**解析过程信息**（选中的 S2SQL、候选解析、各阶段耗时）。这些对开发者调试有用，但对数据分析师是噪音。

```python
# 默认 detailed=True：返回 ChatQueryResult（含 selected_parse / candidate_parses / time_cost）
# detailed=False：返回 QueryResult（仅 columns + result_rows）
```

用 `@overload` + `Literal[True/False]` 实现类型收窄——mypy 能根据 `detailed` 值推断返回类型，IDE 自动补全准确。简洁模式解析失败时显式抛 `ServerError`（而非返回 None），避免"用户困惑为什么结果是 None"。

---

### Q5：为什么不做 MCP Server？CLI 不够吗？

**A：** 这是我做过的一个重要 YAGNI 决策。分析如下：

**MCP 的唯一不可替代场景**：Claude Desktop（无 bash 工具，只能用 MCP 协议调用工具）。

**CLI 已覆盖的场景**：Claude Code / Cursor / Aider 等"能 bash 的 Agent"——`--json` 输出结构化数据 + 5 类语义化退出码 + 错误到 stderr，Agent 调用体验已经很好。

**跳过的理由**：
1. **我的实际场景是 Claude Code**：CLI 完全覆盖，MCP 是冗余
2. **Claude Desktop 用户极少**：2026 年大多数开发者用 Claude Code / Cursor
3. **维护成本**：多一个子包、多一份测试、多一份文档，但解决的是"假想用户用 Claude Desktop"的场景
4. **简历深度 > 广度**：与其做 3 个浅层子包，不如把 SDK + CLI 做深

**如果未来需要**：MCP Server 是 Phase 1 SDK 的薄包装（预估 400-600 行），因为 SDK 已有 37 方法的完整实现。1-2 天即可完成。我在规格里保留了 Phase 3 的设计草案（工具映射、stdio 传输、对标 ai-sdk 的 MCP 子包），作为"已规划但主动跳过"的工程决策记录。

**面试补充**：这个决策本身就是一个可讲述的工程判断——"不是所有热门技术都要追，要分析实际场景的增量价值"。

---

### Q6：资源特化异常（MetricNotFoundError 等）有什么实际价值？

**A：** 比通用 `NotFoundError` 好三个维度：

```python
# 用户可以精准 catch
try:
    metric = client.metrics.get(99)
except MetricNotFoundError as e:
    print(f"指标 {e.resource_id} 不存在")  # e.resource_id == 99
    # 不需要解析 e.message 提取 ID
except DatasetNotFoundError:
    pass  # 不同资源不同处理
```

1. **精准 catch**：`except MetricNotFoundError:` vs `except NotFoundError:` 后还要判断 message
2. **携带结构化字段**：`e.resource_id` / `e.resource_type`，便于程序化处理
3. **HTTP 层映射**：`_handle_response` 根据 `resource_type` 参数（资源类调用时传入）映射到正确的异常类

**实现机制**：`_NOT_FOUND_MAP: dict[str, type[ResourceNotFoundError]]` 把字符串 `"metric"` 映射到 `MetricNotFoundError` 类。资源类调用 `http.request(resource_type="metric", resource_id=metric_id)`，HTTP 层 404 时查 map 抛对应异常。

---

### Q7：6 层配置优先级链是否过度设计？

**A：** 表面看 6 层多，但每一层都对应真实场景：

| 层 | 场景 | 举例 |
|---|---|---|
| CLI 参数 | 临时调试 | `supersonic --host http://staging:9080 metric list` |
| 环境变量 | CI/CD | GitLab CI 的 variables |
| `--config` TOML | 生产配置 | `~/.supersonic/config.toml` 含结构化 retry 配置 |
| `--env-file` dotenv | 团队习惯 | 已有 `.env` 工作流的团队 |
| 默认路径 | 零配置 | 放 `~/.supersonic/config.toml` 自动加载 |
| 代码默认值 | 兜底 | `timeout=30.0` 等 |

如果砍掉任何一层，对应场景的用户就要 workaround。比如砍掉 `--env-file`，用 dotenv 的团队要把 `.env` 手动 `source` 后再跑 CLI，体验差。

**`--config` 与 `--env-file` 互斥**：避免配置源歧义（同时指定报错），这是清晰性优先于灵活性的决策。

---

### Q8：为什么 Phase 1 的 async 只支持 QueryAPI，元数据 CRUD 不支持？

**A：** 务实的优先级判断：

- **QueryAPI 的 async 是核心场景**：Web 后端（FastAPI）并发查询、MCP Server 并发工具调用
- **元数据 CRUD 的 async 优先级低**：建模型/改指标是低频操作，同步足够；CLI 也是同步调用

如果 Phase 1 强行做全部 async，每个资源类要多写 5-7 个 async 方法（`alist/aget/acreate/aupdate/adelete`），共 30+ 方法，实现周期翻倍。而 Phase 1 的核心价值是"完整覆盖查询 + 元数据管理"，async 是锦上添花。

**实现策略**：资源类的 `__init__` 接受 `async_http: AsyncHTTPClient | None` 参数，保留接口一致性，Phase 1 不暴露 async 方法，v0.2 补全时无需改构造函数。

---

### Q9：规格评审和计划评审各发现了什么问题？修复成本高吗？

**A：** 评审是这套流程的核心价值——发现问题比修复成本低。

**规格评审（14 问题）**：
- AsyncHTTPClient 未定义（必须修复）→ 补完整定义 + 懒加载设计
- API 端点路径未映射 → 加 `api/paths.py` 集中管理 37 个端点
- pyproject.toml 零配置 → 补完整配置（hatchling + extras + ruff + mypy）
- ValidationError 不解析字段级错误 → 加 `FieldError` + `_parse_field_errors`
- 6 个建议修改 + 3 个参考

**计划评审（10 问题）**：
- TDD 流程破坏（任务 14-20 测试依赖未实现的 Client）→ 加 API 级 fixture 解耦
- 30+ async 方法标 NotImplementedError → 明确声明 Phase 1 仅 QueryAPI 支持 async
- `_parse_retry_after` 重复定义 → 删除 config.py 的死代码

**修复成本**：规格修复 ~2 小时，计划修复 ~1 小时。但如果这些问题在实现阶段才暴露，修复成本是 5-10 倍（要改已写的代码 + 重跑测试）。评审的 ROI 极高。

---

### Q10：整个项目的工程流程是什么？为什么走这么重的流程？

**A：** 流程：`规格 → 评审 → 计划 → 评审 → TDD 实现 → 两阶段审查`。

为什么走这么重？因为这个项目不是为了"快速出代码"，而是为了"**简历能讲清楚每个决策**"。

- **规格**：锁定设计决策（为什么 opt-in async、为什么资源特化异常）
- **评审**：暴露未考虑的边界（AsyncHTTPClient 的事件循环绑定、端点路径变更影响面）
- **计划**：锁定任务分解（每个任务有完整代码块，无占位符）
- **TDD**：保证每个功能有测试，覆盖率 94%
- **两阶段审查**：规格合规（不多做不少做）+ 代码质量（mypy strict / ruff）

**面试价值**：面试官问"你怎么保证代码质量"，回答"每个任务都有规格审查 + 代码质量审查，mypy strict 0 error，94% 覆盖率"比"我写完了跑了一下没报错"有说服力得多。

---

## ⑤ 方法论沉淀

1. **对标成熟项目**：选一个业界 reference 实现（ai-sdk），学它的设计模式，但做有意的改进——面试时能讲"学了什么 + 改了什么"
2. **评审闭环**：规格评审 → 计划评审 → 代码审查，每层发现问题都比下层修复成本低 5-10 倍
3. **YAGNI 主动跳过**：MCP Server 经评估后主动跳过——不是所有热门技术都要追，要分析实际场景的增量价值。跳过本身也是可讲述的工程决策
4. **薄包装 + 复用**：CLI 是 SDK 的薄包装（700-900 行），MCP 也会是 SDK 的薄包装——上层依赖下层，下层改了上层自动跟随

---

## ⑥ 附录：产出物

| 产出 | 数量/规模 |
|---|---|
| 设计规格 | 2 份（SDK 1770 行 + CLI 816 行） |
| 实现计划 | 2 份（SDK 4882 行 + CLI 3201 行） |
| 评审报告 | 3 份（规格 14 问题 + 计划 10 问题 + 最终审查 2 bug） |
| 源代码 | ~3500 行（SDK 2500 + CLI 1000） |
| 测试代码 | ~2800 行（230 个测试） |
| 示例 | 3 个（quickstart / semantic_modeling / nl_query） |
| 文档 | README + design spec + plan + review |

### 关键代码片段索引

| 代码 | 文件 | 说明 |
|---|---|---|
| 门面 + 7 命名空间 | `client.py` | 懒加载 property，只装配不请求 |
| HTTPClient + AsyncHTTPClient | `common/http.py` | 共享 `_handle_response`，重试退避 |
| 资源特化异常 | `exceptions.py` | 13 个异常类 + `FieldError` pydantic 模型 |
| QueryAPI @overload | `api/query.py` | `Literal[True/False]` 类型收窄双模式 |
| Page.from_response | `common/pagination.py` | 泛型分页 + pydantic model_validate |
| CLI 共享工具 | `cli/common.py` | get_client / format_output / exit_code_for |
| 配置加载 | `cli/config_schema.py` | TOML/dotenv 解析 + 6 层优先级链 |
| 端点常量 | `api/paths.py` | 38 个端点集中管理 |
