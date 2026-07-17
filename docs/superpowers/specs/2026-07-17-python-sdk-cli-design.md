# SuperSonic Python SDK CLI — 设计规格（Phase 2）

> CLI 子包 · 镜像 SDK 命名空间 · typer + rich · TOML/dotenv 双配置 · Agent 友好退出码

---

## 设计概述

- **目标**：为 SuperSonic Python SDK 提供命令行接口，让 SDK 能力可被人类用户和 AI Agent 通过 bash 直接调用
- **范围（Phase 2）**：CLI 子包（38 命令），不含 MCP Server（Phase 3 独立规格）
- **打包关系**：CLI 是 SDK 的**子包**（`python-sdk/src/supersonic/cli/`），共享同一个 `supersonic-sdk` distribution，通过 `[cli]` extra 安装依赖
- **核心约束**：CLI 是**薄包装层**，所有业务逻辑走 SDK；CLI 文件总量预计 700-900 行（不含测试）
- **简历价值**：「CLI 命令与 SDK API 完全对称」是一个可讲述的工程决策；同时让人和 Agent 都能用同套工具
- **技术栈**：Python 3.10+ / typer 0.9+ / rich 13+ / tomllib（3.11+ 内建，3.10 用 `tomli` backport）
- **依赖来源**：直接 import Phase 1 的 `supersonic` 包，零业务逻辑重复

**规格来源**：
- Phase 1 规格：`docs/superpowers/specs/2026-07-16-python-sdk-design.md`（§ 后续 Phase → Phase 2）
- Phase 1 已完成 SDK：`python-sdk/src/supersonic/`（154 测试 / 95% 覆盖率）

---

## 背景

### Phase 2 定位

Phase 1 完成了 Python SDK，覆盖 5 query + 30 元数据 CRUD + 2 dataset 只读，共 37 方法。但 SDK 只能从 Python 代码调用，对以下场景不便：

1. **运维 / DevOps**：CI/CD 脚本中要 `bash` 调用 SuperSonic 做 schema 巡检或批量发布
2. **数据分析师**：临时查询，不想写 Python 脚本，只想要 `supersonic query sql "..."`
3. **AI Agent**：Claude Code / Cursor / Aider 等通过 bash 工具调用 SuperSonic，需要稳定的命令行接口和退出码
4. **Demo / 教学**：CLI 比 SDK 代码更适合演示能力

CLI 是**通用接口**——人、shell 脚本、Agent 都能用同一套命令。

### 设计原则

1. **对称性**：CLI 命令与 SDK API 完全镜像（`client.metrics.list()` ↔ `supersonic metric list`），降低学习成本
2. **薄包装**：CLI 不写业务逻辑，所有调用转发到 SDK；如果 SDK 改了，CLI 自动跟随
3. **Agent 友好**：稳定 stdout 格式（JSON / 表格）、错误到 stderr、语义化退出码
4. **配置灵活**：6 层优先级链覆盖开发/测试/生产切换场景
5. **渐进增强**：默认 rich 表格（人友好），`--json` 切 JSON（机器友好），`--no-color` 禁色（Agent 友好）

### 与 Phase 1 SDK 的关系

```
┌──────────────────────────────────────────┐
│  Phase 3 (未来): MCP Server              │  Agent 协议层
├──────────────────────────────────────────┤
│  Phase 2 (本次): CLI                     │  人 + Agent 通用入口
│  - import supersonic SDK                 │
│  - typer + rich                          │
├──────────────────────────────────────────┤
│  Phase 1 (已完成): Python SDK            │  编程入口
└──────────────────────────────────────────┘
```

CLI 通过 `[cli]` extra 安装：`pip install supersonic-sdk[cli]`。

---

## 包布局

CLI 子包追加到现有 `python-sdk/`：

```
python-sdk/
├── pyproject.toml                      # 修改：加 [project.scripts] + 改 [cli] extra
├── src/supersonic/
│   ├── (Phase 1 已有的 client/api/models/common/utils/...)
│   └── cli/                            # 新增子包
│       ├── __init__.py                 # re-export app（让 `from supersonic.cli import app` 可用）
│       ├── main.py                     # typer 主 app + 全局 callback + cli_main 入口
│       ├── common.py                   # 共享：get_client / format_output / exit_code_for / 配置加载
│       ├── query.py                    # query 子命令组（sql/sqls/validate/metric/chat）
│       ├── domain.py                   # domain CRUD 5 子命令
│       ├── model.py                    # model CRUD 5 子命令
│       ├── dimension.py                # dimension 6 子命令（含 query-values）
│       ├── metric.py                   # metric 7 子命令（含 publish/unpublish）
│       ├── database.py                 # database 7 子命令（含 test-connect/get-tables/get-columns）
│       ├── dataset.py                  # dataset 2 子命令（只读）
│       └── config_cmd.py               # config show 子命令
├── tests/
│   ├── (Phase 1 已有的 conftest.py / test_*.py)
│   └── cli/                            # 新增 CLI 测试
│       ├── __init__.py
│       ├── conftest.py                 # CLI 专用 fixtures（cli_runner / mock_client / sample_toml）
│       ├── test_main.py                # 全局选项 + 版本 + 配置加载
│       ├── test_query.py
│       ├── test_domain.py
│       ├── test_model.py
│       ├── test_dimension.py
│       ├── test_metric.py
│       ├── test_database.py
│       ├── test_dataset.py
│       └── test_config_cmd.py
└── README.md                           # 修改：加 CLI 使用章节
```

### 文件职责约定

| 文件 | 职责 | 预估行数 |
|---|---|---|
| `main.py` | typer app 定义、全局 callback、子命令组挂载、`cli_main()` 入口 | 100-150 |
| `common.py` | 配置加载（TOML/dotenv）、`get_client(ctx)`、`format_output()`、`exit_code_for()` | 150-200 |
| `query.py` | 5 个 query 子命令 | 120-150 |
| `domain.py` / `model.py` | 各 5 子命令（CRUD 五件套） | 80-100 / 文件 |
| `dimension.py` | 6 子命令（含 query-values） | 100-130 |
| `metric.py` | 7 子命令（含 publish/unpublish） | 120-150 |
| `database.py` | 7 子命令（含 test-connect/get-tables/get-columns） | 130-160 |
| `dataset.py` | 2 子命令（只读） | 40-60 |
| `config_cmd.py` | 1 子命令（show） | 30-50 |

总计约 900-1200 行（含 docstring 和类型注解）。

---

## 命令结构全景（38 命令）

```
supersonic [GLOBAL OPTIONS] <command> <subcommand> [SUBCOMMAND OPTIONS]
```

### 全局选项（顶层 callback）

| 选项 | 类型 | 说明 | 环境变量等价 |
|---|---|---|---|
| `--host URL` | str | SuperSonic 服务地址 | `SUPERSONIC_HOST` |
| `--token JWT` | str | 鉴权 token | `SUPERSONIC_TOKEN` |
| `--app-key KEY` | str | App-Key header | `SUPERSONIC_APP_KEY` |
| `--timeout N` | float | HTTP 超时秒数 | `SUPERSONIC_TIMEOUT` |
| `--config FILE` | Path | TOML 配置文件路径 | - |
| `--env-file FILE` | Path | dotenv 文件路径 | - |
| `--json` | flag | 输出 JSON（默认 rich 表格） | - |
| `--no-color` | flag | 禁用彩色输出（Agent 友好） | - |
| `--verbose` / `--debug` | flag | 详细日志 | `SUPERSONIC_LOG_LEVEL=DEBUG` |
| `--quiet` | flag | 仅错误日志 | `SUPERSONIC_LOG_LEVEL=ERROR` |
| `--version` / `-V` | flag | 显示版本后退出 | - |
| `--help` / `-h` | flag | 自动生成帮助 | - |

### 命令清单

#### `query`（5 子命令）

| 子命令 | 必选参数 | 可选参数 | SDK 映射 |
|---|---|---|---|
| `sql` | `SQL`（位置参数） | `--data-set-id N` / `--limit N` / `--json` | `client.query.sql(SQL, data_set_id=N, limit=N)` |
| `sqls` | `--sqls-file FILE`（每行一条 SQL） | `--data-set-id N` / `--json` | `client.query.sqls([line1, line2, ...], data_set_id=N)` |
| `validate` | `SQL`（位置参数） | `--data-set-id N` | `client.query.validate(SQL, data_set_id=N)` |
| `metric` | `--metrics a,b,c` | `--dimensions d,e` / `--filter 'name=value'`（可多次） / `--start YYYY-MM-DD` / `--end YYYY-MM-DD` / `--limit N` / `--json` | `client.query.metric(metrics=[...], dimensions=[...], filters=[...], date_info=DateConf(...), limit=N)` |
| `chat` | `--text "..."` | `--data-set-ids 1,2` / `--detailed`（默认） / `--concise` / `--json` | `client.query.chat(text, data_set_ids=[...], detailed=True/False)` |

#### `domain` / `model` / `dimension` / `metric` / `database`（每组五件套 + 特殊方法）

每组都有统一的 `list / get / create / update / delete`（database 含 6 资源，dataset 仅 list/get），加上资源特有命令。

**示例：`metric` 组（7 命令）**

```bash
# list
supersonic metric list [--model-id 10] [--page 1] [--page-size 20] [--json]

# get
supersonic metric get --id 1

# create（必选参数随资源不同）
supersonic metric create \
  --model-id 10 --name 销售额 --biz-name sales_amt \
  --define-type MEASURE --type NUMBER --expression pay_amt \
  [--description "..."] [--alias "销售金额"]

# update（所有非 id 字段可选）
supersonic metric update --id 1 --description "新描述"

# delete
supersonic metric delete --id 1

# publish（特有）
supersonic metric publish --ids 1,2,3

# unpublish（特有）
supersonic metric unpublish --ids 1,2,3
```

**其他资源组的具体差异**：

| 资源 | 特殊命令 | list 过滤参数 |
|---|---|---|
| `domain` | - | - |
| `model` | - | `--domain-id N`（必填） |
| `dimension` | `query-values --id N [--filter ...]` | `--model-id N` |
| `metric` | `publish --ids` / `unpublish --ids` | `--model-id N` |
| `database` | `test-connect --name --type --host --port --username --password` / `get-tables --id N [--db NAME]` / `get-columns --id N --table NAME [--db NAME]` | - |
| `dataset` | -（仅 list/get） | - |

#### `config`（辅助命令组）

- `supersonic config show` — 显示当前生效配置（合并优先级链后的最终值，token 打码）

---

## 共享工具（`common.py`）

### `get_client(ctx: typer.Context) -> SupersonicClient`

从 `ctx.obj`（全局 callback 已合并的配置 dict）构造 SDK 客户端。

```python
def get_client(ctx: typer.Context) -> SupersonicClient:
    """从 ctx.obj 读取合并后的配置，构造 SupersonicClient。

    ctx.obj 由 main.py 的全局 callback 在调用任何子命令前填充，
    包含合并优先级链后的最终值。
    """
    config: dict = ctx.obj
    return SupersonicClient(
        host=config["host"],
        token=config["token"],
        app_key=config.get("app_key", "supersonic"),
        timeout=config.get("timeout", 30.0),
        retry=_build_retry_config(config.get("retry")),
        log_level=config.get("log_level", "WARNING"),
    )
```

**懒加载策略**：每个子命令调用 `get_client(ctx)` 时才创建 client，退出时通过 `ctx.call_on_close` 清理（避免 httpx 连接泄漏）。

### `format_output(obj, *, as_json, no_color, columns=None) -> None`

统一输出格式化：

```python
def format_output(
    obj: Any,
    *,
    as_json: bool,
    no_color: bool,
    columns: list[str] | None = None,
) -> None:
    if as_json:
        # pydantic 模型走 model_dump_json；其他走 json.dumps
        if isinstance(obj, BaseModel):
            typer.echo(obj.model_dump_json(indent=2))
        else:
            typer.echo(json.dumps(obj, indent=2, ensure_ascii=False, default=str))
        return

    # 表格模式：rich Table
    if no_color:
        # 禁用 rich 彩色，但保留表格结构
        console = Console(no_color=True)
    else:
        console = Console()

    if isinstance(obj, QueryResult):
        # 复用 Phase 1 的 utils.format.format_result_table
        typer.echo(format_result_table(obj))
    elif isinstance(obj, Page):
        _render_page_table(console, obj, columns)
    elif isinstance(obj, BaseModel):
        _render_kv_table(console, obj)
    elif isinstance(obj, list):
        _render_list_table(console, obj, columns)
    else:
        typer.echo(str(obj))
```

**关键决策**：
- `QueryResult` 走 Phase 1 的 `format_result_table`（不重新发明轮子）
- `Page[T]` 渲染为表格 + 底部 "Total: N · Page X/Y"
- 单个 model（如 `Metric`）渲染为 key-value 两列表（属性名 | 值）
- list of model 渲染为标准表格

### `exit_code_for(exc: Exception) -> int`

异常 → 退出码映射：

```python
def exit_code_for(exc: Exception) -> int:
    """异常 → 退出码映射（Agent 友好的语义化退出码）。"""
    if isinstance(exc, AuthenticationError):
        return 2
    if isinstance(exc, ResourceNotFoundError):
        return 3
    if isinstance(exc, ValidationError):
        return 4
    if isinstance(exc, (ServerError, ConnectionError)):
        return 5
    if isinstance(exc, SupersonicError):
        return 1
    return 1  # 未预期错误
```

---

## 配置加载流程

### 优先级链（从高到低）

```
1. CLI 参数（--host/--token/--app-key/--timeout/--verbose/--quiet）
2. 环境变量（SUPERSONIC_HOST/SUPERSONIC_TOKEN/SUPERSONIC_APP_KEY/...）
3. --config 指定的 TOML 文件
4. --env-file 指定的 dotenv 文件
5. ~/.supersonic/config.toml（默认路径，如存在则加载）
6. 代码默认值（host=None/token=None 等触发 fail-fast）
```

**关键点**：`--config` 和 `--env-file` 互斥（同时指定报错），避免配置源歧义。环境变量始终优先于文件，便于 CI 临时覆盖。

### `load_config_file(config, env_file) -> dict`

```python
def load_config_file(
    config: Path | None,
    env_file: Path | None,
) -> dict[str, Any]:
    """加载配置文件，返回扁平 dict。

    优先级：--config > --env-file > ~/.supersonic/config.toml。
    --config 与 --env-file 互斥。
    """
    if config and env_file:
        raise typer.BadParameter(
            "--config and --env-file are mutually exclusive.",
        )

    if config:
        if not config.exists():
            raise typer.BadParameter(f"Config file not found: {config}")
        return _load_toml(config)

    if env_file:
        if not env_file.exists():
            raise typer.BadParameter(f"Env file not found: {env_file}")
        return _load_dotenv(env_file)

    # 默认路径
    default_path = Path.home() / ".supersonic" / "config.toml"
    if default_path.exists():
        return _load_toml(default_path)

    return {}
```

### TOML schema

```toml
# ~/.supersonic/config.toml 示例
host = "http://localhost:9080"
token = "jwt-xxx"
app_key = "supersonic"
timeout = 30.0
enable_async = false
log_level = "WARNING"

[retry]
max_retries = 3
retry_delay = 1.0
max_backoff = 30.0
backoff_jitter = true
```

**校验**：用 pydantic 模型（`CliConfig`）校验 TOML 结构，类型错误给清晰报错。

```python
class RetryConfigFile(BaseModel):
    max_retries: int | None = None
    retry_delay: float | None = None
    max_backoff: float | None = None
    backoff_jitter: bool | None = None

class CliConfig(BaseModel):
    host: str | None = None
    token: str | None = None
    app_key: str | None = None
    timeout: float | None = None
    enable_async: bool | None = None
    log_level: str | None = None
    retry: RetryConfigFile | None = None
```

### Python 3.10 兼容（tomli backport）

Python 3.11+ 用内建 `tomllib`；3.10 需要 `tomli` 包：

```python
try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Python 3.10 backport
```

`tomli` 加入 `[cli]` extra 的 conditional dependency（`tomli; python_version < "3.11"`）。

---

## 输出格式

### 表格模式（默认，人友好）

**QueryResult**（复用 Phase 1 `format_result_table`）：
```
$ supersonic query sql "SELECT category, sales_amt FROM orders LIMIT 3"

category   | sales_amt
-----------+----------
手机       | 12000.0
电脑       | 8500.0
平板       | 4200.0

3 rows
```

**Page[Metric]**：
```
$ supersonic metric list --model-id 10 --page 1 --page-size 5

  ID   Name        Biz Name      Define Type   Type     Status
 ────────────────────────────────────────────────────────────────
  1    销售额      sales_amt     MEASURE       NUMBER   ONLINE
  2    订单数      order_cnt     MEASURE       NUMBER   ONLINE

Total: 50 · Page 1/10
```

**单个 Metric（`metric get`）**：
```
$ supersonic metric get --id 1

  Field           Value
 ──────────────────────────────
  ID              1
  Name            销售额
  Biz Name        sales_amt
  Model ID        10
  Define Type     MEASURE
  Type            NUMBER
  Expression      pay_amt
  Status          ONLINE
```

### JSON 模式（`--json`，机器友好）

所有命令的 `--json` 输出统一的 pydantic `model_dump_json(indent=2)`：

```json
$ supersonic metric list --model-id 10 --json
{
  "items": [
    {
      "id": 1,
      "name": "销售额",
      "biz_name": "sales_amt",
      "model_id": 10,
      "define_type": "MEASURE",
      "type": "NUMBER",
      ...
    },
    {
      "id": 2,
      ...
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 10
}
```

**关键约定**：JSON 输出走 stdout，**绝不**混入错误信息（错误一律 stderr）。这样 Agent 可以安全 `JSON.parse(stdout)`。

### 错误输出（始终到 stderr）

```
$ supersonic metric get --id 999
Error: metric 999 not found (status=404)

Exit code: 3
```

`ValidationError` 额外展开字段级错误：
```
$ supersonic metric create --model-id 10 --name "" --biz-name sales_amt --define-type MEASURE
Error: Request validation failed: name cannot be empty (status=400)
  - name: 不能为空

Exit code: 4
```

---

## 错误处理与退出码

### 顶层异常捕获（`main.py` 的 `cli_main()`）

```python
def cli_main() -> None:
    """CLI 入口（pyproject.toml 的 [project.scripts] 指向这里）。"""
    try:
        app()  # typer app
    except SupersonicError as e:
        exit_code = exit_code_for(e)
        typer.echo(
            f"Error: {e.message} (status={e.status_code})",
            err=True,
        )
        if isinstance(e, ValidationError) and e.field_errors:
            for fe in e.field_errors:
                typer.echo(f"  - {fe.field}: {fe.message}", err=True)
        raise typer.Exit(exit_code) from e
    except typer.Exit:
        raise  # typer 内部退出（如 --help）
    except Exception as e:
        # 未预期错误：--debug 时打印 traceback，否则简短消息
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1) from e
```

### 退出码表

| Code | 含义 | 触发条件 | 示例 |
|---|---|---|---|
| **0** | 成功 | 命令正常完成 | `supersonic metric list` 返回数据 |
| **1** | 通用客户端错误 | 参数错误、配置错误、其他 `SupersonicError` | `--config` 文件不存在；未知异常 |
| **2** | 认证错误 | `AuthenticationError`（401） | token 过期 |
| **3** | 未找到 | `ResourceNotFoundError` 及子类（404） | `metric get --id 999` |
| **4** | 校验错误 | `ValidationError`（400，含 field_errors） | `create` 必填字段缺失 |
| **5** | 服务器错误 | `ServerError` / `ConnectionError`（5xx / 网络） | SuperSonic 服务宕机 |

### Agent 友好性

稳定的退出码 + 结构化 stderr 让 Agent 可程序化处理失败：
- exit 2 → 重新获取 token 后重试
- exit 3 → 报告资源缺失，不再重试
- exit 4 → 展开字段级错误给用户修正
- exit 5 → 等待后重试，或切换实例

---

## 测试策略

### 测试组织（`tests/cli/`）

```
tests/cli/
├── conftest.py                 # CLI 专用 fixtures
├── test_main.py                # 全局选项 + 配置加载
├── test_query.py               # 5 个 query 子命令
├── test_domain.py / test_model.py / test_dimension.py / test_metric.py / test_database.py
├── test_dataset.py
└── test_config_cmd.py
```

### 共享 fixtures

```python
# tests/cli/conftest.py
import pytest
from typer.testing import CliRunner
from unittest.mock import MagicMock

from supersonic.cli.main import app
from supersonic.common.pagination import Page
from supersonic.models.metric import Metric


@pytest.fixture
def cli_runner():
    """typer 测试专用 runner，隔离 stdout/stderr。"""
    return CliRunner()


@pytest.fixture
def mock_client(monkeypatch):
    """Mock SDK 的 SupersonicClient，避免真实 HTTP。

    所有 namespace 都预设合理的默认返回值，
    单个测试可按需 override。
    """
    client = MagicMock(name="MockSupersonicClient")
    # 默认返回：metric list
    client.metrics.list.return_value = Page[Metric](
        items=[Metric(id=1, name="销售额", biz_name="sales_amt",
                      model_id=10, define_type="MEASURE")],
        total=1, page=1, page_size=10,
    )
    # 默认返回：metric get
    client.metrics.get.return_value = Metric(
        id=1, name="销售额", biz_name="sales_amt",
        model_id=10, define_type="MEASURE", type="NUMBER",
    )
    # ... 其他 namespace 默认 mock
    monkeypatch.setattr(
        "supersonic.cli.common.get_client",
        lambda ctx: client,
    )
    return client


@pytest.fixture
def sample_toml_config(tmp_path):
    """临时 TOML 配置文件，用于测试 --config。"""
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
host = "http://from-toml:9080"
token = "jwt-from-toml"
app_key = "from-toml-app"

[retry]
max_retries = 5
""")
    return config_file


@pytest.fixture
def sample_env_file(tmp_path):
    """临时 dotenv 文件，用于测试 --env-file。"""
    env_file = tmp_path / ".env"
    env_file.write_text("""
SUPERSONIC_HOST=http://from-env:9080
SUPERSONIC_TOKEN=jwt-from-env
""")
    return env_file
```

### 测试覆盖要求

- **每个子命令至少 3 个测试**：happy path / 错误码 / `--json` 格式
- **全局选项测试**：`--host` / `--token` / `--config` / `--env-file` / `--no-color` / `--verbose` / `--version`
- **配置优先级链测试**：CLI > env > TOML > dotenv > 默认路径 > 默认值（至少 4 个测试覆盖关键链路）
- **退出码映射测试**：5 类异常 → 5 个退出码（参数化测试）
- **配置文件解析测试**：TOML 解析 / dotenv 解析 / 缺文件处理 / `--config` 与 `--env-file` 互斥
- **目标覆盖率**：CLI 子包 ≥ 85%

### 与 Phase 1 测试的关系

- **共享 conftest.py**：CLI 测试复用 Phase 1 的 `sample_metric_dict` 等 fixtures
- **mock 策略不同**：Phase 1 用 `pytest-httpx` mock HTTP；CLI 测试用 `MagicMock` mock 整个 `SupersonicClient`（CLI 层不需要验证 HTTP 细节，那是 Phase 1 的职责）
- **不重跑 SDK 测试**：CLI 测试假定 SDK 已通过 Phase 1 的 154 个测试

---

## pyproject.toml 变更

### `[project.scripts]` 新增

```toml
[project.scripts]
supersonic = "supersonic.cli.main:cli_main"
```

### `[project.optional-dependencies]` 的 `[cli]` extra 切换

```toml
[project.optional-dependencies]
# ... 其他不变
cli = [
    "typer>=0.9.0",
    "rich>=13.0.0",
    "tomli>=2.0.0; python_version < '3.11'",  # 3.10 backport
]
# ...
```

Phase 1 规格原写 `click>=8.1.0`，切换为 `typer`（typer 内部依赖 click，无版本冲突）。

### 安装与使用

```bash
# 安装（含 CLI）
pip install supersonic-sdk[cli]

# 验证
supersonic --version
supersonic --help
```

---

## 关键设计决策

### 1. typer 而非 click

**决策**：用 typer 作为 CLI 框架。

**理由**：
- typer 基于 click（typer 内部 import click），是 click 的超集
- 用类型注解定义命令，样板代码减半（与 SDK 的 pydantic 风格一致）
- 内建 rich 集成（彩色表格输出）
- 自动生成 help 文档
- 现代教程和示例都用 typer

**代价**：多一层抽象，但 typer 已成熟（0.9+ 版本稳定）。

### 2. 命令结构镜像 SDK 7 命名空间

**决策**：CLI 子命令组与 SDK 命名空间完全对称（query/domain/model/dimension/metric/database/dataset）。

**理由**：
- 学习成本最低：用户学会 SDK 即会用 CLI，反之亦然
- Agent 友好：稳定的命令结构 = 稳定的工具调用
- 完整覆盖：37 个 SDK 方法都对应 CLI 命令，不留缺口
- 简历价值：「CLI 命令与 SDK API 完全对称」是一个可讲述的工程决策

**代价**：命令数较多（38），但每个都很简单。

### 3. TOML + dotenv 双配置源

**决策**：支持 `--config FILE`（TOML）和 `--env-file FILE`（dotenv）互斥二选一，加上默认路径 `~/.supersonic/config.toml`。

**理由**：
- CLI 用户场景：开发者/运维经常在多个实例间切换，配置文件比反复 export 环境变量方便
- TOML 主路径：Python 3.11+ 内建 tomllib，结构清晰，能表达嵌套（如 `[retry]`）
- dotenv 兼容：很多团队已有 dotenv 工作流，不强迫改

**代价**：实现稍复杂，但优先级链清晰。

### 4. 5 类语义化退出码

**决策**：0/1/2/3/4/5 六个退出码（含成功），映射 SDK 异常树。

**理由**：
- Agent 友好：稳定的退出码让 Agent 可程序化处理失败
- 人友好：常见错误有明确数字语义（不用记 1=认证 2=未找到，看 stderr 错误消息即可）
- 与 SDK 异常树对应：5 个错误码恰好覆盖 5 类 SupersonicError 子类

**代价**：用户需学习 6 个退出码，但 typer 的 `--help` 和文档会说明。

### 5. 默认表格 + JSON 双格式

**决策**：默认 rich 表格（人友好），`--json` 切 JSON（机器友好），`--no-color` 禁色（Agent 友好）。

**理由**：
- 三种用户场景对应三种输出：人 / 管道 / Agent
- 复用 Phase 1 的 `format_result_table` 不重复发明轮子
- JSON 输出走 pydantic `model_dump_json`，保证序列化稳定

### 6. 薄包装原则

**决策**：CLI 文件**不包含业务逻辑**，所有调用转发到 SDK。

**理由**：
- 单一职责：SDK 管业务逻辑，CLI 管参数解析和输出
- SDK 改了，CLI 自动跟随（如果命令签名兼容）
- 测试简化：CLI 测试只验证「参数解析 + 输出格式」，不验证业务正确性（那是 SDK 测试的职责）

---

## 范围边界

### IN SCOPE（Phase 2）

- **38 个命令**：5 query + 5+5+6+7+7 元数据 CRUD + 2 dataset + 1 config
- **配置加载**：TOML + dotenv + 6 层优先级链
- **输出格式**：rich 表格 + JSON 双格式，`--no-color` 禁色
- **错误处理**：5 类语义化退出码 + 结构化 stderr
- **全局选项**：12 个（host/token/app-key/timeout/config/env-file/json/no-color/verbose/quiet/version/help）
- **完整测试**：每个子命令至少 3 个测试，CLI 覆盖率 ≥ 85%
- **README 更新**：加 CLI 使用章节
- **shell 补全**：typer 内建 `--install-completion`（bash/zsh/fish）

### OUT OF SCOPE（明确不做）

| 项目 | 原因 | 何时做 |
|---|---|---|
| **交互式 shell（REPL）** | YAGNI，多数用户单次命令即可 | 视需求 |
| **批量操作命令**（如 `metric batch-create --file`） | SDK 已支持循环调用，CLI 包装价值低 | 视需求 |
| **配置文件密码加密** | YAGNI，token 是 JWT 不是密码；用户应通过文件权限保护 | 安全加强版 |
| **Web UI / TUI** | 完全偏离 CLI 定位 | 永不做 |
| **MCP Server** | Phase 3 独立规格 | 下一个规格 |
| **LangChain Tool 包装** | Phase 3 可选项 | 同上 |
| **async 命令** | Phase 1 SDK 仅 QueryAPI 支持 async，CLI 同步足够 | Phase 1 async 元数据 CRUD 完成后 |

---

## 产出物清单

### 源代码（新增）

- `python-sdk/src/supersonic/cli/__init__.py`
- `python-sdk/src/supersonic/cli/main.py`
- `python-sdk/src/supersonic/cli/common.py`
- `python-sdk/src/supersonic/cli/{query,domain,model,dimension,metric,database,dataset,config_cmd}.py`（8 个子命令组文件）

### 测试（新增）

- `python-sdk/tests/cli/__init__.py`
- `python-sdk/tests/cli/conftest.py`
- `python-sdk/tests/cli/test_{main,query,domain,model,dimension,metric,database,dataset,config_cmd}.py`（9 个测试文件）

### 配置变更（修改）

- `python-sdk/pyproject.toml`：加 `[project.scripts]` + 改 `[cli]` extra

### 文档（修改）

- `python-sdk/README.md`：加 CLI 使用章节（安装 / 快速开始 / 命令清单 / 配置 / 退出码）

### 简历文档（Phase 2 完成后，作为完整三层架构叙事的一部分）

- `docs/superpowers/resume/05-python-sdk.md`（三层架构 + CLI + MCP Server 完整叙事；Phase 3 完成后写）

---

## 后续 Phase（仅概述）

### Phase 3：MCP Server

- `mcp/` 子包，`[mcp]` extra
- 协议：MCP（Model Context Protocol）
- 工具定义：每个 SDK 资源类映射为 MCP tool（如 `create_metric`、`query_sql`）
- 传输：stdio（默认）+ HTTP/SSE（可选）
- 框架：`mcp` 官方 Python SDK
- 对标：open-metadata/ai-sdk 的 `mcp/` 子包
- 独立规格：在 Phase 2 完成后启动 brainstorming
