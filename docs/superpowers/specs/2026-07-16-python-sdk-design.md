# SuperSonic Python SDK — 设计规格

> 三层架构（SDK + CLI + MCP Server）· Phase 1 聚焦 SDK · 对标 open-metadata/ai-sdk 模式

---

## 设计概述

- **目标**：为 SuperSonic 项目构建 Python SDK 客户端，对标 [open-metadata/ai-sdk](https://github.com/open-metadata/ai-sdk) 的设计模式
- **本次范围（Phase 1）**：仅 SDK 核心库，不含 CLI 和 MCP Server
- **完整架构**：三层（SDK → CLI → MCP Server），分阶段实施，每个阶段独立规格
- **简历价值**：完整覆盖"编程式语义建模 + 多范式查询"全闭环，是 headless BI as code 的完整故事
- **技术栈**：Python 3.10+ / httpx / pydantic v2 / hatchling / ruff / pytest-httpx
- **运行时依赖**：核心包仅 2 个（httpx + pydantic），其余走 extras

---

## 背景

### 项目定位

SuperSonic 是腾讯开源的 Chat BI + Headless BI 统一平台。当前对外仅有 Java SDK（通过 `SemanticLayerService` 接口），缺少 Python 生态接入能力。Python 是数据科学、AI Agent、自动化测试的主语言，缺 Python SDK 等于堵死这些场景。

### 参考项目：open-metadata/ai-sdk

- **仓库**：https://github.com/open-metadata/ai-sdk
- **定位**：把 OpenMetadata 元数据平台的能力包装成 LLM Agent 可消费的工具
- **设计模式**（本次借鉴）：
  1. 门面 + 资源命名空间（`AISdk` + `AgentsAPI`/`MemoriesAPI`）
  2. pydantic v2 + 手写 `to_api_dict()` 处理复杂变换
  3. sync 优先 + opt-in async（`enable_async=True`）
  4. 资源特化异常（`AgentNotFoundError` 而非通用 `NotFoundError`）
  5. 模块级 `_paginate` helper，不在每个资源类重复
  6. extras 模式（`pip install data-ai-sdk[langchain]`）
  7. pytest-httpx mock 实现零真实网络单元测试
  8. src layout + hatchling + ruff
  9. `__init__.py` 作 Import Guide（按 use case 分组的 import 清单）
 10. `example.py` 生产级示例（完整可跑 + 反幻觉 prompt + 分层异常 + 资源释放）

### SuperSonic Headless API 现状

- **接口类型**：仅 REST API（无 GraphQL/gRPC/OpenAPI 文档生成）
- **认证**：双 header 鉴权——`Authorization: Bearer <JWT>` + `App-Key: <appKey>`
- **API 入口**（`/api/semantic/*`）：
  - 查询：`/query/sql`、`/query/chat`、`/query/metric`、`/query/validate`、`/query/sqls` 等
  - 元数据管理：domain/model/dimension/metric/database/dataset 的 CRUD
  - 知识库：dict/embedding 管理（运维属性强）
- **响应**：`SemanticQueryResp` 统一结构，含 columns + result_rows + sql + use_cache

---

## 整体架构（三层）

```
┌──────────────────────────────────────────────────┐
│  Phase 3: MCP Server                             │  ← Agent 生态接入
│  (mcp/ 子包，[mcp] extra)                        │     Claude/Cursor 等原生集成
├──────────────────────────────────────────────────┤
│  Phase 2: CLI                                    │  ← 人 + 任意 Agent
│  (cli/ 子包，[cli] extra)                        │     bash 调用，通用接口
├──────────────────────────────────────────────────┤
│  Phase 1 (本次): Python SDK                      │  ← 编程接入
│  - supersonic.SupersonicClient 门面              │     Python 开发者/数据科学家
│  - 7 个资源命名空间                              │
│  - pydantic 模型 + auth + http                   │
├──────────────────────────────────────────────────┤
│  SuperSonic Headless REST API (/api/semantic/*)  │  ← 源
└──────────────────────────────────────────────────┘
```

### 三层分工

| 层 | 服务对象 | 复用范围 | 实施时机 |
|---|---|---|---|
| Python SDK | Python 开发者 / 数据科学家 | Python 生态内 | Phase 1（本规格） |
| CLI | 人类 + 几乎所有 Agent | 跨语言跨框架（任何能 bash 调用的环境） | Phase 2 |
| MCP Server | MCP 协议兼容的 Agent | 标准化 Agent 工具协议 | Phase 3 |

### 依赖关系

- 上层依赖下层（CLI 调用 SDK，MCP Server 调用 SDK）
- Phase 1 的设计需要为 Phase 2/3 预留扩展点：资源类的 public API 必须清晰稳定

---

## Phase 1 详细设计

### 包布局

```
python-sdk/
├── pyproject.toml                    # hatchling，name: supersonic-sdk
├── src/supersonic/
│   ├── __init__.py                   # Import Guide docstring（对标 ai-sdk）
│   ├── py.typed                      # PEP 561 marker
│   │
│   ├── client.py                     # SupersonicClient 门面（公共）
│   ├── auth.py                       # TokenAuth 策略（公共）
│   ├── config.py                     # SupersonicConfig（公共）
│   ├── exceptions.py                 # 异常树（公共）
│   │
│   ├── common/                       # 内部基础设施（不导出公共 API）
│   │   ├── __init__.py               # __all__ = []，标记为内部包
│   │   ├── http.py                   # HTTPClient + AsyncHTTPClient
│   │   ├── pagination.py             # _paginate / _apaginate helper
│   │   └── logging.py                # 统一日志
│   │
│   ├── api/                          # 业务资源（每个资源一个文件）
│   │   ├── __init__.py
│   │   ├── paths.py                  # 端点路径常量集中定义（避免散落字符串）
│   │   ├── query.py                  # QueryAPI（5 方法）
│   │   ├── domains.py                # DomainsAPI（5 方法）
│   │   ├── models.py                 # ModelsAPI（5 方法）
│   │   ├── dimensions.py             # DimensionsAPI（6 方法）
│   │   ├── metrics.py                # MetricsAPI（7 方法）
│   │   ├── databases.py              # DatabasesAPI（7 方法）
│   │   └── datasets.py               # DatasetsAPI（2 方法）
│   │
│   ├── models/                       # pydantic 数据模型（按资源拆分）
│   │   ├── __init__.py               # re-export 全部公共模型
│   │   ├── base.py                   # CamelModel 基类
│   │   ├── query.py                  # QuerySqlReq/QueryResult/ChatQueryResult/...
│   │   ├── domain.py
│   │   ├── model.py
│   │   ├── dimension.py
│   │   ├── metric.py
│   │   ├── database.py
│   │   └── dataset.py
│   │
│   └── utils/                        # 公共工具函数
│       ├── __init__.py
│       ├── builders.py               # date_range / filter_eq / order_by 等便捷构造器
│       ├── validators.py             # is_valid_s2sql / validate_host_url
│       └── format.py                 # format_result_table / format_sql
│
├── tests/
│   ├── conftest.py                   # sample dict fixtures
│   ├── test_client.py
│   ├── test_auth.py
│   ├── test_config.py
│   ├── test_async.py
│   ├── common/                       # 镜像 src/supersonic/common/
│   │   ├── test_http.py
│   │   ├── test_pagination.py
│   │   └── test_logging.py
│   ├── api/                          # 镜像 src/supersonic/api/
│   │   ├── test_query.py
│   │   ├── test_domains.py
│   │   ├── test_models.py
│   │   ├── test_dimensions.py
│   │   ├── test_metrics.py
│   │   ├── test_databases.py
│   │   └── test_datasets.py
│   └── integration/                  # 真 API 调用，需凭据
│       └── test_query_live.py
│
├── examples/
│   ├── quickstart.py                 # 3 行查询示例
│   ├── semantic_modeling.py          # 编程式建模示例
│   └── nl_query.py                   # 自然语言查询示例
│
└── README.md
```

### 目录划分约定

| 位置 | 用途 | 用户能否 import |
|---|---|---|
| 顶级文件（`client.py`/`auth.py`/`config.py`/`exceptions.py`） | 用户最常用的公共 API | 是，`from supersonic import SupersonicClient` |
| `common/` | **内部基础设施**（HTTP client、pagination、logging） | 否，不导出 |
| `api/` | **业务资源命名空间**（按领域拆分） | 是，`from supersonic.api import MetricsAPI` |
| `models/` | **pydantic 数据模型**（按资源拆分） | 是，`from supersonic.models import Metric` |
| `utils/` | **公共工具函数**（builders/validators/format） | 是，`from supersonic.utils import date_range` |

---

### 核心抽象

#### SupersonicClient（门面）

对标 ai-sdk 的 `AISdk`。**只装配，不直接发业务请求**——所有业务调用走资源命名空间。

```python
from supersonic import SupersonicClient

# 1. 直接构造
client = SupersonicClient(
    host="http://localhost:9080",
    token="eyJhbGc...",         # JWT
    app_key="supersonic",       # 默认 "supersonic"
    timeout=30.0,
    enable_async=False,         # opt-in async
    retry=RetryConfig(max_retries=3, retry_delay=1.0),  # 可选，默认值见 RetryConfig
)

# 2. 从环境变量（CI/脚本场景）
client = SupersonicClient.from_env()
# 读 SUPERSONIC_HOST / SUPERSONIC_TOKEN / SUPERSONIC_APP_KEY / SUPERSONIC_TIMEOUT 等

# 3. 从配置对象 + 覆盖
config = SupersonicConfig.from_env(timeout=60.0, enable_async=True)
client = SupersonicClient.from_config(config)

# 资源命名空间（懒加载 property）
client.query          # → QueryAPI
client.domains        # → DomainsAPI
client.models         # → ModelsAPI
client.dimensions     # → DimensionsAPI
client.metrics        # → MetricsAPI
client.databases      # → DatabasesAPI
client.datasets       # → DatasetsAPI

# 上下文管理（自动 close httpx client）
with SupersonicClient.from_env() as client:
    result = client.query.sql("SELECT 销售额 ...")
```

**门面职责**：
- 装配 `HTTPClient` + 可选 `AsyncHTTPClient` + 所有资源命名空间
- 持有 `config` 和 `auth`，注入给资源类
- **不直接发业务请求**——业务调用走资源类
- 支持 `with` 上下文管理（自动释放 httpx 连接）

#### 资源命名空间（以 MetricsAPI 为例）

```python
class MetricsAPI:
    def __init__(self, http: HTTPClient, async_http: AsyncHTTPClient | None):
        self._http = http
        self._async_http = async_http

    # 五件套 + 业务方法
    def list(self, *, page: int = 1, page_size: int = 10,
             model_id: int | None = None) -> Page[Metric]: ...
    def get(self, metric_id: int) -> Metric: ...
    def create(self, req: MetricCreateReq) -> Metric: ...
    def update(self, metric_id: int, req: MetricUpdateReq) -> Metric: ...
    def delete(self, metric_id: int) -> None: ...
    def publish(self, metric_ids: list[int]) -> None: ...
    def unpublish(self, metric_ids: list[int]) -> None: ...

    # async 版本（仅 enable_async=True 时可用）
    async def alist(self, ...) -> Page[Metric]: ...
    async def acreate(self, ...) -> Metric: ...
    # ...
```

**资源类约束**：
- **不持有 host/token**——只持有注入的 HTTP client
- 每个业务方法都有 `a`-前缀 async 版（用 `async_http`，若为 None 则 raise `AsyncNotEnabledError`）
- 分页用模块级 `_paginate` helper（在 `common/pagination.py`），不在类内重复
- 调用 HTTP 时显式传 `resource_type="metric"` 和 `resource_id=metric_id`，让 HTTP 层能抛出正确的资源特化异常

---

### Auth 模型

SuperSonic 用**双 header 认证**（与 ai-sdk 单 Bearer 不同）。

```python
# auth.py
@dataclass
class TokenAuth:
    token: str
    app_key: str = "supersonic"

    def __post_init__(self):
        if not self.token:
            raise ValueError("token cannot be empty")  # fail fast

    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "App-Key": self.app_key,
        }
```

**v0.1 不支持**：token 自动刷新、配置文件（`~/.supersonic/config.toml`）—— 留作 v0.2。

---

### HTTP 层与异常映射

#### 重试与退避参数

所有重试相关参数集中在 `SupersonicConfig`，可通过构造函数或环境变量覆盖：

```python
@dataclass
class RetryConfig:
    max_retries: int = 3                          # 最大重试次数（不含首次）
    retry_delay: float = 1.0                      # 基础退避秒数
    max_backoff: float = 30.0                     # 退避上限（避免 attempt=5 时退到 32s）
    backoff_jitter: bool = True                   # 添加 0-1s 随机抖动，避免惊群
    retryable_status_codes: frozenset[int] = frozenset({429, 500, 502, 503, 504})
    respect_retry_after: bool = True              # 优先尊重服务器 Retry-After header

def _compute_backoff(attempt: int, config: RetryConfig,
                     retry_after: float | None = None) -> float:
    """指数退避 + 可选 jitter + Retry-After 优先。"""
    if config.respect_retry_after and retry_after is not None:
        return min(retry_after, config.max_backoff)
    delay = config.retry_delay * (2 ** attempt)
    if config.backoff_jitter:
        delay += random.uniform(0, 1.0)
    return min(delay, config.max_backoff)
```

#### HTTPClient（位于 `common/http.py`）

```python
class HTTPClient:
    def __init__(self, base_url: str, auth: TokenAuth, *,
                 timeout: float = 30.0,
                 retry: RetryConfig | None = None):
        self._client = httpx.Client(base_url=base_url, timeout=timeout, ...)
        self._auth = auth
        self._retry = retry or RetryConfig()

    def request(self, method: str, path: str, *,
                json: dict | None = None,
                params: dict | None = None,
                path_params: dict | None = None,
                resource_type: str | None = None,
                resource_id: int | str | None = None) -> dict:
        url = path.format(**(path_params or {}))
        last_exc: Exception | None = None
        for attempt in range(self._retry.max_retries + 1):
            try:
                resp = self._client.request(method, url, json=json, params=params,
                                             headers=self._auth.headers())
            except httpx.TransportError as e:
                last_exc = e
                if attempt < self._retry.max_retries:
                    time.sleep(_compute_backoff(attempt, self._retry))
                    continue
                raise ConnectionError(f"Transport error: {e}") from e

            if resp.status_code in self._retry.retryable_status_codes and \
               attempt < self._retry.max_retries:
                retry_after = _parse_retry_after(resp) if resp.status_code == 429 else None
                time.sleep(_compute_backoff(attempt, self._retry, retry_after))
                continue
            return _handle_response(resp, path=path,
                                     resource_type=resource_type,
                                     resource_id=resource_id)
        raise ServerError(f"Max retries exceeded for {method} {url}") from last_exc

    def close(self) -> None:
        self._client.close()
```

#### AsyncHTTPClient（位于 `common/http.py`）

**与 HTTPClient 共享**：`_handle_response` / `_compute_backoff` / `_parse_retry_after`（模块级函数，sync/async 通用）。
**差异**：用 `httpx.AsyncClient`（懒加载，避免在 `__init__` 里绑定事件循环）。

```python
class AsyncHTTPClient:
    def __init__(self, base_url: str, auth: TokenAuth, *,
                 timeout: float = 30.0,
                 retry: RetryConfig | None = None):
        # 不在 __init__ 创建 AsyncClient，避免事件循环绑定问题（对标 ai-sdk）
        self._base_url = base_url
        self._auth = auth
        self._timeout = timeout
        self._retry = retry or RetryConfig()
        self._async_client: httpx.AsyncClient | None = None

    @property
    def _client(self) -> httpx.AsyncClient:
        """懒加载：首次调用时才创建 AsyncClient。"""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self._base_url, timeout=self._timeout, ...
            )
        return self._async_client

    async def request(self, method: str, path: str, *,
                      json: dict | None = None,
                      params: dict | None = None,
                      path_params: dict | None = None,
                      resource_type: str | None = None,
                      resource_id: int | str | None = None) -> dict:
        url = path.format(**(path_params or {}))
        last_exc: Exception | None = None
        for attempt in range(self._retry.max_retries + 1):
            try:
                resp = await self._client.request(method, url, json=json, params=params,
                                                   headers=self._auth.headers())
            except httpx.TransportError as e:
                last_exc = e
                if attempt < self._retry.max_retries:
                    await asyncio.sleep(_compute_backoff(attempt, self._retry))
                    continue
                raise ConnectionError(f"Transport error: {e}") from e

            if resp.status_code in self._retry.retryable_status_codes and \
               attempt < self._retry.max_retries:
                retry_after = _parse_retry_after(resp) if resp.status_code == 429 else None
                await asyncio.sleep(_compute_backoff(attempt, self._retry, retry_after))
                continue
            # 复用 sync 版 _handle_response（resp 是 httpx.Response，接口一致）
            return _handle_response(resp, path=path,
                                     resource_type=resource_type,
                                     resource_id=resource_id)
        raise ServerError(f"Max retries exceeded for {method} {url}") from last_exc

    async def aclose(self) -> None:
        if self._async_client is not None:
            await self._async_client.aclose()
```

**关键设计**：
- `_handle_response` 是模块级函数（非方法），sync/async 都能调用——`httpx.Response` 接口一致，不需要 await `resp.json()`
- 重试逻辑结构相同，只是 `time.sleep` ↔ `asyncio.sleep`
- AsyncClient 懒加载，避免在 `SupersonicClient.__init__` 阶段绑定到错误的事件循环
- `aclose()` 仅在 AsyncClient 实际创建后才调用 `.aclose()`

#### 异常树（位于 `exceptions.py`）

```
SupersonicError                    # 根（带 status_code/message/response_body）
├── AuthenticationError            # 401（token 失效）
├── ValidationError                # 400（携带字段级错误详情）
│   └── .field_errors: list[FieldError]
├── RateLimitError                 # 429（带 .retry_after）
├── ServerError                    # 5xx
├── ConnectionError                # 网络层（httpx.TransportError 包装）
├── AsyncNotEnabledError           # 调用 async 方法但未 enable_async=True
└── ResourceNotFoundError          # 404 的基类
    ├── DomainNotFoundError
    ├── ModelNotFoundError
    ├── DimensionNotFoundError
    ├── MetricNotFoundError
    ├── DatasetNotFoundError
    └── DatabaseNotFoundError
```

**异常类签名**：

```python
class SupersonicError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None,
                 response_body: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body

class FieldError(BaseModel):
    field: str                          # 出错字段名
    message: str                        # 错误描述
    rejected_value: Any | None = None   # 被拒绝的值（可选）

class ValidationError(SupersonicError):
    def __init__(self, message: str, *,
                 status_code: int = 400,
                 response_body: dict | None = None,
                 field_errors: list[FieldError] | None = None):
        super().__init__(message, status_code=status_code,
                         response_body=response_body)
        self.field_errors = field_errors or []

class ResourceNotFoundError(SupersonicError):
    def __init__(self, resource_type: str, resource_id: int | str):
        super().__init__(
            f"{resource_type} {resource_id} not found",
            status_code=404,
        )
        self.resource_type = resource_type
        self.resource_id = resource_id

class AsyncNotEnabledError(SupersonicError):
    """调用 .alist()/.acreate() 等异步方法但未启用 enable_async=True。"""
    def __init__(self):
        super().__init__(
            "Async methods require enable_async=True. "
            "Recreate SupersonicClient with enable_async=True to use async API."
        )
```

#### 异常映射（集中在 `common/http.py` 的 `_handle_response`）

```python
_NOT_FOUND_MAP = {
    "domain": DomainNotFoundError,
    "model": ModelNotFoundError,
    "dimension": DimensionNotFoundError,
    "metric": MetricNotFoundError,
    "dataset": DatasetNotFoundError,
    "database": DatabaseNotFoundError,
}

def _handle_response(resp: httpx.Response, *, path: str,
                     resource_type: str | None = None,
                     resource_id: int | str | None = None) -> dict:
    if 200 <= resp.status_code < 300:
        return resp.json() if resp.content else {}

    # 尝试解析响应体，失败也给用户原始文本
    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text}

    if resp.status_code == 401:
        raise AuthenticationError(
            "Authentication failed (token invalid or expired)",
            status_code=401, response_body=body,
        )
    if resp.status_code == 404:
        exc_cls = _NOT_FOUND_MAP.get(resource_type, ResourceNotFoundError)
        if exc_cls is ResourceNotFoundError:
            raise ResourceNotFoundError(resource_type or "resource", resource_id or "")
        raise exc_cls(resource_id=resource_id)
    if resp.status_code == 429:
        raise RateLimitError(
            "Rate limit exceeded",
            status_code=429, response_body=body,
            retry_after=_parse_retry_after(resp),
        )
    if 400 <= resp.status_code < 500:
        # 解析 SuperSonic 返回的字段级错误
        field_errors = _parse_field_errors(body)
        raise ValidationError(
            f"Request validation failed: {body.get('message', resp.reason_phrase)}",
            status_code=resp.status_code,
            response_body=body,
            field_errors=field_errors,
        )
    raise ServerError(
        f"Server error: {body.get('message', resp.reason_phrase)}",
        status_code=resp.status_code, response_body=body,
    )

def _parse_field_errors(body: dict) -> list[FieldError]:
    """从 SuperSonic 400 响应体解析字段级错误。

    支持多种格式（实际格式待集成测试确认）：
    - {"errors": [{"field": "name", "message": "不能为空"}]}
    - {"fieldErrors": {...}}
    - {"message": "name 不能为空"}  # 整体错误，无法结构化
    """
    errors = body.get("errors") or body.get("fieldErrors") or []
    if isinstance(errors, dict):
        return [FieldError(field=k, message=str(v)) for k, v in errors.items()]
    if isinstance(errors, list):
        return [FieldError(**e) for e in errors if isinstance(e, dict)]
    return []
```

---

### 查询子系统

#### 5 个查询方法签名

```python
class QueryAPI:
    def sql(
        self,
        sql: str,                                    # 必选，S2SQL 语句
        *,
        data_set_id: int | None = None,              # 可选，数据集 ID
        model_ids: list[int] | None = None,          # 可选，模型 ID 列表
        limit: int = 1000,                           # 可选，默认 1000
        params: list[Param] | None = None,           # 可选，预编译参数
        cache: CacheConfig | None = None,            # 可选，缓存控制
    ) -> QueryResult: ...

    def sqls(
        self,
        sqls: list[str],                             # 必选，S2SQL 语句列表
        *,
        data_set_id: int | None = None,
        model_ids: list[int] | None = None,
        limit: int = 1000,
    ) -> list[QueryResult]: ...

    def validate(
        self,
        sql: str,                                    # 必选，待校验 S2SQL
        *,
        data_set_id: int | None = None,
        model_ids: list[int] | None = None,
    ) -> ValidationResult: ...

    def metric(
        self,
        metrics: list[str],                          # 必选，指标业务名列表
        *,
        dimensions: list[str] | None = None,         # 可选，分组维度
        filters: list[Filter] | None = None,         # 可选，过滤条件
        date_info: DateConf | None = None,           # 可选，日期范围
        orders: list[Order] | None = None,           # 可选，排序
        limit: int = 1000,                           # 可选，结果行数
    ) -> QueryResult: ...

    @overload
    def chat(self, query_text: str, *, detailed: Literal[True] = True, ...) -> ChatQueryResult: ...
    @overload
    def chat(self, query_text: str, *, detailed: Literal[False], ...) -> QueryResult: ...
    def chat(
        self,
        query_text: str,                             # 必选，自然语言
        *,
        detailed: bool = True,                       # 可选，默认完整模式
        data_set_ids: list[int] | None = None,
        text2sql_type: Text2SqlType = Text2SqlType.LLM_OR_RULE,
        map_mode: MapMode = MapMode.LOOSE,
        save_answer: bool = True,
        query_filters: QueryFilters | None = None,
    ) -> ChatQueryResult | QueryResult: ...
```

#### 统一返回类型（`models/query.py`）

```python
class QueryColumn(BaseModel):
    name: str
    type: str                          # VARCHAR/DOUBLE/...
    display_name: str | None = None

class QueryResult(BaseModel):
    columns: list[QueryColumn]
    result_rows: list[dict[str, Any]]
    sql: str | None = None             # 实际执行的物理 SQL
    use_cache: bool = False
    error_msg: str | None = None

    def to_dataframe(self) -> "pd.DataFrame":
        """仅 [pandas] extra 可用"""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "to_dataframe requires pandas. "
                "Install with: pip install supersonic-sdk[pandas]"
            )
        return pd.DataFrame(self.result_rows, columns=[c.name for c in self.columns])
```

#### ChatQueryResult（NL 查询的完整解析过程）

```python
class ChatQueryResult(BaseModel):
    query_result: QueryResult | None = None
    selected_parse: SemanticParseInfo | None
    candidate_parses: list[SemanticParseInfo]
    parse_state: ParseState                    # COMPLETED / FAILED
    time_cost: ParseTimeCost | None
```

**`detailed` 开关**：
- `detailed=True`（默认）→ 返回 `ChatQueryResult`，含解析过程
- `detailed=False` → 返回 `QueryResult`，仅最终结果
- 简洁模式下若解析失败，显式抛 `ServerError`，提示用户用 `detailed=True` 查看详情
- 用 `@overload` + `Literal[True]` / `Literal[False]` 实现类型收窄，mypy/pyright 完整支持

**辅助模型**（实现时根据 SuperSonic API 响应结构定义，规格不展开字段细节）：
- `SemanticParseInfo`：单次解析结果，含 S2SQL / properties / score
- `ParseTimeCost`：解析耗时统计（map/parse/execute 各阶段毫秒数）
- `ValidationResult`：S2SQL 校验结果，含 `is_valid: bool` / `error_msg: str | None` / `corrected_sql: str | None`
- `ParseState`：枚举（`COMPLETED` / `FAILED`）

#### 支持类型

```python
class Text2SqlType(str, Enum):
    LLM_OR_RULE = "LLM_OR_RULE"             # 默认：LLM + 规则混合
    LLM_ONLY = "LLM_ONLY"
    RULE_ONLY = "RULE_ONLY"

class MapMode(str, Enum):
    STRICT = "STRICT"
    LOOSE = "LOOSE"                         # 默认

class DateConf(BaseModel):
    date_mode: DateMode                     # BETWEEN / IN / ALL / LIST
    start_date: str | None = None
    end_date: str | None = None
    date_list: list[str] | None = None
    period: str | None = None               # DAY/WEEK/MONTH/YEAR

class Filter(BaseModel):
    name: str
    operator: FilterOperator                # = / != / > / < / IN / NOT IN / LIKE / BETWEEN
    value: Any | list[Any] | None = None

class Order(BaseModel):
    name: str
    direction: Literal["ASC", "DESC"] = "ASC"

class Param(BaseModel):
    name: str
    type: str
    value: Any

class CacheConfig(BaseModel):
    enable: bool = True
    ttl: int = 3600
```

---

### 元数据 CRUD 模式

6 个元数据资源类遵循统一模式（list/get/create/update/delete 五件套 + 资源特有方法）。查询命名空间（QueryAPI）是独立的查询方法集，不遵循 CRUD 模式。

#### 完整 API 与端点路径映射

SuperSonic 端点为**驼峰式命名**（非 RESTful），路径需在 SDK 内集中管理。下表为 v0.1 全部端点（路径模板中 `{id}` 为路径参数）：

##### 查询命名空间

| 资源.方法 | HTTP | 路径 |
|---|---|---|
| `client.query.sql` | POST | `/api/semantic/query/sql` |
| `client.query.sqls` | POST | `/api/semantic/query/sqls` |
| `client.query.validate` | POST | `/api/semantic/query/validate` |
| `client.query.metric` | POST | `/api/semantic/query/metric` |
| `client.query.chat` | POST | `/api/semantic/query/chat` |

##### 元数据 CRUD 命名空间

| 资源.方法 | HTTP | 路径 |
|---|---|---|
| `client.domains.list` | GET | `/api/semantic/domain/getDomainList` |
| `client.domains.get` | GET | `/api/semantic/domain/getDomain/{id}` |
| `client.domains.create` | POST | `/api/semantic/domain/createDomain` |
| `client.domains.update` | POST | `/api/semantic/domain/updateDomain` |
| `client.domains.delete` | DELETE | `/api/semantic/domain/deleteDomain/{domainId}` |
| `client.models.list` | GET | `/api/semantic/model/getModelList/{domainId}` |
| `client.models.get` | GET | `/api/semantic/model/getModel/{id}` |
| `client.models.create` | POST | `/api/semantic/model/createModel` |
| `client.models.update` | POST | `/api/semantic/model/updateModel` |
| `client.models.delete` | DELETE | `/api/semantic/model/deleteModel/{modelId}` |
| `client.dimensions.list` | GET | `/api/semantic/dimension/getDimensionList/{modelId}` |
| `client.dimensions.get` | GET | `/api/semantic/dimension/getDimension/{id}` |
| `client.dimensions.create` | POST | `/api/semantic/dimension/createDimension` |
| `client.dimensions.update` | POST | `/api/semantic/dimension/updateDimension` |
| `client.dimensions.delete` | DELETE | `/api/semantic/dimension/deleteDimension/{id}` |
| `client.dimensions.query_values` | POST | `/api/semantic/dimension/queryDimValue` |
| `client.metrics.list` | POST | `/api/semantic/metric/queryMetric` |
| `client.metrics.get` | GET | `/api/semantic/metric/getMetric/{id}` |
| `client.metrics.create` | POST | `/api/semantic/metric/createMetric` |
| `client.metrics.update` | POST | `/api/semantic/metric/updateMetric` |
| `client.metrics.delete` | DELETE | `/api/semantic/metric/deleteMetric/{id}` |
| `client.metrics.publish` | POST | `/api/semantic/metric/batchPublish` |
| `client.metrics.unpublish` | POST | `/api/semantic/metric/batchUnPublish` |
| `client.databases.list` | GET | `/api/semantic/database/getDatabaseList` |
| `client.databases.get` | GET | `/api/semantic/database/getDatabase/{id}` |
| `client.databases.create` | POST | `/api/semantic/database/createOrUpdateDatabase` |
| `client.databases.update` | POST | `/api/semantic/database/createOrUpdateDatabase` |
| `client.databases.test_connect` | POST | `/api/semantic/database/testConnect` |
| `client.databases.get_tables` | GET | `/api/semantic/database/getTables` |
| `client.databases.get_columns` | GET | `/api/semantic/database/getColumnsByName` |
| `client.datasets.list` | GET | `/api/semantic/dataSet/getDataSetList` |
| `client.datasets.get` | GET | `/api/semantic/dataSet/getDataSet/{id}` |

##### 端点常量集中管理

所有路径模板在 `api/paths.py` 定义为常量，资源类引用常量而非散落字符串：

```python
# api/paths.py
class QueryPaths:
    SQL = "/api/semantic/query/sql"
    SQLS = "/api/semantic/query/sqls"
    VALIDATE = "/api/semantic/query/validate"
    METRIC = "/api/semantic/query/metric"
    CHAT = "/api/semantic/query/chat"

class MetricPaths:
    LIST = "/api/semantic/metric/queryMetric"
    GET = "/api/semantic/metric/getMetric/{id}"
    CREATE = "/api/semantic/metric/createMetric"
    UPDATE = "/api/semantic/metric/updateMetric"
    DELETE = "/api/semantic/metric/deleteMetric/{id}"
    PUBLISH = "/api/semantic/metric/batchPublish"
    UNPUBLISH = "/api/semantic/metric/batchUnPublish"

# ... 其他资源类同理
```

**优势**：
- 端点路径变更只改一处，不再散落在 7 个 API 文件
- 测试可与源码共享常量（`from supersonic.api.paths import MetricPaths`），避免硬编码 URL
- SuperSonic 升级导致端点变更时可集中审计

#### 使用示例（以 Metric 为例）

```python
# 创建
metric = client.metrics.create(MetricCreateReq(
    model_id=1,
    name="销售额",
    biz_name="sales_amt",
    define_type="MEASURE",           # MEASURE / FIELD / METRIC
    type="NUMBER",
    expression="pay_amt",
    description="订单支付金额",
))

# 查询列表（分页）
page = client.metrics.list(model_id=1, page=1, page_size=20)
page.items         # list[Metric]
page.total         # int
page.page_size     # int

# 更新
client.metrics.update(metric.id, MetricUpdateReq(description="更新描述"))

# 状态管理（批量）
client.metrics.publish([metric.id])
client.metrics.unpublish([metric.id])

# 删除
client.metrics.delete(metric.id)
```

#### 分页处理（`common/pagination.py`）

`Page[T]` 是泛型容器，自带 `from_response` classmethod 直接消费 SuperSonic 的 `PageInfo` 响应；资源类不再需要传 `mapper` 函数。

```python
T = TypeVar("T", bound=BaseModel)

class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

    @classmethod
    def from_response(
        cls,
        data: dict,
        item_model: type[T],
        *,
        items_key: str = "list",       # SuperSonic PageInfo.list
        total_key: str = "total",
        page_key: str = "pageNum",
        page_size_key: str = "pageSize",
    ) -> "Page[T]":
        """从 SuperSonic PageInfo 响应构造 Page。

        自动用 pydantic 的 model_validate 做类型转换与校验，
        无需调用方传 mapper 函数。
        """
        return cls(
            items=[item_model.model_validate(item) for item in data.get(items_key, [])],
            total=data.get(total_key, 0),
            page=data.get(page_key, 1),
            page_size=data.get(page_size_key, 10),
        )

# 资源类用法（极简）：
def list(self, *, page: int = 1, page_size: int = 10,
         model_id: int | None = None) -> Page[Metric]:
    body = self._http.request(
        "POST", MetricPaths.LIST,
        params={"page": page, "pageSize": page_size, "modelId": model_id},
        resource_type="metric",
    )
    return Page[Metric].from_response(body, item_model=Metric)

# async 版同理
async def alist(self, ...) -> Page[Metric]:
    body = await self._async_http.request("POST", MetricPaths.LIST, ...)
    return Page[Metric].from_response(body, item_model=Metric)
```

---

### 工具函数（`utils/`）

```python
# utils/builders.py - 便捷构造器
def date_range(start: str, end: str) -> DateConf: ...
def last_n_days(n: int) -> DateConf: ...
def month_to_date() -> DateConf: ...
def filter_eq(name: str, value: Any) -> Filter: ...
def filter_in(name: str, values: list[Any]) -> Filter: ...
def order_by(name: str, direction: Literal["ASC", "DESC"] = "ASC") -> Order: ...

# utils/validators.py - 调用前本地校验，fail fast
def is_valid_s2sql(sql: str) -> bool: ...
def validate_host_url(url: str) -> None: ...
def normalize_dataset_id(id: int | str) -> int: ...

# utils/format.py - 输出格式化（CLI 会复用）
def format_result_table(result: QueryResult, max_rows: int = 20) -> str: ...
def format_sql(sql: str, indent: int = 2) -> str: ...
```

---

### 测试策略

#### 三层测试

**单元测试（默认）**：

```python
# tests/api/test_metrics.py
def test_create_returns_metric(client, httpx_mock, sample_metric_dict):
    httpx_mock.add_response(
        url="http://test/api/semantic/metric/createMetric",
        json=sample_metric_dict,
    )
    metric = client.metrics.create(MetricCreateReq(...))
    assert isinstance(metric, Metric)
    assert metric.name == "销售额"
```

- 用 `pytest-httpx` mock 所有 HTTP，**零真实网络**
- `conftest.py` 提供 `sample_metric_dict` / `sample_query_result_dict` 等 fixtures
- **测试与源码 1:1**（`api/test_metrics.py` ↔ `api/metrics.py`）
- 覆盖维度：happy path / 各错误码 / 参数序列化 / 边界（空列表、超大页码、特殊字符）

**集成测试（opt-in）**：

```python
# tests/integration/test_query_live.py
@pytest.mark.integration
def test_live_query():
    client = SupersonicClient.from_env()
    result = client.query.sql("SELECT 1", data_set_id=int(os.environ["S2_TEST_DATASET_ID"]))
    assert len(result.result_rows) > 0
```

仅 CI 环境或本地手动跑，需要真实 SuperSonic 实例。`pytest -m "not integration"` 默认跳过。

#### 覆盖率目标

- 行覆盖率 ≥ 85%
- 每个资源类至少 5 个测试（list/get/create/update/delete + 1 错误码）
- 异常映射函数 `_handle_response` 100% 覆盖（关键路径）

#### pytest 配置

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "integration: requires real SuperSonic instance",
]
addopts = "-m 'not integration'"  # 默认跳过集成测试
```

**端点路径 fixture（避免测试中硬编码 URL）**：

```python
# tests/conftest.py
import pytest
from supersonic.api.paths import MetricPaths, QueryPaths, ...

@pytest.fixture
def metric_paths():
    return MetricPaths

@pytest.fixture
def base_url():
    return "http://test"

# 测试用法
def test_create_returns_metric(client, httpx_mock, sample_metric_dict, metric_paths, base_url):
    httpx_mock.add_response(url=f"{base_url}{metric_paths.CREATE}", json=sample_metric_dict)
    metric = client.metrics.create(MetricCreateReq(...))
    assert isinstance(metric, Metric)
```

源码与测试共享 `paths.py` 常量，端点变更只改一处。

---

### 配置与运行时细节

#### pyproject.toml 完整草稿

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
cli = ["click>=8.1.0", "rich>=13.0.0"]   # Phase 2 启用
mcp = ["mcp>=0.9.0"]                      # Phase 3 启用
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-httpx>=0.30",
    "pytest-cov>=4.0",
    "ruff>=0.8.0",
    "mypy>=1.0",
]
all = ["supersonic-sdk[pandas,dev]"]      # 不含 cli/mcp（未实现）

[project.urls]
Homepage = "https://github.com/tencentmusic/supersonic"
Repository = "https://github.com/tencentmusic/supersonic"
Documentation = "https://github.com/tencentmusic/supersonic/tree/main/python-sdk"

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

**关键设计**：
- 核心包仅 2 个运行时依赖（httpx + pydantic）
- `[pandas]` 是用户可选；`[cli]`/`[mcp]` 在 Phase 2/3 实施时添加
- `[dev]` 包含完整开发工具链（pytest/httpx mock/ruff/mypy）
- `[all]` 不含未实现的 cli/mcp，避免安装空 extras
- `requires-python = ">=3.10"` 锁定 Python 版本（PEP 604 `X | None` 需要）

#### 环境变量表（`from_env()` 配置源）

| 变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `SUPERSONIC_HOST` | 是 | — | SuperSonic 服务地址（如 `http://localhost:9080`） |
| `SUPERSONIC_TOKEN` | 是 | — | JWT token |
| `SUPERSONIC_APP_KEY` | 否 | `supersonic` | App-Key header 值 |
| `SUPERSONIC_TIMEOUT` | 否 | `30.0` | HTTP 超时（秒） |
| `SUPERSONIC_MAX_RETRIES` | 否 | `3` | 最大重试次数 |
| `SUPERSONIC_ENABLE_ASYNC` | 否 | `false` | 是否启用 async client |
| `SUPERSONIC_LOG_LEVEL` | 否 | `WARNING` | 日志级别（`DEBUG`/`INFO`/`WARNING`/`ERROR`） |

**缺必填变量时的行为**：`from_env()` 抛 `ValueError`，消息明确指出缺失的变量名（对标 ai-sdk 的 fail fast）。

```python
@classmethod
def from_env(cls, **overrides) -> "SupersonicClient":
    host = os.environ.get("SUPERSONIC_HOST")
    token = os.environ.get("SUPERSONIC_TOKEN")
    missing = [k for k, v in [("SUPERSONIC_HOST", host), ("SUPERSONIC_TOKEN", token)] if not v]
    if missing:
        raise ValueError(f"Missing required env vars: {', '.join(missing)}")
    ...
```

#### 线程安全

**`SupersonicClient` 不是线程安全的**。底层 `httpx.Client` 在并发请求时会出现连接池竞争（参见 [httpx 文档](https://www.python-httpx.org/advanced/concurrency/)）。

**用户策略**（在 `SupersonicClient` docstring 中明示）：

```python
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
```

**Phase 1 不实现**：连接池封装、contextvars 自动线程隔离。这些留作 v0.2 候选特性，但 docstring 警告必须 v0.1 就有。

#### 日志策略

Phase 1 采用**极简日志**，不自建 logger，复用 std `logging`：

```python
# common/logging.py
import logging

_LOGGER = logging.getLogger("supersonic")

def get_logger() -> logging.Logger:
    return _LOGGER

def configure_logging(level: str | int = "WARNING") -> None:
    """配置 supersonic 命名空间的日志级别。

    可通过 SUPERSONIC_LOG_LEVEL 环境变量在 from_env() 时自动调用，
    或用户显式调用 supersonic.configure_logging("DEBUG")。
    """
    logging.basicConfig(level=level)  # 用户也可自行配置 handler
    _LOGGER.setLevel(level)

# 在 HTTPClient 中：
class HTTPClient:
    def request(self, method, path, *, ...):
        log = get_logger()
        log.debug("HTTP %s %s payload=%s", method, path, json)
        ...
        log.debug("HTTP response status=%s body=%s", resp.status_code, body)
```

**日志约定**：
- 级别：HTTP 请求/响应 → `DEBUG`；连接/重试 → `INFO`；认证失败 → `WARNING`
- 命名空间：`supersonic`（顶级）、`supersonic.http`（HTTP 层）、`supersonic.api.metric`（资源层）
- **不记录敏感信息**：`Authorization` header 始终打码（`Authorization: Bearer ***`）；请求体中的 token 同理
- Phase 1 不实现：X-Request-ID 追踪、结构化日志（JSON）—— 留作 v0.2

#### 与 SuperSonic 版本兼容性

**Phase 1 策略（best-effort）**：
- SDK v0.1 兼容 SuperSonic ≥ 1.1.0（基于当前 master 分支的 API 形态）
- 不主动版本协商，依赖端点路径与 DTO 字段稳定
- README 中明示兼容版本范围

**未来扩展**（Phase 2+）：
- 新增 `client.get_server_version()` 方法（调 SuperSonic `/api/semantic/meta/version` 或类似端点）
- 启动时可选 strict 模式，版本不匹配 raise `IncompatibleVersionError`
- SemVer 约定：SuperSonic major 升级 → SDK major 升级

**当前已知风险**：
- 端点路径（如 `/createMetric` vs `/metrics`）若 SuperSonic 未来重构为 RESTful，需 SDK 同步重构 `paths.py`
- DTO 字段变更：`response_body` 在异常对象上保留，便于调试

---

### 关键示例（`examples/`）

#### `examples/quickstart.py`

```python
"""3 分钟上手：查询销售额（含基础错误处理）"""
import sys
from supersonic import (
    SupersonicClient,
    AuthenticationError,
    MetricNotFoundError,
    SupersonicError,
)
from supersonic.utils import date_range

try:
    with SupersonicClient.from_env() as client:
        result = client.query.metric(
            metrics=["销售额"],
            dimensions=["品类"],
            date_info=date_range("2026-01-01", "2026-06-30"),
        )
        df = result.to_dataframe()  # 需 pip install supersonic-sdk[pandas]
        print(df.sort_values("销售额", ascending=False))
except AuthenticationError:
    print("Token 失效，请检查 SUPERSONIC_TOKEN", file=sys.stderr)
    sys.exit(1)
except MetricNotFoundError as e:
    print(f"指标不存在: {e.resource_id}", file=sys.stderr)
    sys.exit(1)
except SupersonicError as e:
    print(f"查询失败: {e.message} (status={e.status_code})", file=sys.stderr)
    sys.exit(1)
```

#### `examples/semantic_modeling.py`

```python
"""编程式建模：批量创建指标"""
from supersonic import SupersonicClient, MetricCreateReq

with SupersonicClient.from_env() as client:
    for m in METRICS_TO_CREATE:
        client.metrics.create(MetricCreateReq(model_id=1, **m))
    # 批量发布
    page = client.metrics.list(model_id=1, page_size=100)
    client.metrics.publish([m.id for m in page.items])
```

#### `examples/nl_query.py`

```python
"""自然语言查询：双模式对比"""
from supersonic import SupersonicClient

with SupersonicClient.from_env() as client:
    # 完整模式（默认）：看解析过程
    full = client.query.chat("销售额最高的 5 个产品")
    print(f"选中解析: {full.selected_parse.sql}")
    print(f"候选数: {len(full.candidate_parses)}")

    # 简洁模式：直接拿数据
    result = client.query.chat("...", detailed=False)
    print(result.result_rows)
```

---

## 关键设计决策

### 1. 三层架构而非单一 SDK

**决策**：构建 SDK + CLI + MCP Server 三层，每层独立规格。

**理由**：
- 单一 SDK 在 2026 年的简历池里是 commodity，缺乏差异化
- CLI 是任何 Agent 都能用的通用接口（`bash` 调用），覆盖面最广
- MCP Server 是 Agent 生态的标准化协议，对标 ai-sdk 的 MCP 集成
- 三层形成完整故事："让 SuperSonic 语义层可以被 Python 开发者、Agent、运维三类用户复用"

**代价**：3 个独立规格，实施周期长。但每层独立闭环，可以分阶段交付。

### 2. Phase 1 范围：查询 + 完整元数据 CRUD

**决策**：覆盖查询（sql/chat/metric/validate/sqls）+ 6 个元数据资源的完整 CRUD（不含知识库/embedding/download/裸 SQL）。

**理由**：
- 仅查询 SDK 与 `requests.post` 无差别，缺差异化价值
- 完整 CRUD 提供"编程式语义建模"叙事——`sdk.metrics.create(...)` 配合类型提示和模型校验，才是 SDK 的核心价值
- 一个规格能覆盖（37 方法 = 5 query + 5+5+6+7+7+2 元数据 CRUD、6 元数据资源 + 1 查询命名空间、外加基础设施）
- 知识库/embedding 运维属性强，与分析 SDK 定位冲突；裸 SQL 绕过语义层

### 3. Opt-in async 而非默认 async

**决策**：`SupersonicClient(enable_async=True)` 显式开启，每方法同步版 + `a` 前缀版。

**理由**：
- 默认 sync 满足 CLI、脚本、交互式 Jupyter 场景
- async 满足 Web 框架（FastAPI）、MCP Server 并发场景
- 单一类 + 方法分叉比双套独立类简单得多（对标 ai-sdk）

### 4. 查询结果：Pydantic 模型 + 可选 pandas

**决策**：默认返回 `QueryResult`（pydantic），`[pandas]` extra 用户可调 `.to_dataframe()`。

**理由**：
- 核心包零额外依赖（保持 httpx + pydantic 双依赖）
- Web 后端用户：`result.result_rows` 即可
- 数据科学家：`pip install supersonic-sdk[pandas]` 后 `.to_dataframe()` 直接到 df
- AI Agent（MCP）：返回 JSON 序列化的 result_rows

### 5. Chat 查询的 detailed 双模式

**决策**：`detailed: bool = True` 开关，默认返回 `ChatQueryResult`（含解析过程），关闭返回 `QueryResult`（仅结果）。

**理由**：
- 让 SDK 同时服务"想看解析过程的开发者"和"只想要结果的数据分析师"
- 用 `@overload` + `Literal` 实现类型收窄，IDE 自动补全准确
- 简洁模式解析失败时显式抛 `ServerError`，避免返回 None 让用户困惑

### 6. 资源特化异常树

**决策**：`MetricNotFoundError` / `DatasetNotFoundError` 等资源特化异常，而非统一 `NotFoundError`。

**理由**：
- 用户可以 `except MetricNotFoundError:` 精准 catch（对标 ai-sdk 的 `AgentNotFoundError`）
- 异常对象带 `resource_id` 字段，便于调试
- HTTP 层的 `_handle_response` 根据 `resource_type` 参数映射到正确的异常类

### 7. common/ 仅放内部基础设施

**决策**：`common/` 包含 `http.py`/`pagination.py`/`logging.py`，**不包含** `client.py`/`auth.py`/`config.py`。

**理由**：
- Python 约定：顶级文件 = 公共 API（最可发现），下划线/子包 = 内部
- `client`/`auth`/`config` 是用户必 import 的公共 API，放顶级保证 `from supersonic import SupersonicClient` 最简
- `common/` 收纳内部基础设施，物理隔离"公共 vs 内部"
- 对标 SuperSonic Java 端的 `common/` 模块（放基础设施），但保留 Python 的"公共 API 顶级"约定

### 8. extras 模式而非单 huge 包

**决策**：核心包仅 httpx + pydantic，其他能力走 extras（`[cli]` / `[mcp]` / `[pandas]` / `[dev]`）。

**理由**：
- 对标 ai-sdk、httpx、fastapi 等现代 Python SDK
- 用户按需安装，避免依赖膨胀
- Phase 2/3 加 CLI/MCP 时不需要拆包，只加 extras

---

## 范围边界

### IN SCOPE（Phase 1）

- 6 个元数据资源的完整 CRUD（domains/models/dimensions/metrics/databases/datasets，共 32 方法，详见 API 一览表）
- 1 个查询命名空间，5 个查询方法（sql/sqls/validate/metric/chat）
- TokenAuth 双 header 认证 + from_env 配置
- HTTP 层（重试、退避、异常映射）
- Opt-in async 支持
- ChatQueryResult detailed 双模式
- pydantic v2 模型 + 可选 pandas 转 DataFrame
- 工具函数（builders/validators/format）
- 单元测试 + 集成测试框架
- 3 个完整示例

### OUT OF SCOPE（明确不做）

| 项目 | 原因 | 何时做 |
|---|---|---|
| CLI | Phase 2 独立规格 | SDK 稳定后 |
| MCP Server | Phase 3 独立规格 | CLI 完成后 |
| LangChain Tool 包装 | 依赖 MCP，且非核心 | Phase 3 可选 |
| Token 自动刷新 | 复杂度高，v0.1 显式重新获取即可 | v0.2 |
| 配置文件（`~/.supersonic/config.toml`） | 环境变量已够 v0.1 | v0.2 |
| 流式响应（SSE） | chat 查询的 stream 模式 | 视用户需求 |
| 知识库/字典/embedding 管理 | 运维属性强，与分析 SDK 定位冲突 | 独立规格 |
| `database.execute_sql` 裸 SQL | 绕过语义层 | 独立规格 |
| `query.download` 文件下载 | CLI 职责 | Phase 2 |

---

## 产出物清单

### 源代码

- `python-sdk/pyproject.toml`
- `python-sdk/src/supersonic/__init__.py`（含 Import Guide docstring）
- `python-sdk/src/supersonic/py.typed`
- `python-sdk/src/supersonic/{client,auth,config,exceptions}.py`（4 个公共顶级文件）
- `python-sdk/src/supersonic/common/{http,pagination,logging}.py`（内部基础设施）
- `python-sdk/src/supersonic/api/{paths,query,domains,models,dimensions,metrics,databases,datasets}.py`（8 个文件：1 端点常量 + 7 个 API 类）
- `python-sdk/src/supersonic/models/{base,query,domain,model,dimension,metric,database,dataset}.py`（8 个模型文件）
- `python-sdk/src/supersonic/utils/{builders,validators,format}.py`（3 个工具文件）

### 测试

- `python-sdk/tests/conftest.py`
- `python-sdk/tests/test_{client,auth,config,async}.py`
- `python-sdk/tests/common/test_{http,pagination,logging}.py`
- `python-sdk/tests/api/test_{query,domains,models,dimensions,metrics,databases,datasets}.py`
- `python-sdk/tests/integration/test_query_live.py`

### 示例与文档

- `python-sdk/examples/{quickstart,semantic_modeling,nl_query}.py`
- `python-sdk/README.md`
- `python-sdk/CHANGELOG.md`

### 简历文档（Phase 1-3 全部完成后）

- `docs/superpowers/resume/05-python-sdk.md`（三层架构完整叙事）

---

## 后续 Phase（仅概述，详见各自规格）

### Phase 2：CLI

- **打包关系**：CLI 是 SDK 的**子包**（`python-sdk/src/supersonic/cli/`），不是独立 PyPI 包。两者共享同一个 `supersonic-sdk` distribution，CLI 走 `[cli]` extra 安装依赖
- **依赖 SDK**：CLI 直接 import `supersonic.Client` / `supersonic.api.*` / `supersonic.utils.*`，无重复封装
- 命令结构：`supersonic query/metric/model/domain/...`
- 框架：`click` 或 `typer`
- 输出：JSON / 表格双格式（直接复用 SDK 的 `utils/format.py`，因同包无需跨包导出）
- 配置：环境变量 + `--config` 文件
- Agent 友好：稳定的 stdout 格式、退出码语义

### Phase 3：MCP Server

- `mcp/` 子包，`[mcp]` extra
- 协议：MCP（Model Context Protocol）
- 工具定义：每个资源类映射为 MCP tool（如 `create_metric`、`query_sql`）
- 传输：stdio（默认）+ HTTP/SSE（可选）
- 框架：`mcp` 官方 Python SDK
- 对标：ai-sdk 的 `mcp/` 子包
