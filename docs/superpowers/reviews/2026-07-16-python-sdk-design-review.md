# SuperSonic Python SDK 设计规格 — 评审报告

> 评审对象：`docs/superpowers/specs/2026-07-16-python-sdk-design.md`
> 评审日期：2026-07-16
> 评审维度：架构合理性 / API 设计 / 异常与容错 / 测试策略 / 文档完整度 / 可行性

---

## 整体评价

这是一份**高质量的设计文档**，对标 open-metadata/ai-sdk 的设计模式，三层架构（SDK → CLI → MCP Server）的叙事完整且有差异化价值。"编程式语义建模"的定位准确，不满足于做一个薄薄的 HTTP wrapper，而是通过 pydantic 模型校验 + 类型提示 + builder 工具函数来提供真正的 SDK 价值。

文档的 scope 边界清晰（IN SCOPE / OUT OF SCOPE 表格），8 个关键设计决策都有"决策 / 理由 / 代价"三段论，这在中文技术文档中非常难得。

---

## 值得学习的地方

1. **门面 + 资源命名空间**的模式选型正确，`SupersonicClient` 只装配不请求，职责单一。对标 ai-sdk 的 `AISdk` 而非自己造轮子。
2. **extras 模式**让核心包保持 httpx + pydantic 双依赖，数据科学家按需 `pip install supersonic-sdk[pandas]`，符合 2026 年 Python 生态最佳实践。
3. **资源特化异常树**（`MetricNotFoundError` / `DatasetNotFoundError` / ...）比通用 `NotFoundError` 好得多，用户可以做精准 except。
4. **`@overload` + `Literal` 实现 chat 的 detailed 双模式**，类型收窄让 mypy/pyright 能区分返回值类型，质量很高。
5. **测试与源码 1:1 镜像**（`tests/api/test_metrics.py` ↔ `src/supersonic/api/metrics.py`），可发现性极好。
6. **OUT OF SCOPE 明确列出不做的事情及其原因**，比"TODO"式的模糊延期专业得多。

---

## 主要问题

### [必须修复] 1. AsyncHTTPClient 未定义

**位置**：第 226-229 行（MetricsAPI 构造函数）

```python
class MetricsAPI:
    def __init__(self, http: HTTPClient, async_http: AsyncHTTPClient | None):
```

文档仅在 MetricsAPI 签名中提及 `AsyncHTTPClient`，但 `common/http.py` 只定义了 `HTTPClient`（第 286-309 行），没有 AsyncHTTPClient 的设计。缺少：
- AsyncHTTPClient 的接口定义
- 与 HTTPClient 的关系（继承？独立类？共享重试/异常映射逻辑？）
- 是否复用 httpx.AsyncClient

**影响**：实现时必然需要补充设计，可能引入接口不一致。

**建议**：在 `common/http.py` 中增加 AsyncHTTPClient 的定义，明确：
- 与 HTTPClient 共享 `_handle_response` / 退避策略
- 是否需要独立的 `_ahandle_response`（考虑 `resp.aread()` / `resp.json()` 的 async 差异）

---

### [必须修复] 2. API 端点路径未定义

**位置**：第 521-531 行（API 一览表）

表中资源类和方法名很清晰，但路径只写到了 `*` 通配级别：

| 资源类 | 方法 | 路径 |
|---|---|---|
| `client.metrics` | `list` / ... | `/api/semantic/metric/*` |

测试代码（第 623 行）暴露了实际路径：

```python
url="http://test/api/semantic/metric/createMetric",
```

这表明 SuperSonic 的端点命名是驼峰式（`createMetric` / `updateMetric`），而非 RESTful。但文档完全没涉及路径映射规则。

**影响**：
- 实现时每个资源类需要对着 SuperSonic 源码找路径，没有集中定义
- 如果 SuperSonic 升级改了某个端点名，SDK 的修改点分散在 7 个 API 文件中

**建议**：在规格中增加路径映射表，或在 `api/__init__.py` 中定义集中常量：

```python
# 建议：集中定义端点
_METRIC_PATHS = {
    "list": "/api/semantic/metric/getMetricList",     # 待验证实际路径
    "create": "/api/semantic/metric/createMetric",
    "update": "/api/semantic/metric/updateMetric",
    # ...
}
```

---

### [必须修复] 3. 线程安全未讨论

**位置**：全文

`SupersonicClient` 持有 `httpx.Client`，而 httpx.Client 本身**不是线程安全**的（官方文档明确要求每个线程创建独立 Client 或使用锁）。SDK 被定位为"Python 开发者/数据科学家"使用，多线程场景很常见（Flask/FastAPI 多 worker、concurrent.futures）。

**影响**：用户在多线程环境中共享同一个 `SupersonicClient` 实例会导致连接池竞争和数据错乱。

**建议**：
- 在文档中明确声明 `SupersonicClient` 的线程安全性
- 如果有意支持线程安全，设计连接池方案（每个资源调用临时获取 Client，或使用 `contextvars`）
- 如果暂时不支持，在 docstring 中加 `thread_safety: not thread-safe, create one per thread` 警告

---

### [必须修复] 4. pyproject.toml 关键配置缺失

**位置**：包布局（第 91-162 行）提到了 `pyproject.toml`，产出物清单（第 837 行）也列了它，但**全文档零配置细节**。

需要至少定义：
- `[project]`：name / version / requires-python / dependencies
- `[project.optional-dependencies]`：pandas / cli / mcp / dev 的依赖树
- `[build-system]`：hatchling
- `[tool.ruff]`：lint/format 规则

**影响**：extras 模式的设计决策（第 792-798 行）因缺乏 pyproject.toml 示例而无法验证。比如 `[cli]` 和 `[mcp]` extra 的依赖是否与核心包有版本冲突，现在完全不可见。

**建议**：在规格中增加 pyproject.toml 的完整草稿，作为第 5.1 节。

---

### [建议修改] 5. 退避策略参数缺失

**位置**：第 312-314 行

```
- 退避策略：retry_delay * (2 ** attempt)，或尊重 Retry-After header
```

未定义：
- `retry_delay` 的默认值（1.0 秒？0.5 秒？）
- 最大退避上限（避免 attempt=5 时退避到 32 秒）
- 是否支持 jitter（避免惊群效应）
- 可重试状态码是否可配置

**建议**：明确定义退避参数：
- `retry_delay: float = 1.0`
- `max_backoff: float = 30.0`
- `backoff_jitter: bool = True`
- `retryable_status_codes: set[int]` 可通过 `SupersonicConfig` 覆盖

---

### [建议修改] 6. ValidationError 未携带结构化错误详情

**位置**：第 358-359 行

```python
if 400 <= resp.status_code < 500:
    raise ValidationError(...)
```

SuperSonic 返回 400 时通常会在 response body 中给出具体字段级错误（类似 `{"errors": [{"field": "name", "message": "不能为空"}]}`）。当前设计只抛 `ValidationError`，不解析 body。

**影响**：用户 catch 到 `ValidationError` 后只能看到 "Bad Request"，无法知道是哪个字段、什么原因，必须手动抓包看 HTTP response。

**建议**：
```python
class ValidationError(SupersonicError):
    def __init__(self, message: str, *, status_code: int = 400,
                 response_body: dict | None = None,
                 field_errors: list[FieldError] | None = None):
        ...

class FieldError(BaseModel):
    field: str
    message: str
```

---

### [建议修改] 7. async 未启用时的错误类型不够明确

**位置**：第 249 行

> 若为 None 则 raise RuntimeError

`RuntimeError` 是 Python 最宽泛的异常，用户可能和真正的运行时错误混淆。建议定义专用异常：

```python
class AsyncNotEnabledError(SupersonicError):
    """Raised when calling async methods without enable_async=True."""
    def __init__(self):
        super().__init__(
            "Async methods require enable_async=True. "
            "Set SupersonicClient(enable_async=True) to use async API."
        )
```

---

### [建议修改] 8. 分页 helper 设计可简化

**位置**：第 577-586 行

```python
def _paginate(http, path, *, mapper: Callable[[dict], T], ...) -> Page[T]:
```

每个资源类调用 `_paginate` 时需要传入 `mapper` 函数来做 dict→Model 转换。但 pydantic v2 的 `TypeAdapter` 或 `model_validate` 已经能处理这个，mapper 参数实际上就是把每个 dict 传给 `Metric(**item)`。

**建议**：让 `_paginate` 接收 pydantic model 类型而非 mapper 函数：

```python
def _paginate(http, path, *, 
              model: type[BaseModel],  # 而非 mapper: Callable
              ...) -> Page[model]:
```

或直接让 `Page` 的 parse 逻辑内聚：

```python
class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

    @classmethod
    def from_response(cls, data: dict, item_model: type[T]) -> "Page[T]":
        return cls(
            items=[item_model(**item) for item in data["list"]],
            total=data["total"],
            page=data["page"],
            page_size=data["pageSize"],
        )
```

---

### [建议修改] 9. common/logging.py 零说明

**位置**：第 106 行（目录树）和第 785 行（设计决策 #7）

目录结构中列出了 `common/logging.py`，在 8 个设计决策中也提到了 `common/` 包含 logging。但全文档没有一行描述 logging 的设计：
- 用什么级别？（httpx 请求日志用 DEBUG，业务操作用 INFO？）
- 用户如何控制？（环境变量 `SUPERSONIC_LOG_LEVEL`？）
- 日志格式？（是否包含 request_id / correlation_id？）

**建议**：要么补充 logging 设计（建议一个简短小节），要么从 Phase 1 scope 中移除，注明"Phase 1 使用标准 logging 默认配置，不做自定义 logger"。

---

### [建议修改] 10. from_env() 的环境变量名未文档化

**位置**：第 196-198 行

```python
client = SupersonicClient.from_env()
# 读 SUPERSONIC_HOST / SUPERSONIC_TOKEN / SUPERSONIC_APP_KEY
```

环境变量名在注释中提到了，但：
- 没有说明缺少必填变量时的行为（抛 `ValidationError`？`ValueError`？`KeyError`？）
- 没有列出可选变量的默认值（timeout 默认？max_retries 默认？）

**建议**：在 auth 或 config 小节中增加环境变量表格：

| 变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `SUPERSONIC_HOST` | 是 | - | SuperSonic 服务地址 |
| `SUPERSONIC_TOKEN` | 是 | - | JWT |
| `SUPERSONIC_APP_KEY` | 否 | `supersonic` | 应用标识 |
| `SUPERSONIC_TIMEOUT` | 否 | `30.0` | HTTP 超时（秒） |
| `SUPERSONIC_MAX_RETRIES` | 否 | `3` | 最大重试次数 |

---

### [建议修改] 11. 与 SuperSonic 版本兼容性未涉及

**位置**：全文

SDK 将调用 SuperSonic 的 REST API。如果 SuperSonic 升级（字段增减、路径变更），SDK 如何保证兼容？

**建议**：在规格中增加兼容性声明，哪怕只是初版策略：
- SDK v0.1 兼容 SuperSonic ≥ 1.1.0
- 通过 `SupersonicClient(host=...).get_server_version()` 在连接时验证版本
- 或者 Phase 1 先不管（"best effort"），Phase 2 再加版本协商

---

### [仅供参考] 12. utils/format.py 的复用路径有歧义

**位置**：第 873 行

> 输出：JSON / 表格双格式（复用 `utils/format.py`）

Phase 2 CLI 将复用 SDK 的 `utils/format.py`。但如果 CLI 是 SDK 的子包（从包布局推测，`python-sdk/src/supersonic/cli/`），复用是自然的。如果 CLI 是独立包，则需要依赖 SDK。

**建议**：明确 CLI/SDK 的打包关系——是 monorepo 子包还是独立 PyPI 包。

---

### [仅供参考] 13. 测试示例中 URL 为硬编码字符串

**位置**：第 621-625 行

```python
httpx_mock.add_response(
    url="http://test/api/semantic/metric/createMetric",
)
```

硬编码 URL 意味着如果 SuperSonic 改了端点名，需要改两处（源码 + 测试）。更好的做法是让测试和源码共享端点常量。

**建议**：在 `conftest.py` 中暴露端点 fixtures：

```python
@pytest.fixture
def metric_paths():
    return {"create": "/api/semantic/metric/createMetric", ...}

def test_create_returns_metric(client, httpx_mock, sample_metric_dict, metric_paths):
    httpx_mock.add_response(url=f"http://test{metric_paths['create']}", ...)
```

---

### [仅供参考] 14. examples/quickstart.py 可补充错误处理

**位置**：第 671-685 行

quickstart 展示了 happy path，但作为"生产级示例"（规格对标 ai-sdk 的 `example.py` 要求"分层异常 + 资源释放"），可以增加：

```python
from supersonic import SupersonicClient, AuthenticationError, MetricNotFoundError

try:
    with SupersonicClient.from_env() as client:
        result = client.query.metric(...)
        print(result.to_dataframe())
except AuthenticationError:
    print("Token 失效，请重新获取")
except MetricNotFoundError as e:
    print(f"指标 {e.resource_id} 不存在")
```

---

## 检查清单

- [x] 架构层次清晰（门面 → 资源命名空间 → HTTP）
- [x] 异常体系完整（资源特化异常树）
- [x] 测试策略合理（pytest-httpx mock + 集成测试 opt-in）
- [x] 范围边界明确（IN SCOPE / OUT OF SCOPE）
- [x] 设计决策有"决策/理由/代价"三段论
- [ ] AsyncHTTPClient 定义缺失（必须修复）
- [ ] API 端点路径映射未定义（必须修复）
- [ ] 线程安全未声明（必须修复）
- [ ] pyproject.toml 配置缺失（必须修复）
- [ ] 退避策略参数未完整定义
- [ ] ValidationError 未携带结构化错误详情
- [ ] async 未启用时的错误类型太宽泛
- [ ] 分页 helper 的 mapper 参数设计可简化
- [ ] logging 设计零说明
- [ ] from_env 环境变量未文档化
- [ ] 与 SuperSonic 版本兼容性未涉及

---

## 总结

总体评分：**7.5/10** — 架构思路和设计决策都很扎实，对标 ai-sdk 的策略正确。主要扣分在**实现细节缺失**：AsyncHTTPClient 未定义、端点路径未映射、pyproject.toml 零配置，这三个问题如果不在规格阶段补上，实现时会反复回来看文档找答案，规格的价值就打折了。

建议先修复 4 个[必须修复]项，[建议修改]项可以在实现过程中逐个澄清。整体来看，这份规格已经足够驱动 Phase 1 的开发启动——前提是把上面标红的缺口补上。
