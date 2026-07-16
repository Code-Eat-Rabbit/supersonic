# SuperSonic Python SDK Phase 1 实现计划 — 评审报告

> 评审对象：`docs/superpowers/plans/2026-07-16-python-sdk-phase1.md`（4598 行）
> 评审日期：2026-07-16
> 上次评审：`docs/superpowers/reviews/2026-07-16-python-sdk-design-review.md`（4 必须修复 + 6 建议修改）
> 评审维度：规格覆盖 / TDD 完整性 / 任务粒度 / 可行性 / 依赖顺序 / 代码质量

---

## 整体评价

这是一份**非常扎实的实现计划**，完全符合 `writing-plans` 技能的"禁止占位符"标准——24 个任务，每个任务都有完整的代码块、精确的测试和 commit 命令。对比我第一次对 spec 的评审发现的 14 个问题，这份计划**逐个击破**：

| 上次 spec 评审的问题 | 计划中的解决方案 | 任务 |
|---|---|---|
| AsyncHTTPClient 未定义 | 完整实现，含懒加载 | 任务 7 |
| API 端点路径未映射 | `api/paths.py` 集中定义全部 37 个端点 | 任务 10 |
| 线程安全未讨论 | Client docstring 明确声明 NOT thread-safe | 任务 21 |
| pyproject.toml 零配置 | 完整的 toml，含 extras/ruff/mypy/pytest | 任务 1 |
| 退避策略参数缺失 | `RetryConfig` 含 jitter/max_backoff/retry_after | 任务 4 |
| ValidationError 不解析 body | `_parse_field_errors` 支持 3 种格式 | 任务 6 |
| async 未启用抛 RuntimeError | `AsyncNotEnabledError` 专用异常 | 任务 2 |
| 分页 mapper 设计不优 | `Page.from_response(item_model=T)` | 任务 8 |
| logging 零说明 | 完整 logger + header redaction | 任务 5 |
| from_env 环境变量未文档化 | README 环境变量表 | 任务 24 |
| 测试 URL 硬编码 | `base_url` + `*_paths` fixtures | 任务 10 |
| format.py 复用路径不明 | CLI 复用已明确 | 不变 |
| quickstart 缺错误处理 | 完整 error handling | 任务 24 |
| 版本兼容性未涉及 | README 提及但未深度处理 | 中等 |

这说明了**规格评审的价值闭环**：spec 问题 → plan 修复 → 可执行的 TDD 任务。

总分：**8.5/10**，扣分在 TDD 排序问题和 async 方法缺失。

---

## 值得学习的地方

1. **TDD 粒度极细**。每个任务严格遵循"编写失败测试 → 运行验证失败 → 实现最小代码 → 运行验证通过 → commit"。这不是形式上的 TDD，是真正可执行的——测试代码给出了，预期失败原因给出了（`ModuleNotFoundError: No module named 'supersonic.exceptions'`）。

2. **依赖图清晰且经过深思**。任务依赖图（第 92-125 行）不是简单的线性编排——任务 6（HTTPClient）和任务 7（AsyncHTTPClient）并行推进，任务 11-13（模型）和任务 10（paths）可同时进行，最终汇合到任务 14（Client）。

3. **`api/paths.py` 是个很好的设计决策**。37 个端点集中定义，测试和源码共享常量。如果 SuperSonic 改端点名，只改一个文件。这是对 spec 评审中"端点路径未定义"问题的最优解。

4. **`_parse_field_errors` 支持 3 种格式**（列表格式、字典格式、无结构化错误），比我在 spec 评审中建议的更灵活。这说明计划不是机械翻译 spec，而是在实现层面做了增强。

5. **自检章节（第 4547-4585 行）质量很高**。对照 spec 逐条检查覆盖度、占位符扫描、类型一致性——这些都是 `writing-plans` 技能要求的自检项，执行得很到位。

---

## 主要问题

### [必须修复] 1. 任务 14-20 的 TDD 流程被破坏

**位置**：任务 14 第 3317-3321 行

> 此任务的测试依赖 `SupersonicClient`，但 Client 在任务 21 实现。
> 此任务的测试在此阶段会持续失败（直到任务 21 完成 Client），属预期。
> **推荐**：本任务先实现 query.py 但跳过运行测试

**这是整个计划中最大的结构性问题。** 任务 14-20（QueryAPI + 6 个元数据 API）共 7 个任务、几十个测试，全部依赖还没写的 `SupersonicClient`。按照当前顺序：

- 任务 14 写完 QueryAPI → 无法验证测试通过（Client 不存在）
- 任务 15-20 写完 6 个元数据 API → 无法验证测试通过
- 任务 21 写完 Client → 一次性跑 7 个任务的测试，如果出错需要回溯

这违反了 `writing-plans` 技能的核心理念："每步是一个操作（2-5 分钟）— 编写测试 → 确认失败 → 实现 → 确认通过"。你现在是"写完所有代码 → 一次性验证"，回滚成本太高。

**根本原因**：API 类的测试直接使用了 `client.query.sql(...)`，而 API 类的构造函数只需要 `(http, async_http)`。完全可以**在任务 7（HTTPClient 就绪）之后，直接用 mock HTTPClient 测试 API 类**，无需等 Client 门面。

**建议**：两种修复方案，推荐 A：

**方案 A（推荐）：API 测试改为直接注入 mock HTTPClient**

```python
# 当前（依赖 Client）
client = SupersonicClient(host="http://test", token="jwt")
result = client.query.sql("SELECT 1")

# 改为（直接测 API 类，不依赖 Client）
from supersonic.common.http import HTTPClient
from supersonic.api.query import QueryAPI

http = HTTPClient(base_url="http://test", auth=TokenAuth(token="jwt"), retry=RetryConfig(max_retries=0))
api = QueryAPI(http=http, async_http=None)
result = api.sql("SELECT 1")
```

这样任务 14 可以在任务 10 之后立即独立测试，无需等到任务 21。

**方案 B**：调整任务顺序，把任务 21（Client）提前到任务 14 之前。但这要求所有 API 类先写个骨架——更复杂。

---

### [必须修复] 2. Async 方法全是 `NotImplementedError`

**位置**：任务 15 第 3424-3431 行

```python
async def alist(self, **kwargs) -> Page[Metric]:
    if self._async_http is None:
        raise AsyncNotEnabledError()
    raise NotImplementedError("async list TODO in implementation phase")
```

所有 6 个元数据 API 类的 async 方法（`alist`、`aget`、`acreate` 等 30+ 方法）都是 `NotImplementedError`，且没有后续任务来补全。

**影响**：计划结尾自检写道"37 方法全实现"——但 async 版本没实现。`enable_async=True` 用户调用 `client.metrics.alist()` 会直接 crash。

**建议**：两种方案：
- **方案 A**：给每个 API 类增加 async 方法实现的任务（每个资源类约 15 分钟），任务 14b/15b/.../20b
- **方案 B**：声明 Phase 1 不包含 async 元数据方法，仅 QueryAPI 有 async 支持（当前 QueryAPI 的 asql 是完整实现）

方案 B 更务实——async 查询是核心场景，async CRUD 优先级低。但要**在 out-of-scope 中明确声明**。

---

### [建议修改] 3. `ResourceNotFoundError` 构造函数不一致

**位置**：任务 2 第 492-501 行 vs 任务 6 第 1365-1368 行

任务 2 中 `ResourceNotFoundError.__init__` 的签名是：

```python
class ResourceNotFoundError(SupersonicError):
    def __init__(self, resource_type: str, resource_id: int | str) -> None:
```

但任务 6 的 `_handle_response` 调用时传了三个参数：

```python
if exc_cls is ResourceNotFoundError:
    raise ResourceNotFoundError(resource_type or "resource", resource_id or "")
```

而子类（如 `MetricNotFoundError`）的构造函数是：

```python
class MetricNotFoundError(ResourceNotFoundError):
    def __init__(self, resource_id: int | str) -> None:
        super().__init__("metric", resource_id)
```

这里有一个细微的不一致：`_handle_response` 中 `resource_id` 可能为 `""`（空字符串），但类型标注是 `int | str`。如果 `resource_id` 是空字符串，`MetricNotFoundError` 的 `str(err)` 断言 `"42" in str(err)`（任务 2 测试 358 行）就会失败。 不过在实际使用中，资源类调用 `http.request(resource_id=metric_id)` 时总是传 int，所以不会触发。建议统一签名或加防御。

---

### [建议修改] 4. MetricAPI.list 的 `resource_type` 传递可能引起误判

**位置**：任务 15 第 3369-3373 行

```python
body = self._http.request(
    "POST", MetricPaths.LIST,
    params=params,
    resource_type="metric",    # ← 这里
)
```

`list()` 操作传了 `resource_type="metric"`，但 list 是一个**集合查询**，不太可能返回 404（最坏情况是空列表）。但如果 SuperSonic 的 list 端点对不存在的 model_id 返回 404，就会被映射为 `MetricNotFoundError`，而实际语义是"该 model 下没有 metric"或"model 不存在"。

**建议**：list 操作不传 `resource_type`，让 404 落到通用的 `ResourceNotFoundError`，或者确认 SuperSonic 的 list 端点不会返回 404。

---

### [建议修改] 5. 缺少类型检查验证任务

**位置**：任务 23 第 4304-4313 行

类型检查（`mypy src/`）和 lint（`ruff check`）放在任务 23（集成测试）之后才运行，但：

- `@overload` 的 `Literal[True]`/`Literal[False]` 类型收窄需要 mypy 验证
- `Page[Metric].from_response(...)` 的泛型推断需要验证
- `ConnectionError` 覆盖 Python 内置名需要确认影响范围

**建议**：在任务 13（模型全部完成）之后增加一个**类型检查里程碑**：

```bash
# 任务 13b：类型检查验证
mypy src/supersonic/models/ --strict
ruff check src/supersonic/models/
```

在任务 21（Client 完成）之后再全量跑一次。这样错误早点暴露，不用攒到最后。

---

### [建议修改] 6. `utils/format.py` 的 `import re` 放在文件底部

**位置**：任务 22 第 4225-4227 行

```python
import re  # noqa: E402 (放底部避免顶部循环引用假象，实际不影响)
```

注释说"避免顶部循环引用假象"——但实际上 `format.py` 从 `supersonic.models.query` 导入，`models.query` 从 `models.base` 导入，不存在循环引用。`import re` 放底部是纯代码异味。

**建议**：移到文件顶部，删除 `noqa: E402`。

---

### [建议修改] 7. 任务 15-20 的 async 方法不应标 `NotImplementedError` 又设 guard

**位置**：任务 15 第 3425-3429 行

```python
async def alist(self, **kwargs) -> Page[Metric]:
    if self._async_http is None:
        raise AsyncNotEnabledError()
    raise NotImplementedError(...)
```

如果 async_http 是 None，raise `AsyncNotEnabledError`——这是对的。但如果 async_http 不是 None（用户确实 `enable_async=True`），就会触发 `NotImplementedError`。更好的做法是：在 Phase 1 中干脆不定义这些 async 方法，等补全时再加。或者至少抛出更明确的错误：

```python
async def alist(self, **kwargs) -> Page[Metric]:
    if self._async_http is None:
        raise AsyncNotEnabledError()
    raise NotImplementedError(
        "Async metadata CRUD is not available in Phase 1. "
        "Use sync methods or check for updates."
    )
```

---

### [仅供参考] 8. 任务编号与文件注释不完全匹配

**位置**：任务 1 文件结构注释 vs 实际任务编号

第 31 行标注 `client.py` 为任务 14，但实际 `client.py` 在任务 21 实现。第 32-36 行标注 `common/` 各文件为任务 6/7/8/9，但计划中：
- `common/__init__.py` 在任务 5（logging）而非任务 6
- `common/logging.py` 在任务 5 而非任务 6
- `common/http.py` 在任务 6 + 任务 7

文件结构注释与实际任务分配的错位会误导只看文件树的读者。建议统一。

---

### [仅供参考] 9. 数据库 `create` 和 `update` 共用同一路径

**位置**：任务 10 第 2008-2010 行

```python
CREATE = "/api/semantic/database/createOrUpdateDatabase"
UPDATE = "/api/semantic/database/createOrUpdateDatabase"  # 同路径
```

这是 SuperSonic API 的真实行为（upsert 语义），但 SDK 层面 `DatabasesAPI.create()` 和 `DatabasesAPI.update()` 调同一个端点会让人疑惑——请求体的差异如何区分 create 和 update 语义？建议在 DatabasePaths 的注释中说明。

---

### [仅供参考] 10. 计划中引用的规格行号可能不准确

**位置**：多处（如任务 2 "§ 异常树（第 420-480 行）"）

规格文档 `2026-07-16-python-sdk-design.md` 只有 884 行。第 420-480 行对应的是规格中异常树部分——行号大致正确。但在 4598 行计划中混用"规格第 X 行"和"计划第 X 行"的引用，执行者可能混淆。建议统一用章节名而非行号引用。

---

## 任务粒度分析

| 任务 | 估算时间 | 粒度评价 |
|---|---|---|
| 任务 1（项目骨架） | 10 min | 合适 |
| 任务 2（异常体系） | 15 min | 合适 |
| 任务 3（Auth） | 10 min | 合适 |
| 任务 4（Config + Retry） | 20 min | 合适（含退避算法测试） |
| 任务 5（Logging） | 10 min | 合适 |
| 任务 6（HTTPClient） | 25 min | **偏大**（含 retry/test/error mapping，可拆） |
| 任务 7（AsyncHTTPClient） | 15 min | 合适 |
| 任务 8（Pagination） | 10 min | 合适 |
| 任务 9（CamelModel） | 5 min | 合适 |
| 任务 10（Paths + Fixtures） | 15 min | 合适 |
| 任务 11（Query Models） | 20 min | 合适 |
| 任务 12（Metadata Models） | 15 min | 合适 |
| 任务 13（Models re-export） | 5 min | 合适 |
| 任务 14（QueryAPI） | 20 min | 合适（但不独立可测） |
| 任务 15-20（6 API 类） | 60 min | **偏大**，建议拆成 6 个独立任务 |
| 任务 21（Client 门面） | 15 min | 合适 |
| 任务 22（Utils） | 15 min | 合适 |
| 任务 23（集成测试） | 10 min | 合适 |
| 任务 24（Examples） | 15 min | 合适 |

**总计估算**：约 5.5 小时连续工作时间，或 2-3 个分散的会话。

---

## 执行风险

1. **任务 14-20 的批量验证风险**（最高）— 已在上方详述，7 个任务的测试一次性验证，失败时需要大量回溯。
2. **async 方法缺失风险**（高）— 30+ 个方法标记 `NotImplementedError`，无后续任务补全。
3. **SuperSonic API 端点名猜测风险**（中）— `api/paths.py` 的 37 个路径是推断的，没有对照 SuperSonic 源码验证过。如果实际端点名不同（如 `createMetric` vs `create`），需要改 paths.py。
4. **pytest-httpx mock URL 匹配风险**（低）— 已用 `base_url + paths` fixtures，风险可控。

---

## 检查清单

- [x] 规格覆盖完整（24 任务覆盖 spec 全部需求）
- [x] 无占位符（每个代码步骤都有完整代码）
- [x] 类型一致性检查通过（自检章节已验证）
- [x] 依赖图合理
- [ ] 任务 14-20 TDD 流程被破坏（必须修复）
- [ ] 30+ async 方法为 NotImplementedError（必须修复）
- [ ] ResourceNotFoundError 构造函数签名不一致
- [ ] MetricAPI.list 的 resource_type 可能误判
- [ ] 类型检查应提前到任务 13 之后
- [ ] utils/format.py 的 import re 位置不当
- [ ] 任务 15-20 可进一步拆分

---

## 总结

这份计划**已经达到可执行标准**。两个[必须修复]问题（TDD 流程破坏 + async 方法缺失）修复后即可放心交付子代理执行。估计修复工作量约 1-2 小时（主要是改写 API 测试和补 async 方法）。

与第一次 spec 评审形成完整闭环：spec 中发现 14 个问题 → plan 修复了 14 个 → plan 中又发现 10 个新问题 → 修复后进入执行阶段。这就是"规格 → 评审 → 计划 → 评审 → 执行"的工程化流程价值。
