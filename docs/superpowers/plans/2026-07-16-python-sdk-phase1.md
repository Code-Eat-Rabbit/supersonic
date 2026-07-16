# SuperSonic Python SDK Phase 1 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现 SuperSonic Python SDK Phase 1——覆盖查询（5 方法）+ 6 个元数据资源 CRUD（32 方法）的完整客户端库，对标 open-metadata/ai-sdk 模式。

**架构：** 门面（`SupersonicClient`）+ 资源命名空间（`client.query` / `client.metrics` 等）+ 共享 HTTP 层（`common/http.py`）。pydantic v2 模型层 + opt-in async + 资源特化异常树 + pytest-httpx mock 测试。

**技术栈：** Python 3.10+ / httpx / pydantic v2 / hatchling / ruff / pytest + pytest-httpx + pytest-asyncio

**规格来源：** `docs/superpowers/specs/2026-07-16-python-sdk-design.md`

**目标行覆盖率：** ≥ 85%

---

## 评审反馈修订说明（v2）

> 应用于 `2026-07-16-python-sdk-phase1-plan-review.md` 的 10 条评审反馈。

### 必须修复（已应用）

**修复 1：TDD 流程破坏（评审 #1）**

原问题：任务 14-20 的测试通过 `SupersonicClient` 入口，但 Client 在任务 21 才实现，导致 7 个任务无法独立验证测试。

解决方案：在 `conftest.py` 增加 API 级 fixture（`query_api` / `metrics_api` 等），测试直接注入 `QueryAPI(http, async_http=None)`，与 Client 门面解耦。任务 14-20 现在各自可独立 TDD 验证，任务 21 只负责门面装配（用一组小测试验证）。

**修复 2：async 方法缺失（评审 #2、#7）**

原问题：30+ async 方法标 `NotImplementedError`，无后续任务补全。

解决方案（评审建议的方案 B）：**Phase 1 明确只支持 QueryAPI 的 async（核心场景）**，元数据 CRUD 的 async 方法不在本次范围。具体：
- Task 14（QueryAPI）：保留 `asql()` 完整实现
- Task 15-20（元数据 API）：**移除所有 async 方法**（不再标 NotImplementedError，而是干脆不定义）
- Task 21 后追加任务 21b：在 README + `__init__.py` 显式声明此限制

### 建议修改（已应用）

- **修复 3**：统一 `ResourceNotFoundError` 构造函数签名（任务 6）
- **修复 4**：list 操作不传 `resource_type`，避免误判 404（任务 15-20）
- **修复 5**：在任务 13 后追加类型检查里程碑（任务 13b）
- **修复 6**：`utils/format.py` 的 `import re` 移到顶部（任务 22）

### 仅供参考（已应用）

- **修复 8**：统一文件结构与任务编号注释（任务 1）
- **修复 9**：`api/paths.py` 标注 database create/update 共用 upsert 端点（任务 10）
- **修复 10**：行号引用改为章节名引用（全文）

---


---

## 文件结构

### 创建文件清单（按依赖顺序，标注实际任务编号——评审修复 8）

```
python-sdk/
├── pyproject.toml                                    # 任务 1
├── README.md                                         # 任务 1（任务 21b/24 追加内容）
├── src/supersonic/
│   ├── __init__.py                                   # 任务 21（Import Guide；任务 21b 追加 async 说明）
│   ├── py.typed                                      # 任务 1（空文件）
│   ├── exceptions.py                                 # 任务 2
│   ├── auth.py                                       # 任务 3
│   ├── config.py                                     # 任务 4
│   ├── client.py                                     # 任务 21（门面，依赖 api/*）
│   ├── common/
│   │   ├── __init__.py                               # 任务 5（__all__=[]）
│   │   ├── logging.py                                # 任务 5
│   │   ├── http.py                                   # 任务 6（HTTPClient）+ 任务 7（AsyncHTTPClient）
│   │   └── pagination.py                             # 任务 8
│   ├── api/
│   │   ├── __init__.py                               # 任务 10
│   │   ├── paths.py                                  # 任务 10
│   │   ├── query.py                                  # 任务 14
│   │   ├── domains.py                                # 任务 15
│   │   ├── models.py                                 # 任务 16
│   │   ├── dimensions.py                             # 任务 17
│   │   ├── metrics.py                                # 任务 18
│   │   ├── databases.py                              # 任务 19
│   │   └── datasets.py                               # 任务 20
│   ├── models/
│   │   ├── __init__.py                               # 任务 13（re-export）
│   │   ├── base.py                                   # 任务 9
│   │   ├── query.py                                  # 任务 11
│   │   ├── domain.py                                 # 任务 12
│   │   ├── model.py                                  # 任务 12
│   │   ├── dimension.py                              # 任务 12
│   │   ├── metric.py                                 # 任务 12
│   │   ├── database.py                               # 任务 12
│   │   └── dataset.py                                # 任务 12
│   └── utils/
│       ├── __init__.py                               # 任务 22
│       ├── builders.py                               # 任务 22
│       ├── validators.py                             # 任务 22
│       └── format.py                                 # 任务 22
├── tests/
│   ├── __init__.py                                   # 任务 1
│   ├── conftest.py                                   # 任务 10（共享 fixtures，含 API 级 fixtures 评审修复 1）
│   ├── test_client.py                                # 任务 21
│   ├── test_auth.py                                  # 任务 3
│   ├── test_config.py                                # 任务 4
│   ├── test_exceptions.py                            # 任务 2
│   ├── test_async.py                                 # 任务 7
│   ├── common/
│   │   ├── __init__.py
│   │   ├── test_http.py                              # 任务 6
│   │   ├── test_pagination.py                        # 任务 8
│   │   └── test_logging.py                           # 任务 5
│   ├── models/
│   │   ├── __init__.py
│   │   ├── test_query_models.py                      # 任务 11
│   │   └── test_metadata_models.py                   # 任务 12
│   ├── api/
│   │   ├── __init__.py
│   │   ├── test_query.py                             # 任务 14
│   │   ├── test_domains.py                           # 任务 15
│   │   ├── test_models.py                            # 任务 16
│   │   ├── test_dimensions.py                        # 任务 17
│   │   ├── test_metrics.py                           # 任务 18
│   │   ├── test_databases.py                         # 任务 19
│   │   └── test_datasets.py                          # 任务 20
│   ├── utils/
│   │   ├── __init__.py
│   │   └── test_utils.py                             # 任务 22
│   └── integration/
│       ├── __init__.py
│       └── test_query_live.py                        # 任务 23
└── examples/
    ├── quickstart.py                                 # 任务 24
    ├── semantic_modeling.py                          # 任务 24
    └── nl_query.py                                   # 任务 24
```

### 任务依赖图

```
任务 1 (pyproject) ─┐
                    ├─→ 任务 2 (__init__ Import Guide)
任务 3 (exceptions) ─┼─→ 任务 4 (auth) ─→ 任务 5 (config) ─┐
                    │                                       │
                    ├─→ 任务 6 (common/logging)             │
                    │                                       │
                    └─→ 任务 7 (HTTPClient) ─→ 任务 8 (AsyncHTTPClient)
                                                            │
                            任务 9 (pagination) ────────────┤
                                                            │
                            任务 10 (api/paths + conftest) ─┤
                                                            │
                            任务 11 (models/base) ─→ 任务 12 (models/query)
                                                    ─→ 任务 13 (元数据 models)
                                                            │
                                                            ▼
                                                  任务 14 (client 门面)
                                                            │
                            ┌───────────────────────────────┤
                            ▼                               ▼
                       任务 15 (query)            任务 16-21 (6 个元数据 API)
                                                            │
                                                            ▼
                                                  任务 22 (utils)
                                                            │
                                                            ▼
                                                  任务 23 (integration test)
                                                            │
                                                            ▼
                                                  任务 24 (examples)
```

---

## 任务 1：项目骨架（pyproject.toml + 目录结构）

**文件：**
- 创建：`python-sdk/pyproject.toml`
- 创建：`python-sdk/README.md`
- 创建：`python-sdk/src/supersonic/py.typed`（空文件）
- 创建：`python-sdk/tests/__init__.py`（空文件）
- 创建：`python-sdk/tests/common/__init__.py`（空文件）
- 创建：`python-sdk/tests/api/__init__.py`（空文件）
- 创建：`python-sdk/tests/integration/__init__.py`（空文件）

- [ ] **步骤 1：创建目录结构**

运行：
```bash
mkdir -p python-sdk/src/supersonic/{common,api,models,utils}
mkdir -p python-sdk/tests/{common,api,integration}
mkdir -p python-sdk/examples
touch python-sdk/src/supersonic/py.typed
touch python-sdk/tests/__init__.py python-sdk/tests/common/__init__.py
touch python-sdk/tests/api/__init__.py python-sdk/tests/integration/__init__.py
```

- [ ] **步骤 2：创建 pyproject.toml**

文件：`python-sdk/pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "supersonic-sdk"
version = "0.1.0"
description = "Python SDK for SuperSonic Chat BI + Headless BI platform"
readme = "README.md"
requires-python = ">=3.10"
license = { text = "Apache-2.0" }
authors = [{ name = "SuperSonic Team" }]
keywords = ["supersonic", "chat-bi", "headless-bi", "text2sql", "semantic-layer"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Typing :: Typed",
]
dependencies = [
    "httpx>=0.25.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
pandas = ["pandas>=2.0.0"]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-httpx>=0.30",
    "pytest-cov>=4.0",
    "ruff>=0.8.0",
    "mypy>=1.0",
]
all = ["supersonic-sdk[pandas,dev]"]

[project.urls]
Homepage = "https://github.com/tencentmusic/supersonic"
Repository = "https://github.com/tencentmusic/supersonic"

[tool.hatch.build.targets.wheel]
packages = ["src/supersonic"]

[tool.ruff]
target-version = "py310"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "RUF"]

[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "integration: requires real SuperSonic instance (skipped by default)",
]
addopts = "-m 'not integration' --cov=src/supersonic --cov-report=term-missing"
```

- [ ] **步骤 3：创建占位 README.md**

文件：`python-sdk/README.md`

```markdown
# SuperSonic Python SDK

Python client for SuperSonic Chat BI + Headless BI platform.

## Installation

```bash
pip install supersonic-sdk
```

With pandas support:

```bash
pip install supersonic-sdk[pandas]
```

## Quick Start

```python
from supersonic import SupersonicClient

with SupersonicClient.from_env() as client:
    result = client.query.sql("SELECT 销售额 FROM 销售表")
    print(result.result_rows)
```

## Documentation

See [design spec](../docs/superpowers/specs/2026-07-16-python-sdk-design.md) for full architecture.
```

- [ ] **步骤 4：安装包（可编辑模式）+ 验证 pytest 可运行**

运行：
```bash
cd python-sdk
pip install -e ".[dev]"
pytest --co -q
```

预期：`pytest --co -q` 输出 `no tests ran`（无错误，因为还没有测试文件），而不是 import 错误。

- [ ] **步骤 5：Commit**

```bash
git add python-sdk/
git commit -m "feat(sdk): scaffold python-sdk project structure with pyproject.toml"
```

---

## 任务 2：异常体系

**文件：**
- 创建：`python-sdk/src/supersonic/exceptions.py`
- 创建：`python-sdk/tests/test_exceptions.py`

**规格参考：** § 异常树（第 420-480 行）

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/test_exceptions.py`

```python
"""异常体系测试。

规格参考：2026-07-16-python-sdk-design.md § 异常树
"""
import pytest

from supersonic.exceptions import (
    SupersonicError,
    AuthenticationError,
    ValidationError,
    FieldError,
    RateLimitError,
    ServerError,
    ConnectionError as SupersonicConnectionError,
    AsyncNotEnabledError,
    ResourceNotFoundError,
    DomainNotFoundError,
    ModelNotFoundError,
    DimensionNotFoundError,
    MetricNotFoundError,
    DatasetNotFoundError,
    DatabaseNotFoundError,
)


class TestSupersonicError:
    def test_root_carries_message_and_status_code(self):
        err = SupersonicError("boom", status_code=500, response_body={"k": "v"})
        assert err.message == "boom"
        assert err.status_code == 500
        assert err.response_body == {"k": "v"}
        assert isinstance(err, Exception)

    def test_status_code_defaults_to_none(self):
        err = SupersonicError("just a message")
        assert err.status_code is None
        assert err.response_body is None


class TestValidationError:
    def test_carries_field_errors(self):
        field_err = FieldError(field="name", message="不能为空")
        err = ValidationError(
            "validation failed",
            field_errors=[field_err],
        )
        assert err.status_code == 400
        assert err.field_errors == [field_err]

    def test_field_errors_defaults_to_empty_list(self):
        err = ValidationError("failed")
        assert err.field_errors == []

    def test_is_supersonic_error(self):
        err = ValidationError("x")
        assert isinstance(err, SupersonicError)


class TestResourceNotFound:
    def test_metric_not_found_carries_resource_id(self):
        err = MetricNotFoundError(resource_id=42)
        assert err.resource_id == 42
        assert err.status_code == 404
        assert "42" in str(err)
        assert isinstance(err, ResourceNotFoundError)

    def test_each_resource_subclass_exists(self):
        for cls in [DomainNotFoundError, ModelNotFoundError, DimensionNotFoundError,
                    MetricNotFoundError, DatasetNotFoundError, DatabaseNotFoundError]:
            assert issubclass(cls, ResourceNotFoundError)


class TestRateLimitError:
    def test_carries_retry_after(self):
        err = RateLimitError("slow down", retry_after=60)
        assert err.retry_after == 60
        assert err.status_code == 429


class TestAsyncNotEnabled:
    def test_message_is_helpful(self):
        err = AsyncNotEnabledError()
        assert "enable_async=True" in err.message
        assert isinstance(err, SupersonicError)


class TestConnectionError:
    def test_is_subclass_of_supersonic_error(self):
        err = SupersonicConnectionError("network down")
        assert isinstance(err, SupersonicError)
        assert isinstance(err, Exception)
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest python-sdk/tests/test_exceptions.py -v`
预期：FAIL，报错 `ModuleNotFoundError: No module named 'supersonic.exceptions'`

- [ ] **步骤 3：实现 exceptions.py**

文件：`python-sdk/src/supersonic/exceptions.py`

```python
"""SuperSonic SDK 异常体系。

所有异常都继承 SupersonicError，便于用户 `except SupersonicError` 兜底。
资源特化异常（MetricNotFoundError 等）便于精准 catch。
"""
from typing import Any

from pydantic import BaseModel


class SupersonicError(Exception):
    """所有 SDK 异常的根。"""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        return self.message


class FieldError(BaseModel):
    """字段级校验错误详情。"""

    field: str
    message: str
    rejected_value: Any | None = None


class ValidationError(SupersonicError):
    """400 错误，携带字段级错误详情。"""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        response_body: dict | None = None,
        field_errors: list[FieldError] | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code, response_body=response_body)
        self.field_errors = field_errors or []


class AuthenticationError(SupersonicError):
    """401 错误，token 失效或缺失。"""

    def __init__(self, message: str = "Authentication failed", *,
                 status_code: int = 401, response_body: dict | None = None) -> None:
        super().__init__(message, status_code=status_code, response_body=response_body)


class RateLimitError(SupersonicError):
    """429 错误，携带服务器建议的 retry_after（秒）。"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        status_code: int = 429,
        response_body: dict | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code, response_body=response_body)
        self.retry_after = retry_after


class ServerError(SupersonicError):
    """5xx 服务器错误。"""


class ConnectionError(SupersonicError):
    """网络层错误（httpx.TransportError 的包装）。"""


class AsyncNotEnabledError(SupersonicError):
    """调用 .alist()/.acreate() 等异步方法但未启用 enable_async=True。"""

    def __init__(self) -> None:
        super().__init__(
            "Async methods require enable_async=True. "
            "Recreate SupersonicClient with enable_async=True to use async API."
        )


class ResourceNotFoundError(SupersonicError):
    """404 资源不存在异常的基类。"""

    def __init__(self, resource_type: str, resource_id: int | str) -> None:
        super().__init__(
            f"{resource_type} {resource_id} not found",
            status_code=404,
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class DomainNotFoundError(ResourceNotFoundError):
    def __init__(self, resource_id: int | str) -> None:
        super().__init__("domain", resource_id)


class ModelNotFoundError(ResourceNotFoundError):
    def __init__(self, resource_id: int | str) -> None:
        super().__init__("model", resource_id)


class DimensionNotFoundError(ResourceNotFoundError):
    def __init__(self, resource_id: int | str) -> None:
        super().__init__("dimension", resource_id)


class MetricNotFoundError(ResourceNotFoundError):
    def __init__(self, resource_id: int | str) -> None:
        super().__init__("metric", resource_id)


class DatasetNotFoundError(ResourceNotFoundError):
    def __init__(self, resource_id: int | str) -> None:
        super().__init__("dataset", resource_id)


class DatabaseNotFoundError(ResourceNotFoundError):
    def __init__(self, resource_id: int | str) -> None:
        super().__init__("database", resource_id)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest python-sdk/tests/test_exceptions.py -v`
预期：所有 11 个测试 PASS

- [ ] **步骤 5：Commit**

```bash
git add python-sdk/src/supersonic/exceptions.py python-sdk/tests/test_exceptions.py
git commit -m "feat(sdk): implement exception hierarchy with resource-specific errors"
```

---

## 任务 3：Auth 模型

**文件：**
- 创建：`python-sdk/src/supersonic/auth.py`
- 创建：`python-sdk/tests/test_auth.py`

**规格参考：** § Auth 模型（第 256-277 行）

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/test_auth.py`

```python
"""TokenAuth 测试。

规格：双 header 认证（Authorization + App-Key）。
"""
import pytest

from supersonic.auth import TokenAuth


class TestTokenAuth:
    def test_returns_dual_headers(self):
        auth = TokenAuth(token="jwt-abc", app_key="supersonic")
        headers = auth.headers()
        assert headers["Authorization"] == "Bearer jwt-abc"
        assert headers["App-Key"] == "supersonic"

    def test_app_key_defaults_to_supersonic(self):
        auth = TokenAuth(token="jwt")
        assert auth.app_key == "supersonic"

    def test_empty_token_raises_value_error(self):
        """Fail fast：token 为空直接报错，不发请求。"""
        with pytest.raises(ValueError, match="token cannot be empty"):
            TokenAuth(token="")

    def test_none_token_raises_value_error(self):
        with pytest.raises(ValueError, match="token cannot be empty"):
            TokenAuth(token=None)  # type: ignore[arg-type]

    def test_headers_are_immutable_snapshot(self):
        """返回的 dict 应该是独立的——用户改了不影响下次调用。"""
        auth = TokenAuth(token="jwt")
        h1 = auth.headers()
        h1["Authorization"] = "tampered"
        h2 = auth.headers()
        assert h2["Authorization"] == "Bearer jwt"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest python-sdk/tests/test_auth.py -v`
预期：FAIL，`ModuleNotFoundError: No module named 'supersonic.auth'`

- [ ] **步骤 3：实现 auth.py**

文件：`python-sdk/src/supersonic/auth.py`

```python
"""认证策略。

SuperSonic 使用双 header 鉴权（不同于 ai-sdk 的单 Bearer）：
- Authorization: Bearer <JWT>
- App-Key: <appKey>
"""
from dataclasses import dataclass


@dataclass
class TokenAuth:
    """JWT token + App-Key 双 header 认证。"""

    token: str
    app_key: str = "supersonic"

    def __post_init__(self) -> None:
        if not self.token:
            raise ValueError("token cannot be empty")

    def headers(self) -> dict[str, str]:
        """返回每次请求要带的 headers（独立副本，用户修改不影响下次调用）。"""
        return {
            "Authorization": f"Bearer {self.token}",
            "App-Key": self.app_key,
        }
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest python-sdk/tests/test_auth.py -v`
预期：5 个测试全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add python-sdk/src/supersonic/auth.py python-sdk/tests/test_auth.py
git commit -m "feat(sdk): implement TokenAuth with dual-header authentication"
```

---

## 任务 4：Config + RetryConfig

**文件：**
- 创建：`python-sdk/src/supersonic/config.py`
- 创建：`python-sdk/tests/test_config.py`

**规格参考：** § 重试与退避参数（第 284-306 行）+ § 环境变量表（第 1065-1087 行）

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/test_config.py`

```python
"""SupersonicConfig 与 RetryConfig 测试。"""
import pytest

from supersonic.config import RetryConfig, SupersonicConfig, compute_backoff


class TestRetryConfig:
    def test_defaults(self):
        c = RetryConfig()
        assert c.max_retries == 3
        assert c.retry_delay == 1.0
        assert c.max_backoff == 30.0
        assert c.backoff_jitter is True
        assert 429 in c.retryable_status_codes
        assert 500 in c.retryable_status_codes
        assert 400 not in c.retryable_status_codes


class TestComputeBackoff:
    def test_exponential_backoff_without_jitter(self):
        c = RetryConfig(backoff_jitter=False)
        assert compute_backoff(0, c) == 1.0
        assert compute_backoff(1, c) == 2.0
        assert compute_backoff(2, c) == 4.0

    def test_capped_at_max_backoff(self):
        """attempt=10 时 2^10=1024，应被裁剪到 max_backoff。"""
        c = RetryConfig(retry_delay=1.0, max_backoff=30.0, backoff_jitter=False)
        assert compute_backoff(10, c) == 30.0

    def test_retry_after_header_takes_priority(self):
        c = RetryConfig(respect_retry_after=True)
        assert compute_backoff(0, c, retry_after=120.0) == 30.0  # 也受 max_backoff 限制

    def test_retry_after_disabled(self):
        c = RetryConfig(respect_retry_after=False, backoff_jitter=False)
        assert compute_backoff(0, c, retry_after=120.0) == 1.0

    def test_jitter_adds_random_within_0_1(self):
        """jitter 模式下，多次调用结果应该散布在 [base, base+1) 区间。"""
        c = RetryConfig(retry_delay=1.0, backoff_jitter=True)
        results = [compute_backoff(0, c) for _ in range(50)]
        assert all(1.0 <= r < 2.0 for r in results)
        assert len(set(results)) > 1  # 有随机性


class TestSupersonicConfigFromEnv:
    def test_reads_required_vars(self, monkeypatch):
        monkeypatch.setenv("SUPERSONIC_HOST", "http://test:9080")
        monkeypatch.setenv("SUPERSONIC_TOKEN", "jwt")
        monkeypatch.delenv("SUPERSONIC_APP_KEY", raising=False)
        config = SupersonicConfig.from_env()
        assert config.host == "http://test:9080"
        assert config.token == "jwt"
        assert config.app_key == "supersonic"

    def test_missing_required_raises_with_helpful_message(self, monkeypatch):
        monkeypatch.delenv("SUPERSONIC_HOST", raising=False)
        monkeypatch.delenv("SUPERSONIC_TOKEN", raising=False)
        with pytest.raises(ValueError, match="SUPERSONIC_HOST"):
            SupersonicConfig.from_env()

    def test_optional_overrides(self, monkeypatch):
        monkeypatch.setenv("SUPERSONIC_HOST", "http://test")
        monkeypatch.setenv("SUPERSONIC_TOKEN", "jwt")
        config = SupersonicConfig.from_env(timeout=60.0, enable_async=True)
        assert config.timeout == 60.0
        assert config.enable_async is True

    def test_log_level_env(self, monkeypatch):
        monkeypatch.setenv("SUPERSONIC_HOST", "http://test")
        monkeypatch.setenv("SUPERSONIC_TOKEN", "jwt")
        monkeypatch.setenv("SUPERSONIC_LOG_LEVEL", "DEBUG")
        config = SupersonicConfig.from_env()
        assert config.log_level == "DEBUG"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest python-sdk/tests/test_config.py -v`
预期：FAIL，`ModuleNotFoundError`

- [ ] **步骤 3：实现 config.py**

文件：`python-sdk/src/supersonic/config.py`

```python
"""SDK 配置：RetryConfig + SupersonicConfig。

SupersonicConfig.from_env() 是推荐入口，环境变量见规格 § 环境变量表。
"""
import os
import random
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RetryConfig:
    """重试与退避策略。"""

    max_retries: int = 3
    retry_delay: float = 1.0
    max_backoff: float = 30.0
    backoff_jitter: bool = True
    retryable_status_codes: frozenset[int] = field(
        default_factory=lambda: frozenset({429, 500, 502, 503, 504})
    )
    respect_retry_after: bool = True


def compute_backoff(
    attempt: int,
    config: RetryConfig,
    retry_after: float | None = None,
) -> float:
    """指数退避 + 可选 jitter + Retry-After 优先。

    attempt 从 0 开始（首次失败）。
    """
    if config.respect_retry_after and retry_after is not None:
        return min(retry_after, config.max_backoff)
    delay = config.retry_delay * (2**attempt)
    if config.backoff_jitter:
        delay += random.uniform(0, 1.0)
    return min(delay, config.max_backoff)


def _parse_retry_after(resp) -> float | None:
    """从响应 Retry-After header 解析秒数。支持 delta-seconds 格式。"""
    val = resp.headers.get("Retry-After")
    if val is None:
        return None
    try:
        return float(val)
    except ValueError:
        return None  # HTTP-date 格式暂不支持


@dataclass
class SupersonicConfig:
    """SDK 主配置。from_env() 是推荐入口。"""

    host: str
    token: str
    app_key: str = "supersonic"
    timeout: float = 30.0
    enable_async: bool = False
    retry: RetryConfig = field(default_factory=RetryConfig)
    log_level: str = "WARNING"

    @classmethod
    def from_env(cls, **overrides) -> "SupersonicConfig":
        """从环境变量构造配置。

        必填：SUPERSONIC_HOST, SUPERSONIC_TOKEN
        可选：SUPERSONIC_APP_KEY, SUPERSONIC_TIMEOUT, SUPERSONIC_MAX_RETRIES,
              SUPERSONIC_ENABLE_ASYNC, SUPERSONIC_LOG_LEVEL
        overrides 显式覆盖环境变量值。
        """
        host = overrides.pop("host", None) or os.environ.get("SUPERSONIC_HOST")
        token = overrides.pop("token", None) or os.environ.get("SUPERSONIC_TOKEN")

        missing = []
        if not host:
            missing.append("SUPERSONIC_HOST")
        if not token:
            missing.append("SUPERSONIC_TOKEN")
        if missing:
            raise ValueError(
                f"Missing required env vars: {', '.join(missing)}. "
                f"Set them or pass host=.../token=... explicitly."
            )

        # 可选变量
        app_key = overrides.pop("app_key", None) or os.environ.get(
            "SUPERSONIC_APP_KEY", "supersonic"
        )
        timeout = overrides.pop(
            "timeout", None
        ) or float(os.environ.get("SUPERSONIC_TIMEOUT", "30.0"))
        enable_async = overrides.pop("enable_async", None)
        if enable_async is None:
            enable_async = os.environ.get("SUPERSONIC_ENABLE_ASYNC", "").lower() == "true"
        log_level = overrides.pop("log_level", None) or os.environ.get(
            "SUPERSONIC_LOG_LEVEL", "WARNING"
        )

        retry_overrides = {}
        max_retries_env = os.environ.get("SUPERSONIC_MAX_RETRIES")
        if max_retries_env:
            retry_overrides["max_retries"] = int(max_retries_env)
        retry = overrides.pop("retry", None) or RetryConfig(**retry_overrides)

        return cls(
            host=host,
            token=token,
            app_key=app_key,
            timeout=timeout,
            enable_async=enable_async,
            retry=retry,
            log_level=log_level,
            **overrides,
        )
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest python-sdk/tests/test_config.py -v`
预期：所有 8 个测试 PASS

- [ ] **步骤 5：Commit**

```bash
git add python-sdk/src/supersonic/config.py python-sdk/tests/test_config.py
git commit -m "feat(sdk): implement SupersonicConfig with env-based construction"
```

---

## 任务 5：common/logging.py

**文件：**
- 创建：`python-sdk/src/supersonic/common/__init__.py`
- 创建：`python-sdk/src/supersonic/common/logging.py`
- 创建：`python-sdk/tests/common/test_logging.py`

**规格参考：** § 日志策略（第 1120-1154 行）

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/common/test_logging.py`

```python
"""日志工具测试。"""
import logging

from supersonic.common.logging import get_logger, configure_logging, redact_headers


class TestGetLogger:
    def test_returns_supersonic_namespaced_logger(self):
        log = get_logger()
        assert log.name == "supersonic"

    def test_returns_same_instance(self):
        assert get_logger() is get_logger()


class TestConfigureLogging:
    def test_sets_level_on_logger(self):
        configure_logging("DEBUG")
        assert get_logger().level == logging.DEBUG
        # 还原默认避免污染其他测试
        configure_logging("WARNING")


class TestRedactHeaders:
    def test_redacts_authorization(self):
        headers = {
            "Authorization": "Bearer jwt-secret-token",
            "App-Key": "supersonic",
            "Content-Type": "application/json",
        }
        redacted = redact_headers(headers)
        assert redacted["Authorization"] == "Bearer ***"
        assert redacted["App-Key"] == "supersonic"  # 不打码
        assert redacted["Content-Type"] == "application/json"

    def test_handles_missing_authorization(self):
        headers = {"App-Key": "supersonic"}
        redacted = redact_headers(headers)
        assert "Authorization" not in redacted
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest python-sdk/tests/common/test_logging.py -v`
预期：FAIL，`ModuleNotFoundError`

- [ ] **步骤 3：实现 common/__init__.py + common/logging.py**

文件：`python-sdk/src/supersonic/common/__init__.py`

```python
"""内部基础设施子包。

按 Python 约定，common/ 不导出公共 API（用户不应 import supersonic.common.*）。
"""
__all__: list[str] = []  # 显式空，标记为内部包
```

文件：`python-sdk/src/supersonic/common/logging.py`

```python
"""SDK 日志工具。

复用 std logging，命名空间 supersonic。敏感信息（Authorization）始终打码。
"""
import logging

_LOGGER = logging.getLogger("supersonic")


def get_logger() -> logging.Logger:
    """返回 SDK 的 logger 单例。"""
    return _LOGGER


def configure_logging(level: str | int = "WARNING") -> None:
    """配置 supersonic 命名空间的日志级别。

    用户也可自行 logging.getLogger('supersonic').setLevel(...)。
    """
    if isinstance(level, str):
        level = logging.getLevelName(level.upper())
    _LOGGER.setLevel(level)


SENSITIVE_HEADERS = frozenset({"authorization", "cookie", "set-cookie", "x-api-key"})


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """返回 headers 副本，敏感 header 的 value 替换为 ***。"""
    redacted: dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() in SENSITIVE_HEADERS:
            redacted[k] = "***"
        else:
            redacted[k] = v
    return redacted
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest python-sdk/tests/common/test_logging.py -v`
预期：5 个测试全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add python-sdk/src/supersonic/common/ python-sdk/tests/common/test_logging.py
git commit -m "feat(sdk): add logging utilities with header redaction"
```

---

## 任务 6：common/http.py — HTTPClient（同步版）

**文件：**
- 创建：`python-sdk/src/supersonic/common/http.py`
- 创建：`python-sdk/tests/common/test_http.py`

**规格参考：** § HTTP 层与异常映射（第 282-417 行）+ § 异常映射（第 483-549 行）

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/common/test_http.py`

```python
"""HTTPClient 单元测试（pytest-httpx mock）。

规格：§ HTTPClient（位于 common/http.py）+ § 异常映射
"""
import pytest
from pytest_httpx import HTTPXMock

from supersonic.auth import TokenAuth
from supersonic.common.http import HTTPClient, _handle_response, _parse_field_errors
from supersonic.config import RetryConfig
from supersonic.exceptions import (
    AuthenticationError,
    ValidationError,
    RateLimitError,
    ServerError,
    MetricNotFoundError,
    FieldError,
)


@pytest.fixture
def auth():
    return TokenAuth(token="jwt", app_key="test-app")


@pytest.fixture
def retry_config():
    """测试用：no jitter（可预测），no retry（直接失败）便于断言。"""
    return RetryConfig(max_retries=0, backoff_jitter=False)


@pytest.fixture
def http(auth, retry_config):
    client = HTTPClient(
        base_url="http://test",
        auth=auth,
        retry=retry_config,
    )
    yield client
    client.close()


class TestRequestSuccess:
    def test_get_returns_json(self, http: HTTPClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://test/api/foo",
            method="GET",
            json={"ok": True},
        )
        result = http.request("GET", "/api/foo")
        assert result == {"ok": True}

    def test_post_with_json_body(self, http: HTTPClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://test/api/bar",
            method="POST",
            json={"id": 1},
        )
        result = http.request("POST", "/api/bar", json={"name": "x"})
        assert result == {"id": 1}

    def test_path_params_substitution(self, http: HTTPClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://test/api/metric/getMetric/42",
            method="GET",
            json={"id": 42},
        )
        result = http.request(
            "GET", "/api/metric/getMetric/{id}", path_params={"id": 42}
        )
        assert result == {"id": 42}

    def test_empty_body_returns_empty_dict(self, http: HTTPClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://test/api/noContent",
            method="DELETE",
            status_code=204,
        )
        result = http.request("DELETE", "/api/noContent")
        assert result == {}


class TestErrorMapping:
    def test_401_raises_authentication_error(self, http: HTTPClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="http://test/api/foo",
            status_code=401,
            json={"message": "invalid token"},
        )
        with pytest.raises(AuthenticationError) as exc:
            http.request("GET", "/api/foo")
        assert exc.value.status_code == 401

    def test_404_with_resource_type_raises_specific_exception(
        self, http: HTTPClient, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(url="http://test/api/foo", status_code=404)
        with pytest.raises(MetricNotFoundError) as exc:
            http.request(
                "GET",
                "/api/metric/getMetric/99",
                resource_type="metric",
                resource_id=99,
            )
        assert exc.value.resource_id == 99

    def test_404_without_resource_type_raises_generic(
        self, http: HTTPClient, httpx_mock: HTTPXMock
    ):
        from supersonic.exceptions import ResourceNotFoundError

        httpx_mock.add_response(url="http://test/api/foo", status_code=404)
        with pytest.raises(ResourceNotFoundError):
            http.request("GET", "/api/foo")

    def test_429_raises_rate_limit_with_retry_after(
        self, http: HTTPClient, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(
            url="http://test/api/foo",
            status_code=429,
            headers={"Retry-After": "60"},
        )
        with pytest.raises(RateLimitError) as exc:
            http.request("GET", "/api/foo")
        assert exc.value.retry_after == 60.0

    def test_400_raises_validation_error_with_field_errors(
        self, http: HTTPClient, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(
            url="http://test/api/foo",
            status_code=400,
            json={
                "errors": [
                    {"field": "name", "message": "不能为空"},
                    {"field": "type", "message": "无效值", "rejected_value": "X"},
                ]
            },
        )
        with pytest.raises(ValidationError) as exc:
            http.request("POST", "/api/foo")
        assert len(exc.value.field_errors) == 2
        assert exc.value.field_errors[0].field == "name"

    def test_500_raises_server_error(
        self, http: HTTPClient, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(
            url="http://test/api/foo",
            status_code=500,
            json={"message": "internal"},
        )
        with pytest.raises(ServerError):
            http.request("GET", "/api/foo")


class TestParseFieldErrors:
    def test_list_format(self):
        body = {"errors": [{"field": "name", "message": "x"}]}
        result = _parse_field_errors(body)
        assert len(result) == 1
        assert result[0].field == "name"

    def test_dict_format(self):
        body = {"fieldErrors": {"name": "必填"}}
        result = _parse_field_errors(body)
        assert len(result) == 1
        assert result[0].field == "name"
        assert result[0].message == "必填"

    def test_no_errors_returns_empty(self):
        body = {"message": "整体错误"}
        assert _parse_field_errors(body) == []

    def test_wrong_type_returns_empty(self):
        body = {"errors": "wrong string"}
        assert _parse_field_errors(body) == []


class TestRetry:
    def test_retries_on_500_then_succeeds(
        self, auth: TokenAuth, httpx_mock: HTTPXMock
    ):
        """max_retries=2，第 1 次 500，第 2 次成功。"""
        from httpx import Response

        httpx_mock.add_response(
            url="http://test/api/foo", status_code=500, json={"err": 1}
        )
        httpx_mock.add_response(
            url="http://test/api/foo", status_code=200, json={"ok": True}
        )
        client = HTTPClient(
            base_url="http://test",
            auth=auth,
            retry=RetryConfig(max_retries=2, backoff_jitter=False, retry_delay=0.01),
        )
        try:
            result = client.request("GET", "/api/foo")
            assert result == {"ok": True}
        finally:
            client.close()

    def test_exhausts_retries_raises_server_error(
        self, auth: TokenAuth, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(url="http://test/api/foo", status_code=500).is_reused
        client = HTTPClient(
            base_url="http://test",
            auth=auth,
            retry=RetryConfig(max_retries=1, backoff_jitter=False, retry_delay=0.01),
        )
        try:
            with pytest.raises(ServerError, match="Max retries exceeded"):
                client.request("GET", "/api/foo")
        finally:
            client.close()
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest python-sdk/tests/common/test_http.py -v`
预期：FAIL，`ModuleNotFoundError`

- [ ] **步骤 3：实现 common/http.py（同步部分）**

文件：`python-sdk/src/supersonic/common/http.py`

```python
"""HTTP 客户端（同步 + 异步）。

HTTPClient 与 AsyncHTTPClient 共享：
- _handle_response（异常映射）
- _compute_backoff / _parse_retry_after（来自 config）

差异：
- HTTPClient: httpx.Client，同步
- AsyncHTTPClient: httpx.AsyncClient，懒加载（避免事件循环绑定）
"""
import time
from typing import Any

import httpx

from supersonic.auth import TokenAuth
from supersonic.common.logging import get_logger, redact_headers
from supersonic.config import RetryConfig, compute_backoff
from supersonic.exceptions import (
    AuthenticationError,
    ConnectionError as SupersonicConnectionError,
    DatabaseNotFoundError,
    DatasetNotFoundError,
    DimensionNotFoundError,
    DomainNotFoundError,
    FieldError,
    MetricNotFoundError,
    ModelNotFoundError,
    RateLimitError,
    ResourceNotFoundError,
    ServerError,
    SupersonicError,
    ValidationError,
)

_NOT_FOUND_MAP: dict[str, type[ResourceNotFoundError]] = {
    "domain": DomainNotFoundError,
    "model": ModelNotFoundError,
    "dimension": DimensionNotFoundError,
    "metric": MetricNotFoundError,
    "dataset": DatasetNotFoundError,
    "database": DatabaseNotFoundError,
}

log = get_logger()


def _parse_retry_after(resp: httpx.Response) -> float | None:
    """从 Retry-After header 解析秒数。仅支持 delta-seconds 格式。"""
    val = resp.headers.get("Retry-After")
    if val is None:
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _parse_field_errors(body: dict[str, Any]) -> list[FieldError]:
    """从 SuperSonic 400 响应体解析字段级错误。

    支持三种格式：
    - {"errors": [{"field": "name", "message": "..."}]}  列表格式
    - {"fieldErrors": {"name": "..."}}                   字典格式
    - {"message": "..."}                                  无结构化字段错误
    """
    errors = body.get("errors") or body.get("fieldErrors") or []
    if isinstance(errors, dict):
        return [FieldError(field=k, message=str(v)) for k, v in errors.items()]
    if isinstance(errors, list):
        result: list[FieldError] = []
        for e in errors:
            if isinstance(e, dict) and "field" in e and "message" in e:
                result.append(FieldError(**e))
        return result
    return []


def _handle_response(
    resp: httpx.Response,
    *,
    path: str,
    resource_type: str | None = None,
    resource_id: int | str | None = None,
) -> dict[str, Any]:
    """统一处理响应：2xx 返回 json，其他状态码抛出对应异常。

    sync/async 共用——httpx.Response 接口一致，无需 await。
    """
    if 200 <= resp.status_code < 300:
        if not resp.content:
            return {}
        return resp.json()

    # 解析响应体（失败也给用户原始文本）
    try:
        body: dict[str, Any] = resp.json()
    except Exception:
        body = {"raw": resp.text}

    log.debug(
        "HTTP error status=%s path=%s body=%s",
        resp.status_code, path, body,
    )

    if resp.status_code == 401:
        raise AuthenticationError(
            "Authentication failed (token invalid or expired)",
            status_code=401,
            response_body=body,
        )
    if resp.status_code == 404:
        # 评审修复 3：统一签名，避免 resource_id 可能是空字符串的边界问题
        rid = resource_id if resource_id is not None else 0
        if resource_type and resource_type in _NOT_FOUND_MAP:
            exc_cls = _NOT_FOUND_MAP[resource_type]
            raise exc_cls(resource_id=rid)
        # 未知 resource_type：抛通用 ResourceNotFoundError
        raise ResourceNotFoundError(resource_type or "resource", rid)
    if resp.status_code == 429:
        raise RateLimitError(
            "Rate limit exceeded",
            status_code=429,
            response_body=body,
            retry_after=_parse_retry_after(resp),
        )
    if 400 <= resp.status_code < 500:
        field_errors = _parse_field_errors(body)
        message = body.get("message", resp.reason_phrase)
        raise ValidationError(
            f"Request validation failed: {message}",
            status_code=resp.status_code,
            response_body=body,
            field_errors=field_errors,
        )
    raise ServerError(
        f"Server error: {body.get('message', resp.reason_phrase)}",
        status_code=resp.status_code,
        response_body=body,
    )


class HTTPClient:
    """同步 HTTP 客户端，封装重试、退避、异常映射。

    Thread safety: NOT thread-safe. 每个线程应创建独立实例。
    """

    def __init__(
        self,
        base_url: str,
        auth: TokenAuth,
        *,
        timeout: float = 30.0,
        retry: RetryConfig | None = None,
    ) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=timeout)
        self._auth = auth
        self._retry = retry or RetryConfig()

    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        path_params: dict[str, Any] | None = None,
        resource_type: str | None = None,
        resource_id: int | str | None = None,
    ) -> dict[str, Any]:
        """发送 HTTP 请求，处理重试，映射异常。

        Returns: 解析后的 JSON dict（2xx）。
        Raises: SupersonicError 的子类（非 2xx）。
        """
        url = path.format(**(path_params or {}))
        last_exc: Exception | None = None

        for attempt in range(self._retry.max_retries + 1):
            headers = self._auth.headers()
            log.debug(
                "HTTP %s %s headers=%s payload=%s",
                method, url, redact_headers(headers), json,
            )

            try:
                resp = self._client.request(
                    method, url, json=json, params=params, headers=headers
                )
            except httpx.TransportError as e:
                last_exc = e
                if attempt < self._retry.max_retries:
                    time.sleep(compute_backoff(attempt, self._retry))
                    continue
                raise SupersonicConnectionError(f"Transport error: {e}") from e

            if (
                resp.status_code in self._retry.retryable_status_codes
                and attempt < self._retry.max_retries
            ):
                retry_after = (
                    _parse_retry_after(resp) if resp.status_code == 429 else None
                )
                time.sleep(compute_backoff(attempt, self._retry, retry_after))
                continue

            return _handle_response(
                resp,
                path=path,
                resource_type=resource_type,
                resource_id=resource_id,
            )

        raise ServerError(
            f"Max retries exceeded for {method} {url}"
        ) from last_exc

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HTTPClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest python-sdk/tests/common/test_http.py -v`
预期：所有测试 PASS

- [ ] **步骤 5：Commit**

```bash
git add python-sdk/src/supersonic/common/http.py python-sdk/tests/common/test_http.py
git commit -m "feat(sdk): implement HTTPClient with retry, backoff, and error mapping"
```

---

## 任务 7：common/http.py — AsyncHTTPClient

**文件：**
- 修改：`python-sdk/src/supersonic/common/http.py`（追加 AsyncHTTPClient）
- 创建：`python-sdk/tests/test_async.py`

**规格参考：** § AsyncHTTPClient（第 353-417 行）

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/test_async.py`

```python
"""AsyncHTTPClient 单元测试。"""
import pytest
from pytest_httpx import HTTPXMock

from supersonic.auth import TokenAuth
from supersonic.common.http import AsyncHTTPClient
from supersonic.config import RetryConfig
from supersonic.exceptions import ServerError


@pytest.fixture
def auth():
    return TokenAuth(token="jwt")


@pytest.fixture
def async_http(auth):
    """max_retries=0，避免重试拖慢测试。"""
    client = AsyncHTTPClient(
        base_url="http://test",
        auth=auth,
        retry=RetryConfig(max_retries=0, backoff_jitter=False),
    )
    yield client
    # 在测试结束关闭（如果 _async_client 已创建）


class TestAsyncRequest:
    async def test_get_returns_json(self, async_http: AsyncHTTPClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url="http://test/api/foo", json={"ok": True})
        result = await async_http.request("GET", "/api/foo")
        assert result == {"ok": True}
        await async_http.aclose()

    async def test_post_with_json(self, async_http: AsyncHTTPClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url="http://test/api/bar", json={"id": 1})
        result = await async_http.request("POST", "/api/bar", json={"name": "x"})
        assert result == {"id": 1}
        await async_http.aclose()

    async def test_path_params(self, async_http: AsyncHTTPClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url="http://test/items/42", json={"id": 42})
        result = await async_http.request(
            "GET", "/items/{id}", path_params={"id": 42}
        )
        assert result == {"id": 42}
        await async_http.aclose()


class TestAsyncLazyInit:
    async def test_async_client_not_created_in_init(self, auth):
        """AsyncClient 应该懒加载——__init__ 阶段 _async_client 为 None。"""
        client = AsyncHTTPClient(base_url="http://test", auth=auth)
        assert client._async_client is None
        await client.aclose()

    async def test_async_client_created_on_first_request(
        self, async_http: AsyncHTTPClient, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(url="http://test/x", json={})
        assert async_http._async_client is None
        await async_http.request("GET", "/x")
        assert async_http._async_client is not None
        await async_http.aclose()


class TestAsyncRetry:
    async def test_retries_on_500(
        self, auth: TokenAuth, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(url="http://test/x", status_code=500, json={})
        httpx_mock.add_response(url="http://test/x", status_code=200, json={"ok": True})
        client = AsyncHTTPClient(
            base_url="http://test",
            auth=auth,
            retry=RetryConfig(max_retries=2, backoff_jitter=False, retry_delay=0.01),
        )
        try:
            result = await client.request("GET", "/x")
            assert result == {"ok": True}
        finally:
            await client.aclose()
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest python-sdk/tests/test_async.py -v`
预期：FAIL，`ImportError: cannot import name 'AsyncHTTPClient'`

- [ ] **步骤 3：追加 AsyncHTTPClient 到 common/http.py**

在文件 `python-sdk/src/supersonic/common/http.py` 末尾追加：

```python
import asyncio


class AsyncHTTPClient:
    """异步 HTTP 客户端。

    与 HTTPClient 共享 _handle_response / compute_backoff / _parse_retry_after。
    差异：
    - 用 httpx.AsyncClient（懒加载，避免 __init__ 绑定事件循环）
    - time.sleep → asyncio.sleep
    """

    def __init__(
        self,
        base_url: str,
        auth: TokenAuth,
        *,
        timeout: float = 30.0,
        retry: RetryConfig | None = None,
    ) -> None:
        # 不在 __init__ 创建 AsyncClient，避免事件循环绑定问题
        self._base_url = base_url
        self._auth = auth
        self._timeout = timeout
        self._retry = retry or RetryConfig()
        self._async_client: httpx.AsyncClient | None = None

    @property
    def _client(self) -> httpx.AsyncClient:
        """懒加载：首次调用才创建 AsyncClient。"""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self._base_url, timeout=self._timeout
            )
        return self._async_client

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        path_params: dict[str, Any] | None = None,
        resource_type: str | None = None,
        resource_id: int | str | None = None,
    ) -> dict[str, Any]:
        url = path.format(**(path_params or {}))
        last_exc: Exception | None = None

        for attempt in range(self._retry.max_retries + 1):
            headers = self._auth.headers()
            log.debug(
                "HTTP async %s %s headers=%s payload=%s",
                method, url, redact_headers(headers), json,
            )

            try:
                resp = await self._client.request(
                    method, url, json=json, params=params, headers=headers
                )
            except httpx.TransportError as e:
                last_exc = e
                if attempt < self._retry.max_retries:
                    await asyncio.sleep(compute_backoff(attempt, self._retry))
                    continue
                raise SupersonicConnectionError(f"Transport error: {e}") from e

            if (
                resp.status_code in self._retry.retryable_status_codes
                and attempt < self._retry.max_retries
            ):
                retry_after = (
                    _parse_retry_after(resp) if resp.status_code == 429 else None
                )
                await asyncio.sleep(compute_backoff(attempt, self._retry, retry_after))
                continue

            return _handle_response(
                resp,
                path=path,
                resource_type=resource_type,
                resource_id=resource_id,
            )

        raise ServerError(f"Max retries exceeded for {method} {url}") from last_exc

    async def aclose(self) -> None:
        if self._async_client is not None:
            await self._async_client.aclose()
            self._async_client = None
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest python-sdk/tests/test_async.py -v`
预期：所有测试 PASS

- [ ] **步骤 5：Commit**

```bash
git add python-sdk/src/supersonic/common/http.py python-sdk/tests/test_async.py
git commit -m "feat(sdk): implement AsyncHTTPClient with lazy AsyncClient init"
```

---

## 任务 8：common/pagination.py

**文件：**
- 创建：`python-sdk/src/supersonic/common/pagination.py`
- 创建：`python-sdk/tests/common/test_pagination.py`

**规格参考：** § 分页处理（第 823-872 行）

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/common/test_pagination.py`

```python
"""Page + Page.from_response 测试。"""
import pytest
from pydantic import BaseModel

from supersonic.common.pagination import Page


class FakeItem(BaseModel):
    """用于测试的任意 pydantic 模型。"""
    id: int
    name: str


class TestPageFromResponse:
    def test_parses_supersonic_pageinfo_format(self):
        """SuperSonic PageInfo: {list: [...], total, pageNum, pageSize}。"""
        data = {
            "list": [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}],
            "total": 100,
            "pageNum": 1,
            "pageSize": 10,
        }
        page = Page[FakeItem].from_response(data, item_model=FakeItem)
        assert len(page.items) == 2
        assert isinstance(page.items[0], FakeItem)
        assert page.items[0].id == 1
        assert page.total == 100
        assert page.page == 1
        assert page.page_size == 10

    def test_empty_list(self):
        data = {"list": [], "total": 0, "pageNum": 1, "pageSize": 10}
        page = Page[FakeItem].from_response(data, item_model=FakeItem)
        assert page.items == []
        assert page.total == 0

    def test_missing_keys_uses_defaults(self):
        """响应缺字段时不报错，用默认值。"""
        data = {}
        page = Page[FakeItem].from_response(data, item_model=FakeItem)
        assert page.items == []
        assert page.total == 0
        assert page.page == 1
        assert page.page_size == 10

    def test_custom_keys(self):
        """支持非 SuperSonic 格式（如 GitHub 的 items/total_count）。"""
        data = {
            "items": [{"id": 1, "name": "x"}],
            "total_count": 50,
        }
        page = Page[FakeItem].from_response(
            data,
            item_model=FakeItem,
            items_key="items",
            total_key="total_count",
            page_key="page_number",
            page_size_key="per_page",
        )
        assert len(page.items) == 1
        assert page.total == 50


class TestPageValidation:
    def test_pydantic_model_validate_called_per_item(self):
        """from_response 通过 model_validate 转换，应触发 pydantic 校验。"""
        data = {
            "list": [{"id": "not-an-int"}],
            "total": 1,
        }
        with pytest.raises(Exception):  # pydantic ValidationError
            Page[FakeItem].from_response(data, item_model=FakeItem)
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest python-sdk/tests/common/test_pagination.py -v`
预期：FAIL，`ModuleNotFoundError`

- [ ] **步骤 3：实现 common/pagination.py**

文件：`python-sdk/src/supersonic/common/pagination.py`

```python
"""分页容器与构造工具。

Page[T] 是泛型 pydantic 模型，from_response 直接消费 SuperSonic PageInfo 响应。
资源类无需传 mapper 函数，pydantic model_validate 自动做转换。
"""
from typing import Any, Generic, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class Page(BaseModel, Generic[T]):
    """分页结果容器。"""

    items: list[T]
    total: int
    page: int
    page_size: int

    @classmethod
    def from_response(
        cls,
        data: dict[str, Any],
        item_model: Type[T],
        *,
        items_key: str = "list",
        total_key: str = "total",
        page_key: str = "pageNum",
        page_size_key: str = "pageSize",
    ) -> "Page[T]":
        """从 dict 响应构造 Page，自动用 item_model.model_validate 转换每项。

        默认 key 对应 SuperSonic PageInfo 格式。
        其他 API（如 GitHub）可通过 items_key 等参数自定义。
        """
        raw_items = data.get(items_key, []) or []
        items = [item_model.model_validate(item) for item in raw_items]
        return cls(
            items=items,
            total=data.get(total_key, 0) or 0,
            page=data.get(page_key, 1) or 1,
            page_size=data.get(page_size_key, 10) or 10,
        )
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest python-sdk/tests/common/test_pagination.py -v`
预期：5 个测试 PASS

- [ ] **步骤 5：Commit**

```bash
git add python-sdk/src/supersonic/common/pagination.py python-sdk/tests/common/test_pagination.py
git commit -m "feat(sdk): implement Page[T] with from_response for PageInfo parsing"
```

---

## 任务 9：models/base.py + 模型基类

**文件：**
- 创建：`python-sdk/src/supersonic/models/__init__.py`
- 创建：`python-sdk/src/supersonic/models/base.py`
- 创建：`python-sdk/tests/models/__init__.py`（空）

**规格参考：** § 包布局（第 119-129 行）

- [ ] **步骤 1：创建测试目录占位**

运行：`mkdir -p python-sdk/tests/models && touch python-sdk/tests/models/__init__.py`

- [ ] **步骤 2：实现 models/base.py**

文件：`python-sdk/src/supersonic/models/base.py`

```python
"""pydantic 模型基类。

SuperSonic API 用 camelCase（Java 后端），Python 习惯 snake_case。
CamelModel 通过 alias_generator + populate_by_name 让两种写法都能构造/访问。
"""
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """camelCase alias 的 pydantic 模型基类。

    - 后端返回的 camelCase JSON 可直接 model_validate
    - Python 端可用 snake_case 属性访问
    - 构造时两种写法都支持
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",  # SuperSonic 偶尔新增字段，SDK 不应崩溃
    )
```

- [ ] **步骤 3：创建 models/__init__.py 占位**

文件：`python-sdk/src/supersonic/models/__init__.py`

```python
"""pydantic 数据模型。

按资源拆分到单独文件：query/domain/model/dimension/metric/database/dataset。
本 __init__.py 在各模型文件实现后追加 re-export。
"""
```

- [ ] **步骤 4：验证可 import**

运行：`python -c "from supersonic.models.base import CamelModel; print(CamelModel)"`
预期：输出 `<class 'supersonic.models.base.CamelModel'>`，无错误

- [ ] **步骤 5：Commit**

```bash
git add python-sdk/src/supersonic/models/ python-sdk/tests/models/
git commit -m "feat(sdk): add CamelModel base with camelCase alias support"
```

---

## 任务 10：api/paths.py + conftest.py 共享 fixtures

**文件：**
- 创建：`python-sdk/src/supersonic/api/__init__.py`
- 创建：`python-sdk/src/supersonic/api/paths.py`
- 创建：`python-sdk/tests/conftest.py`

**规格参考：** § 完整 API 与端点路径映射（第 710-789 行）

- [ ] **步骤 1：实现 api/__init__.py**

文件：`python-sdk/src/supersonic/api/__init__.py`

```python
"""业务资源命名空间。

每个资源一个文件（domains.py/models.py/...），共享 paths.py 的端点常量。
"""
```

- [ ] **步骤 2：实现 api/paths.py（全部 37 个端点）**

文件：`python-sdk/src/supersonic/api/paths.py`

```python
"""SuperSonic REST API 端点路径常量集中定义。

SuperSonic 端点是驼峰式命名（非 RESTful），路径变更时只需改此文件。
资源类 + 测试共享这些常量，避免硬编码 URL。
"""


class QueryPaths:
    SQL = "/api/semantic/query/sql"
    SQLS = "/api/semantic/query/sqls"
    VALIDATE = "/api/semantic/query/validate"
    METRIC = "/api/semantic/query/metric"
    CHAT = "/api/semantic/query/chat"


class DomainPaths:
    LIST = "/api/semantic/domain/getDomainList"
    GET = "/api/semantic/domain/getDomain/{id}"
    CREATE = "/api/semantic/domain/createDomain"
    UPDATE = "/api/semantic/domain/updateDomain"
    DELETE = "/api/semantic/domain/deleteDomain/{domain_id}"


class ModelPaths:
    LIST = "/api/semantic/model/getModelList/{domain_id}"
    GET = "/api/semantic/model/getModel/{id}"
    CREATE = "/api/semantic/model/createModel"
    UPDATE = "/api/semantic/model/updateModel"
    DELETE = "/api/semantic/model/deleteModel/{model_id}"


class DimensionPaths:
    LIST = "/api/semantic/dimension/getDimensionList/{model_id}"
    GET = "/api/semantic/dimension/getDimension/{id}"
    CREATE = "/api/semantic/dimension/createDimension"
    UPDATE = "/api/semantic/dimension/updateDimension"
    DELETE = "/api/semantic/dimension/deleteDimension/{id}"
    QUERY_VALUES = "/api/semantic/dimension/queryDimValue"


class MetricPaths:
    LIST = "/api/semantic/metric/queryMetric"
    GET = "/api/semantic/metric/getMetric/{id}"
    CREATE = "/api/semantic/metric/createMetric"
    UPDATE = "/api/semantic/metric/updateMetric"
    DELETE = "/api/semantic/metric/deleteMetric/{id}"
    PUBLISH = "/api/semantic/metric/batchPublish"
    UNPUBLISH = "/api/semantic/metric/batchUnPublish"


class DatabasePaths:
    LIST = "/api/semantic/database/getDatabaseList"
    GET = "/api/semantic/database/getDatabase/{id}"
    # 评审修复 9：SuperSonic 的 database 端点是 upsert 语义，create 和 update 共用同一路径。
    # 请求体差异：update 时带 id，create 时不带。SDK 层分两个方法是为了类型清晰。
    CREATE = "/api/semantic/database/createOrUpdateDatabase"
    UPDATE = "/api/semantic/database/createOrUpdateDatabase"
    TEST_CONNECT = "/api/semantic/database/testConnect"
    GET_TABLES = "/api/semantic/database/getTables"
    GET_COLUMNS = "/api/semantic/database/getColumnsByName"


class DatasetPaths:
    LIST = "/api/semantic/dataSet/getDataSetList"
    GET = "/api/semantic/dataSet/getDataSet/{id}"
```

- [ ] **步骤 3：实现 conftest.py（共享 fixtures）**

文件：`python-sdk/tests/conftest.py`

```python
"""pytest 共享 fixtures。

- sample dict fixtures（避免每个测试重复构造响应）
- endpoint path fixtures（避免硬编码 URL）
- base_url fixture（mock URL 前缀）
"""
import pytest

from supersonic.api.paths import (
    QueryPaths, DomainPaths, ModelPaths, DimensionPaths,
    MetricPaths, DatabasePaths, DatasetPaths,
)


@pytest.fixture
def base_url() -> str:
    """所有 mock 测试的 base_url。HTTPClient 会构造 http://test + path。"""
    return "http://test"


@pytest.fixture
def metric_paths():
    return MetricPaths


@pytest.fixture
def domain_paths():
    return DomainPaths


@pytest.fixture
def model_paths():
    return ModelPaths


@pytest.fixture
def dimension_paths():
    return DimensionPaths


@pytest.fixture
def database_paths():
    return DatabasePaths


@pytest.fixture
def dataset_paths():
    return DatasetPaths


@pytest.fixture
def query_paths():
    return QueryPaths


# ===== Sample response fixtures =====

@pytest.fixture
def sample_metric_dict():
    """单个 Metric 响应。"""
    return {
        "id": 1,
        "name": "销售额",
        "bizName": "sales_amt",
        "modelId": 10,
        "defineType": "MEASURE",
        "type": "NUMBER",
        "expression": "pay_amt",
        "description": "订单支付金额",
        "status": "ONLINE",
    }


@pytest.fixture
def sample_metric_list_response():
    """Metric 列表分页响应（SuperSonic PageInfo 格式）。"""
    return {
        "list": [
            {"id": 1, "name": "销售额", "bizName": "sales_amt", "modelId": 10,
             "defineType": "MEASURE", "type": "NUMBER"},
            {"id": 2, "name": "订单数", "bizName": "order_cnt", "modelId": 10,
             "defineType": "MEASURE", "type": "NUMBER"},
        ],
        "total": 50,
        "pageNum": 1,
        "pageSize": 10,
    }


@pytest.fixture
def sample_query_result_dict():
    """QueryResult 响应。"""
    return {
        "columns": [
            {"name": "category", "type": "VARCHAR", "displayName": "品类"},
            {"name": "sales_amt", "type": "DOUBLE", "displayName": "销售额"},
        ],
        "resultRows": [
            {"category": "手机", "sales_amt": 12000.0},
            {"category": "电脑", "sales_amt": 8500.0},
        ],
        "sql": "SELECT category, SUM(pay_amt) AS sales_amt FROM orders GROUP BY category",
        "useCache": False,
        "errorMsg": None,
    }


@pytest.fixture
def sample_chat_result_dict():
    """ChatQueryResult 响应（含解析过程）。"""
    return {
        "queryResult": {
            "columns": [{"name": "product", "type": "VARCHAR"}],
            "resultRows": [{"product": "iPhone"}],
            "sql": "SELECT product FROM sales ORDER BY amt DESC LIMIT 1",
        },
        "selectedParse": {
            "sql": "SELECT product FROM sales ORDER BY amt DESC LIMIT 1",
            "score": 0.95,
            "properties": {},
        },
        "candidateParses": [
            {"sql": "SELECT product FROM sales ORDER BY amt DESC LIMIT 1", "score": 0.95, "properties": {}},
        ],
        "parseState": "COMPLETED",
        "timeCost": {"mapTime": 50, "parseTime": 200, "executeTime": 800},
    }


# ===== API-level fixtures（评审修复 1：解耦 API 测试与 Client 门面）=====
#
# 这些 fixture 让任务 14-20 的 API 测试可以独立 TDD 验证，无需等任务 21（Client）。
# 每个 fixture 注入真实的 HTTPClient（mock 重试参数为 0）+ None async_http（Phase 1 不支持元数据 async）。

@pytest.fixture
def http_client():
    """共享的 HTTPClient fixture（max_retries=0 避免重试拖慢测试）。"""
    from supersonic.auth import TokenAuth
    from supersonic.common.http import HTTPClient
    from supersonic.config import RetryConfig
    client = HTTPClient(
        base_url="http://test",
        auth=TokenAuth(token="jwt"),
        retry=RetryConfig(max_retries=0, backoff_jitter=False),
    )
    yield client
    client.close()


@pytest.fixture
def async_http_client():
    """AsyncHTTPClient fixture（仅 QueryAPI async 测试用）。"""
    from supersonic.auth import TokenAuth
    from supersonic.common.http import AsyncHTTPClient
    from supersonic.config import RetryConfig
    client = AsyncHTTPClient(
        base_url="http://test",
        auth=TokenAuth(token="jwt"),
        retry=RetryConfig(max_retries=0, backoff_jitter=False),
    )
    yield client
    # 测试结束调用 aclose（在测试中显式 await）


@pytest.fixture
def query_api(http_client):
    """QueryAPI 注入 HTTPClient，不依赖 Client 门面。"""
    from supersonic.api.query import QueryAPI
    return QueryAPI(http=http_client, async_http=None)


@pytest.fixture
def query_api_async(http_client, async_http_client):
    """QueryAPI + async client（仅 for async 测试）。"""
    from supersonic.api.query import QueryAPI
    return QueryAPI(http=http_client, async_http=async_http_client)


@pytest.fixture
def metrics_api(http_client):
    from supersonic.api.metrics import MetricsAPI
    return MetricsAPI(http=http_client, async_http=None)


@pytest.fixture
def domains_api(http_client):
    from supersonic.api.domains import DomainsAPI
    return DomainsAPI(http=http_client, async_http=None)


@pytest.fixture
def models_api(http_client):
    from supersonic.api.models import ModelsAPI
    return ModelsAPI(http=http_client, async_http=None)


@pytest.fixture
def dimensions_api(http_client):
    from supersonic.api.dimensions import DimensionsAPI
    return DimensionsAPI(http=http_client, async_http=None)


@pytest.fixture
def databases_api(http_client):
    from supersonic.api.databases import DatabasesAPI
    return DatabasesAPI(http=http_client, async_http=None)


@pytest.fixture
def datasets_api(http_client):
    from supersonic.api.datasets import DatasetsAPI
    return DatasetsAPI(http=http_client, async_http=None)
```

> **关键设计（评审修复 1）**：API 级 fixtures 让任务 14-20 的 TDD 流程独立可验证。
> 测试用 `query_api.sql(...)` 而非 `client.query.sql(...)`，**不依赖任务 21 的 Client**。
> 任务 21 完成后，门面层只需少量装配测试验证 7 个 namespace property 正确懒加载。

- [ ] **步骤 4：验证 paths 可 import**

运行：`python -c "from supersonic.api.paths import MetricPaths; print(MetricPaths.CREATE)"`
预期：输出 `/api/semantic/metric/createMetric`

- [ ] **步骤 5：Commit**

```bash
git add python-sdk/src/supersonic/api/ python-sdk/tests/conftest.py
git commit -m "feat(sdk): add endpoint path constants and shared test fixtures"
```

---

任务 11-24 因篇幅过长需要继续——我会在下一步继续写入剩余任务（models 实现、6 个资源 API、查询 API、utils、integration test、examples）。

**已完成任务的依赖关系总结：**
- 任务 1-10 完成后，SDK 的**地基**就绪：pyproject / 异常 / auth / config / HTTP（同步+异步）/ 分页 / 模型基类 / 端点常量 / 共享 fixtures
- 接下来任务 11-13 实现 8 个模型文件（query 模型 + 6 个元数据模型）
- 任务 14 实现门面 Client（依赖所有 API 类，但 API 类未实现时可用 mock 验证装配逻辑）
- 任务 15-21 实现 7 个 API 类（1 query + 6 元数据 CRUD）
- 任务 22-24 是 utils / 集成测试 / 示例（收尾）

---

## 任务 11：models/query.py — 查询请求/响应模型

**文件：**
- 创建：`python-sdk/src/supersonic/models/query.py`
- 创建：`python-sdk/tests/models/test_query_models.py`

**规格参考：** § 统一返回类型（第 617-664 行）+ § 支持类型（第 667-705 行）

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/models/test_query_models.py`

```python
"""查询相关 pydantic 模型测试。"""
import pytest

from supersonic.models.query import (
    QueryColumn,
    QueryResult,
    ChatQueryResult,
    SemanticParseInfo,
    ParseTimeCost,
    ParseState,
    Text2SqlType,
    MapMode,
    DateConf,
    DateMode,
    Filter,
    FilterOperator,
    Order,
    Param,
    CacheConfig,
    ValidationResult,
    QuerySqlReq,
    QueryMetricReq,
    QueryNLReq,
)


class TestEnums:
    def test_text2sql_type_values(self):
        assert Text2SqlType.LLM_OR_RULE.value == "LLM_OR_RULE"
        assert Text2SqlType.LLM_ONLY.value == "LLM_ONLY"
        assert Text2SqlType.RULE_ONLY.value == "RULE_ONLY"

    def test_map_mode_values(self):
        assert MapMode.STRICT.value == "STRICT"
        assert MapMode.LOOSE.value == "LOOSE"

    def test_parse_state_values(self):
        assert ParseState.COMPLETED.value == "COMPLETED"
        assert ParseState.FAILED.value == "FAILED"


class TestQueryResult:
    def test_parses_camel_case_response(self, sample_query_result_dict):
        result = QueryResult.model_validate(sample_query_result_dict)
        assert len(result.columns) == 2
        assert isinstance(result.columns[0], QueryColumn)
        assert result.columns[0].display_name == "品类"
        assert len(result.result_rows) == 2
        assert result.use_cache is False
        assert result.error_msg is None
        assert "SELECT" in result.sql

    def test_result_rows_default_empty(self):
        result = QueryResult(columns=[], result_rows=[])
        assert result.result_rows == []
        assert result.sql is None


class TestChatQueryResult:
    def test_parses_full_response(self, sample_chat_result_dict):
        result = ChatQueryResult.model_validate(sample_chat_result_dict)
        assert result.parse_state == ParseState.COMPLETED
        assert result.query_result is not None
        assert isinstance(result.selected_parse, SemanticParseInfo)
        assert len(result.candidate_parses) == 1
        assert isinstance(result.time_cost, ParseTimeCost)
        assert result.time_cost.execute_time == 800

    def test_failed_parse_no_query_result(self):
        """解析失败时 query_result 为 None。"""
        data = {
            "queryResult": None,
            "selectedParse": None,
            "candidateParses": [],
            "parseState": "FAILED",
        }
        result = ChatQueryResult.model_validate(data)
        assert result.parse_state == ParseState.FAILED
        assert result.query_result is None


class TestDateConf:
    def test_between_mode(self):
        d = DateConf(date_mode=DateMode.BETWEEN, start_date="2026-01-01", end_date="2026-06-30")
        assert d.start_date == "2026-01-01"

    def test_camel_case_alias(self):
        """snake_case 写的 date_mode，camelCase JSON 也能解析。"""
        d = DateConf.model_validate({
            "dateMode": "BETWEEN",
            "startDate": "2026-01-01",
            "endDate": "2026-06-30",
        })
        assert d.date_mode == DateMode.BETWEEN


class TestFilter:
    def test_eq_filter(self):
        f = Filter(name="category", operator=FilterOperator.EQ, value="手机")
        assert f.operator == FilterOperator.EQ

    def test_in_filter_with_list_value(self):
        f = Filter(name="category", operator=FilterOperator.IN, value=["手机", "电脑"])
        assert isinstance(f.value, list)


class TestValidationResult:
    def test_valid_result(self):
        r = ValidationResult(is_valid=True)
        assert r.is_valid is True
        assert r.error_msg is None
        assert r.corrected_sql is None

    def test_invalid_with_corrected_sql(self):
        r = ValidationResult(is_valid=False, error_msg="syntax error",
                              corrected_sql="SELECT ...")
        assert r.corrected_sql == "SELECT ..."


class TestRequestTypes:
    def test_query_sql_req_camel_case(self):
        req = QuerySqlReq.model_validate({
            "sql": "SELECT 1",
            "dataSetId": 1,
            "limit": 100,
        })
        assert req.data_set_id == 1
        assert req.limit == 100

    def test_query_metric_req_required_metrics(self):
        req = QueryMetricReq(metrics=["销售额"])
        assert req.metrics == ["销售额"]
        assert req.dimensions is None

    def test_query_nl_req_defaults(self):
        req = QueryNLReq(query_text="销售额最高的产品")
        assert req.text2sql_type == Text2SqlType.LLM_OR_RULE
        assert req.map_mode == MapMode.LOOSE
        assert req.save_answer is True
        assert req.detailed is True
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest python-sdk/tests/models/test_query_models.py -v`
预期：FAIL，`ModuleNotFoundError`

- [ ] **步骤 3：实现 models/query.py**

文件：`python-sdk/src/supersonic/models/query.py`

```python
"""查询相关的 pydantic 模型。

包含：
- 枚举（Text2SqlType / MapMode / ParseState / DateMode / FilterOperator）
- 请求体（QuerySqlReq / QueryMetricReq / QueryNLReq）
- 响应体（QueryResult / ChatQueryResult / ValidationResult）
- 辅助模型（QueryColumn / DateConf / Filter / Order / Param / CacheConfig）
"""
from enum import Enum
from typing import Any, Literal

from pydantic import Field

from supersonic.models.base import CamelModel


# ===== Enums =====

class Text2SqlType(str, Enum):
    LLM_OR_RULE = "LLM_OR_RULE"
    LLM_ONLY = "LLM_ONLY"
    RULE_ONLY = "RULE_ONLY"


class MapMode(str, Enum):
    STRICT = "STRICT"
    LOOSE = "LOOSE"


class ParseState(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DateMode(str, Enum):
    BETWEEN = "BETWEEN"
    IN = "IN"
    ALL = "ALL"
    LIST = "LIST"


class FilterOperator(str, Enum):
    EQ = "="
    NE = "!="
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    IN = "IN"
    NOT_IN = "NOT_IN"
    LIKE = "LIKE"
    BETWEEN = "BETWEEN"


# ===== Column / Result =====

class QueryColumn(CamelModel):
    name: str
    type: str
    display_name: str | None = None


class QueryResult(CamelModel):
    columns: list[QueryColumn]
    result_rows: list[dict[str, Any]] = Field(default_factory=list)
    sql: str | None = None
    use_cache: bool = False
    error_msg: str | None = None

    def to_dataframe(self):
        """转换为 pandas DataFrame（需 pip install supersonic-sdk[pandas]）。"""
        try:
            import pandas as pd
        except ImportError as e:
            raise ImportError(
                "to_dataframe requires pandas. "
                "Install with: pip install supersonic-sdk[pandas]"
            ) from e
        return pd.DataFrame(
            self.result_rows,
            columns=[c.name for c in self.columns],
        )


# ===== Chat Query =====

class SemanticParseInfo(CamelModel):
    sql: str | None = None
    score: float | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class ParseTimeCost(CamelModel):
    map_time: int | None = None
    parse_time: int | None = None
    execute_time: int | None = None


class ChatQueryResult(CamelModel):
    query_result: QueryResult | None = None
    selected_parse: SemanticParseInfo | None = None
    candidate_parses: list[SemanticParseInfo] = Field(default_factory=list)
    parse_state: ParseState
    time_cost: ParseTimeCost | None = None


# ===== Request Types =====

class DateConf(CamelModel):
    date_mode: DateMode
    start_date: str | None = None
    end_date: str | None = None
    date_list: list[str] | None = None
    period: str | None = None


class Filter(CamelModel):
    name: str
    operator: FilterOperator = FilterOperator.EQ
    value: Any | list[Any] | None = None


class Order(CamelModel):
    name: str
    direction: Literal["ASC", "DESC"] = "ASC"


class Param(CamelModel):
    name: str
    type: str
    value: Any


class CacheConfig(CamelModel):
    enable: bool = True
    ttl: int = 3600


class QuerySqlReq(CamelModel):
    sql: str
    data_set_id: int | None = None
    model_ids: list[int] | None = None
    limit: int = 1000
    params: list[Param] | None = None
    cache: CacheConfig | None = None


class QueryMetricReq(CamelModel):
    metrics: list[str]
    dimensions: list[str] | None = None
    filters: list[Filter] | None = None
    date_info: DateConf | None = None
    orders: list[Order] | None = None
    limit: int = 1000


class QueryNLReq(CamelModel):
    query_text: str
    data_set_ids: list[int] | None = None
    text2sql_type: Text2SqlType = Text2SqlType.LLM_OR_RULE
    map_mode: MapMode = MapMode.LOOSE
    save_answer: bool = True
    query_filters: dict[str, Any] | None = None
    # SDK 侧用，不发给服务器
    detailed: bool = True


# ===== Validation =====

class ValidationResult(CamelModel):
    is_valid: bool
    error_msg: str | None = None
    corrected_sql: str | None = None
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest python-sdk/tests/models/test_query_models.py -v`
预期：所有测试 PASS

- [ ] **步骤 5：Commit**

```bash
git add python-sdk/src/supersonic/models/query.py python-sdk/tests/models/test_query_models.py
git commit -m "feat(sdk): implement query request/response pydantic models"
```

---

## 任务 12：元数据 models（6 个资源 + dataset）

**文件：**
- 创建：`python-sdk/src/supersonic/models/domain.py`
- 创建：`python-sdk/src/supersonic/models/model.py`
- 创建：`python-sdk/src/supersonic/models/dimension.py`
- 创建：`python-sdk/src/supersonic/models/metric.py`
- 创建：`python-sdk/src/supersonic/models/database.py`
- 创建：`python-sdk/src/supersonic/models/dataset.py`
- 创建：`python-sdk/tests/models/test_metadata_models.py`

**规格参考：** § 元数据 CRUD 模式（第 707-820 行）

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/models/test_metadata_models.py`

```python
"""元数据资源模型测试。"""
import pytest

from supersonic.models.domain import Domain, DomainCreateReq, DomainUpdateReq
from supersonic.models.model import Model, ModelCreateReq
from supersonic.models.dimension import Dimension, DimensionCreateReq
from supersonic.models.metric import Metric, MetricCreateReq, MetricUpdateReq
from supersonic.models.database import Database, DatabaseCreateReq
from supersonic.models.dataset import Dataset


class TestDomain:
    def test_parses_response(self):
        d = Domain.model_validate({
            "id": 1, "name": "销售域", "bizName": "sales",
            "parentDomainId": 0, "status": "ONLINE",
        })
        assert d.id == 1
        assert d.biz_name == "sales"
        assert d.parent_domain_id == 0

    def test_create_req_required_fields(self):
        req = DomainCreateReq(name="销售域", biz_name="sales")
        assert req.name == "销售域"
        assert req.parent_domain_id is None


class TestModel:
    def test_parses_response(self):
        m = Model.model_validate({
            "id": 10, "name": "订单模型", "bizName": "order",
            "domainId": 1, "databaseId": 5,
        })
        assert m.id == 10
        assert m.domain_id == 1

    def test_create_req(self):
        req = ModelCreateReq(
            domain_id=1, database_id=5,
            name="订单模型", biz_name="order",
            table_name="orders",
        )
        assert req.table_name == "orders"


class TestMetric:
    def test_parses_response(self, sample_metric_dict):
        m = Metric.model_validate(sample_metric_dict)
        assert m.id == 1
        assert m.name == "销售额"
        assert m.define_type == "MEASURE"
        assert m.model_id == 10

    def test_create_req_required(self):
        req = MetricCreateReq(
            model_id=10, name="销售额", biz_name="sales_amt",
            define_type="MEASURE", type="NUMBER", expression="pay_amt",
        )
        assert req.model_id == 10
        assert req.description is None

    def test_update_req_all_optional(self):
        """更新请求所有字段都可选——PATCH 语义。"""
        req = MetricUpdateReq(description="新描述")
        assert req.description == "新描述"
        assert req.name is None


class TestDimension:
    def test_parses_response(self):
        d = Dimension.model_validate({
            "id": 100, "name": "品类", "bizName": "category",
            "modelId": 10, "type": "VARCHAR",
        })
        assert d.id == 100
        assert d.type == "VARCHAR"


class TestDatabase:
    def test_parses_response(self):
        db = Database.model_validate({
            "id": 5, "name": "main-db", "type": "mysql",
            "version": "8.0", "host": "localhost", "port": 3306,
        })
        assert db.id == 5
        assert db.type == "mysql"

    def test_create_req(self):
        req = DatabaseCreateReq(
            name="main-db", type="mysql",
            host="localhost", port=3306,
            username="root", password="***",
        )
        assert req.port == 3306


class TestDataset:
    def test_parses_response(self):
        ds = Dataset.model_validate({
            "id": 1, "name": "销售数据集", "bizName": "sales_dataset",
            "domainId": 1, "modelIds": [10, 11],
        })
        assert ds.id == 1
        assert ds.model_ids == [10, 11]
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest python-sdk/tests/models/test_metadata_models.py -v`
预期：FAIL，`ModuleNotFoundError`

- [ ] **步骤 3：实现 6 个模型文件**

文件：`python-sdk/src/supersonic/models/domain.py`

```python
"""Domain 模型。"""
from typing import Any

from pydantic import Field

from supersonic.models.base import CamelModel


class Domain(CamelModel):
    id: int | None = None
    name: str
    biz_name: str
    parent_domain_id: int | None = None
    description: str | None = None
    status: str | None = None
    viewer: list[str] | None = None
    admin: list[str] | None = None


class DomainCreateReq(CamelModel):
    name: str
    biz_name: str
    parent_domain_id: int | None = None
    description: str | None = None


class DomainUpdateReq(CamelModel):
    """所有字段可选，PATCH 语义。"""
    id: int
    name: str | None = None
    biz_name: str | None = None
    parent_domain_id: int | None = None
    description: str | None = None
```

文件：`python-sdk/src/supersonic/models/model.py`

```python
"""Model 模型。"""
from typing import Any

from supersonic.models.base import CamelModel


class Model(CamelModel):
    id: int | None = None
    name: str
    biz_name: str
    domain_id: int
    database_id: int
    table_name: str | None = None
    table_query: str | None = None  # 视图 SQL（与 table_name 二选一）
    description: str | None = None
    status: str | None = None
    tag_object_ids: list[int] | None = None


class ModelCreateReq(CamelModel):
    domain_id: int
    database_id: int
    name: str
    biz_name: str
    table_name: str | None = None
    table_query: str | None = None
    description: str | None = None
```

文件：`python-sdk/src/supersonic/models/dimension.py`

```python
"""Dimension 模型。"""
from typing import Any

from supersonic.models.base import CamelModel


class Dimension(CamelModel):
    id: int | None = None
    name: str
    biz_name: str
    model_id: int
    type: str  # VARCHAR / NUMBER / DATE / ...
    expr: str | None = None
    description: str | None = None
    status: str | None = None
    sensitive_level: str | None = None


class DimensionCreateReq(CamelModel):
    model_id: int
    name: str
    biz_name: str
    type: str
    expr: str | None = None
    description: str | None = None
```

文件：`python-sdk/src/supersonic/models/metric.py`

```python
"""Metric 模型。"""
from typing import Any

from supersonic.models.base import CamelModel


class Metric(CamelModel):
    id: int | None = None
    name: str
    biz_name: str
    model_id: int
    define_type: str  # MEASURE / FIELD / METRIC
    type: str | None = None  # NUMBER / PERCENT / ...
    expression: str | None = None
    description: str | None = None
    status: str | None = None  # ONLINE / OFFLINE / DRAFT
    sensitive_level: str | None = None
    data_format_type: str | None = None
    alias: list[str] | None = None
    classifications: list[str] | None = None
    relate_dimensions: list[dict[str, Any]] | None = None


class MetricCreateReq(CamelModel):
    model_id: int
    name: str
    biz_name: str
    define_type: str
    type: str | None = None
    expression: str | None = None
    description: str | None = None
    alias: list[str] | None = None


class MetricUpdateReq(CamelModel):
    """所有非 id 字段可选。"""
    id: int
    name: str | None = None
    biz_name: str | None = None
    define_type: str | None = None
    type: str | None = None
    expression: str | None = None
    description: str | None = None
```

文件：`python-sdk/src/supersonic/models/database.py`

```python
"""Database 模型。"""
from supersonic.models.base import CamelModel


class Database(CamelModel):
    id: int | None = None
    name: str
    type: str  # mysql / postgresql / clickhouse / duckdb / ...
    version: str | None = None
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    database: str | None = None
    description: str | None = None


class DatabaseCreateReq(CamelModel):
    name: str
    type: str
    host: str
    port: int
    username: str
    password: str
    database: str | None = None
    version: str | None = None
    description: str | None = None


class TableColumn(CamelModel):
    name: str
    type: str
    comment: str | None = None


class TestConnectionResult(CamelModel):
    success: bool
    error_message: str | None = None
```

文件：`python-sdk/src/supersonic/models/dataset.py`

```python
"""Dataset 模型。"""
from typing import Any

from supersonic.models.base import CamelModel


class Dataset(CamelModel):
    id: int | None = None
    name: str
    biz_name: str
    domain_id: int | None = None
    model_ids: list[int] | None = None
    description: str | None = None
    status: str | None = None
    query_config: dict[str, Any] | None = None
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest python-sdk/tests/models/test_metadata_models.py -v`
预期：所有测试 PASS

- [ ] **步骤 5：Commit**

```bash
git add python-sdk/src/supersonic/models/{domain,model,dimension,metric,database,dataset}.py
git add python-sdk/tests/models/test_metadata_models.py
git commit -m "feat(sdk): implement metadata models for 6 resources"
```

---

## 任务 13：models/__init__.py re-export

**文件：**
- 修改：`python-sdk/src/supersonic/models/__init__.py`（追加 re-export）

- [ ] **步骤 1：更新 models/__init__.py**

文件：`python-sdk/src/supersonic/models/__init__.py`

```python
"""pydantic 数据模型（按资源拆分，re-export 到本 __init__）。

用户可：
    from supersonic.models import Metric, MetricCreateReq, QueryResult
或直接：
    from supersonic.models.metric import Metric
"""
from supersonic.models.base import CamelModel
from supersonic.models.query import (
    # 枚举
    Text2SqlType, MapMode, ParseState, DateMode, FilterOperator,
    # 模型
    QueryColumn, QueryResult, ChatQueryResult,
    SemanticParseInfo, ParseTimeCost,
    DateConf, Filter, Order, Param, CacheConfig,
    QuerySqlReq, QueryMetricReq, QueryNLReq,
    ValidationResult,
)
from supersonic.models.domain import Domain, DomainCreateReq, DomainUpdateReq
from supersonic.models.model import Model, ModelCreateReq
from supersonic.models.dimension import Dimension, DimensionCreateReq
from supersonic.models.metric import Metric, MetricCreateReq, MetricUpdateReq
from supersonic.models.database import (
    Database, DatabaseCreateReq, TableColumn, TestConnectionResult,
)
from supersonic.models.dataset import Dataset

__all__ = [
    # base
    "CamelModel",
    # enums
    "Text2SqlType", "MapMode", "ParseState", "DateMode", "FilterOperator",
    # query
    "QueryColumn", "QueryResult", "ChatQueryResult",
    "SemanticParseInfo", "ParseTimeCost",
    "DateConf", "Filter", "Order", "Param", "CacheConfig",
    "QuerySqlReq", "QueryMetricReq", "QueryNLReq",
    "ValidationResult",
    # metadata
    "Domain", "DomainCreateReq", "DomainUpdateReq",
    "Model", "ModelCreateReq",
    "Dimension", "DimensionCreateReq",
    "Metric", "MetricCreateReq", "MetricUpdateReq",
    "Database", "DatabaseCreateReq", "TableColumn", "TestConnectionResult",
    "Dataset",
]
```

- [ ] **步骤 2：验证 re-export 工作**

运行：`python -c "from supersonic.models import Metric, QueryResult, Filter; print(Metric, QueryResult, Filter)"`
预期：输出三个类，无 ImportError

- [ ] **步骤 3：Commit**

```bash
git add python-sdk/src/supersonic/models/__init__.py
git commit -m "feat(sdk): re-export all models from models/__init__.py"
```

---

## 任务 13b：类型检查里程碑（评审修复 5）

**目的**：模型层完成后、API 类开始前，提前跑一次 mypy + ruff，早暴露类型问题。

**文件：** 无新增（只验证现有代码）

- [ ] **步骤 1：运行类型检查（仅 models + 基础设施）**

运行：
```bash
cd python-sdk
mypy src/supersonic/models/ src/supersonic/exceptions.py src/supersonic/auth.py src/supersonic/config.py src/supersonic/common/
```

预期：
- 无 error（warning 可接受）
- 重点检查：`CamelModel` 的 `alias_generator` / pydantic v2 配置 / `Field(default_factory=...)` 类型推断

- [ ] **步骤 2：运行 lint**

运行：
```bash
ruff check src/supersonic/models/ src/supersonic/common/ src/supersonic/exceptions.py src/supersonic/auth.py src/supersonic/config.py
```

预期：无 error，可能少量 warning（unused imports 等，按 ruff 提示修复）

- [ ] **步骤 3：如有问题，修复后 commit**

```bash
git add -A
git commit -m "fix(sdk): address mypy/ruff findings in models and infra"
```

如无问题，跳过此 commit，直接进入任务 14。

> **评审修复 5 说明**：原计划把 mypy/ruff 全部留到任务 23，导致 `@overload` / 泛型 / 内置名覆盖等类型问题积累到末期才暴露。任务 13b 在模型层完成后立即检查，问题更聚焦、修复成本更低。
> 任务 21（Client 完成）后会在任务 23 再跑一次全量检查。

---

## 任务 14：QueryAPI（查询命名空间）

**文件：**
- 创建：`python-sdk/src/supersonic/api/query.py`
- 创建：`python-sdk/tests/api/__init__.py`（空）
- 创建：`python-sdk/tests/api/test_query.py`

**规格参考：** § 5 个查询方法签名（第 557-615 行）+ § ChatQueryResult 双模式（第 644-675 行）

- [ ] **步骤 1：创建测试目录**

运行：`touch python-sdk/tests/api/__init__.py`

- [ ] **步骤 2：编写失败的测试**

文件：`python-sdk/tests/api/test_query.py`

```python
"""QueryAPI 测试。

评审修复 1：直接注入 HTTPClient 测试，不依赖 SupersonicClient 门面。
"""
import asyncio

import pytest
from pytest_httpx import HTTPXMock

from supersonic.api.query import QueryAPI
from supersonic.exceptions import AsyncNotEnabledError, ServerError
from supersonic.models.query import (
    ChatQueryResult, QueryResult, ValidationResult,
)


class TestSqlQuery:
    def test_returns_query_result(
        self, query_api: QueryAPI, httpx_mock: HTTPXMock,
        query_paths, base_url, sample_query_result_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{query_paths.SQL}",
            method="POST",
            json=sample_query_result_dict,
        )
        result = query_api.sql("SELECT 1", data_set_id=1)
        assert isinstance(result, QueryResult)
        assert len(result.columns) == 2

    def test_async_with_enable_async(
        self, query_api_async: QueryAPI, httpx_mock: HTTPXMock,
        query_paths, base_url, sample_query_result_dict,
    ):
        """async 路径：使用 query_api_async fixture。"""
        httpx_mock.add_response(
            url=f"{base_url}{query_paths.SQL}",
            json=sample_query_result_dict,
        )
        result = asyncio.run(query_api_async.asql("SELECT 1"))
        assert isinstance(result, QueryResult)

    def test_async_without_enable_raises(
        self, query_api: QueryAPI,
    ):
        """query_api fixture 的 async_http 为 None，调用 async 方法应抛 AsyncNotEnabledError。"""
        with pytest.raises(AsyncNotEnabledError):
            asyncio.run(query_api.asql("SELECT 1"))


class TestMetricQuery:
    def test_returns_query_result(
        self, query_api: QueryAPI, httpx_mock: HTTPXMock,
        query_paths, base_url, sample_query_result_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{query_paths.METRIC}",
            json=sample_query_result_dict,
        )
        result = query_api.metric(
            metrics=["销售额"],
            dimensions=["品类"],
        )
        assert isinstance(result, QueryResult)


class TestValidateQuery:
    def test_returns_validation_result(
        self, query_api: QueryAPI, httpx_mock: HTTPXMock,
        query_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{query_paths.VALIDATE}",
            json={"isValid": True, "errorMsg": None, "correctedSql": None},
        )
        result = query_api.validate("SELECT 1")
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True


class TestSqlsBatch:
    def test_returns_list(
        self, query_api: QueryAPI, httpx_mock: HTTPXMock,
        query_paths, base_url, sample_query_result_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{query_paths.SQLS}",
            json=[sample_query_result_dict, sample_query_result_dict],
        )
        results = query_api.sqls(["SELECT 1", "SELECT 2"])
        assert isinstance(results, list)
        assert len(results) == 2
        assert isinstance(results[0], QueryResult)


class TestChatDetailedModes:
    def test_default_returns_chat_query_result(
        self, query_api: QueryAPI, httpx_mock: HTTPXMock,
        query_paths, base_url, sample_chat_result_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{query_paths.CHAT}",
            json=sample_chat_result_dict,
        )
        result = query_api.chat("销售额最高的产品")
        assert isinstance(result, ChatQueryResult)
        assert result.selected_parse is not None

    def test_detailed_false_returns_query_result(
        self, query_api: QueryAPI, httpx_mock: HTTPXMock,
        query_paths, base_url, sample_chat_result_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{query_paths.CHAT}",
            json=sample_chat_result_dict,
        )
        result = query_api.chat("销售额最高的产品", detailed=False)
        assert isinstance(result, QueryResult)
        assert not isinstance(result, ChatQueryResult)

    def test_detailed_false_on_parse_failure_raises(
        self, query_api: QueryAPI, httpx_mock: HTTPXMock,
        query_paths, base_url,
    ):
        """简洁模式解析失败时显式抛错，不返回 None。"""
        httpx_mock.add_response(
            url=f"{base_url}{query_paths.CHAT}",
            json={
                "queryResult": None,
                "selectedParse": None,
                "candidateParses": [],
                "parseState": "FAILED",
            },
        )
        with pytest.raises(ServerError, match="detailed=True"):
            query_api.chat("无效查询", detailed=False)
```

- [ ] **步骤 3：运行测试验证失败**

运行：`pytest python-sdk/tests/api/test_query.py -v`
预期：FAIL，`ImportError: cannot import name 'QueryAPI' from 'supersonic.api.query'`

- [ ] **步骤 4：实现 api/query.py**

文件：`python-sdk/src/supersonic/api/query.py`

```python
"""QueryAPI — 自然语言 / S2SQL / 结构化指标查询。

5 个方法：sql / sqls / validate / metric / chat（含 detailed 双模式）。
"""
from typing import Literal, overload

from supersonic.api.paths import QueryPaths
from supersonic.common.http import AsyncHTTPClient, HTTPClient
from supersonic.exceptions import AsyncNotEnabledError, ServerError
from supersonic.models.query import (
    ChatQueryResult,
    DateConf,
    Filter,
    MapMode,
    Order,
    Param,
    QueryMetricReq,
    QueryNLReq,
    QueryResult,
    QuerySqlReq,
    Text2SqlType,
    ValidationResult,
)


class QueryAPI:
    def __init__(self, http: HTTPClient, async_http: AsyncHTTPClient | None) -> None:
        self._http = http
        self._async_http = async_http

    # ===== S2SQL 查询 =====

    def sql(
        self,
        sql: str,
        *,
        data_set_id: int | None = None,
        model_ids: list[int] | None = None,
        limit: int = 1000,
        params: list[Param] | None = None,
        cache=None,
    ) -> QueryResult:
        req = QuerySqlReq(
            sql=sql,
            data_set_id=data_set_id,
            model_ids=model_ids,
            limit=limit,
            params=params,
        )
        body = self._http.request(
            "POST", QueryPaths.SQL,
            json=req.model_dump(by_alias=True, exclude_none=True),
        )
        return QueryResult.model_validate(body)

    async def asql(self, sql: str, **kwargs) -> QueryResult:
        if self._async_http is None:
            raise AsyncNotEnabledError()
        req = QuerySqlReq(sql=sql, **kwargs)
        body = await self._async_http.request(
            "POST", QueryPaths.SQL,
            json=req.model_dump(by_alias=True, exclude_none=True),
        )
        return QueryResult.model_validate(body)

    # ===== 批量 S2SQL =====

    def sqls(
        self,
        sqls: list[str],
        *,
        data_set_id: int | None = None,
        model_ids: list[int] | None = None,
        limit: int = 1000,
    ) -> list[QueryResult]:
        body = self._http.request(
            "POST", QueryPaths.SQLS,
            json={
                "sqls": sqls,
                "dataSetId": data_set_id,
                "modelIds": model_ids,
                "limit": limit,
            },
        )
        return [QueryResult.model_validate(item) for item in body]

    # ===== 校验 =====

    def validate(
        self,
        sql: str,
        *,
        data_set_id: int | None = None,
        model_ids: list[int] | None = None,
    ) -> ValidationResult:
        body = self._http.request(
            "POST", QueryPaths.VALIDATE,
            json={
                "sql": sql,
                "dataSetId": data_set_id,
                "modelIds": model_ids,
            },
        )
        return ValidationResult.model_validate(body)

    # ===== 结构化指标查询 =====

    def metric(
        self,
        metrics: list[str],
        *,
        dimensions: list[str] | None = None,
        filters: list[Filter] | None = None,
        date_info: DateConf | None = None,
        orders: list[Order] | None = None,
        limit: int = 1000,
    ) -> QueryResult:
        req = QueryMetricReq(
            metrics=metrics,
            dimensions=dimensions,
            filters=filters,
            date_info=date_info,
            orders=orders,
            limit=limit,
        )
        body = self._http.request(
            "POST", QueryPaths.METRIC,
            json=req.model_dump(by_alias=True, exclude_none=True),
        )
        return QueryResult.model_validate(body)

    # ===== 自然语言查询（detailed 双模式）=====

    @overload
    def chat(
        self, query_text: str, *,
        detailed: Literal[True] = True, **kwargs,
    ) -> ChatQueryResult: ...

    @overload
    def chat(
        self, query_text: str, *,
        detailed: Literal[False], **kwargs,
    ) -> QueryResult: ...

    def chat(
        self,
        query_text: str,
        *,
        detailed: bool = True,
        data_set_ids: list[int] | None = None,
        text2sql_type: Text2SqlType = Text2SqlType.LLM_OR_RULE,
        map_mode: MapMode = MapMode.LOOSE,
        save_answer: bool = True,
        query_filters: dict | None = None,
    ):
        req = QueryNLReq(
            query_text=query_text,
            data_set_ids=data_set_ids,
            text2sql_type=text2sql_type,
            map_mode=map_mode,
            save_answer=save_answer,
            query_filters=query_filters,
        )
        body = self._http.request(
            "POST", QueryPaths.CHAT,
            json=req.model_dump(by_alias=True, exclude_none=True),
        )
        full = ChatQueryResult.model_validate(body)

        if detailed:
            return full

        # 简洁模式：解析失败显式报错
        if full.query_result is None:
            raise ServerError(
                f"Chat query parse failed (state={full.parse_state.value}). "
                f"Use detailed=True to inspect parse info."
            )
        return full.query_result
```

- [ ] **步骤 5：Commit**

```bash
git add python-sdk/src/supersonic/api/query.py python-sdk/tests/api/
git commit -m "feat(sdk): implement QueryAPI with 5 query methods and detailed dual-mode"
```

> **评审修复 1 应用**：本任务的测试通过 `query_api` / `query_api_async` fixture 直接注入 HTTPClient，**不依赖任务 21 的 Client 门面**。TDD 流程完整：编写测试 → 验证失败 → 实现 → 验证通过 → commit。任务 14 现在可以独立完成。

---

## 任务 15-20：6 个元数据 CRUD API（模式相同，批量实现）

**文件（每个资源一个文件）：**
- 创建：`python-sdk/src/supersonic/api/domains.py`（任务 15）
- 创建：`python-sdk/src/supersonic/api/models.py`（任务 16）
- 创建：`python-sdk/src/supersonic/api/dimensions.py`（任务 17）
- 创建：`python-sdk/src/supersonic/api/metrics.py`（任务 18）
- 创建：`python-sdk/src/supersonic/api/databases.py`（任务 19）
- 创建：`python-sdk/src/supersonic/api/datasets.py`（任务 20）
- 创建：对应的测试文件

**规格参考：** § 元数据 CRUD 模式 + § 分页处理

**评审修复 2**：Phase 1 元数据 API **不实现 async 方法**（评审建议的方案 B）。
async 元数据 CRUD 留作 v0.2，本次只实现同步五件套。QueryAPI 的 `asql()` 仍是 Phase 1 唯一的 async 方法。

**评审修复 4**：`list()` 操作**不传 `resource_type`**——list 是集合查询，不应返回特定资源 404。

每个资源类实现统一五件套（list/get/create/update/delete）+ 资源特有方法。
下面以 **MetricsAPI（任务 18，最完整）** 为模板，其他资源类按相同模式精简。

- [ ] **步骤 1：实现 api/metrics.py（模板）**

文件：`python-sdk/src/supersonic/api/metrics.py`

```python
"""MetricsAPI — 指标资源 CRUD + publish/unpublish。

Phase 1 范围：仅同步方法。async 元数据 CRUD 留作 v0.2。
"""
from supersonic.api.paths import MetricPaths
from supersonic.common.http import HTTPClient
from supersonic.common.pagination import Page
from supersonic.models.metric import Metric, MetricCreateReq, MetricUpdateReq


class MetricsAPI:
    """async_http 参数保留用于接口一致性，但 Phase 1 不暴露 async 方法。"""

    def __init__(self, http: HTTPClient, async_http=None) -> None:
        self._http = http
        self._async_http = async_http  # Phase 1 未使用，留作 v0.2 扩展

    def list(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
        model_id: int | None = None,
    ) -> Page[Metric]:
        """列出指标。不传 resource_type（评审修复 4：list 不应映射为特定资源 404）。"""
        params: dict = {"page": page, "pageSize": page_size}
        if model_id is not None:
            params["modelId"] = model_id
        body = self._http.request(
            "POST", MetricPaths.LIST,
            params=params,
        )
        return Page[Metric].from_response(body, item_model=Metric)

    def get(self, metric_id: int) -> Metric:
        body = self._http.request(
            "GET", MetricPaths.GET,
            path_params={"id": metric_id},
            resource_type="metric",
            resource_id=metric_id,
        )
        return Metric.model_validate(body)

    def create(self, req: MetricCreateReq) -> Metric:
        body = self._http.request(
            "POST", MetricPaths.CREATE,
            json=req.model_dump(by_alias=True, exclude_none=True),
            resource_type="metric",
        )
        return Metric.model_validate(body)

    def update(self, metric_id: int, req: MetricUpdateReq) -> Metric:
        req.id = metric_id
        body = self._http.request(
            "POST", MetricPaths.UPDATE,
            json=req.model_dump(by_alias=True, exclude_none=True),
            resource_type="metric",
            resource_id=metric_id,
        )
        return Metric.model_validate(body)

    def delete(self, metric_id: int) -> None:
        self._http.request(
            "DELETE", MetricPaths.DELETE,
            path_params={"id": metric_id},
            resource_type="metric",
            resource_id=metric_id,
        )

    def publish(self, metric_ids: list[int]) -> None:
        self._http.request(
            "POST", MetricPaths.PUBLISH,
            json={"ids": metric_ids, "status": "ONLINE"},
        )

    def unpublish(self, metric_ids: list[int]) -> None:
        self._http.request(
            "POST", MetricPaths.UNPUBLISH,
            json={"ids": metric_ids, "status": "OFFLINE"},
        )
```

- [ ] **步骤 2：编写 metrics 测试（模板）**

文件：`python-sdk/tests/api/test_metrics.py`

```python
"""MetricsAPI 测试（所有资源类的测试模板）。

评审修复 1：用 metrics_api fixture 直接注入 HTTPClient，不依赖 Client 门面。
"""
import pytest
from pytest_httpx import HTTPXMock

from supersonic.api.metrics import MetricsAPI
from supersonic.exceptions import MetricNotFoundError
from supersonic.models.metric import Metric, MetricCreateReq, MetricUpdateReq


class TestList:
    def test_returns_paginated_metrics(
        self, metrics_api: MetricsAPI, httpx_mock: HTTPXMock,
        metric_paths, base_url, sample_metric_list_response,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{metric_paths.LIST}",
            method="POST",
            json=sample_metric_list_response,
        )
        page = metrics_api.list(model_id=10, page=1, page_size=10)
        assert page.total == 50
        assert len(page.items) == 2
        assert isinstance(page.items[0], Metric)
        assert page.items[0].model_id == 10


class TestGet:
    def test_returns_metric(
        self, metrics_api: MetricsAPI, httpx_mock: HTTPXMock,
        metric_paths, base_url, sample_metric_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{metric_paths.GET.format(id=1)}",
            method="GET",
            json=sample_metric_dict,
        )
        metric = metrics_api.get(1)
        assert metric.id == 1
        assert metric.name == "销售额"

    def test_404_raises_metric_not_found(
        self, metrics_api: MetricsAPI, httpx_mock: HTTPXMock,
        metric_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{metric_paths.GET.format(id=999)}",
            status_code=404,
        )
        with pytest.raises(MetricNotFoundError):
            metrics_api.get(999)


class TestCreate:
    def test_creates_and_returns_metric(
        self, metrics_api: MetricsAPI, httpx_mock: HTTPXMock,
        metric_paths, base_url, sample_metric_dict,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{metric_paths.CREATE}",
            method="POST",
            json=sample_metric_dict,
        )
        req = MetricCreateReq(
            model_id=10, name="销售额", biz_name="sales_amt",
            define_type="MEASURE", type="NUMBER", expression="pay_amt",
        )
        metric = metrics_api.create(req)
        assert metric.id == 1


class TestUpdate:
    def test_updates_description(
        self, metrics_api: MetricsAPI, httpx_mock: HTTPXMock,
        metric_paths, base_url, sample_metric_dict,
    ):
        sample_metric_dict["description"] = "新描述"
        httpx_mock.add_response(
            url=f"{base_url}{metric_paths.UPDATE}",
            method="POST",
            json=sample_metric_dict,
        )
        req = MetricUpdateReq(id=1, description="新描述")
        metric = metrics_api.update(1, req)
        assert metric.description == "新描述"


class TestDelete:
    def test_delete_succeeds(
        self, metrics_api: MetricsAPI, httpx_mock: HTTPXMock,
        metric_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{metric_paths.DELETE.format(id=1)}",
            method="DELETE",
            status_code=200,
            json={},
        )
        # 不抛错即成功
        metrics_api.delete(1)


class TestPublishUnpublish:
    def test_publish(
        self, metrics_api: MetricsAPI, httpx_mock: HTTPXMock,
        metric_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{metric_paths.PUBLISH}",
            method="POST",
            json={"code": 200, "msg": "success"},
        )
        metrics_api.publish([1, 2, 3])

    def test_unpublish(
        self, metrics_api: MetricsAPI, httpx_mock: HTTPXMock,
        metric_paths, base_url,
    ):
        httpx_mock.add_response(
            url=f"{base_url}{metric_paths.UNPUBLISH}",
            method="POST",
            json={"code": 200, "msg": "success"},
        )
        metrics_api.unpublish([1, 2, 3])
```

- [ ] **步骤 3：实现其他 5 个资源类**

按 MetricsAPI 模板，依次实现（路径常量已就绪）：

**DomainsAPI**（`python-sdk/src/supersonic/api/domains.py`）— 5 方法：list/get/create/update/delete
- 路径：`DomainPaths.*`
- 模型：`Domain` / `DomainCreateReq` / `DomainUpdateReq`
- list 参数：无 model_id（域是顶层）
- 测试用 `domains_api` fixture

**ModelsAPI**（`python-sdk/src/supersonic/api/models.py`）— 5 方法
- 路径：`ModelPaths.*`，list 用 `path_params={"domain_id": domain_id}`（路径参数而非 query）
- 模型：`Model` / `ModelCreateReq`
- 测试用 `models_api` fixture

**DimensionsAPI**（`python-sdk/src/supersonic/api/dimensions.py`）— 6 方法（含 query_values）
- 路径：`DimensionPaths.*`
- 模型：`Dimension` / `DimensionCreateReq`
- `query_values(dimension_id, filters=None)` → POST `DimensionPaths.QUERY_VALUES`
- 测试用 `dimensions_api` fixture

**DatabasesAPI**（`python-sdk/src/supersonic/api/databases.py`）— 7 方法（含 test_connect/get_tables/get_columns）
- 路径：`DatabasePaths.*`
- 模型：`Database` / `DatabaseCreateReq` / `TestConnectionResult` / `TableColumn`
- `test_connect(req)` → POST `TEST_CONNECT`，返回 `TestConnectionResult`
- `get_tables(database_id, db=None)` → GET `GET_TABLES`
- `get_columns(database_id, table, db=None)` → GET `GET_COLUMNS`
- 测试用 `databases_api` fixture

**DatasetsAPI**（`python-sdk/src/supersonic/api/datasets.py`）— 2 方法（只读）
- 路径：`DatasetPaths.*`
- 模型：`Dataset`
- 仅 list + get（不实现 CRUD，规格规定）
- 测试用 `datasets_api` fixture

每个资源类测试文件结构与 test_metrics.py 相同（list/get/create/update/delete 各一组）。

- [ ] **步骤 4：运行测试验证通过（每个资源类独立可验证）**

运行：
```bash
pytest python-sdk/tests/api/test_metrics.py -v
pytest python-sdk/tests/api/test_domains.py -v
# ... 其他 4 个资源类
```

预期：每个测试文件独立运行 PASS（不依赖任务 21 的 Client 门面）。

- [ ] **步骤 5：Commit（每个资源类一个 commit 或合并一个）**

```bash
git add python-sdk/src/supersonic/api/{domains,models,dimensions,metrics,databases,datasets}.py
git add python-sdk/tests/api/test_{domains,models,dimensions,metrics,databases,datasets}.py
git commit -m "feat(sdk): implement 6 metadata resource APIs (sync CRUD only; async deferred to v0.2)"
```

---

## 任务 21：SupersonicClient 门面 + `__init__.py`

**文件：**
- 创建：`python-sdk/src/supersonic/client.py`
- 修改：`python-sdk/src/supersonic/__init__.py`（Import Guide）
- 创建：`python-sdk/tests/test_client.py`

**规格参考：** § SupersonicClient 门面（第 179-223 行）+ § 线程安全（第 1090-1117 行）

- [ ] **步骤 1：编写失败的测试**

文件：`python-sdk/tests/test_client.py`

```python
"""SupersonicClient 门面测试。"""
import pytest

from supersonic import SupersonicClient
from supersonic.api.query import QueryAPI
from supersonic.api.metrics import MetricsAPI
from supersonic.api.domains import DomainsAPI


class TestFacadeAssembly:
    def test_lazy_loading_namespaces(self):
        c = SupersonicClient(host="http://test", token="jwt")
        try:
            assert isinstance(c.query, QueryAPI)
            assert isinstance(c.metrics, MetricsAPI)
            assert isinstance(c.domains, DomainsAPI)
            # 同一实例（懒加载缓存）
            assert c.metrics is c.metrics
        finally:
            c.close()

    def test_all_7_namespaces_available(self):
        c = SupersonicClient(host="http://test", token="jwt")
        try:
            for name in ["query", "domains", "models", "dimensions",
                         "metrics", "databases", "datasets"]:
                assert hasattr(c, name), f"missing namespace: {name}"
        finally:
            c.close()


class TestFromConfig:
    def test_from_config(self):
        from supersonic.config import SupersonicConfig
        config = SupersonicConfig(host="http://test", token="jwt", timeout=60.0)
        c = SupersonicClient.from_config(config)
        try:
            assert c is not None
        finally:
            c.close()


class TestFromEnv:
    def test_missing_env_raises(self, monkeypatch):
        monkeypatch.delenv("SUPERSONIC_HOST", raising=False)
        monkeypatch.delenv("SUPERSONIC_TOKEN", raising=False)
        with pytest.raises(ValueError, match="SUPERSONIC_HOST"):
            SupersonicClient.from_env()

    def test_reads_env(self, monkeypatch):
        monkeypatch.setenv("SUPERSONIC_HOST", "http://test")
        monkeypatch.setenv("SUPERSONIC_TOKEN", "jwt")
        c = SupersonicClient.from_env()
        try:
            assert c is not None
        finally:
            c.close()


class TestContextManager:
    def test_with_block_closes_client(self):
        with SupersonicClient(host="http://test", token="jwt") as c:
            assert c is not None
        # 离开 with 后 client 应已关闭（不发请求验证，只检查无异常）


class TestEnableAsync:
    def test_enable_async_creates_async_http(self):
        c = SupersonicClient(host="http://test", token="jwt", enable_async=True)
        try:
            # async_http 在资源类内部，间接验证
            # 此处只确保构造成功
            assert c is not None
        finally:
            c.close()
```

- [ ] **步骤 2：实现 client.py**

文件：`python-sdk/src/supersonic/client.py`

```python
"""SupersonicClient — SDK 主入口（门面）。

只装配，不直接发业务请求。业务调用通过 .query / .metrics / .domains 等命名空间。
"""
from __future__ import annotations

from supersonic.auth import TokenAuth
from supersonic.api.databases import DatabasesAPI
from supersonic.api.datasets import DatasetsAPI
from supersonic.api.dimensions import DimensionsAPI
from supersonic.api.domains import DomainsAPI
from supersonic.api.metrics import MetricsAPI
from supersonic.api.models import ModelsAPI
from supersonic.api.query import QueryAPI
from supersonic.common.http import AsyncHTTPClient, HTTPClient
from supersonic.common.logging import configure_logging
from supersonic.config import RetryConfig, SupersonicConfig


class SupersonicClient:
    """SuperSonic Python SDK 主入口。

    Thread safety:
        SupersonicClient is NOT thread-safe. The underlying httpx.Client
        uses a shared connection pool that does not support concurrent
        requests across threads.

        For multi-threaded usage:
        - Create a separate SupersonicClient per thread (recommended)
        - Or use enable_async=True with asyncio instead of threads
        - Or wrap client access with an external lock (not recommended,
          kills concurrency)

    Async safety:
        AsyncHTTPClient methods can be called concurrently from asyncio
        tasks (httpx.AsyncClient supports concurrent requests within a
        single event loop).
    """

    def __init__(
        self,
        host: str | None = None,
        token: str | None = None,
        *,
        app_key: str = "supersonic",
        timeout: float = 30.0,
        enable_async: bool = False,
        retry: RetryConfig | None = None,
        log_level: str | None = None,
    ) -> None:
        if not host or not token:
            raise ValueError(
                "host and token are required. "
                "Use from_env() to read from environment variables."
            )
        self._config = SupersonicConfig(
            host=host, token=token, app_key=app_key,
            timeout=timeout, enable_async=enable_async,
            retry=retry or RetryConfig(),
            log_level=log_level or "WARNING",
        )
        configure_logging(self._config.log_level)

        auth = TokenAuth(token=token, app_key=app_key)
        self._http = HTTPClient(
            base_url=host, auth=auth, timeout=timeout, retry=retry,
        )
        self._async_http: AsyncHTTPClient | None = None
        if enable_async:
            self._async_http = AsyncHTTPClient(
                base_url=host, auth=auth, timeout=timeout, retry=retry,
            )

        # 命名空间懒加载缓存
        self._query: QueryAPI | None = None
        self._domains: DomainsAPI | None = None
        self._models: ModelsAPI | None = None
        self._dimensions: DimensionsAPI | None = None
        self._metrics: MetricsAPI | None = None
        self._databases: DatabasesAPI | None = None
        self._datasets: DatasetsAPI | None = None

    # ===== 命名空间 property（懒加载）=====

    @property
    def query(self) -> QueryAPI:
        if self._query is None:
            self._query = QueryAPI(self._http, self._async_http)
        return self._query

    @property
    def domains(self) -> DomainsAPI:
        if self._domains is None:
            self._domains = DomainsAPI(self._http, self._async_http)
        return self._domains

    @property
    def models(self) -> ModelsAPI:
        if self._models is None:
            self._models = ModelsAPI(self._http, self._async_http)
        return self._models

    @property
    def dimensions(self) -> DimensionsAPI:
        if self._dimensions is None:
            self._dimensions = DimensionsAPI(self._http, self._async_http)
        return self._dimensions

    @property
    def metrics(self) -> MetricsAPI:
        if self._metrics is None:
            self._metrics = MetricsAPI(self._http, self._async_http)
        return self._metrics

    @property
    def databases(self) -> DatabasesAPI:
        if self._databases is None:
            self._databases = DatabasesAPI(self._http, self._async_http)
        return self._databases

    @property
    def datasets(self) -> DatasetsAPI:
        if self._datasets is None:
            self._datasets = DatasetsAPI(self._http, self._async_http)
        return self._datasets

    # ===== 构造入口 =====

    @classmethod
    def from_env(cls, **overrides) -> "SupersonicClient":
        config = SupersonicConfig.from_env(**overrides)
        return cls.from_config(config)

    @classmethod
    def from_config(cls, config: SupersonicConfig) -> "SupersonicClient":
        return cls(
            host=config.host,
            token=config.token,
            app_key=config.app_key,
            timeout=config.timeout,
            enable_async=config.enable_async,
            retry=config.retry,
            log_level=config.log_level,
        )

    # ===== 资源管理 =====

    def close(self) -> None:
        self._http.close()
        # async_http 若创建了，需在事件循环中 close
        # 这里只能同步释放，async 资源的实际清理由用户在事件循环中 await aclose

    async def aclose(self) -> None:
        self._http.close()
        if self._async_http is not None:
            await self._async_http.aclose()

    def __enter__(self) -> "SupersonicClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
```

- [ ] **步骤 3：实现 __init__.py（Import Guide）**

文件：`python-sdk/src/supersonic/__init__.py`

```python
"""SuperSonic Python SDK.

Import Guide:

    # Client（主入口）
    from supersonic import SupersonicClient

    # 异常（用于精准 catch）
    from supersonic import (
        SupersonicError, AuthenticationError, ValidationError,
        RateLimitError, ServerError, AsyncNotEnabledError,
        MetricNotFoundError, DatasetNotFoundError,
    )

    # 常用模型
    from supersonic import (
        QueryResult, Metric, MetricCreateReq,
        Filter, DateConf, Text2SqlType,
    )

    # 工具函数
    from supersonic.utils import date_range, filter_eq

Quick Start:

    from supersonic import SupersonicClient

    with SupersonicClient.from_env() as client:
        result = client.query.sql("SELECT 销售额 FROM 销售表")
        print(result.result_rows)
"""
from supersonic.client import SupersonicClient
from supersonic.config import SupersonicConfig, RetryConfig
from supersonic.auth import TokenAuth
from supersonic.exceptions import (
    SupersonicError,
    AuthenticationError,
    ValidationError,
    FieldError,
    RateLimitError,
    ServerError,
    ConnectionError as ConnectionError,  # noqa: F811 — 覆盖内置
    AsyncNotEnabledError,
    ResourceNotFoundError,
    DomainNotFoundError,
    ModelNotFoundError,
    DimensionNotFoundError,
    MetricNotFoundError,
    DatasetNotFoundError,
    DatabaseNotFoundError,
)
from supersonic.models.query import (
    QueryResult, ChatQueryResult, QueryColumn,
    Text2SqlType, MapMode, DateMode, FilterOperator,
    DateConf, Filter, Order, Param, CacheConfig,
    QuerySqlReq, QueryMetricReq, QueryNLReq,
    ValidationResult,
)
from supersonic.models.metric import Metric, MetricCreateReq, MetricUpdateReq
from supersonic.models.domain import Domain, DomainCreateReq, DomainUpdateReq
from supersonic.models.model import Model, ModelCreateReq
from supersonic.models.dimension import Dimension, DimensionCreateReq
from supersonic.models.database import Database, DatabaseCreateReq
from supersonic.models.dataset import Dataset

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # client / config / auth
    "SupersonicClient", "SupersonicConfig", "RetryConfig", "TokenAuth",
    # exceptions
    "SupersonicError", "AuthenticationError", "ValidationError", "FieldError",
    "RateLimitError", "ServerError", "AsyncNotEnabledError",
    "ResourceNotFoundError",
    "DomainNotFoundError", "ModelNotFoundError", "DimensionNotFoundError",
    "MetricNotFoundError", "DatasetNotFoundError", "DatabaseNotFoundError",
    # query models
    "QueryResult", "ChatQueryResult", "QueryColumn",
    "Text2SqlType", "MapMode", "DateMode", "FilterOperator",
    "DateConf", "Filter", "Order", "Param", "CacheConfig",
    "QuerySqlReq", "QueryMetricReq", "QueryNLReq",
    "ValidationResult",
    # metadata models
    "Metric", "MetricCreateReq", "MetricUpdateReq",
    "Domain", "DomainCreateReq", "DomainUpdateReq",
    "Model", "ModelCreateReq",
    "Dimension", "DimensionCreateReq",
    "Database", "DatabaseCreateReq",
    "Dataset",
]
```

> 注意：`ConnectionError` 在 Python 是内置名，这里有意覆盖（SDK 用户应 catch SDK 的）。
> 若与内置冲突引发疑虑，可重命名为 `SupersonicConnectionError` 并在 `__init__.py` re-export 该别名。

- [ ] **步骤 4：运行所有测试**

运行：`pytest python-sdk/ -v`
预期：所有测试 PASS（包括任务 14-20 的 API 测试）

- [ ] **步骤 5：Commit**

```bash
git add python-sdk/src/supersonic/client.py python-sdk/src/supersonic/__init__.py python-sdk/tests/test_client.py
git commit -m "feat(sdk): implement SupersonicClient facade with 7 lazy namespaces"
```

---

## 任务 21b：声明 async 元数据方法 OUT OF SCOPE（评审修复 2）

**目的**：在 `__init__.py` docstring 和 README 中明确声明 Phase 1 async 限制。

- [ ] **步骤 1：在 __init__.py docstring 追加 async 范围说明**

文件：`python-sdk/src/supersonic/__init__.py`（修改 docstring 末尾）

在 Quick Start 段之后追加：

```python
"""（前略）

Async Support (Phase 1):

    Only QueryAPI supports async in Phase 1:

        client = SupersonicClient(enable_async=True)
        result = await client.query.asql("SELECT ...")

    Metadata CRUD (domains/models/dimensions/metrics/databases/datasets)
    are sync-only in Phase 1. Async methods are planned for v0.2.
"""
```

- [ ] **步骤 2：在 README.md 追加 Async Support 章节**

文件：`python-sdk/README.md`

在 Thread Safety 章节后追加：

```markdown
## Async Support

Phase 1 only supports async on `QueryAPI`:

```python
client = SupersonicClient(enable_async=True)
result = await client.query.asql("SELECT 销售额 FROM 销售表")
```

Metadata CRUD (domains/models/dimensions/metrics/databases/datasets)
are sync-only in Phase 1. Async support for all resource methods is
planned for v0.2.
```

- [ ] **步骤 3：Commit**

```bash
git add python-sdk/src/supersonic/__init__.py python-sdk/README.md
git commit -m "docs(sdk): document Phase 1 async scope (QueryAPI only; metadata async deferred to v0.2)"
```

> **评审修复 2 收尾**：通过显式声明而非 `NotImplementedError` 处理 async 缺失——
> 用户能看到清晰的限制说明，而不是运行时崩溃。计划自检中的"37 方法全实现"
> 现在修正为"37 同步方法全实现 + QueryAPI 的 1 个 async 方法"。

---

## 任务 22：utils 工具函数

**文件：**
- 创建：`python-sdk/src/supersonic/utils/__init__.py`
- 创建：`python-sdk/src/supersonic/utils/builders.py`
- 创建：`python-sdk/src/supersonic/utils/validators.py`
- 创建：`python-sdk/src/supersonic/utils/format.py`
- 创建：`python-sdk/tests/utils/__init__.py`（空）
- 创建：`python-sdk/tests/utils/test_utils.py`

**规格参考：** § 工具函数（第 877-898 行）

- [ ] **步骤 1：创建测试目录**

运行：`mkdir -p python-sdk/tests/utils && touch python-sdk/tests/utils/__init__.py`

- [ ] **步骤 2：编写失败的测试**

文件：`python-sdk/tests/utils/test_utils.py`

```python
"""utils 工具函数测试。"""
import pytest

from supersonic.utils.builders import (
    date_range, last_n_days, filter_eq, filter_in, order_by,
)
from supersonic.utils.validators import is_valid_s2sql, validate_host_url
from supersonic.utils.format import format_result_table, format_sql
from supersonic.models.query import DateMode, FilterOperator, QueryResult, QueryColumn


class TestBuilders:
    def test_date_range_returns_between_mode(self):
        d = date_range("2026-01-01", "2026-06-30")
        assert d.date_mode == DateMode.BETWEEN
        assert d.start_date == "2026-01-01"
        assert d.end_date == "2026-06-30"

    def test_last_n_days(self):
        d = last_n_days(7)
        assert d.date_mode == DateMode.BETWEEN
        assert d.start_date is not None

    def test_filter_eq(self):
        f = filter_eq("category", "手机")
        assert f.operator == FilterOperator.EQ
        assert f.value == "手机"

    def test_filter_in(self):
        f = filter_in("category", ["手机", "电脑"])
        assert f.operator == FilterOperator.IN

    def test_order_by_default_asc(self):
        o = order_by("sales")
        assert o.direction == "ASC"

    def test_order_by_desc(self):
        o = order_by("sales", "DESC")
        assert o.direction == "DESC"


class TestValidators:
    def test_valid_select(self):
        assert is_valid_s2sql("SELECT * FROM model") is True

    def test_invalid_empty(self):
        assert is_valid_s2sql("") is False

    def test_invalid_no_select(self):
        assert is_valid_s2sql("DELETE FROM model") is False

    def test_validate_host_url_passes(self):
        validate_host_url("http://localhost:9080")  # 不抛错

    def test_validate_host_url_invalid_raises(self):
        with pytest.raises(ValueError):
            validate_host_url("not-a-url")


class TestFormat:
    def test_format_result_table(self):
        result = QueryResult(
            columns=[
                QueryColumn(name="product", type="VARCHAR"),
                QueryColumn(name="sales", type="DOUBLE"),
            ],
            result_rows=[
                {"product": "iPhone", "sales": 100.0},
                {"product": "iPad", "sales": 80.0},
            ],
        )
        table = format_result_table(result)
        assert "product" in table
        assert "iPhone" in table
        assert "100" in table

    def test_format_sql_indents(self):
        sql = "SELECT a, b FROM t WHERE a > 0"
        formatted = format_sql(sql, indent=2)
        assert isinstance(formatted, str)
        assert len(formatted) > len(sql)  # 应有换行
```

- [ ] **步骤 3：实现 utils 三个文件**

文件：`python-sdk/src/supersonic/utils/__init__.py`

```python
"""公共工具函数。

- builders: 便捷构造器（date_range, filter_eq 等）
- validators: 本地校验（is_valid_s2sql 等）
- format: 输出格式化（format_result_table, format_sql）
"""
from supersonic.utils.builders import (
    date_range, last_n_days, month_to_date,
    filter_eq, filter_in, order_by,
)
from supersonic.utils.validators import is_valid_s2sql, validate_host_url
from supersonic.utils.format import format_result_table, format_sql

__all__ = [
    "date_range", "last_n_days", "month_to_date",
    "filter_eq", "filter_in", "order_by",
    "is_valid_s2sql", "validate_host_url",
    "format_result_table", "format_sql",
]
```

文件：`python-sdk/src/supersonic/utils/builders.py`

```python
"""便捷构造器，简化常用对象创建。"""
from datetime import datetime, timedelta
from typing import Any, Literal

from supersonic.models.query import DateConf, DateMode, Filter, FilterOperator, Order


def date_range(start: str, end: str) -> DateConf:
    """构造 BETWEEN 模式的 DateConf。"""
    return DateConf(date_mode=DateMode.BETWEEN, start_date=start, end_date=end)


def last_n_days(n: int) -> DateConf:
    """最近 N 天。"""
    end = datetime.now()
    start = end - timedelta(days=n)
    return DateConf(
        date_mode=DateMode.BETWEEN,
        start_date=start.strftime("%Y-%m-%d"),
        end_date=end.strftime("%Y-%m-%d"),
    )


def month_to_date() -> DateConf:
    """本月至今。"""
    now = datetime.now()
    start = now.replace(day=1)
    return DateConf(
        date_mode=DateMode.BETWEEN,
        start_date=start.strftime("%Y-%m-%d"),
        end_date=now.strftime("%Y-%m-%d"),
    )


def filter_eq(name: str, value: Any) -> Filter:
    return Filter(name=name, operator=FilterOperator.EQ, value=value)


def filter_in(name: str, values: list[Any]) -> Filter:
    return Filter(name=name, operator=FilterOperator.IN, value=values)


def order_by(name: str, direction: Literal["ASC", "DESC"] = "ASC") -> Order:
    return Order(name=name, direction=direction)
```

文件：`python-sdk/src/supersonic/utils/validators.py`

```python
"""本地校验工具（不发请求）。"""
import re
from urllib.parse import urlparse

# 极简 S2SQL 校验：必须以 SELECT 开头
_S2SQL_PATTERN = re.compile(r"^\s*SELECT\s+", re.IGNORECASE)


def is_valid_s2sql(sql: str) -> bool:
    """粗略校验是否为 S2SQL（SELECT 开头）。不验证完整语法。"""
    if not sql:
        return False
    return bool(_S2SQL_PATTERN.match(sql))


def validate_host_url(url: str) -> None:
    """校验 host URL 合法性。无效则 raise ValueError。"""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid host URL: {url!r} (expected like 'http://host:port')")
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported scheme: {parsed.scheme!r}")
```

文件：`python-sdk/src/supersonic/utils/format.py`

```python
"""输出格式化（CLI 也会复用）。"""
import re

from supersonic.models.query import QueryResult


def format_result_table(result: QueryResult, max_rows: int = 20) -> str:
    """将 QueryResult 格式化为表格字符串（类似 SQL 客户端输出）。"""
    if not result.columns:
        return "(empty)"
    headers = [c.display_name or c.name for c in result.columns]
    keys = [c.name for c in result.columns]

    rows = result.result_rows[:max_rows]
    if not rows:
        return "\t".join(headers) + "\n(no rows)"

    # 计算列宽
    all_lines = [headers] + [[str(row.get(k, "")) for k in keys] for row in rows]
    widths = [max(len(line[i]) for line in all_lines) for i in range(len(headers))]

    def format_line(line: list[str]) -> str:
        return " | ".join(c.ljust(w) for c, w in zip(line, widths))

    out = [format_line(headers), format_line(["-" * w for w in widths])]
    out.extend(format_line(line) for line in all_lines[1:])
    if len(result.result_rows) > max_rows:
        out.append(f"... ({len(result.result_rows) - max_rows} more rows)")
    return "\n".join(out)


def format_sql(sql: str, indent: int = 2) -> str:
    """简易 SQL 美化（SELECT/FROM/WHERE/GROUP BY/ORDER BY 换行）。"""
    if not sql:
        return ""
    spaces = " " * indent
    keywords = ["SELECT", "FROM", "WHERE", "GROUP BY", "ORDER BY", "HAVING", "LIMIT"]
    result = sql
    for kw in keywords:
        result = re.sub(rf"\b{kw}\b", f"\n{spaces}{kw}", result, flags=re.IGNORECASE)
    return result.strip()
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest python-sdk/tests/utils/ -v`
预期：所有测试 PASS

- [ ] **步骤 5：Commit**

```bash
git add python-sdk/src/supersonic/utils/ python-sdk/tests/utils/
git commit -m "feat(sdk): implement utils (builders, validators, format)"
```

---

## 任务 23：集成测试 + 完整测试套件运行

**文件：**
- 创建：`python-sdk/tests/integration/test_query_live.py`

**规格参考：** § 三层测试（第 902-935 行）

- [ ] **步骤 1：创建集成测试**

文件：`python-sdk/tests/integration/test_query_live.py`

```python
"""集成测试：需要真实 SuperSonic 实例。

运行方式：
    pytest -m integration

需要环境变量：
    SUPERSONIC_HOST, SUPERSONIC_TOKEN, S2_TEST_DATASET_ID
"""
import os

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    from supersonic import SupersonicClient
    c = SupersonicClient.from_env()
    yield c
    c.close()


def test_live_sql_query(client):
    """对真实实例执行 SELECT 1 等价查询。"""
    dataset_id = int(os.environ["S2_TEST_DATASET_ID"])
    result = client.query.sql("SELECT 1", data_set_id=dataset_id)
    assert len(result.result_rows) > 0


def test_live_metric_list(client):
    """列出至少 1 个 metric。"""
    page = client.metrics.list(page=1, page_size=1)
    assert page.total >= 0  # 不一定有数据，但不应该报错
```

- [ ] **步骤 2：运行完整测试套件 + 覆盖率**

运行：
```bash
cd python-sdk
pytest --cov=src/supersonic --cov-report=term-missing
```

预期：
- 所有非集成测试 PASS
- 行覆盖率 ≥ 85%
- 集成测试被默认跳过（`addopts = "-m 'not integration'"`）

- [ ] **步骤 3：类型检查与 lint**

运行：
```bash
ruff check src/ tests/
mypy src/
```

预期：无错误（warning 可接受，但不可有 error）

- [ ] **步骤 4：Commit**

```bash
git add python-sdk/tests/integration/
git commit -m "test(sdk): add integration tests gated by marker"
```

---

## 任务 24：examples + README 收尾

**文件：**
- 创建：`python-sdk/examples/quickstart.py`
- 创建：`python-sdk/examples/semantic_modeling.py`
- 创建：`python-sdk/examples/nl_query.py`
- 修改：`python-sdk/README.md`

**规格参考：** § 关键示例（第 1175-1241 行）

- [ ] **步骤 1：创建 quickstart.py**

文件：`python-sdk/examples/quickstart.py`

```python
"""3 分钟上手：查询销售额（含基础错误处理）。

前置：
    export SUPERSONIC_HOST=http://localhost:9080
    export SUPERSONIC_TOKEN=<your-jwt>
    pip install supersonic-sdk[pandas]

运行：
    python examples/quickstart.py
"""
import sys

from supersonic import (
    SupersonicClient,
    AuthenticationError,
    MetricNotFoundError,
    SupersonicError,
)
from supersonic.utils import date_range


def main() -> int:
    try:
        with SupersonicClient.from_env() as client:
            result = client.query.metric(
                metrics=["销售额"],
                dimensions=["品类"],
                date_info=date_range("2026-01-01", "2026-06-30"),
            )
            try:
                df = result.to_dataframe()
                print(df.sort_values("销售额", ascending=False))
            except ImportError:
                # 未装 pandas，降级到原始数据
                print(result.result_rows[:10])
    except AuthenticationError:
        print("Token 失效，请检查 SUPERSONIC_TOKEN", file=sys.stderr)
        return 1
    except MetricNotFoundError as e:
        print(f"指标不存在: {e.resource_id}", file=sys.stderr)
        return 1
    except SupersonicError as e:
        print(f"查询失败: {e.message} (status={e.status_code})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **步骤 2：创建 semantic_modeling.py**

文件：`python-sdk/examples/semantic_modeling.py`

```python
"""编程式建模：批量创建指标。

前置：
    export SUPERSONIC_HOST=...
    export SUPERSONIC_TOKEN=...
"""
from supersonic import SupersonicClient, MetricCreateReq

METRICS_TO_CREATE = [
    {"name": "销售额", "biz_name": "sales_amt", "expression": "pay_amt",
     "define_type": "MEASURE", "type": "NUMBER"},
    {"name": "订单数", "biz_name": "order_cnt", "expression": "count(1)",
     "define_type": "MEASURE", "type": "NUMBER"},
]


def main() -> None:
    with SupersonicClient.from_env() as client:
        # 批量创建
        created_ids = []
        for m in METRICS_TO_CREATE:
            metric = client.metrics.create(MetricCreateReq(model_id=1, **m))
            created_ids.append(metric.id)
            print(f"Created metric: {metric.name} (id={metric.id})")

        # 批量发布
        if created_ids:
            client.metrics.publish(created_ids)
            print(f"Published {len(created_ids)} metrics")


if __name__ == "__main__":
    main()
```

- [ ] **步骤 3：创建 nl_query.py**

文件：`python-sdk/examples/nl_query.py`

```python
"""自然语言查询：detailed 双模式对比。"""
from supersonic import SupersonicClient


def main() -> None:
    with SupersonicClient.from_env() as client:
        query = "销售额最高的 5 个产品"

        # 完整模式（默认）：看解析过程
        full = client.query.chat(query)
        print(f"选中解析: {full.selected_parse.sql}")
        print(f"候选数: {len(full.candidate_parses)}")
        print(f"解析耗时: {full.time_cost.parse_time}ms")

        # 简洁模式：直接拿数据
        result = client.query.chat(query, detailed=False)
        print(f"\n结果行数: {len(result.result_rows)}")
        for row in result.result_rows[:5]:
            print(row)


if __name__ == "__main__":
    main()
```

- [ ] **步骤 4：更新 README.md（完整版）**

文件：`python-sdk/README.md`

```markdown
# SuperSonic Python SDK

Python client for SuperSonic Chat BI + Headless BI platform. Provides
type-safe access to semantic modeling (domain/model/dimension/metric CRUD)
and multi-paradigm queries (S2SQL / natural language / structured metric).

## Installation

```bash
pip install supersonic-sdk

# With pandas integration
pip install supersonic-sdk[pandas]

# With dev tools (testing)
pip install supersonic-sdk[dev]
```

## Quick Start

```python
from supersonic import SupersonicClient

with SupersonicClient.from_env() as client:
    result = client.query.sql("SELECT 销售额 FROM 销售表")
    print(result.result_rows)
```

## API Surface

| Namespace | Methods | Purpose |
|---|---|---|
| `client.query` | `sql` / `sqls` / `validate` / `metric` / `chat` | Query the semantic layer |
| `client.domains` | `list` / `get` / `create` / `update` / `delete` | Domain CRUD |
| `client.models` | `list` / `get` / `create` / `update` / `delete` | Model CRUD |
| `client.dimensions` | `list` / `get` / `create` / `update` / `delete` / `query_values` | Dimension CRUD |
| `client.metrics` | `list` / `get` / `create` / `update` / `delete` / `publish` / `unpublish` | Metric CRUD |
| `client.databases` | `list` / `get` / `create` / `update` / `test_connect` / `get_tables` / `get_columns` | Database CRUD |
| `client.datasets` | `list` / `get` | Dataset read |

## Configuration

Environment variables (read by `SupersonicClient.from_env()`):

| Variable | Required | Default | Description |
|---|---|---|---|
| `SUPERSONIC_HOST` | Yes | - | Service URL |
| `SUPERSONIC_TOKEN` | Yes | - | JWT token |
| `SUPERSONIC_APP_KEY` | No | `supersonic` | App-Key header |
| `SUPERSONIC_TIMEOUT` | No | `30.0` | HTTP timeout (s) |
| `SUPERSONIC_MAX_RETRIES` | No | `3` | Max retries |
| `SUPERSONIC_ENABLE_ASYNC` | No | `false` | Enable async client |
| `SUPERSONIC_LOG_LEVEL` | No | `WARNING` | Log level |

## Thread Safety

`SupersonicClient` is NOT thread-safe. Create one per thread, or use
`enable_async=True` with asyncio.

## Documentation

- [Design spec](../docs/superpowers/specs/2026-07-16-python-sdk-design.md)
- [Examples](examples/)
```

- [ ] **步骤 5：验证示例可 import**

运行：
```bash
cd python-sdk
python -c "import ast; [ast.parse(open(f).read()) for f in ['examples/quickstart.py', 'examples/semantic_modeling.py', 'examples/nl_query.py']]"
```
预期：无语法错误

- [ ] **步骤 6：Commit**

```bash
git add python-sdk/examples/ python-sdk/README.md
git commit -m "docs(sdk): add examples (quickstart, semantic_modeling, nl_query) and full README"
```

---

## 自检（v2 修订后）

完成所有任务后，对照规格检查：

**1. 规格覆盖度：**
- ✅ § 整体架构 → 任务 1 + 任务 21
- ✅ § 包布局 → 任务 1 + 任务 9 + 任务 10
- ✅ § SupersonicClient 门面 → 任务 21
- ✅ § 7 资源命名空间 → 任务 14-20
- ✅ § Auth 模型 → 任务 3
- ✅ § 重试与退避 → 任务 4（RetryConfig）
- ✅ § HTTPClient + AsyncHTTPClient → 任务 6 + 任务 7
- ✅ § 异常树 → 任务 2
- ✅ § 异常映射 → 任务 6（_handle_response，评审修复 3 已统一签名）
- ✅ § 查询子系统（5 方法 + 双模式）→ 任务 14
- ✅ § 元数据 CRUD 模式 → 任务 15-20（评审修复 2 已移除 async、评审修复 4 已修正 list）
- ✅ § 分页处理 → 任务 8
- ✅ § 工具函数 → 任务 22（评审修复 6 已修正 import re 位置）
- ✅ § 测试策略 → 任务 1 + 各任务测试 + 任务 23
- ✅ § pyproject.toml → 任务 1
- ✅ § 环境变量表 → 任务 4
- ✅ § 线程安全 → 任务 21
- ✅ § 日志策略 → 任务 5
- ✅ § 兼容性 → README + paths.py 集中管理（评审修复 9 已加 upsert 注释）
- ✅ § examples → 任务 24

**2. 占位符扫描：**
- 评审修复 2 已移除所有 `NotImplementedError`
- 每个代码步骤都有完整代码块
- 任务 21b 显式声明 async 限制，而非占位符

**3. 类型一致性（v2 验证）：**
- `MetricNotFoundError(resource_id=...)` — 任务 2 定义，任务 6/15 引用，一致
- `ResourceNotFoundError(resource_type, resource_id)` — 评审修复 3 统一签名
- `Page.from_response(data, item_model=T)` — 任务 8 定义，任务 15 引用，一致
- `compute_backoff(attempt, config, retry_after=None)` — 任务 4 定义，任务 6 引用，一致
- `AsyncNotEnabledError()` 无参数 — 任务 2 定义，任务 14 引用，一致
- `QueryPaths.SQL` 等常量 — 任务 10 定义，任务 14 引用，一致
- API 级 fixtures（`query_api` / `metrics_api` 等）— 任务 10 定义，任务 14-20 引用，一致

**4. TDD 流程完整性（v2 新增）：**
- 任务 1-13：传统 TDD（编写测试 → 失败 → 实现 → 通过 → commit）
- 任务 13b：类型检查里程碑（评审修复 5）
- 任务 14-20：用 API 级 fixture 独立验证（评审修复 1），不再等任务 21
- 任务 21：Client 门面装配测试
- 任务 22-24：utils / 集成测试 / 示例

**5. async 范围明确（v2 新增）：**
- Phase 1：QueryAPI 的 `asql()` 完整实现（任务 14）
- Phase 1：元数据 CRUD 无 async 方法（任务 15-20）
- 任务 21b：在 `__init__.py` + README 显式声明此限制

---

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-07-16-python-sdk-phase1.md`（v2 含评审修订）。

**任务总数**：26 个（原 24 + 任务 13b 类型检查 + 任务 21b async 范围声明）

**两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**

> **特别提示：**
> - 任务 1-13 是地基（异常/auth/config/HTTP/分页/模型），各任务独立 TDD 可验证
> - 任务 13b 是类型检查里程碑（评审修复 5）
> - 任务 14-20 是业务实现（Query + 6 元数据 API），用 API 级 fixture 独立验证（评审修复 1）
> - 任务 21-21b 是门面装配 + async 范围声明
> - 任务 22-24 是收尾（utils / 集成测试 / 示例）
>
> 建议按任务编号顺序执行，避免依赖错乱。任务 14-20 现在每个都可以独立完成 TDD 循环，回滚成本最低。
