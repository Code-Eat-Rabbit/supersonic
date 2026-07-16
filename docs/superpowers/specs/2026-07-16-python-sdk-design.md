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
    max_retries=3,
)

# 2. 从环境变量（CI/脚本场景）
client = SupersonicClient.from_env()
# 读 SUPERSONIC_HOST / SUPERSONIC_TOKEN / SUPERSONIC_APP_KEY

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
- 每个业务方法都有 `a`-前缀 async 版（用 `async_http`，若为 None 则 raise RuntimeError）
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

#### HTTPClient（位于 `common/http.py`）

```python
class HTTPClient:
    def __init__(self, base_url: str, auth: TokenAuth, *,
                 timeout: float = 30.0, max_retries: int = 3):
        self._client = httpx.Client(base_url=base_url, timeout=timeout, ...)
        self._auth = auth
        self._max_retries = max_retries

    def request(self, method: str, path: str, *,
                json: dict | None = None,
                params: dict | None = None,
                path_params: dict | None = None,
                resource_type: str | None = None,
                resource_id: int | str | None = None) -> dict:
        url = path.format(**(path_params or {}))
        for attempt in range(self._max_retries + 1):
            resp = self._client.request(method, url, json=json, params=params,
                                         headers=self._auth.headers())
            if resp.status_code in RETRYABLE_STATUS_CODES:
                self._sleep_backoff(attempt, resp)  # 指数退避 / Retry-After
                continue
            return self._handle_response(resp, path=path,
                                          resource_type=resource_type,
                                          resource_id=resource_id)
        raise ServerError(f"Max retries exceeded for {method} {url}")
```

- **可重试状态码**：`{429, 500, 502, 503, 504}`（对标 ai-sdk）
- **退避策略**：`retry_delay * (2 ** attempt)`，或尊重 `Retry-After` header
- 流式不重试（v0.1 不涉及流式）

#### 异常树（位于 `exceptions.py`）

```
SupersonicError                    # 根
├── AuthenticationError            # 401（token 失效）
├── ValidationError                # 400（参数校验失败）
├── RateLimitError                 # 429（带 .retry_after）
├── ServerError                    # 5xx
├── ConnectionError                # 网络层
└── ResourceNotFoundError          # 404 的基类
    ├── DomainNotFoundError
    ├── ModelNotFoundError
    ├── DimensionNotFoundError
    ├── MetricNotFoundError
    ├── DatasetNotFoundError
    └── DatabaseNotFoundError
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
    if resp.status_code == 401:
        raise AuthenticationError(...)
    if resp.status_code == 404:
        exc_cls = _NOT_FOUND_MAP.get(resource_type, ResourceNotFoundError)
        raise exc_cls(resource_id=resource_id, ...)
    if resp.status_code == 429:
        raise RateLimitError(retry_after=_parse_retry_after(resp))
    if 400 <= resp.status_code < 500:
        raise ValidationError(...)
    raise ServerError(...)
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

#### 完整 API 一览

| 资源类 | 方法 | 路径 |
|---|---|---|
| `client.query` | `sql` / `sqls` / `validate` / `metric` / `chat` | `/api/semantic/query/*` |
| `client.domains` | `list` / `get` / `create` / `update` / `delete` | `/api/semantic/domain/*` |
| `client.models` | `list` / `get` / `create` / `update` / `delete` | `/api/semantic/model/*` |
| `client.dimensions` | `list` / `get` / `create` / `update` / `delete` / `query_values` | `/api/semantic/dimension/*` |
| `client.metrics` | `list` / `get` / `create` / `update` / `delete` / `publish` / `unpublish` | `/api/semantic/metric/*` |
| `client.databases` | `list` / `get` / `create` / `update` / `test_connect` / `get_tables` / `get_columns` | `/api/semantic/database/*` |
| `client.datasets` | `list` / `get` | `/api/semantic/dataSet/*` |

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

模块级泛型 helper，资源类直接复用：

```python
T = TypeVar("T")

class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

def _paginate(
    http: HTTPClient,
    path: str,
    *,
    mapper: Callable[[dict], T],
    page: int = 1,
    page_size: int = 10,
    extra_params: dict | None = None,
) -> Page[T]: ...
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

---

### 关键示例（`examples/`）

#### `examples/quickstart.py`

```python
"""3 分钟上手：查询销售额"""
from supersonic import SupersonicClient

with SupersonicClient.from_env() as client:
    result = client.query.metric(
        metrics=["销售额"],
        dimensions=["品类"],
        date_info=date_range("2026-01-01", "2026-06-30"),
    )
    df = result.to_dataframe()
    print(df.sort_values("销售额", ascending=False))
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
- `python-sdk/src/supersonic/api/{query,domains,models,dimensions,metrics,databases,datasets}.py`（7 个 API 类 = 1 查询 + 6 元数据 CRUD）
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

- `cli/` 子包，`[cli]` extra
- 命令结构：`supersonic query/metric/model/domain/...`
- 框架：`click` 或 `typer`
- 输出：JSON / 表格双格式（复用 `utils/format.py`）
- 配置：环境变量 + `--config` 文件
- Agent 友好：稳定的 stdout 格式、退出码语义

### Phase 3：MCP Server

- `mcp/` 子包，`[mcp]` extra
- 协议：MCP（Model Context Protocol）
- 工具定义：每个资源类映射为 MCP tool（如 `create_metric`、`query_sql`）
- 传输：stdio（默认）+ HTTP/SSE（可选）
- 框架：`mcp` 官方 Python SDK
- 对标：ai-sdk 的 `mcp/` 子包
