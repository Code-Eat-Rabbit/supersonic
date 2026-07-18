# SuperSonic Python SDK CLI Phase 2 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为 SuperSonic Python SDK 实现 CLI 子包——38 个命令镜像 SDK 命名空间，支持 TOML/dotenv 双配置 + 6 层优先级链 + 5 类语义化退出码。

**架构：** CLI 是 SDK 的薄包装子包（`python-sdk/src/supersonic/cli/`），所有业务逻辑走 SDK。typer 定义命令结构，rich 渲染表格，pydantic 校验配置文件。CLI 测试用 MagicMock mock 整个 Client（不复用 pytest-httpx，那是 SDK 层的职责）。

**技术栈：** Python 3.10+ / typer 0.9+ / rich 13+ / tomllib（3.11+ 内建，3.10 用 tomli backport）/ pytest + typer.testing.CliRunner

**规格来源：** `docs/superpowers/specs/2026-07-17-python-sdk-cli-design.md`

**目标覆盖率：** CLI 子包 ≥ 85%

**前置条件：** Phase 1 SDK 已完成（154 测试 / 95% 覆盖率）

---

## 文件结构

### 创建文件清单（按依赖顺序）

```
python-sdk/
├── pyproject.toml                                    # 任务 1（修改：加 [project.scripts] + 改 [cli] extra）
├── src/supersonic/
│   └── cli/                                          # 新增子包
│       ├── __init__.py                               # 任务 2（re-export app）
│       ├── common.py                                 # 任务 3（get_client / format_output / exit_code_for / 配置加载）
│       ├── config_schema.py                          # 任务 4（CliConfig pydantic 模型 + TOML/dotenv 解析）
│       ├── main.py                                   # 任务 5（typer app + 全局 callback + cli_main 入口）
│       ├── query.py                                  # 任务 7
│       ├── domain.py                                 # 任务 8
│       ├── model.py                                  # 任务 9
│       ├── dimension.py                              # 任务 10
│       ├── metric.py                                 # 任务 11
│       ├── database.py                               # 任务 12
│       ├── dataset.py                                # 任务 13
│       └── config_cmd.py                             # 任务 14
├── tests/
│   └── cli/                                          # 新增测试目录
│       ├── __init__.py                               # 任务 2
│       ├── conftest.py                               # 任务 6（cli_runner / mock_client / sample_toml / sample_env_file fixtures）
│       ├── test_config_schema.py                     # 任务 4
│       ├── test_common.py                            # 任务 3 + 任务 5
│       ├── test_main.py                              # 任务 5
│       ├── test_query.py                             # 任务 7
│       ├── test_domain.py                            # 任务 8
│       ├── test_model.py                             # 任务 9
│       ├── test_dimension.py                         # 任务 10
│       ├── test_metric.py                            # 任务 11
│       ├── test_database.py                          # 任务 12
│       ├── test_dataset.py                           # 任务 13
│       └── test_config_cmd.py                        # 任务 14
└── README.md                                         # 任务 15（加 CLI 章节）
```

### 任务依赖图

```
任务 1 (pyproject) ─→ 任务 2 (cli/ 骨架)
                          │
                          ├─→ 任务 3 (common.py: get_client/format_output/exit_code_for)
                          ├─→ 任务 4 (config_schema.py: TOML/dotenv 解析 + CliConfig pydantic)
                          │       │
                          │       └─→ 任务 5 (main.py: typer app + 全局 callback + cli_main)
                          │               │
                          │               └─→ 任务 6 (conftest.py: 共享 fixtures)
                          │                       │
                          │                       ├─→ 任务 7 (query.py)
                          │                       ├─→ 任务 8 (domain.py)
                          │                       ├─→ 任务 9 (model.py)
                          │                       ├─→ 任务 10 (dimension.py)
                          │                       ├─→ 任务 11 (metric.py)
                          │                       ├─→ 任务 12 (database.py)
                          │                       ├─→ 任务 13 (dataset.py)
                          │                       └─→ 任务 14 (config_cmd.py)
                          │                               │
                          │                               ▼
                          └─────────────────────→  任务 15 (README + 类型检查里程碑)
```

**关键路径**：任务 1 → 2 → 3/4 → 5 → 6 → 7-14（资源命令组可并行）→ 15

---

## 任务 1：pyproject.toml 变更（加 [project.scripts] + 改 [cli] extra）

**文件：**
- 修改：`python-sdk/pyproject.toml`

**规格参考：** § pyproject.toml 变更

- [ ] **步骤 1：修改 pyproject.toml**

在 `[project]` 章节后追加 `[project.scripts]`：

```toml
[project.scripts]
supersonic = "supersonic.cli.main:cli_main"
```

修改 `[project.optional-dependencies]` 的 `cli`：

```toml
[project.optional-dependencies]
pandas = ["pandas>=2.0.0"]
cli = [
    "typer>=0.9.0",
    "rich>=13.0.0",
    "tomli>=2.0.0; python_version < '3.11'",
]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-httpx>=0.30",
    "pytest-cov>=4.0",
    "ruff>=0.8.0",
    "mypy>=1.0",
]
all = ["supersonic-sdk[pandas,dev]"]
```

- [ ] **步骤 2：安装新依赖**

运行：
```bash
cd /Users/yourton_ma/workspace/supersonic/python-sdk
python3.11 -m pip install -e ".[cli,dev]"
```

预期：成功安装 typer/rich（tomli 仅 3.10 需要，3.11+ 跳过）。

- [ ] **步骤 3：验证 typer/rich 可 import**

运行：
```bash
python3.11 -c "import typer, rich; print('typer', typer.__version__, 'rich', rich.__version__)"
```

预期：输出版本号，无 ImportError。

- [ ] **步骤 4：Commit**

```bash
cd /Users/yourton_ma/workspace/supersonic
git add python-sdk/pyproject.toml
git commit -m "feat(sdk): add CLI entry point and switch [cli] extra to typer+rich"
```

---

## 任务 2：cli/ 子包骨架（`__init__.py` + 测试目录）

**文件：**
- 创建：`python-sdk/src/supersonic/cli/__init__.py`（暂为空，任务 5 会填 re-export）
- 创建：`python-sdk/tests/cli/__init__.py`（空）

- [ ] **步骤 1：创建目录 + 占位 __init__.py**

运行：
```bash
mkdir -p python-sdk/src/supersonic/cli
mkdir -p python-sdk/tests/cli
touch python-sdk/tests/cli/__init__.py
```

文件：`python-sdk/src/supersonic/cli/__init__.py`

```python
"""SuperSonic CLI subpackage.

Provides `supersonic` command via typer. Importable as `from supersonic.cli import app`.
"""
```

- [ ] **步骤 2：验证可 import**

运行：
```bash
python3.11 -c "import supersonic.cli; print(supersonic.cli.__doc__)"
```

预期：输出 docstring，无 ImportError。

- [ ] **步骤 3：Commit**

```bash
git add python-sdk/src/supersonic/cli/__init__.py python-sdk/tests/cli/__init__.py
git commit -m "feat(sdk): scaffold cli/ subpackage skeleton"
```

---

## 任务 3：common.py — 共享工具（get_client / format_output / exit_code_for）

**文件：**
- 创建：`python-sdk/src/supersonic/cli/common.py`
- 创建：`python-sdk/tests/cli/test_common.py`

**规格参考：** § 共享工具（`common.py`）

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/cli/test_common.py`

```python
"""Tests for cli/common.py shared utilities."""
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from supersonic.cli.common import (
    exit_code_for,
    format_output,
    get_client,
)
from supersonic.common.pagination import Page
from supersonic.exceptions import (
    AuthenticationError,
    ConnectionError as SupersonicConnectionError,
    DatabaseNotFoundError,
    MetricNotFoundError,
    RateLimitError,
    ServerError,
    SupersonicError,
    ValidationError,
)
from supersonic.models.metric import Metric
from supersonic.models.query import QueryColumn, QueryResult


class TestExitCodeFor:
    """Review spec § 错误处理与退出码."""

    def test_authentication_error_returns_2(self):
        assert exit_code_for(AuthenticationError()) == 2

    def test_resource_not_found_returns_3(self):
        assert exit_code_for(MetricNotFoundError(resource_id=99)) == 3
        assert exit_code_for(DatabaseNotFoundError(resource_id=1)) == 3

    def test_validation_error_returns_4(self):
        assert exit_code_for(ValidationError("bad")) == 4

    def test_server_error_returns_5(self):
        assert exit_code_for(ServerError("boom", status_code=500)) == 5

    def test_connection_error_returns_5(self):
        assert exit_code_for(SupersonicConnectionError("net down")) == 5

    def test_rate_limit_returns_1(self):
        """RateLimitError 不在 2-5 范围，落到通用 1。"""
        assert exit_code_for(RateLimitError(retry_after=60)) == 1

    def test_generic_supersonic_error_returns_1(self):
        assert exit_code_for(SupersonicError("other")) == 1

    def test_unexpected_exception_returns_1(self):
        assert exit_code_for(ValueError("unexpected")) == 1


class TestFormatOutput:
    def test_json_mode_for_pydantic_model(self, capsys):
        m = Metric(id=1, name="销售额", biz_name="sales_amt",
                   model_id=10, define_type="MEASURE")
        format_output(m, as_json=True, no_color=True)
        captured = capsys.readouterr()
        assert '"name": "销售额"' in captured.out
        assert '"id": 1' in captured.out

    def test_json_mode_for_page(self, capsys):
        page = Page[Metric](
            items=[Metric(id=1, name="x", biz_name="x", model_id=1, define_type="MEASURE")],
            total=1, page=1, page_size=10,
        )
        format_output(page, as_json=True, no_color=True)
        captured = capsys.readouterr()
        assert '"total": 1' in captured.out
        assert '"items":' in captured.out

    def test_table_mode_for_query_result(self, capsys):
        """QueryResult 走 format_result_table（复用 Phase 1 utils）。"""
        result = QueryResult(
            columns=[QueryColumn(name="product", type="VARCHAR")],
            result_rows=[{"product": "iPhone"}],
        )
        format_output(result, as_json=False, no_color=True)
        captured = capsys.readouterr()
        assert "product" in captured.out
        assert "iPhone" in captured.out

    def test_table_mode_for_page(self, capsys):
        page = Page[Metric](
            items=[Metric(id=1, name="销售额", biz_name="sales_amt",
                          model_id=10, define_type="MEASURE")],
            total=1, page=1, page_size=10,
        )
        format_output(page, as_json=False, no_color=True)
        captured = capsys.readouterr()
        assert "销售额" in captured.out
        assert "Total: 1" in captured.out

    def test_table_mode_for_single_model(self, capsys):
        m = Metric(id=42, name="测试", biz_name="test", model_id=1, define_type="MEASURE")
        format_output(m, as_json=False, no_color=True)
        captured = capsys.readouterr()
        assert "测试" in captured.out
        assert "42" in captured.out


class TestGetClient:
    def test_get_client_returns_supersonic_client(self):
        """get_client 从 ctx.obj 读取合并配置，构造 SupersonicClient。"""
        import typer
        from supersonic.client import SupersonicClient

        ctx = MagicMock(spec=typer.Context)
        ctx.obj = {
            "host": "http://test:9080",
            "token": "jwt-test",
            "app_key": "test-app",
            "timeout": 60.0,
        }
        client = get_client(ctx)
        assert isinstance(client, SupersonicClient)
        client.close()
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
cd /Users/yourton_ma/workspace/supersonic/python-sdk
python3.11 -m pytest tests/cli/test_common.py -v
```
预期：FAIL，`ModuleNotFoundError: No module named 'supersonic.cli.common'`

- [ ] **步骤 3：实现 common.py**

文件：`python-sdk/src/supersonic/cli/common.py`

```python
"""CLI shared utilities: client construction, output formatting, exit code mapping.

Review spec § 共享工具（common.py）.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import typer
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

from supersonic.client import SupersonicClient
from supersonic.common.pagination import Page
from supersonic.config import RetryConfig
from supersonic.exceptions import (
    AuthenticationError,
    ConnectionError as SupersonicConnectionError,
    ResourceNotFoundError,
    ServerError,
    SupersonicError,
    ValidationError,
)
from supersonic.models.query import QueryResult
from supersonic.utils.format import format_result_table

if TYPE_CHECKING:
    import typer as typer_module


def get_client(ctx: typer.Context) -> SupersonicClient:
    """Build SupersonicClient from ctx.obj (merged config).

    ctx.obj is populated by main.py's global callback before any subcommand runs.
    """
    config: dict[str, Any] = ctx.obj or {}
    host = config.get("host")
    token = config.get("token")
    if not host or not token:
        raise typer.BadParameter(
            "host and token are required. Provide via --host/--token, "
            "env vars SUPERSONIC_HOST/SUPERSONIC_TOKEN, or config file."
        )

    retry_dict = config.get("retry") or {}
    retry = RetryConfig(**retry_dict) if retry_dict else RetryConfig()

    return SupersonicClient(
        host=host,
        token=token,
        app_key=config.get("app_key", "supersonic"),
        timeout=config.get("timeout", 30.0),
        retry=retry,
        log_level=config.get("log_level", "WARNING"),
    )


def format_output(
    obj: Any,
    *,
    as_json: bool,
    no_color: bool,
    columns: list[str] | None = None,
) -> None:
    """Unified output formatting.

    - as_json=True: pydantic model_dump_json or json.dumps
    - as_json=False: rich Table (or format_result_table for QueryResult)
    """
    if as_json:
        if isinstance(obj, BaseModel):
            typer.echo(obj.model_dump_json(indent=2))
        else:
            typer.echo(json.dumps(obj, indent=2, ensure_ascii=False, default=str))
        return

    console = Console(no_color=no_color)

    if isinstance(obj, QueryResult):
        # Reuse Phase 1 utils.format.format_result_table
        typer.echo(format_result_table(obj))
    elif isinstance(obj, Page):
        _render_page_table(console, obj, columns)
    elif isinstance(obj, BaseModel):
        _render_kv_table(console, obj)
    elif isinstance(obj, list):
        _render_list_table(console, obj, columns)
    else:
        typer.echo(str(obj))


def _render_page_table(
    console: Console,
    page: Page[BaseModel],
    columns: list[str] | None,
) -> None:
    """Render Page[T] as rich table with footer 'Total: N · Page X/Y'."""
    if not page.items:
        typer.echo("(no items)")
        return

    sample = page.items[0]
    headers = columns or list(sample.model_dump(by_alias=False).keys())

    table = Table(show_header=True, header_style="bold")
    for h in headers:
        table.add_column(str(h))

    for item in page.items:
        data = item.model_dump(by_alias=False)
        table.add_row(*[str(data.get(h, "")) for h in headers])

    console.print(table)
    total_pages = (page.total + page.page_size - 1) // page.page_size if page.page_size else 1
    typer.echo(f"\nTotal: {page.total} · Page {page.page}/{total_pages}")


def _render_kv_table(console: Console, model: BaseModel) -> None:
    """Render single pydantic model as key-value two-column table."""
    table = Table(show_header=True, header_style="bold")
    table.add_column("Field")
    table.add_column("Value")

    data = model.model_dump(by_alias=False)
    for k, v in data.items():
        table.add_row(str(k), str(v) if v is not None else "")

    console.print(table)


def _render_list_table(
    console: Console,
    items: list[BaseModel],
    columns: list[str] | None,
) -> None:
    """Render list of pydantic models as rich table."""
    if not items:
        typer.echo("(empty)")
        return

    sample = items[0]
    if not isinstance(sample, BaseModel):
        # Fallback: just print
        for i in items:
            typer.echo(str(i))
        return

    headers = columns or list(sample.model_dump(by_alias=False).keys())

    table = Table(show_header=True, header_style="bold")
    for h in headers:
        table.add_column(str(h))

    for item in items:
        if isinstance(item, BaseModel):
            data = item.model_dump(by_alias=False)
            table.add_row(*[str(data.get(h, "")) for h in headers])
        else:
            table.add_row(str(item))

    console.print(table)


def exit_code_for(exc: Exception) -> int:
    """Map exception to semantic exit code.

    0: success (not handled here)
    1: generic client error / unknown SupersonicError
    2: AuthenticationError (401)
    3: ResourceNotFoundError (404)
    4: ValidationError (400)
    5: ServerError / ConnectionError (5xx / network)
    """
    if isinstance(exc, AuthenticationError):
        return 2
    if isinstance(exc, ResourceNotFoundError):
        return 3
    if isinstance(exc, ValidationError):
        return 4
    if isinstance(exc, (ServerError, SupersonicConnectionError)):
        return 5
    return 1
```

- [ ] **步骤 4：运行测试验证通过**

运行：
```bash
python3.11 -m pytest tests/cli/test_common.py -v
```
预期：所有测试 PASS（约 11 个）

- [ ] **步骤 5：Lint + 类型检查**

```bash
python3.11 -m ruff check src/supersonic/cli/common.py tests/cli/test_common.py
python3.11 -m mypy src/supersonic/cli/common.py
```

**重点**：`Page[BaseModel]` 泛型在 mypy strict 下可能报错。如果 mypy 不接受，加 `# type: ignore[type-arg]` 并附原因注释。

- [ ] **步骤 6：Commit**

```bash
cd /Users/yourton_ma/workspace/supersonic
git add python-sdk/src/supersonic/cli/common.py python-sdk/tests/cli/test_common.py
git commit -m "feat(sdk): implement CLI common utilities (get_client/format_output/exit_code_for)"
```

---

## 任务 4：config_schema.py — TOML/dotenv 解析 + CliConfig pydantic

**文件：**
- 创建：`python-sdk/src/supersonic/cli/config_schema.py`
- 创建：`python-sdk/tests/cli/test_config_schema.py`

**规格参考：** § 配置加载流程（TOML schema / load_config_file / Python 3.10 兼容）

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/cli/test_config_schema.py`

```python
"""Tests for cli/config_schema.py: TOML/dotenv parsing + CliConfig validation."""
from pathlib import Path

import pytest

from supersonic.cli.config_schema import (
    CliConfig,
    load_config_file,
)


class TestCliConfig:
    def test_empty_config_valid(self):
        c = CliConfig()
        assert c.host is None
        assert c.token is None
        assert c.retry is None

    def test_full_config_parses(self):
        c = CliConfig(
            host="http://test:9080",
            token="jwt-xxx",
            app_key="test-app",
            timeout=60.0,
            enable_async=True,
            log_level="DEBUG",
            retry={"max_retries": 5, "retry_delay": 2.0},
        )
        assert c.host == "http://test:9080"
        assert c.retry is not None
        assert c.retry.max_retries == 5

    def test_invalid_type_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CliConfig(timeout="not-a-float")

    def test_to_flat_dict_excludes_none(self):
        c = CliConfig(host="http://x", token="jwt")
        flat = c.to_flat_dict()
        assert flat["host"] == "http://x"
        assert flat["token"] == "jwt"
        assert "app_key" not in flat  # None values excluded
        assert "retry" not in flat


class TestLoadConfigFile:
    def test_toml_load(self, tmp_path: Path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
host = "http://from-toml:9080"
token = "jwt-from-toml"
timeout = 45.0

[retry]
max_retries = 5
""")
        result = load_config_file(config_file, None)
        assert result["host"] == "http://from-toml:9080"
        assert result["token"] == "jwt-from-toml"
        assert result["timeout"] == 45.0
        assert result["retry"]["max_retries"] == 5

    def test_env_file_load(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text("""
SUPERSONIC_HOST=http://from-env:9080
SUPERSONIC_TOKEN=jwt-from-env
SUPERSONIC_APP_KEY=env-app
""")
        result = load_config_file(None, env_file)
        assert result["host"] == "http://from-env:9080"
        assert result["token"] == "jwt-from-env"
        assert result["app_key"] == "env-app"

    def test_config_and_env_file_mutually_exclusive(self, tmp_path: Path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('host = "http://x"')
        env_file = tmp_path / ".env"
        env_file.write_text("SUPERSONIC_HOST=http://y")

        with pytest.raises(Exception):  # typer.BadParameter
            load_config_file(config_file, env_file)

    def test_config_file_not_found_raises(self, tmp_path: Path):
        missing = tmp_path / "nonexistent.toml"
        with pytest.raises(Exception):
            load_config_file(missing, None)

    def test_env_file_not_found_raises(self, tmp_path: Path):
        missing = tmp_path / "nonexistent.env"
        with pytest.raises(Exception):
            load_config_file(None, missing)

    def test_default_path_used_when_no_args(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        """When neither --config nor --env-file, check ~/.supersonic/config.toml."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        config_dir = fake_home / ".supersonic"
        config_dir.mkdir()
        default_config = config_dir / "config.toml"
        default_config.write_text('host = "http://default:9080"\ntoken = "jwt-default"')

        monkeypatch.setenv("HOME", str(fake_home))

        result = load_config_file(None, None)
        assert result["host"] == "http://default:9080"
        assert result["token"] == "jwt-default"

    def test_returns_empty_when_no_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """No --config, no --env-file, no ~/.supersonic/config.toml → empty dict."""
        fake_home = tmp_path / "empty-home"
        fake_home.mkdir()
        monkeypatch.setenv("HOME", str(fake_home))

        result = load_config_file(None, None)
        assert result == {}

    def test_env_file_parses_retry_not_supported(self, tmp_path: Path):
        """dotenv cannot express nested retry; only flat keys loaded."""
        env_file = tmp_path / ".env"
        env_file.write_text("SUPERSONIC_HOST=http://x\nSUPERSONIC_MAX_RETRIES=5")

        result = load_config_file(None, env_file)
        assert result["host"] == "http://x"
        # MAX_RETRIES maps to retry dict by build_pipeline; not parsed here
        assert "retry" not in result
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
python3.11 -m pytest tests/cli/test_config_schema.py -v
```
预期：FAIL，`ModuleNotFoundError`

- [ ] **步骤 3：实现 config_schema.py**

文件：`python-sdk/src/supersonic/cli/config_schema.py`

```python
"""CLI config schema: TOML/dotenv parsing + pydantic validation.

Review spec § 配置加载流程.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import typer
from pydantic import BaseModel, ConfigDict

# tomllib (3.11+) or tomli backport (3.10)
try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]  # Python 3.10 backport


class RetryConfigFile(BaseModel):
    """Retry config section in TOML file."""

    model_config = ConfigDict(extra="ignore")

    max_retries: int | None = None
    retry_delay: float | None = None
    max_backoff: float | None = None
    backoff_jitter: bool | None = None


class CliConfig(BaseModel):
    """Top-level CLI config schema (parsed from TOML or env vars)."""

    model_config = ConfigDict(extra="ignore")

    host: str | None = None
    token: str | None = None
    app_key: str | None = None
    timeout: float | None = None
    enable_async: bool | None = None
    log_level: str | None = None
    retry: RetryConfigFile | None = None

    def to_flat_dict(self) -> dict[str, Any]:
        """Flatten to dict with None values excluded.

        Nested 'retry' is kept as a dict if present.
        """
        data = self.model_dump(exclude_none=True)
        if self.retry is not None:
            data["retry"] = self.retry.model_dump(exclude_none=True)
        return data


def _load_toml(path: Path) -> dict[str, Any]:
    """Load TOML file, return raw dict."""
    with path.open("rb") as f:
        return tomllib.load(f)


def _load_dotenv(path: Path) -> dict[str, Any]:
    """Load dotenv file, mapping SUPERSONIC_X to flat keys.

    Supports: SUPERSONIC_HOST, SUPERSONIC_TOKEN, SUPERSONIC_APP_KEY,
              SUPERSONIC_TIMEOUT, SUPERSONIC_ENABLE_ASYNC, SUPERSONIC_LOG_LEVEL,
              SUPERSONIC_MAX_RETRIES
    """
    env_to_key = {
        "SUPERSONIC_HOST": "host",
        "SUPERSONIC_TOKEN": "token",
        "SUPERSONIC_APP_KEY": "app_key",
        "SUPERSONIC_TIMEOUT": "timeout",
        "SUPERSONIC_ENABLE_ASYNC": "enable_async",
        "SUPERSONIC_LOG_LEVEL": "log_level",
        "SUPERSONIC_MAX_RETRIES": "max_retries",  # special handling
    }

    result: dict[str, Any] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")

        if key not in env_to_key:
            continue
        flat_key = env_to_key[key]
        if flat_key == "enable_async":
            result[flat_key] = value.lower() == "true"
        elif flat_key == "timeout":
            result[flat_key] = float(value)
        elif flat_key == "max_retries":
            result.setdefault("retry", {})["max_retries"] = int(value)
        else:
            result[flat_key] = value

    return result


def load_config_file(
    config: Path | None,
    env_file: Path | None,
) -> dict[str, Any]:
    """Load config file based on priority: --config > --env-file > default path.

    --config and --env-file are mutually exclusive.
    Returns flat dict (not validated yet).
    """
    if config and env_file:
        raise typer.BadParameter(
            "--config and --env-file are mutually exclusive.",
        )

    if config is not None:
        if not config.exists():
            raise typer.BadParameter(f"Config file not found: {config}")
        return _load_toml(config)

    if env_file is not None:
        if not env_file.exists():
            raise typer.BadParameter(f"Env file not found: {env_file}")
        return _load_dotenv(env_file)

    # Default path: ~/.supersonic/config.toml
    default_path = Path.home() / ".supersonic" / "config.toml"
    if default_path.exists():
        return _load_toml(default_path)

    return {}


def validate_config_dict(data: dict[str, Any]) -> CliConfig:
    """Validate raw dict via CliConfig pydantic model."""
    return CliConfig.model_validate(data)


def merge_priority(
    cli_args: dict[str, Any],
    env_vars: dict[str, str],
    file_config: dict[str, Any],
) -> dict[str, Any]:
    """Merge config sources by priority: CLI > env > file > default.

    Returns flat dict ready for CliConfig.model_validate.
    """
    env_mapping = {
        "SUPERSONIC_HOST": "host",
        "SUPERSONIC_TOKEN": "token",
        "SUPERSONIC_APP_KEY": "app_key",
        "SUPERSONIC_TIMEOUT": "timeout",
        "SUPERSONIC_ENABLE_ASYNC": "enable_async",
        "SUPERSONIC_LOG_LEVEL": "log_level",
        "SUPERSONIC_MAX_RETRIES": "max_retries",
    }

    parsed_env: dict[str, Any] = {}
    for env_key, flat_key in env_mapping.items():
        if env_key not in env_vars:
            continue
        raw = env_vars[env_key]
        if flat_key == "enable_async":
            parsed_env[flat_key] = raw.lower() == "true"
        elif flat_key == "timeout":
            parsed_env[flat_key] = float(raw)
        elif flat_key == "max_retries":
            parsed_env.setdefault("retry", {})["max_retries"] = int(raw)
        else:
            parsed_env[flat_key] = raw

    # Priority: cli_args > env > file
    merged: dict[str, Any] = {}
    merged.update(file_config)
    merged.update(parsed_env)
    # CLI args may have None values (when option not provided); skip those
    for k, v in cli_args.items():
        if v is not None:
            merged[k] = v

    return merged
```

- [ ] **步骤 4：运行测试验证通过**

运行：
```bash
python3.11 -m pytest tests/cli/test_config_schema.py -v
```
预期：所有测试 PASS

- [ ] **步骤 5：Lint + 类型检查**

```bash
python3.11 -m ruff check src/supersonic/cli/config_schema.py tests/cli/test_config_schema.py
python3.11 -m mypy src/supersonic/cli/config_schema.py
```

- [ ] **步骤 6：Commit**

```bash
cd /Users/yourton_ma/workspace/supersonic
git add python-sdk/src/supersonic/cli/config_schema.py python-sdk/tests/cli/test_config_schema.py
git commit -m "feat(sdk): implement CLI config schema (TOML/dotenv parsing + CliConfig pydantic)"
```

---

## 任务 5：main.py — typer app + 全局 callback + cli_main 入口

**文件：**
- 创建：`python-sdk/src/supersonic/cli/main.py`
- 修改：`python-sdk/src/supersonic/cli/__init__.py`（追加 `from .main import app`）
- 创建：`python-sdk/tests/cli/test_main.py`

**规格参考：** § 命令结构（全局选项）+ § 错误处理（cli_main）

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/cli/test_main.py`

```python
"""Tests for cli/main.py: global options + version + cli_main wrapper."""
from pathlib import Path

import pytest
from typer.testing import CliRunner

from supersonic.cli.main import app, cli_main


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestVersionAndHelp:
    def test_version_flag(self, cli_runner):
        result = cli_runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.stdout

    def test_help_flag(self, cli_runner):
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "supersonic" in result.stdout.lower()
        # Subcommand groups should be listed
        assert "query" in result.stdout.lower()
        assert "metric" in result.stdout.lower()


class TestGlobalOptions:
    def test_host_token_via_cli(self, cli_runner, monkeypatch):
        """--host/--token on CLI should populate ctx.obj."""
        monkeypatch.delenv("SUPERSONIC_HOST", raising=False)
        monkeypatch.delenv("SUPERSONIC_TOKEN", raising=False)

        # Use a subcommand that prints config (config show)
        result = cli_runner.invoke(
            app,
            ["--host", "http://cli-test:9080", "--token", "jwt-cli", "config", "show"],
        )
        assert result.exit_code == 0
        assert "http://cli-test:9080" in result.stdout

    def test_host_token_via_env(self, cli_runner, monkeypatch):
        monkeypatch.setenv("SUPERSONIC_HOST", "http://env-test:9080")
        monkeypatch.setenv("SUPERSONIC_TOKEN", "jwt-env")

        result = cli_runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "http://env-test:9080" in result.stdout

    def test_config_file_loads(self, cli_runner, tmp_path: Path, monkeypatch):
        monkeypatch.delenv("SUPERSONIC_HOST", raising=False)
        monkeypatch.delenv("SUPERSONIC_TOKEN", raising=False)
        # Ensure default path doesn't exist
        monkeypatch.setenv("HOME", str(tmp_path / "empty-home"))

        config_file = tmp_path / "config.toml"
        config_file.write_text('host = "http://from-file:9080"\ntoken = "jwt-file"')

        result = cli_runner.invoke(
            app, ["--config", str(config_file), "config", "show"],
        )
        assert result.exit_code == 0
        assert "http://from-file:9080" in result.stdout

    def test_cli_overrides_env(self, cli_runner, monkeypatch):
        """CLI args take priority over env vars."""
        monkeypatch.setenv("SUPERSONIC_HOST", "http://env:9080")
        monkeypatch.setenv("SUPERSONIC_TOKEN", "jwt-env")

        result = cli_runner.invoke(
            app,
            ["--host", "http://cli:9080", "--token", "jwt-cli", "config", "show"],
        )
        assert result.exit_code == 0
        assert "http://cli:9080" in result.stdout
        assert "http://env:9080" not in result.stdout

    def test_missing_host_token_errors(self, cli_runner, monkeypatch):
        """Without host/token anywhere, should fail with exit code 1."""
        monkeypatch.delenv("SUPERSONIC_HOST", raising=False)
        monkeypatch.delenv("SUPERSONIC_TOKEN", raising=False)
        # Ensure no default config file
        monkeypatch.setenv("HOME", "/nonexistent-home-for-test")

        result = cli_runner.invoke(app, ["config", "show"])
        assert result.exit_code != 0


class TestCliMainWrapper:
    def test_cli_main_catches_supersonic_error(self, cli_runner, monkeypatch):
        """cli_main should catch SupersonicError and emit semantic exit code."""
        from unittest.mock import patch
        from supersonic.exceptions import MetricNotFoundError

        monkeypatch.setenv("SUPERSONIC_HOST", "http://x")
        monkeypatch.setenv("SUPERSONIC_TOKEN", "jwt")

        # Patch get_client to return a mock that raises
        from unittest.mock import MagicMock
        mock_client = MagicMock()
        mock_client.metrics.get.side_effect = MetricNotFoundError(resource_id=99)
        # config show won't trigger this; use metric get instead
        with patch("supersonic.cli.common.get_client", return_value=mock_client):
            result = cli_runner.invoke(app, ["metric", "get", "--id", "99"])
        assert result.exit_code == 3  # ResourceNotFoundError → exit 3
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
python3.11 -m pytest tests/cli/test_main.py -v
```
预期：FAIL，`ImportError: cannot import name 'app'`

- [ ] **步骤 3：实现 main.py**

文件：`python-sdk/src/supersonic/cli/main.py`

```python
"""CLI main entry: typer app + global callback + cli_main wrapper.

Review spec § 命令结构 + § 错误处理.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import typer

from supersonic import __version__
from supersonic.cli.config_schema import (
    load_config_file,
    merge_priority,
    validate_config_dict,
)
from supersonic.exceptions import SupersonicError, ValidationError
from supersonic.common.logging import configure_logging

app = typer.Typer(
    name="supersonic",
    help="SuperSonic Python SDK CLI - query and manage semantic models.",
    no_args_is_help=True,
    add_completion=True,
)


@app.callback()
def main_callback(
    ctx: typer.Context,
    host: str | None = typer.Option(None, "--host", help="SuperSonic service URL"),
    token: str | None = typer.Option(None, "--token", help="JWT auth token"),
    app_key: str | None = typer.Option(None, "--app-key", help="App-Key header value"),
    timeout: float | None = typer.Option(None, "--timeout", help="HTTP timeout in seconds"),
    config: Path | None = typer.Option(None, "--config", help="TOML config file path"),
    env_file: Path | None = typer.Option(None, "--env-file", help="dotenv file path"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON instead of table"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output"),
    verbose: bool = typer.Option(False, "--verbose", "--debug", help="Verbose logging"),
    quiet: bool = typer.Option(False, "--quiet", help="Error-only logging"),
    show_version: bool = typer.Option(False, "--version", "-V", help="Show version and exit"),
) -> None:
    """SuperSonic CLI - manage semantic models and run queries."""
    if show_version:
        typer.echo(f"supersonic-sdk {__version__}")
        raise typer.Exit(0)

    if verbose and quiet:
        raise typer.BadParameter("--verbose and --quiet are mutually exclusive.")

    # Determine log level
    if verbose:
        log_level = "DEBUG"
    elif quiet:
        log_level = "ERROR"
    else:
        log_level = "WARNING"
    configure_logging(log_level)

    # Load config file (TOML or dotenv)
    file_config = load_config_file(config, env_file)

    # CLI args dict (None values mean "not provided")
    cli_args: dict[str, Any] = {
        "host": host,
        "token": token,
        "app_key": app_key,
        "timeout": timeout,
        "log_level": log_level if (verbose or quiet) else None,
    }

    # Merge by priority: CLI > env > file
    merged = merge_priority(cli_args, dict(__import__("os").environ), file_config)
    validated = validate_config_dict(merged)
    flat = validated.to_flat_dict()

    # Override with CLI flags that aren't in config schema
    flat.setdefault("log_level", log_level)

    ctx.obj = flat
    ctx.obj["__json"] = json_output
    ctx.obj["__no_color"] = no_color


# Mount subcommand groups.
# Each subcommand module exports a `app` (typer.Typer instance).
# Lazy import to avoid circular deps and allow partial testing.
def _register_subcommands() -> None:
    from supersonic.cli.config_cmd import app as config_app
    from supersonic.cli.database import app as database_app
    from supersonic.cli.dataset import app as dataset_app
    from supersonic.cli.dimension import app as dimension_app
    from supersonic.cli.domain import app as domain_app
    from supersonic.cli.metric import app as metric_app
    from supersonic.cli.model import app as model_app
    from supersonic.cli.query import app as query_app

    app.add_typer(query_app, name="query", help="Query the semantic layer (sql/metric/chat)")
    app.add_typer(domain_app, name="domain", help="Domain CRUD")
    app.add_typer(model_app, name="model", help="Model CRUD")
    app.add_typer(dimension_app, name="dimension", help="Dimension CRUD")
    app.add_typer(metric_app, name="metric", help="Metric CRUD + publish/unpublish")
    app.add_typer(database_app, name="database", help="Database CRUD + test-connect")
    app.add_typer(dataset_app, name="dataset", help="Dataset read")
    app.add_typer(config_app, name="config", help="Configuration utilities")


_register_subcommands()


def cli_main() -> None:
    """CLI entry point referenced by pyproject.toml [project.scripts]."""
    try:
        app()
    except SupersonicError as e:
        from supersonic.cli.common import exit_code_for

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
        raise
    except Exception as e:
        logging.getLogger("supersonic").exception("Unexpected CLI error")
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1) from e


if __name__ == "__main__":
    cli_main()
```

- [ ] **步骤 4：修改 cli/__init__.py（re-export app）**

文件：`python-sdk/src/supersonic/cli/__init__.py`

```python
"""SuperSonic CLI subpackage.

Provides `supersonic` command via typer. Importable as `from supersonic.cli import app`.
"""
from supersonic.cli.main import app, cli_main

__all__ = ["app", "cli_main"]
```

- [ ] **步骤 5：Commit（即使子命令组未实现，先 commit main.py 框架）**

> **注**：`_register_subcommands()` 会 import 7 个还未实现的子命令组模块，导致 ImportError。
> 此时先不运行测试（main.py 测试会失败）。本任务先 commit main.py + __init__.py，
> 任务 6（conftest）+ 任务 7-14（子命令组）会让测试逐步通过。

```bash
cd /Users/yourton_ma/workspace/supersonic
git add python-sdk/src/supersonic/cli/main.py python-sdk/src/supersonic/cli/__init__.py
git commit -m "feat(sdk): implement CLI main.py with global callback and cli_main wrapper"
```

> **替代方案**（如果 main.py 因 ImportError 无法 import）：把 `_register_subcommands()`
> 改为延迟注册——在 `cli_main()` 内部调用而非模块加载时。但 typer 的子命令注册必须在
> `app()` 调用前完成，所以最终仍是模块加载时注册。**推荐**：先 commit 但跳过测试，
> 任务 6+ 之后让测试逐步通过。

---

## 任务 6：conftest.py — CLI 共享 fixtures

**文件：**
- 创建：`python-sdk/tests/cli/conftest.py`

**规格参考：** § 测试策略（共享 fixtures）

- [ ] **步骤 1：创建 conftest.py**

文件：`python-sdk/tests/cli/conftest.py`

```python
"""Shared fixtures for CLI tests.

Strategy: mock SupersonicClient via MagicMock (not pytest-httpx).
CLI layer tests assume SDK is already tested by Phase 1 (154 tests / 95% coverage).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    """typer test runner, isolates stdout/stderr."""
    return CliRunner()


@pytest.fixture
def mock_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock SDK SupersonicClient to avoid real HTTP.

    Each namespace has sensible defaults; individual tests can override.
    """
    client = MagicMock(name="MockSupersonicClient")

    # Default: metric list returns empty page
    from supersonic.common.pagination import Page
    from supersonic.models.metric import Metric

    client.metrics.list.return_value = Page[Metric](
        items=[], total=0, page=1, page_size=10,
    )
    client.metrics.get.return_value = Metric(
        id=1, name="销售额", biz_name="sales_amt",
        model_id=10, define_type="MEASURE", type="NUMBER",
    )

    # Patch get_client so all CLI commands use this mock
    monkeypatch.setattr(
        "supersonic.cli.common.get_client",
        lambda ctx: client,
    )
    return client


@pytest.fixture
def sample_toml_config(tmp_path: Path) -> Path:
    """Temp TOML config file for --config tests."""
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
def sample_env_file(tmp_path: Path) -> Path:
    """Temp dotenv file for --env-file tests."""
    env_file = tmp_path / ".env"
    env_file.write_text("""
SUPERSONIC_HOST=http://from-env:9080
SUPERSONIC_TOKEN=jwt-from-env
""")
    return env_file


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure no SUPERSONIC_* env vars and no default config file."""
    for key in [
        "SUPERSONIC_HOST", "SUPERSONIC_TOKEN", "SUPERSONIC_APP_KEY",
        "SUPERSONIC_TIMEOUT", "SUPERSONIC_ENABLE_ASYNC", "SUPERSONIC_LOG_LEVEL",
        "SUPERSONIC_MAX_RETRIES",
    ]:
        monkeypatch.delenv(key, raising=False)
    # Point HOME to empty dir to avoid ~/.supersonic/config.toml
    empty_home = tmp_path / "empty-home"
    empty_home.mkdir()
    monkeypatch.setenv("HOME", str(empty_home))
```

- [ ] **步骤 2：Commit**

```bash
cd /Users/yourton_ma/workspace/supersonic
git add python-sdk/tests/cli/conftest.py
git commit -m "test(sdk): add CLI shared fixtures (cli_runner/mock_client/sample configs)"
```

---

## 任务 7：query.py — 5 个查询子命令

**文件：**
- 创建：`python-sdk/src/supersonic/cli/query.py`
- 创建：`python-sdk/tests/cli/test_query.py`

**规格参考：** § 命令清单 → query

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/cli/test_query.py`

```python
"""Tests for cli/query.py: sql/sqls/validate/metric/chat subcommands."""
import pytest
from typer.testing import CliRunner

from supersonic.cli.main import app
from supersonic.models.query import (
    ChatQueryResult,
    ParseState,
    QueryColumn,
    QueryResult,
    SemanticParseInfo,
    ValidationResult,
)


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestSqlSubcommand:
    def test_sql_returns_query_result_table(self, cli_runner, mock_client):
        mock_client.query.sql.return_value = QueryResult(
            columns=[QueryColumn(name="product", type="VARCHAR")],
            result_rows=[{"product": "iPhone"}],
        )
        result = cli_runner.invoke(app, ["query", "sql", "SELECT product FROM sales"])
        assert result.exit_code == 0
        assert "product" in result.stdout
        assert "iPhone" in result.stdout

    def test_sql_json_output(self, cli_runner, mock_client):
        mock_client.query.sql.return_value = QueryResult(
            columns=[QueryColumn(name="x", type="INT")],
            result_rows=[{"x": 1}],
        )
        result = cli_runner.invoke(app, ["--json", "query", "sql", "SELECT 1"])
        assert result.exit_code == 0
        assert '"columns"' in result.stdout
        assert '"result_rows"' in result.stdout

    def test_sql_with_data_set_id(self, cli_runner, mock_client):
        mock_client.query.sql.return_value = QueryResult(
            columns=[], result_rows=[],
        )
        result = cli_runner.invoke(
            app, ["query", "sql", "SELECT 1", "--data-set-id", "5"],
        )
        assert result.exit_code == 0
        # Verify SDK was called with data_set_id=5
        mock_client.query.sql.assert_called_once()
        _, kwargs = mock_client.query.sql.call_args
        assert kwargs.get("data_set_id") == 5


class TestValidateSubcommand:
    def test_validate_returns_validation_result(self, cli_runner, mock_client):
        mock_client.query.validate.return_value = ValidationResult(is_valid=True)
        result = cli_runner.invoke(app, ["query", "validate", "SELECT 1"])
        assert result.exit_code == 0
        assert "True" in result.stdout or "true" in result.stdout


class TestMetricSubcommand:
    def test_metric_query_with_filters(self, cli_runner, mock_client):
        mock_client.query.metric.return_value = QueryResult(
            columns=[QueryColumn(name="category", type="VARCHAR"),
                     QueryColumn(name="sales", type="DOUBLE")],
            result_rows=[{"category": "手机", "sales": 100.0}],
        )
        result = cli_runner.invoke(
            app,
            [
                "query", "metric",
                "--metrics", "销售额",
                "--dimensions", "品类",
                "--start", "2026-01-01",
                "--end", "2026-06-30",
            ],
        )
        assert result.exit_code == 0
        assert "手机" in result.stdout
        # Verify SDK call signature
        _, kwargs = mock_client.query.metric.call_args
        assert kwargs["metrics"] == ["销售额"]
        assert kwargs["dimensions"] == ["品类"]


class TestChatSubcommand:
    def test_chat_detailed_default(self, cli_runner, mock_client):
        mock_client.query.chat.return_value = ChatQueryResult(
            query_result=QueryResult(
                columns=[QueryColumn(name="p", type="VARCHAR")],
                result_rows=[{"p": "iPhone"}],
            ),
            selected_parse=SemanticParseInfo(sql="SELECT p FROM sales LIMIT 1", score=0.95),
            parse_state=ParseState.COMPLETED,
        )
        result = cli_runner.invoke(app, ["query", "chat", "--text", "top product"])
        assert result.exit_code == 0
        # Detailed mode shows parse info
        assert "SELECT p FROM sales" in result.stdout

    def test_chat_concise_mode(self, cli_runner, mock_client):
        mock_client.query.chat.return_value = QueryResult(
            columns=[QueryColumn(name="p", type="VARCHAR")],
            result_rows=[{"p": "iPhone"}],
        )
        result = cli_runner.invoke(
            app, ["query", "chat", "--text", "top product", "--concise"],
        )
        assert result.exit_code == 0
        # Concise mode: detailed=False passed to SDK
        _, kwargs = mock_client.query.chat.call_args
        assert kwargs["detailed"] is False
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
python3.11 -m pytest tests/cli/test_query.py -v
```
预期：FAIL，`ImportError: cannot import name 'query'`（query.py 还没创建）

- [ ] **步骤 3：实现 query.py**

文件：`python-sdk/src/supersonic/cli/query.py`

```python
"""Query subcommand group: sql/sqls/validate/metric/chat.

Review spec § 命令清单 → query.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from supersonic.cli.common import format_output, get_client
from supersonic.models.query import DateConf, DateMode, Filter, FilterOperator

app = typer.Typer(name="query", help="Query the semantic layer.")


@app.command(name="sql")
def sql_cmd(
    ctx: typer.Context,
    sql: str = typer.Argument(..., help="S2SQL query"),
    data_set_id: int | None = typer.Option(None, "--data-set-id", help="Dataset ID"),
    limit: int = typer.Option(1000, "--limit", help="Row limit"),
) -> None:
    """Execute S2SQL query."""
    client = get_client(ctx)
    result = client.query.sql(sql, data_set_id=data_set_id, limit=limit)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="sqls")
def sqls_cmd(
    ctx: typer.Context,
    sqls_file: Path = typer.Option(..., "--sqls-file", help="File with one SQL per line"),
    data_set_id: int | None = typer.Option(None, "--data-set-id"),
) -> None:
    """Execute batch S2SQL queries from file."""
    if not sqls_file.exists():
        raise typer.BadParameter(f"File not found: {sqls_file}")

    sqls = [line.strip() for line in sqls_file.read_text().splitlines() if line.strip()]
    if not sqls:
        raise typer.BadParameter(f"No SQL statements found in {sqls_file}")

    client = get_client(ctx)
    results = client.query.sqls(sqls, data_set_id=data_set_id)
    format_output(
        results,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="validate")
def validate_cmd(
    ctx: typer.Context,
    sql: str = typer.Argument(..., help="S2SQL to validate"),
    data_set_id: int | None = typer.Option(None, "--data-set-id"),
) -> None:
    """Validate S2SQL without executing."""
    client = get_client(ctx)
    result = client.query.validate(sql, data_set_id=data_set_id)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="metric")
def metric_cmd(
    ctx: typer.Context,
    metrics: str = typer.Option(..., "--metrics", help="Comma-separated metric biz names"),
    dimensions: str | None = typer.Option(None, "--dimensions", help="Comma-separated dim biz names"),
    start: str | None = typer.Option(None, "--start", help="Start date YYYY-MM-DD"),
    end: str | None = typer.Option(None, "--end", help="End date YYYY-MM-DD"),
    limit: int = typer.Option(1000, "--limit"),
) -> None:
    """Structured metric query (no SQL needed)."""
    metric_list = [m.strip() for m in metrics.split(",") if m.strip()]
    dim_list = [d.strip() for d in dimensions.split(",")] if dimensions else None

    date_info: DateConf | None = None
    if start and end:
        date_info = DateConf(
            date_mode=DateMode.BETWEEN,
            start_date=start,
            end_date=end,
        )
    elif start or end:
        raise typer.BadParameter("Both --start and --end are required for date range.")

    client = get_client(ctx)
    result = client.query.metric(
        metrics=metric_list,
        dimensions=dim_list,
        date_info=date_info,
        limit=limit,
    )
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="chat")
def chat_cmd(
    ctx: typer.Context,
    text: str = typer.Option(..., "--text", "-t", help="Natural language query"),
    data_set_ids: str | None = typer.Option(None, "--data-set-ids", help="Comma-separated dataset IDs"),
    detailed: bool = typer.Option(True, "--detailed/--concise", help="Show parse info (default) or just result"),
) -> None:
    """Natural language query via Chat BI."""
    ds_ids = None
    if data_set_ids:
        ds_ids = [int(x.strip()) for x in data_set_ids.split(",") if x.strip()]

    client = get_client(ctx)
    result = client.query.chat(
        text,
        data_set_ids=ds_ids,
        detailed=detailed,
    )
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )
```

- [ ] **步骤 4：运行测试验证通过**

运行：
```bash
python3.11 -m pytest tests/cli/test_query.py -v
```
预期：所有测试 PASS

- [ ] **步骤 5：Lint + 类型检查 + Commit**

```bash
python3.11 -m ruff check src/supersonic/cli/query.py tests/cli/test_query.py
python3.11 -m mypy src/supersonic/cli/query.py
```

```bash
cd /Users/yourton_ma/workspace/supersonic
git add python-sdk/src/supersonic/cli/query.py python-sdk/tests/cli/test_query.py
git commit -m "feat(sdk): implement query subcommand group (sql/sqls/validate/metric/chat)"
```

---

## 任务 8：domain.py — 5 个 domain CRUD 子命令

**文件：**
- 创建：`python-sdk/src/supersonic/cli/domain.py`
- 创建：`python-sdk/tests/cli/test_domain.py`

**规格参考：** § 命令清单 → 元数据 CRUD 命名空间（domain 是模板）

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/cli/test_domain.py`

```python
"""Tests for cli/domain.py: list/get/create/update/delete subcommands.

domain is the template for all 6 metadata resource command groups.
"""
import pytest
from typer.testing import CliRunner

from supersonic.cli.main import app
from supersonic.common.pagination import Page
from supersonic.models.domain import Domain


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def sample_domain():
    return Domain(
        id=1, name="销售域", biz_name="sales",
        parent_domain_id=0, status="ONLINE",
    )


class TestDomainList:
    def test_list_table_output(self, cli_runner, mock_client, sample_domain):
        mock_client.domains.list.return_value = Page[Domain](
            items=[sample_domain], total=1, page=1, page_size=10,
        )
        result = cli_runner.invoke(app, ["domain", "list"])
        assert result.exit_code == 0
        assert "销售域" in result.stdout
        assert "Total: 1" in result.stdout

    def test_list_json_output(self, cli_runner, mock_client, sample_domain):
        mock_client.domains.list.return_value = Page[Domain](
            items=[sample_domain], total=1, page=1, page_size=10,
        )
        result = cli_runner.invoke(app, ["--json", "domain", "list"])
        assert result.exit_code == 0
        assert '"name": "销售域"' in result.stdout


class TestDomainGet:
    def test_get_returns_domain(self, cli_runner, mock_client, sample_domain):
        mock_client.domains.get.return_value = sample_domain
        result = cli_runner.invoke(app, ["domain", "get", "--id", "1"])
        assert result.exit_code == 0
        assert "销售域" in result.stdout

    def test_get_404_exit_code_3(self, cli_runner, mock_client):
        from supersonic.exceptions import DomainNotFoundError
        mock_client.domains.get.side_effect = DomainNotFoundError(resource_id=999)
        result = cli_runner.invoke(app, ["domain", "get", "--id", "999"])
        assert result.exit_code == 3


class TestDomainCreate:
    def test_create_minimal(self, cli_runner, mock_client, sample_domain):
        result = cli_runner.invoke(
            app,
            ["domain", "create", "--name", "销售域", "--biz-name", "sales"],
        )
        assert result.exit_code == 0
        mock_client.domains.create.assert_called_once()


class TestDomainUpdate:
    def test_update_description(self, cli_runner, mock_client, sample_domain):
        result = cli_runner.invoke(
            app,
            ["domain", "update", "--id", "1", "--description", "新描述"],
        )
        assert result.exit_code == 0


class TestDomainDelete:
    def test_delete_succeeds(self, cli_runner, mock_client):
        result = cli_runner.invoke(app, ["domain", "delete", "--id", "1"])
        assert result.exit_code == 0
        mock_client.domains.delete.assert_called_once_with(1)
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```bash
python3.11 -m pytest tests/cli/test_domain.py -v
```
预期：FAIL，`ImportError`

- [ ] **步骤 3：实现 domain.py**

文件：`python-sdk/src/supersonic/cli/domain.py`

```python
"""Domain subcommand group: list/get/create/update/delete.

Review spec § 命令清单 → 元数据 CRUD.
"""
from __future__ import annotations

import typer

from supersonic.cli.common import format_output, get_client
from supersonic.models.domain import DomainCreateReq, DomainUpdateReq

app = typer.Typer(name="domain", help="Domain CRUD.")


@app.command(name="list")
def list_cmd(
    ctx: typer.Context,
    page: int = typer.Option(1, "--page"),
    page_size: int = typer.Option(10, "--page-size"),
) -> None:
    """List domains."""
    client = get_client(ctx)
    result = client.domains.list(page=page, page_size=page_size)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="get")
def get_cmd(
    ctx: typer.Context,
    id: int = typer.Option(..., "--id", help="Domain ID"),
) -> None:
    """Get a domain by ID."""
    client = get_client(ctx)
    result = client.domains.get(id)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="create")
def create_cmd(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name"),
    biz_name: str = typer.Option(..., "--biz-name"),
    parent_domain_id: int | None = typer.Option(None, "--parent-domain-id"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    """Create a new domain."""
    client = get_client(ctx)
    req = DomainCreateReq(
        name=name, biz_name=biz_name,
        parent_domain_id=parent_domain_id, description=description,
    )
    result = client.domains.create(req)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="update")
def update_cmd(
    ctx: typer.Context,
    id: int = typer.Option(..., "--id"),
    name: str | None = typer.Option(None, "--name"),
    biz_name: str | None = typer.Option(None, "--biz-name"),
    parent_domain_id: int | None = typer.Option(None, "--parent-domain-id"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    """Update a domain."""
    client = get_client(ctx)
    req = DomainUpdateReq(
        id=id, name=name, biz_name=biz_name,
        parent_domain_id=parent_domain_id, description=description,
    )
    result = client.domains.update(id, req)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="delete")
def delete_cmd(
    ctx: typer.Context,
    id: int = typer.Option(..., "--id"),
) -> None:
    """Delete a domain."""
    client = get_client(ctx)
    client.domains.delete(id)
    typer.echo(f"Deleted domain {id}")
```

- [ ] **步骤 4：运行测试验证通过 + Lint + 类型检查 + Commit**

```bash
python3.11 -m pytest tests/cli/test_domain.py -v
python3.11 -m ruff check src/supersonic/cli/domain.py tests/cli/test_domain.py
python3.11 -m mypy src/supersonic/cli/domain.py
```

```bash
cd /Users/yourton_ma/workspace/supersonic
git add python-sdk/src/supersonic/cli/domain.py python-sdk/tests/cli/test_domain.py
git commit -m "feat(sdk): implement domain subcommand group (CRUD)"
```

---

## 任务 9：model.py — 5 个 model CRUD 子命令

**文件：**
- 创建：`python-sdk/src/supersonic/cli/model.py`
- 创建：`python-sdk/tests/cli/test_model.py`

**规格参考：** § 命令清单 → model

**特殊点**：model list 用 `--domain-id`（必填），是路径参数而非 query。

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/cli/test_model.py`

```python
"""Tests for cli/model.py."""
import pytest
from typer.testing import CliRunner

from supersonic.cli.main import app
from supersonic.common.pagination import Page
from supersonic.models.model import Model


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def sample_model():
    return Model(
        id=10, name="订单模型", biz_name="order",
        domain_id=1, database_id=5,
    )


class TestModelList:
    def test_list_requires_domain_id(self, cli_runner, mock_client, sample_model):
        """--domain-id is required for model list."""
        mock_client.models.list.return_value = Page[Model](
            items=[sample_model], total=1, page=1, page_size=10,
        )
        # Missing --domain-id should error
        result = cli_runner.invoke(app, ["model", "list"])
        assert result.exit_code != 0

    def test_list_with_domain_id(self, cli_runner, mock_client, sample_model):
        mock_client.models.list.return_value = Page[Model](
            items=[sample_model], total=1, page=1, page_size=10,
        )
        result = cli_runner.invoke(app, ["model", "list", "--domain-id", "1"])
        assert result.exit_code == 0
        assert "订单模型" in result.stdout


class TestModelGet:
    def test_get_returns_model(self, cli_runner, mock_client, sample_model):
        mock_client.models.get.return_value = sample_model
        result = cli_runner.invoke(app, ["model", "get", "--id", "10"])
        assert result.exit_code == 0
        assert "订单模型" in result.stdout


class TestModelCreate:
    def test_create_minimal(self, cli_runner, mock_client, sample_model):
        result = cli_runner.invoke(
            app,
            [
                "model", "create",
                "--domain-id", "1", "--database-id", "5",
                "--name", "订单模型", "--biz-name", "order",
                "--table-name", "orders",
            ],
        )
        assert result.exit_code == 0
        mock_client.models.create.assert_called_once()


class TestModelUpdate:
    def test_update_description(self, cli_runner, mock_client, sample_model):
        result = cli_runner.invoke(
            app, ["model", "update", "--id", "10", "--table-name", "new_orders"],
        )
        assert result.exit_code == 0


class TestModelDelete:
    def test_delete_succeeds(self, cli_runner, mock_client):
        result = cli_runner.invoke(app, ["model", "delete", "--id", "10"])
        assert result.exit_code == 0
        mock_client.models.delete.assert_called_once_with(10)
```

- [ ] **步骤 2：运行测试验证失败 + 实现模型 list/get/create/update/delete**

文件：`python-sdk/src/supersonic/cli/model.py`

```python
"""Model subcommand group: list/get/create/update/delete.

Review spec § 命令清单 → model.
Note: model list requires --domain-id (path param in SDK, not query).
"""
from __future__ import annotations

import typer

from supersonic.cli.common import format_output, get_client
from supersonic.models.model import ModelCreateReq

app = typer.Typer(name="model", help="Model CRUD.")


@app.command(name="list")
def list_cmd(
    ctx: typer.Context,
    domain_id: int = typer.Option(..., "--domain-id", help="Domain ID (required)"),
    page: int = typer.Option(1, "--page"),
    page_size: int = typer.Option(10, "--page-size"),
) -> None:
    """List models in a domain."""
    client = get_client(ctx)
    result = client.models.list(domain_id=domain_id, page=page, page_size=page_size)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="get")
def get_cmd(
    ctx: typer.Context,
    id: int = typer.Option(..., "--id"),
) -> None:
    """Get a model by ID."""
    client = get_client(ctx)
    result = client.models.get(id)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="create")
def create_cmd(
    ctx: typer.Context,
    domain_id: int = typer.Option(..., "--domain-id"),
    database_id: int = typer.Option(..., "--database-id"),
    name: str = typer.Option(..., "--name"),
    biz_name: str = typer.Option(..., "--biz-name"),
    table_name: str | None = typer.Option(None, "--table-name"),
    table_query: str | None = typer.Option(None, "--table-query", help="View SQL (alternative to table-name)"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    """Create a new model."""
    if not table_name and not table_query:
        raise typer.BadParameter("Either --table-name or --table-query is required.")
    client = get_client(ctx)
    req = ModelCreateReq(
        domain_id=domain_id, database_id=database_id,
        name=name, biz_name=biz_name,
        table_name=table_name, table_query=table_query,
        description=description,
    )
    result = client.models.create(req)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="update")
def update_cmd(
    ctx: typer.Context,
    id: int = typer.Option(..., "--id"),
    name: str | None = typer.Option(None, "--name"),
    biz_name: str | None = typer.Option(None, "--biz-name"),
    table_name: str | None = typer.Option(None, "--table-name"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    """Update a model."""
    client = get_client(ctx)
    req = ModelCreateReq(  # SDK uses same req type for create/update
        domain_id=0, database_id=0,  # required by schema, ignored on update
        name=name, biz_name=biz_name,
        table_name=table_name, description=description,
    )
    result = client.models.update(id, req)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="delete")
def delete_cmd(
    ctx: typer.Context,
    id: int = typer.Option(..., "--id"),
) -> None:
    """Delete a model."""
    client = get_client(ctx)
    client.models.delete(id)
    typer.echo(f"Deleted model {id}")
```

- [ ] **步骤 3：运行测试 + Lint + Commit**

```bash
python3.11 -m pytest tests/cli/test_model.py -v
python3.11 -m ruff check src/supersonic/cli/model.py tests/cli/test_model.py
python3.11 -m mypy src/supersonic/cli/model.py
```

```bash
cd /Users/yourton_ma/workspace/supersonic
git add python-sdk/src/supersonic/cli/model.py python-sdk/tests/cli/test_model.py
git commit -m "feat(sdk): implement model subcommand group (CRUD)"
```

---

## 任务 10：dimension.py — 6 个 dimension 子命令（含 query-values）

**文件：**
- 创建：`python-sdk/src/supersonic/cli/dimension.py`
- 创建：`python-sdk/tests/cli/test_dimension.py`

**规格参考：** § 命令清单 → dimension（含特有 query-values 命令）

**注**：dimension list 用 `--model-id`（query 参数，可空）。

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/cli/test_dimension.py`

```python
"""Tests for cli/dimension.py: CRUD + query-values."""
import pytest
from typer.testing import CliRunner

from supersonic.cli.main import app
from supersonic.common.pagination import Page
from supersonic.models.dimension import Dimension


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def sample_dimension():
    return Dimension(
        id=100, name="品类", biz_name="category",
        model_id=10, type="VARCHAR",
    )


class TestDimensionList:
    def test_list_with_model_id(self, cli_runner, mock_client, sample_dimension):
        mock_client.dimensions.list.return_value = Page[Dimension](
            items=[sample_dimension], total=1, page=1, page_size=10,
        )
        result = cli_runner.invoke(app, ["dimension", "list", "--model-id", "10"])
        assert result.exit_code == 0
        assert "品类" in result.stdout


class TestDimensionCRUD:
    def test_get_returns_dimension(self, cli_runner, mock_client, sample_dimension):
        mock_client.dimensions.get.return_value = sample_dimension
        result = cli_runner.invoke(app, ["dimension", "get", "--id", "100"])
        assert result.exit_code == 0

    def test_create(self, cli_runner, mock_client, sample_dimension):
        result = cli_runner.invoke(
            app,
            [
                "dimension", "create",
                "--model-id", "10", "--name", "品类", "--biz-name", "category",
                "--type", "VARCHAR",
            ],
        )
        assert result.exit_code == 0

    def test_update(self, cli_runner, mock_client, sample_dimension):
        result = cli_runner.invoke(
            app, ["dimension", "update", "--id", "100", "--description", "新描述"],
        )
        assert result.exit_code == 0

    def test_delete(self, cli_runner, mock_client):
        result = cli_runner.invoke(app, ["dimension", "delete", "--id", "100"])
        assert result.exit_code == 0


class TestDimensionQueryValues:
    def test_query_values_returns_list(self, cli_runner, mock_client):
        mock_client.dimensions.query_values.return_value = [
            {"value": "手机"}, {"value": "电脑"},
        ]
        result = cli_runner.invoke(
            app, ["dimension", "query-values", "--id", "100"],
        )
        assert result.exit_code == 0
        assert "手机" in result.stdout
        assert "电脑" in result.stdout
```

- [ ] **步骤 2：实现 dimension.py**

文件：`python-sdk/src/supersonic/cli/dimension.py`

```python
"""Dimension subcommand group: list/get/create/update/delete + query-values.

Review spec § 命令清单 → dimension.
"""
from __future__ import annotations

import typer

from supersonic.cli.common import format_output, get_client
from supersonic.models.dimension import DimensionCreateReq

app = typer.Typer(name="dimension", help="Dimension CRUD + query values.")


@app.command(name="list")
def list_cmd(
    ctx: typer.Context,
    model_id: int | None = typer.Option(None, "--model-id"),
    page: int = typer.Option(1, "--page"),
    page_size: int = typer.Option(10, "--page-size"),
) -> None:
    """List dimensions (optionally filtered by model)."""
    client = get_client(ctx)
    result = client.dimensions.list(model_id=model_id, page=page, page_size=page_size)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="get")
def get_cmd(ctx: typer.Context, id: int = typer.Option(..., "--id")) -> None:
    client = get_client(ctx)
    result = client.dimensions.get(id)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="create")
def create_cmd(
    ctx: typer.Context,
    model_id: int = typer.Option(..., "--model-id"),
    name: str = typer.Option(..., "--name"),
    biz_name: str = typer.Option(..., "--biz-name"),
    type: str = typer.Option(..., "--type", help="Data type: VARCHAR/NUMBER/DATE/..."),
    expr: str | None = typer.Option(None, "--expr"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    client = get_client(ctx)
    req = DimensionCreateReq(
        model_id=model_id, name=name, biz_name=biz_name,
        type=type, expr=expr, description=description,
    )
    result = client.dimensions.create(req)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="update")
def update_cmd(
    ctx: typer.Context,
    id: int = typer.Option(..., "--id"),
    name: str | None = typer.Option(None, "--name"),
    biz_name: str | None = typer.Option(None, "--biz-name"),
    type: str | None = typer.Option(None, "--type"),
    expr: str | None = typer.Option(None, "--expr"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    client = get_client(ctx)
    req = DimensionCreateReq(  # SDK uses same req type for create/update
        model_id=0,  # required by schema, ignored on update
        name=name, biz_name=biz_name, type=type or "",
        expr=expr, description=description,
    )
    result = client.dimensions.update(id, req)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="delete")
def delete_cmd(ctx: typer.Context, id: int = typer.Option(..., "--id")) -> None:
    client = get_client(ctx)
    client.dimensions.delete(id)
    typer.echo(f"Deleted dimension {id}")


@app.command(name="query-values")
def query_values_cmd(
    ctx: typer.Context,
    id: int = typer.Option(..., "--id", help="Dimension ID"),
) -> None:
    """Query distinct values of a dimension."""
    client = get_client(ctx)
    result = client.dimensions.query_values(id)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )
```

- [ ] **步骤 3：运行测试 + Lint + Commit**

```bash
python3.11 -m pytest tests/cli/test_dimension.py -v
python3.11 -m ruff check src/supersonic/cli/dimension.py tests/cli/test_dimension.py
python3.11 -m mypy src/supersonic/cli/dimension.py
```

```bash
cd /Users/yourton_ma/workspace/supersonic
git add python-sdk/src/supersonic/cli/dimension.py python-sdk/tests/cli/test_dimension.py
git commit -m "feat(sdk): implement dimension subcommand group (CRUD + query-values)"
```

---

## 任务 11：metric.py — 7 个 metric 子命令（含 publish/unpublish）

**文件：**
- 创建：`python-sdk/src/supersonic/cli/metric.py`
- 创建：`python-sdk/tests/cli/test_metric.py`

**规格参考：** § 命令清单 → metric

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/cli/test_metric.py`

```python
"""Tests for cli/metric.py: CRUD + publish/unpublish."""
import pytest
from typer.testing import CliRunner

from supersonic.cli.main import app
from supersonic.common.pagination import Page
from supersonic.models.metric import Metric


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def sample_metric():
    return Metric(
        id=1, name="销售额", biz_name="sales_amt",
        model_id=10, define_type="MEASURE", type="NUMBER",
    )


class TestMetricList:
    def test_list_table(self, cli_runner, mock_client, sample_metric):
        mock_client.metrics.list.return_value = Page[Metric](
            items=[sample_metric], total=1, page=1, page_size=10,
        )
        result = cli_runner.invoke(app, ["metric", "list", "--model-id", "10"])
        assert result.exit_code == 0
        assert "销售额" in result.stdout


class TestMetricCRUD:
    def test_get(self, cli_runner, mock_client, sample_metric):
        mock_client.metrics.get.return_value = sample_metric
        result = cli_runner.invoke(app, ["metric", "get", "--id", "1"])
        assert result.exit_code == 0

    def test_create(self, cli_runner, mock_client, sample_metric):
        result = cli_runner.invoke(
            app,
            [
                "metric", "create",
                "--model-id", "10", "--name", "销售额", "--biz-name", "sales_amt",
                "--define-type", "MEASURE", "--type", "NUMBER",
                "--expression", "pay_amt",
            ],
        )
        assert result.exit_code == 0

    def test_update(self, cli_runner, mock_client, sample_metric):
        result = cli_runner.invoke(
            app, ["metric", "update", "--id", "1", "--description", "新描述"],
        )
        assert result.exit_code == 0

    def test_delete(self, cli_runner, mock_client):
        result = cli_runner.invoke(app, ["metric", "delete", "--id", "1"])
        assert result.exit_code == 0


class TestMetricPublishUnpublish:
    def test_publish(self, cli_runner, mock_client):
        result = cli_runner.invoke(app, ["metric", "publish", "--ids", "1,2,3"])
        assert result.exit_code == 0
        mock_client.metrics.publish.assert_called_once_with([1, 2, 3])

    def test_unpublish(self, cli_runner, mock_client):
        result = cli_runner.invoke(app, ["metric", "unpublish", "--ids", "1,2,3"])
        assert result.exit_code == 0
        mock_client.metrics.unpublish.assert_called_once_with([1, 2, 3])
```

- [ ] **步骤 2：实现 metric.py**

文件：`python-sdk/src/supersonic/cli/metric.py`

```python
"""Metric subcommand group: list/get/create/update/delete + publish/unpublish.

Review spec § 命令清单 → metric.
"""
from __future__ import annotations

import typer

from supersonic.cli.common import format_output, get_client
from supersonic.models.metric import MetricCreateReq, MetricUpdateReq

app = typer.Typer(name="metric", help="Metric CRUD + publish/unpublish.")


@app.command(name="list")
def list_cmd(
    ctx: typer.Context,
    model_id: int | None = typer.Option(None, "--model-id"),
    page: int = typer.Option(1, "--page"),
    page_size: int = typer.Option(10, "--page-size"),
) -> None:
    client = get_client(ctx)
    result = client.metrics.list(model_id=model_id, page=page, page_size=page_size)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="get")
def get_cmd(ctx: typer.Context, id: int = typer.Option(..., "--id")) -> None:
    client = get_client(ctx)
    result = client.metrics.get(id)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="create")
def create_cmd(
    ctx: typer.Context,
    model_id: int = typer.Option(..., "--model-id"),
    name: str = typer.Option(..., "--name"),
    biz_name: str = typer.Option(..., "--biz-name"),
    define_type: str = typer.Option(..., "--define-type", help="MEASURE/FIELD/METRIC"),
    type: str | None = typer.Option(None, "--type", help="NUMBER/PERCENT/..."),
    expression: str | None = typer.Option(None, "--expression"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    client = get_client(ctx)
    req = MetricCreateReq(
        model_id=model_id, name=name, biz_name=biz_name,
        define_type=define_type, type=type, expression=expression,
        description=description,
    )
    result = client.metrics.create(req)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="update")
def update_cmd(
    ctx: typer.Context,
    id: int = typer.Option(..., "--id"),
    name: str | None = typer.Option(None, "--name"),
    biz_name: str | None = typer.Option(None, "--biz-name"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    client = get_client(ctx)
    req = MetricUpdateReq(id=id, name=name, biz_name=biz_name, description=description)
    result = client.metrics.update(id, req)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="delete")
def delete_cmd(ctx: typer.Context, id: int = typer.Option(..., "--id")) -> None:
    client = get_client(ctx)
    client.metrics.delete(id)
    typer.echo(f"Deleted metric {id}")


@app.command(name="publish")
def publish_cmd(
    ctx: typer.Context,
    ids: str = typer.Option(..., "--ids", help="Comma-separated metric IDs"),
) -> None:
    """Publish metrics (set status to ONLINE)."""
    id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
    client = get_client(ctx)
    client.metrics.publish(id_list)
    typer.echo(f"Published {len(id_list)} metrics")


@app.command(name="unpublish")
def unpublish_cmd(
    ctx: typer.Context,
    ids: str = typer.Option(..., "--ids", help="Comma-separated metric IDs"),
) -> None:
    """Unpublish metrics (set status to OFFLINE)."""
    id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
    client = get_client(ctx)
    client.metrics.unpublish(id_list)
    typer.echo(f"Unpublished {len(id_list)} metrics")
```

- [ ] **步骤 3：运行测试 + Lint + Commit**

```bash
python3.11 -m pytest tests/cli/test_metric.py -v
python3.11 -m ruff check src/supersonic/cli/metric.py tests/cli/test_metric.py
python3.11 -m mypy src/supersonic/cli/metric.py
```

```bash
cd /Users/yourton_ma/workspace/supersonic
git add python-sdk/src/supersonic/cli/metric.py python-sdk/tests/cli/test_metric.py
git commit -m "feat(sdk): implement metric subcommand group (CRUD + publish/unpublish)"
```

---

## 任务 12：database.py — 7 个 database 子命令（含 test-connect/get-tables/get-columns）

**文件：**
- 创建：`python-sdk/src/supersonic/cli/database.py`
- 创建：`python-sdk/tests/cli/test_database.py`

**规格参考：** § 命令清单 → database

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/cli/test_database.py`

```python
"""Tests for cli/database.py: CRUD + test-connect/get-tables/get-columns."""
import pytest
from typer.testing import CliRunner

from supersonic.cli.main import app
from supersonic.common.pagination import Page
from supersonic.models.database import Database, TableColumn, TestConnectionResult


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def sample_database():
    return Database(
        id=5, name="main-db", type="mysql",
        host="localhost", port=3306,
    )


class TestDatabaseList:
    def test_list(self, cli_runner, mock_client, sample_database):
        mock_client.databases.list.return_value = Page[Database](
            items=[sample_database], total=1, page=1, page_size=10,
        )
        result = cli_runner.invoke(app, ["database", "list"])
        assert result.exit_code == 0
        assert "main-db" in result.stdout


class TestDatabaseCRUD:
    def test_get(self, cli_runner, mock_client, sample_database):
        mock_client.databases.get.return_value = sample_database
        result = cli_runner.invoke(app, ["database", "get", "--id", "5"])
        assert result.exit_code == 0

    def test_create(self, cli_runner, mock_client, sample_database):
        result = cli_runner.invoke(
            app,
            [
                "database", "create",
                "--name", "main-db", "--type", "mysql",
                "--host", "localhost", "--port", "3306",
                "--username", "root", "--password", "***",
            ],
        )
        assert result.exit_code == 0

    def test_delete(self, cli_runner, mock_client):
        result = cli_runner.invoke(app, ["database", "delete", "--id", "5"])
        assert result.exit_code == 0


class TestDatabaseTestConnect:
    def test_test_connect_success(self, cli_runner, mock_client):
        mock_client.databases.test_connect.return_value = TestConnectionResult(success=True)
        result = cli_runner.invoke(
            app,
            [
                "database", "test-connect",
                "--name", "test-db", "--type", "mysql",
                "--host", "localhost", "--port", "3306",
                "--username", "root", "--password", "***",
            ],
        )
        assert result.exit_code == 0
        assert "True" in result.stdout or "true" in result.stdout


class TestDatabaseGetTables:
    def test_get_tables(self, cli_runner, mock_client):
        mock_client.databases.get_tables.return_value = ["orders", "users", "products"]
        result = cli_runner.invoke(app, ["database", "get-tables", "--id", "5"])
        assert result.exit_code == 0
        assert "orders" in result.stdout


class TestDatabaseGetColumns:
    def test_get_columns(self, cli_runner, mock_client):
        mock_client.databases.get_columns.return_value = [
            TableColumn(name="id", type="INT"),
            TableColumn(name="name", type="VARCHAR"),
        ]
        result = cli_runner.invoke(
            app,
            ["database", "get-columns", "--id", "5", "--table", "users"],
        )
        assert result.exit_code == 0
        assert "id" in result.stdout
```

- [ ] **步骤 2：实现 database.py**

文件：`python-sdk/src/supersonic/cli/database.py`

```python
"""Database subcommand group: CRUD + test-connect/get-tables/get-columns.

Review spec § 命令清单 → database.
"""
from __future__ import annotations

import typer

from supersonic.cli.common import format_output, get_client
from supersonic.models.database import DatabaseCreateReq

app = typer.Typer(name="database", help="Database CRUD + connection utilities.")


@app.command(name="list")
def list_cmd(
    ctx: typer.Context,
    page: int = typer.Option(1, "--page"),
    page_size: int = typer.Option(10, "--page-size"),
) -> None:
    client = get_client(ctx)
    result = client.databases.list(page=page, page_size=page_size)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="get")
def get_cmd(ctx: typer.Context, id: int = typer.Option(..., "--id")) -> None:
    client = get_client(ctx)
    result = client.databases.get(id)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="create")
def create_cmd(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name"),
    type: str = typer.Option(..., "--type", help="mysql/postgresql/clickhouse/..."),
    host: str = typer.Option(..., "--host"),
    port: int = typer.Option(..., "--port"),
    username: str = typer.Option(..., "--username"),
    password: str = typer.Option(..., "--password"),
    database: str | None = typer.Option(None, "--database"),
    version: str | None = typer.Option(None, "--version"),
    description: str | None = typer.Option(None, "--description"),
) -> None:
    client = get_client(ctx)
    req = DatabaseCreateReq(
        name=name, type=type, host=host, port=port,
        username=username, password=password,
        database=database, version=version, description=description,
    )
    result = client.databases.create(req)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="delete")
def delete_cmd(ctx: typer.Context, id: int = typer.Option(..., "--id")) -> None:
    client = get_client(ctx)
    client.databases.delete(id)
    typer.echo(f"Deleted database {id}")


@app.command(name="test-connect")
def test_connect_cmd(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name"),
    type: str = typer.Option(..., "--type"),
    host: str = typer.Option(..., "--host"),
    port: int = typer.Option(..., "--port"),
    username: str = typer.Option(..., "--username"),
    password: str = typer.Option(..., "--password"),
    database: str | None = typer.Option(None, "--database"),
) -> None:
    """Test database connection without saving."""
    client = get_client(ctx)
    req = DatabaseCreateReq(
        name=name, type=type, host=host, port=port,
        username=username, password=password, database=database,
    )
    result = client.databases.test_connect(req)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="get-tables")
def get_tables_cmd(
    ctx: typer.Context,
    id: int = typer.Option(..., "--id", help="Database ID"),
    db: str | None = typer.Option(None, "--db", help="Database name (for multi-DB servers)"),
) -> None:
    """List tables in a database."""
    client = get_client(ctx)
    result = client.databases.get_tables(id, db=db)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="get-columns")
def get_columns_cmd(
    ctx: typer.Context,
    id: int = typer.Option(..., "--id"),
    table: str = typer.Option(..., "--table"),
    db: str | None = typer.Option(None, "--db"),
) -> None:
    """List columns of a table."""
    client = get_client(ctx)
    result = client.databases.get_columns(id, table, db=db)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )
```

- [ ] **步骤 3：运行测试 + Lint + Commit**

```bash
python3.11 -m pytest tests/cli/test_database.py -v
python3.11 -m ruff check src/supersonic/cli/database.py tests/cli/test_database.py
python3.11 -m mypy src/supersonic/cli/database.py
```

```bash
cd /Users/yourton_ma/workspace/supersonic
git add python-sdk/src/supersonic/cli/database.py python-sdk/tests/cli/test_database.py
git commit -m "feat(sdk): implement database subcommand group (CRUD + test-connect + schema)"
```

---

## 任务 13：dataset.py — 2 个 dataset 只读子命令

**文件：**
- 创建：`python-sdk/src/supersonic/cli/dataset.py`
- 创建：`python-sdk/tests/cli/test_dataset.py`

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/cli/test_dataset.py`

```python
"""Tests for cli/dataset.py: list/get (read-only)."""
import pytest
from typer.testing import CliRunner

from supersonic.cli.main import app
from supersonic.common.pagination import Page
from supersonic.models.dataset import Dataset


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def sample_dataset():
    return Dataset(
        id=1, name="销售数据集", biz_name="sales_dataset",
        domain_id=1, model_ids=[10, 11],
    )


class TestDatasetList:
    def test_list(self, cli_runner, mock_client, sample_dataset):
        mock_client.datasets.list.return_value = Page[Dataset](
            items=[sample_dataset], total=1, page=1, page_size=10,
        )
        result = cli_runner.invoke(app, ["dataset", "list"])
        assert result.exit_code == 0
        assert "销售数据集" in result.stdout


class TestDatasetGet:
    def test_get(self, cli_runner, mock_client, sample_dataset):
        mock_client.datasets.get.return_value = sample_dataset
        result = cli_runner.invoke(app, ["dataset", "get", "--id", "1"])
        assert result.exit_code == 0
```

- [ ] **步骤 2：实现 dataset.py**

文件：`python-sdk/src/supersonic/cli/dataset.py`

```python
"""Dataset subcommand group: list/get (read-only).

Review spec § 命令清单 → dataset.
"""
from __future__ import annotations

import typer

from supersonic.cli.common import format_output, get_client

app = typer.Typer(name="dataset", help="Dataset read operations.")


@app.command(name="list")
def list_cmd(
    ctx: typer.Context,
    page: int = typer.Option(1, "--page"),
    page_size: int = typer.Option(10, "--page-size"),
) -> None:
    client = get_client(ctx)
    result = client.datasets.list(page=page, page_size=page_size)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )


@app.command(name="get")
def get_cmd(ctx: typer.Context, id: int = typer.Option(..., "--id")) -> None:
    client = get_client(ctx)
    result = client.datasets.get(id)
    format_output(
        result,
        as_json=ctx.obj.get("__json", False),
        no_color=ctx.obj.get("__no_color", False),
    )
```

- [ ] **步骤 3：运行测试 + Lint + Commit**

```bash
python3.11 -m pytest tests/cli/test_dataset.py -v
python3.11 -m ruff check src/supersonic/cli/dataset.py tests/cli/test_dataset.py
python3.11 -m mypy src/supersonic/cli/dataset.py
```

```bash
cd /Users/yourton_ma/workspace/supersonic
git add python-sdk/src/supersonic/cli/dataset.py python-sdk/tests/cli/test_dataset.py
git commit -m "feat(sdk): implement dataset subcommand group (read-only)"
```

---

## 任务 14：config_cmd.py — config show 子命令

**文件：**
- 创建：`python-sdk/src/supersonic/cli/config_cmd.py`
- 创建：`python-sdk/tests/cli/test_config_cmd.py`

**规格参考：** § 命令清单 → config show

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/cli/test_config_cmd.py`

```python
"""Tests for cli/config_cmd.py: config show."""
import pytest
from typer.testing import CliRunner

from supersonic.cli.main import app


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestConfigShow:
    def test_shows_host_and_token_masked(self, cli_runner, monkeypatch):
        monkeypatch.setenv("SUPERSONIC_HOST", "http://test:9080")
        monkeypatch.setenv("SUPERSONIC_TOKEN", "jwt-secret-token-12345")
        result = cli_runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "http://test:9080" in result.stdout
        # Token should be masked
        assert "jwt-secret-token-12345" not in result.stdout
        assert "***" in result.stdout

    def test_shows_default_when_unset(self, cli_runner, monkeypatch, tmp_path):
        for key in ["SUPERSONIC_HOST", "SUPERSONIC_TOKEN", "SUPERSONIC_APP_KEY"]:
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("HOME", str(tmp_path / "empty"))
        result = cli_runner.invoke(app, ["config", "show"])
        # Should show defaults (app_key=supersonic etc.)
        # host/token will be empty/missing
        assert result.exit_code == 0
```

- [ ] **步骤 2：实现 config_cmd.py**

文件：`python-sdk/src/supersonic/cli/config_cmd.py`

```python
"""Config subcommand group: show effective configuration.

Review spec § 命令清单 → config.
"""
from __future__ import annotations

import typer

app = typer.Typer(name="config", help="Configuration utilities.")


@app.command(name="show")
def show_cmd(ctx: typer.Context) -> None:
    """Show effective configuration (token masked)."""
    config: dict = ctx.obj or {}

    typer.echo("Effective configuration:")
    typer.echo(f"  host:      {config.get('host', '(not set)')}")
    typer.echo(f"  token:     {_mask(config.get('token'))}")
    typer.echo(f"  app_key:   {config.get('app_key', 'supersonic')}")
    typer.echo(f"  timeout:   {config.get('timeout', 30.0)}")
    typer.echo(f"  log_level: {config.get('log_level', 'WARNING')}")

    retry = config.get("retry") or {}
    if retry:
        typer.echo("  retry:")
        for k, v in retry.items():
            typer.echo(f"    {k}: {v}")


def _mask(token: str | None) -> str:
    """Mask token, showing only first 4 and last 4 characters."""
    if not token:
        return "(not set)"
    if len(token) <= 8:
        return "***"
    return f"{token[:4]}***{token[-4:]}"
```

- [ ] **步骤 3：运行测试 + Lint + Commit**

```bash
python3.11 -m pytest tests/cli/test_config_cmd.py -v
python3.11 -m ruff check src/supersonic/cli/config_cmd.py tests/cli/test_config_cmd.py
python3.11 -m mypy src/supersonic/cli/config_cmd.py
```

```bash
cd /Users/yourton_ma/workspace/supersonic
git add python-sdk/src/supersonic/cli/config_cmd.py python-sdk/tests/cli/test_config_cmd.py
git commit -m "feat(sdk): implement config show subcommand (token masked)"
```

---

## 任务 15：完整测试套件 + 类型检查里程碑 + README 更新

**文件：**
- 修改：`python-sdk/README.md`（加 CLI 章节）

- [ ] **步骤 1：跑全量测试 + 覆盖率**

运行：
```bash
cd /Users/yourton_ma/workspace/supersonic/python-sdk
python3.11 -m pytest --cov=src/supersonic --cov-report=term 2>&1 | tail -50
```

预期：
- 所有测试 PASS（Phase 1 的 154 + Phase 2 的新增）
- CLI 子包覆盖率 ≥ 85%
- 整体覆盖率不应下降（Phase 1 是 95%，CLI 加入后会略降但应 ≥ 85%）

如果 CLI 覆盖率 < 85%，识别未覆盖文件并补充测试。

- [ ] **步骤 2：全量 ruff + mypy**

运行：
```bash
python3.11 -m ruff check src/ tests/
python3.11 -m mypy src/
```

预期：0 error。如有 error，优先修复类型注解或 lint 问题。

- [ ] **步骤 3：CLI 实际运行验证（手动）**

```bash
# 验证 CLI 可执行
supersonic --version
supersonic --help

# 验证配置错误处理
SUPERC_HOST="" SUPERC_TOKEN="" supersonic config show || echo "exit code: $?"

# 验证 --json 输出格式（用 mock 数据需要启动真实 SuperSonic，或跳过此步）
```

预期：`--version` 输出 `supersonic-sdk 0.1.0`；`--help` 列出所有子命令组；缺 host/token 时退出码非 0。

- [ ] **步骤 4：更新 README.md（加 CLI 章节）**

在现有 README.md 的 `## Async Support` 章节前插入：

```markdown
## CLI

The `supersonic` command-line tool provides bash access to all SDK capabilities.
Install with the `[cli]` extra:

```bash
pip install supersonic-sdk[cli]
```

### Quick Start

```bash
# Set credentials (or use --config FILE)
export SUPERSONIC_HOST=http://localhost:9080
export SUPERSONIC_TOKEN=your-jwt-token

# List metrics
supersonic metric list --model-id 10

# Query
supersonic query sql "SELECT 销售额 FROM 销售表"
supersonic query chat --text "top 5 products by sales"

# JSON output for scripting
supersonic metric list --json | jq '.items[].name'
```

### Configuration Priority

Config is resolved in this order (highest first):

1. CLI flags (`--host`, `--token`, ...)
2. Environment variables (`SUPERSONIC_HOST`, `SUPERSONIC_TOKEN`, ...)
3. `--config FILE` (TOML format)
4. `--env-file FILE` (dotenv format)
5. `~/.supersonic/config.toml` (default path if exists)
6. Built-in defaults

### Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Generic client error |
| 2 | Authentication error (401) |
| 3 | Resource not found (404) |
| 4 | Validation error (400) |
| 5 | Server error (5xx) or connection error |

### TOML Config Example

```toml
# ~/.supersonic/config.toml
host = "http://localhost:9080"
token = "your-jwt-token"
app_key = "supersonic"

[retry]
max_retries = 5
```

### Shell Completion

```bash
supersonic --install-completion bash  # or zsh/fish
```

See [design spec](../docs/superpowers/specs/2026-07-17-python-sdk-cli-design.md) for full architecture.
```

- [ ] **步骤 5：Commit**

```bash
cd /Users/yourton_ma/workspace/supersonic
git add python-sdk/README.md
git commit -m "docs(sdk): add CLI usage chapter to README"
```

---

## 自检

完成所有任务后，对照规格检查：

**1. 规格覆盖度：**
- ✅ § 包布局 → 任务 2（cli/ 骨架）+ 任务 3-5（common/config_schema/main）+ 任务 7-14（8 个子命令组）
- ✅ § 命令结构（38 命令）→ 任务 7（5 query）+ 任务 8-12（5+5+6+7+7=30 元数据 CRUD）+ 任务 13（2 dataset）+ 任务 14（1 config）= 38
- ✅ § 共享工具 → 任务 3（get_client/format_output/exit_code_for）
- ✅ § 配置加载 → 任务 4（TOML/dotenv 解析 + 6 层优先级链）
- ✅ § 输出格式 → 任务 3（format_output 的 table/json 双模式）
- ✅ § 错误处理与退出码 → 任务 3（exit_code_for）+ 任务 5（cli_main 包装）
- ✅ § 测试策略 → 任务 6（conftest fixtures）+ 各任务的测试
- ✅ § pyproject.toml → 任务 1
- ✅ § 关键设计决策 → 全部体现（typer/镜像命名空间/TOML+dotenv/5 类退出码/薄包装）

**2. 占位符扫描：**
- 无 TODO / 待定 / 后续实现
- 每个步骤都有完整代码块
- 所有子命令组实现完整（不像 Phase 1 有 NotImplementedError 占位）

**3. 类型一致性：**
- `get_client(ctx)` 签名：任务 3 定义，任务 5/7-14 引用，一致
- `format_output(obj, *, as_json, no_color, columns=None)` 签名：任务 3 定义，任务 7-14 引用，一致
- `exit_code_for(exc)` 签名：任务 3 定义，任务 5 引用，一致
- `CliConfig` pydantic 模型：任务 4 定义，任务 5 引用（validate_config_dict + to_flat_dict），一致
- `load_config_file(config, env_file)` 签名：任务 4 定义，任务 5 引用，一致
- mock_client fixture：任务 6 定义，任务 7-14 测试引用，一致

**4. 任务粒度：**
- 任务 1-6 是基础设施（必须按序）
- 任务 7-14 是子命令组（可并行，但推荐按序避免 main.py 注册冲突）
- 任务 15 是收尾（类型检查 + README）

---

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-07-17-python-sdk-cli-phase2.md`。

**任务总数**：15 个（比 Phase 1 的 26 个少，因为 CLI 是薄包装层，模式重复度高）

**两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**

> **特别提示：**
> - 任务 1-6 是地基（pyproject + cli/ 骨架 + common + config_schema + main + conftest），必须按序
> - 任务 5（main.py）会触发 ImportError（因为子命令组未实现），此时 commit 但不跑测试
> - 任务 7-14 是子命令组（每个独立），任务 6 完成后可批量推进
> - 任务 15 是收尾（全量测试 + 类型检查 + README）
> - 关键风险：typer 的子命令注册在模块加载时，main.py 测试要等所有子命令组实现后才能跑通
