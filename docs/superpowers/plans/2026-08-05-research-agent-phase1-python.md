# 深度研究集成 — Phase 1：Python 侧基础设施实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在 miro-flow-solution 新增 REST `/v1/research/jobs` 异步 job 层，让 Java 网关能通过 HTTP 接入深度研究 pipeline。完成本 Phase 后，Python 侧能接收 POST 创建 job、asyncio 后台执行、SQLite 持久化状态、GET 返回状态，并具备 service token 鉴权、启动恢复、终态不可变、硬超时四层健壮性保障。

**架构：** FastAPI 新增 router 挂载到现有 app；SQLite 单文件存储 job 元数据（不带大字段）；ReportStore 抽象（当前 FileSystemReportStore 实现）把完整报告写到 `outputs/{tenant}/research_jobs/{job_id}.json`；IntentClassifier 启动时扫描 `domains/*.md` frontmatter 动态构建分类清单；pipeline_adapter 用 `asyncio.wait_for` 包装 `execute_task_pipeline` 实现 14 分钟硬超时；启动时 `recover_stale_jobs` 把 PENDING/RUNNING 标 FAILED。

**技术栈：** Python 3.12+、FastAPI、asyncio、SQLite3（stdlib）、Pydantic、Hydra（现有）、pytest（现有）

**规格出处：** `docs/resume/interview/深度研究/01-集成设计.md` §7（Python 侧设计）

**前置约束（来自评审 + 用户决策）：**
- 不复用 SuperSonic user JWT，用独立 service token（§7.10）
- 终态不可变三层守卫：Python `JobStore.update` + Java `mergeStatus` + SQL `WHERE` 子句（§4.3）
- Python 14min 硬超时是权威，Java 15min 仅兜底（§4.4）
- IntentClassifier 启动时扫描 domains/ 目录，新增数据域零代码改动（§7.4）
- 完整报告不存 SQLite 大字段，存 JSON 文件 + `report_uri` 索引（§7.2/§7.3）
- demo 期不实现断点续传、任务取消、任务列表查询（§2.3）

**依赖检查（实现前必做）：**
- `execute_task_pipeline` 的真实签名（规格 §7.8 已写，但实现时务必 `grep -rn "def execute_task_pipeline" src/core/pipeline.py` 核对参数名和顺序）
- `compose_config` / `create_pipeline_components` 当前位置：评审指出 `server/bridge/config_loader.py` 不存在，需把 `StreamingTaskRunner._compose_config` 提升为模块级函数（任务 11 会处理）

**Phase 1 范围：** Python 侧完整实现（13 个任务），产出可独立通过 FastAPI TestClient 测试的 REST 服务。Java/前端在 Phase 2/3 实现。

---

## 文件结构

```
miro-flow-solution/
└── server/
    ├── app.py                              [修改] 挂载 REST router + startup 事件 + trace_id middleware
    ├── rest/                               [新增目录]
    │   ├── __init__.py                     [新增] 空
    │   ├── models.py                       [新增] Pydantic 请求/响应模型
    │   ├── deps.py                         [新增] FastAPI dependency: verify_service_token
    │   ├── routes.py                       [新增] FastAPI router: POST/GET /v1/research/jobs
    │   ├── job_store.py                    [新增] SQLite + 启动恢复 + 终态不可变
    │   ├── report_store.py                 [新增] ReportStore Protocol + FileSystemReportStore
    │   ├── intent.py                       [新增] IntentClassifier + DomainMeta + frontmatter 扫描
    │   ├── research_directive.py           [新增] ResearchDirective 拼核心+领域片段
    │   ├── query_rewriter.py               [新增] QueryRewriter 按 type 分发
    │   ├── length_control.py               [新增] 句子边界截断
    │   ├── logging_config.py               [新增] trace_id filter + research logger
    │   ├── pipeline_timeout.py             [新增] asyncio.wait_for 包装 + PipelineTimeoutError
    │   ├── pipeline_adapter.py             [新增] run_pipeline_async 整合
    │   ├── config_loader.py                [新增] 模块级 compose_config（从 runner.py 提升）
    │   └── research_prompts/               [新增目录]
    │       ├── financial_analyst.md        [新增] 核心框架（四步归因法）
    │       ├── academic.md                 [新增] 学术研究框架
    │       ├── default.md                  [新增] 通用
    │       └── domains/                    [新增目录]
    │           ├── _template.md            [新增] frontmatter 规范 + 新增领域指南
    │           ├── corporate_finance.md    [新增] 公司金融片段（含估值 opt-in）
    │           ├── macroeconomy.md         [新增] 宏观经济片段
    │           ├── green_economy.md        [新增] 绿色经济片段
    │           └── industry_analysis.md    [新增] 行业分析片段
    └── tests/rest/                         [新增目录]
        ├── __init__.py
        ├── conftest.py                     [新增] TestClient fixture + 临时 SQLite
        ├── test_length_control.py
        ├── test_report_store.py
        ├── test_job_store.py
        ├── test_intent.py
        ├── test_query_rewriter.py
        ├── test_research_directive.py
        ├── test_routes.py
        ├── test_pipeline_timeout.py
        └── test_pipeline_adapter.py
```

**职责锁定**：
- `models.py` 只定义 Pydantic 类型，无业务逻辑
- `deps.py` 只提供 FastAPI dependency 函数
- `routes.py` 只做 HTTP 入口参数解析和调度，不写业务
- `job_store.py` 只管 SQLite CRUD + 终态守卫，不调 LLM、不写文件
- `report_store.py` 只管 JSON 文件读写，不关心状态机
- `intent.py` 只做分类，不改 query、不拼 prompt
- `research_directive.py` 只拼 prompt 字符串，不调度执行
- `pipeline_adapter.py` 是编排器，调用上述所有组件
- 每个文件 < 200 行，单一职责

---

## 任务 1：长度控制（无外部依赖，最简单的 TDD 起点）

**文件：**
- 创建：`server/rest/length_control.py`
- 测试：`server/tests/rest/test_length_control.py`

- [ ] **步骤 1：编写失败的测试**

```python
# server/tests/rest/test_length_control.py
import pytest
from server.rest.length_control import enforce_length_budget


class TestEnforceLengthBudget:
    def test_short_report_unchanged(self):
        """短报告（在预算内）原样返回"""
        report = "这是一份短报告。共三句话。结束。"
        result = enforce_length_budget(report, budget=900)
        assert result == report

    def test_within_20_percent_buffer_unchanged(self):
        """报告在预算 × 1.2 内，允许浮动，不截断"""
        # 构造 1000 字的报告（budget=900, 1.2x=1080，所以 1000 不截断）
        report = "句子一。" * 200  # 1000 字
        result = enforce_length_budget(report, budget=900)
        assert result == report

    def test_over_budget_truncates_at_sentence_boundary(self):
        """超预算时按句子边界截断，不切断句子"""
        report = "第一句。" * 300  # 1500 字
        result = enforce_length_budget(report, budget=900)
        # 截断后应该比原报告短
        assert len(result) < len(report)
        # 截断后应该以句号结尾或省略提示结尾
        assert result.endswith("。") or "已省略" in result

    def test_truncated_adds_ellipsis_hint(self):
        """截断后追加省略提示"""
        report = "这是一句话。" * 300
        result = enforce_length_budget(report, budget=100)
        assert "已省略" in result or "…" in result

    def test_no_truncation_marker_when_not_truncated(self):
        """未截断时不应该出现省略提示"""
        report = "短报告。"
        result = enforce_length_budget(report, budget=900)
        assert "已省略" not in result
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd /Users/yourton_ma/workspace/agent_project/research-agent/miro-flow-solution && python -m pytest server/tests/rest/test_length_control.py -v`

预期：FAIL，报错 `ModuleNotFoundError: No module named 'server.rest.length_control'`

- [ ] **步骤 3：编写最少实现代码**

```python
# server/rest/length_control.py
"""报告长度控制：句子边界感知截断

设计原则（spec §7.7）：
- Prompt 软引导（task description 内已要求 length_budget 字数）
- 产出后硬兜底（此处）：按句子边界截断，不破坏内容
- 允许 20% 浮动，避免勉强
"""
import re

SENTENCE_BOUNDARY = re.compile(r'(?<=[。！？\n])')


def enforce_length_budget(report: str, budget: int = 900) -> str:
    """按句子边界截断到 budget 字数以内，保留句子完整性。

    Args:
        report: 完整报告文本
        budget: 字数预算（默认 900）

    Returns:
        截断后的报告；如未超预算则原样返回
    """
    if len(report) <= int(budget * 1.2):
        return report

    parts = SENTENCE_BOUNDARY.split(report)
    result: list[str] = []
    total = 0
    for part in parts:
        if total + len(part) > budget:
            break
        result.append(part)
        total += len(part)

    summary = "".join(result).rstrip()
    if len(summary) < len(report):
        summary += "\n\n…（已省略部分细节，完整报告见 report_full）"
    return summary
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd /Users/yourton_ma/workspace/agent_project/research-agent/miro-flow-solution && python -m pytest server/tests/rest/test_length_control.py -v`

预期：5 passed

- [ ] **步骤 5：Commit**

```bash
cd /Users/yourton_ma/workspace/agent_project/research-agent/miro-flow-solution
git add server/rest/length_control.py server/tests/rest/test_length_control.py
git commit -m "feat(research): add sentence-boundary length control"
```

---

## 任务 2：ReportStore 抽象 + FileSystemReportStore 实现

**文件：**
- 创建：`server/rest/report_store.py`
- 测试：`server/tests/rest/test_report_store.py`

**spec 出处：** §7.3

- [ ] **步骤 1：编写失败的测试**

```python
# server/tests/rest/test_report_store.py
import json
import pytest
from pathlib import Path
from server.rest.report_store import FileSystemReportStore


@pytest.fixture
def store(tmp_path: Path) -> FileSystemReportStore:
    return FileSystemReportStore(base_dir=str(tmp_path))


class TestFileSystemReportStore:
    def test_save_writes_json_and_returns_uri(self, store: FileSystemReportStore, tmp_path: Path):
        payload = {"job_id": "j1", "report_markdown": "# Hello"}
        uri = store.save("j1", "default", payload)

        # URI 形如 fs://...
        assert uri.startswith("fs://")
        # 文件实际存在
        path = tmp_path / "default" / "research_jobs" / "j1.json"
        assert path.exists()
        # 内容是合法 JSON
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["job_id"] == "j1"
        assert data["report_markdown"] == "# Hello"

    def test_get_returns_payload(self, store: FileSystemReportStore):
        payload = {"job_id": "j2", "report_markdown": "x"}
        store.save("j2", "default", payload)

        got = store.get("j2", "default")
        assert got is not None
        assert got["job_id"] == "j2"

    def test_get_missing_returns_none(self, store: FileSystemReportStore):
        assert store.get("nonexistent", "default") is None

    def test_tenant_isolation_by_subdirectory(self, store: FileSystemReportStore, tmp_path: Path):
        """不同租户落到不同子目录"""
        store.save("j1", "tenant_a", {"job_id": "j1"})
        store.save("j1", "tenant_b", {"job_id": "j1"})

        path_a = tmp_path / "tenant_a" / "research_jobs" / "j1.json"
        path_b = tmp_path / "tenant_b" / "research_jobs" / "j1.json"
        assert path_a.exists()
        assert path_b.exists()
        # 同一 job_id 在不同租户下互不覆盖
        assert store.get("j1", "tenant_a") is not None
        assert store.get("j1", "tenant_b") is not None

    def test_delete_removes_file(self, store: FileSystemReportStore):
        store.save("j3", "default", {"job_id": "j3"})
        store.delete("j3", "default")
        assert store.get("j3", "default") is None

    def test_delete_missing_is_noop(self, store: FileSystemReportStore):
        # 不应抛异常
        store.delete("nonexistent", "default")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd /Users/yourton_ma/workspace/agent_project/research-agent/miro-flow-solution && python -m pytest server/tests/rest/test_report_store.py -v`

预期：FAIL，`ModuleNotFoundError`

- [ ] **步骤 3：编写最少实现代码**

```python
# server/rest/report_store.py
"""报告存储抽象（spec §7.3）

设计动机：
- JSON 含结构化字段（report_markdown + boxed_answer + metadata），
  未来迁移 MongoDB/PostgreSQL JSONB 格式不变
- 按 tenant 分目录，未来多租户自然隔离
- 开发者可直接打开 JSON 文件调试
"""
import json
import pathlib
from typing import Protocol


class ReportStore(Protocol):
    """报告存储抽象接口（演进锚点 #1）"""

    def save(self, job_id: str, tenant_id: str, payload: dict) -> str:
        """保存报告，返回 URI（如 fs://path 或 mongo://...）"""
        ...

    def get(self, job_id: str, tenant_id: str = "default") -> dict | None:
        """读取报告；不存在返回 None"""
        ...

    def delete(self, job_id: str, tenant_id: str = "default") -> None:
        """删除报告；不存在时 no-op"""
        ...


class FileSystemReportStore:
    """当前实现：JSON 文件存到 {base_dir}/{tenant_id}/research_jobs/{job_id}.json"""

    def __init__(self, base_dir: str = "outputs"):
        self.base_dir = pathlib.Path(base_dir)

    def _path_for(self, tenant_id: str, job_id: str) -> pathlib.Path:
        return self.base_dir / tenant_id / "research_jobs" / f"{job_id}.json"

    def save(self, job_id: str, tenant_id: str, payload: dict) -> str:
        path = self._path_for(tenant_id, job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return f"fs://{path}"

    def get(self, job_id: str, tenant_id: str = "default") -> dict | None:
        path = self._path_for(tenant_id, job_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def delete(self, job_id: str, tenant_id: str = "default") -> None:
        path = self._path_for(tenant_id, job_id)
        if path.exists():
            path.unlink()
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd /Users/yourton_ma/workspace/agent_project/research-agent/miro-flow-solution && python -m pytest server/tests/rest/test_report_store.py -v`

预期：6 passed

- [ ] **步骤 5：Commit**

```bash
cd /Users/yourton_ma/workspace/agent_project/research-agent/miro-flow-solution
git add server/rest/report_store.py server/tests/rest/test_report_store.py
git commit -m "feat(research): add ReportStore protocol with FileSystemReportStore"
```

---

## 任务 3：JobStore SQLite + 终态不可变 + 启动恢复

**文件：**
- 创建：`server/rest/job_store.py`
- 测试：`server/tests/rest/test_job_store.py`

**spec 出处：** §7.2（schema）、§7.9（终态不可变 + 启动恢复）、§4.3（终态不可变约束）

- [ ] **步骤 1：编写失败的测试**

```python
# server/tests/rest/test_job_store.py
import pytest
from datetime import datetime, timezone
from server.rest.job_store import JobStore, JobRecord, TERMINAL_STATUSES


@pytest.fixture
def store(tmp_path) -> JobStore:
    return JobStore(db_path=str(tmp_path / "test.db"))


def _make_record(job_id: str = "j1", status: str = "PENDING") -> JobRecord:
    now = datetime.now(timezone.utc).isoformat()
    return JobRecord(
        job_id=job_id,
        tenant_id="default",
        trace_id="trace_x",
        task="测试任务",
        context="上下文",
        research_type="default",
        data_domain="unknown",
        config_file_name="agent_llm_gpt5",
        status=status,
        created_at=now,
        updated_at=now,
    )


class TestJobStoreCRUD:
    def test_create_and_get(self, store: JobStore):
        rec = _make_record()
        assert store.create(rec) is True
        got = store.get("j1")
        assert got is not None
        assert got.job_id == "j1"
        assert got.status == "PENDING"

    def test_get_missing_returns_none(self, store: JobStore):
        assert store.get("nonexistent") is None

    def test_list_by_status_in(self, store: JobStore):
        store.create(_make_record("j1", "PENDING"))
        store.create(_make_record("j2", "RUNNING"))
        store.create(_make_record("j3", "COMPLETED"))

        active = store.list_by_status_in(["PENDING", "RUNNING"])
        ids = {r.job_id for r in active}
        assert ids == {"j1", "j2"}


class TestTerminalImmutability:
    """spec §4.3 / §7.9：终态不可变"""

    def test_update_to_completed_blocks_flip_to_failed(self, store: JobStore):
        """COMPLETED 后不允许反向迁移到 FAILED"""
        store.create(_make_record("j1", "RUNNING"))
        # 标 COMPLETED
        assert store.update("j1", status="COMPLETED", report_summary="x") is True
        # 尝试反向迁移到 FAILED → 应被拒绝
        result = store.update("j1", status="FAILED", error_msg="too late")
        assert result is False
        # 状态仍是 COMPLETED
        assert store.get("j1").status == "COMPLETED"

    def test_update_same_terminal_status_is_idempotent(self, store: JobStore):
        """同终态更新（幂等）允许"""
        store.create(_make_record("j1", "FAILED"))
        # 重复 FAILED + 更新 error_msg → 允许（业务字段更新）
        result = store.update("j1", status="FAILED", error_msg="more details")
        assert result is True

    def test_update_non_status_fields_always_allowed(self, store: JobStore):
        """非状态字段更新始终允许"""
        store.create(_make_record("j1", "COMPLETED"))
        result = store.update("j1", report_summary="new summary")
        assert result is True
        assert store.get("j1").report_summary == "new summary"


class TestStartupRecovery:
    """spec §7.9：启动恢复"""

    def test_recover_stale_jobs_marks_pending_and_running_as_failed(self, store: JobStore):
        store.create(_make_record("j1", "PENDING"))
        store.create(_make_record("j2", "RUNNING"))
        store.create(_make_record("j3", "COMPLETED"))
        store.create(_make_record("j4", "FAILED"))

        store.recover_stale_jobs()

        assert store.get("j1").status == "FAILED"
        assert "runner restarted" in store.get("j1").error_msg
        assert store.get("j2").status == "FAILED"
        # 已终态的不动
        assert store.get("j3").status == "COMPLETED"
        assert store.get("j4").status == "FAILED"

    def test_recover_with_no_stale_jobs_is_noop(self, store: JobStore):
        store.create(_make_record("j1", "COMPLETED"))
        store.recover_stale_jobs()  # 不应抛异常
        assert store.get("j1").status == "COMPLETED"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest server/tests/rest/test_job_store.py -v`

预期：FAIL，`ModuleNotFoundError`

- [ ] **步骤 3：编写最少实现代码**

```python
# server/rest/job_store.py
"""SQLite job 存储 + 终态不可变守卫 + 启动恢复（spec §7.2 / §7.9）

设计要点：
- SQLite 单文件，不引入外部 DB 进程
- 不存完整报告大字段（report_summary 是截断版小字段，report_uri 是路径索引）
- 终态不可变三层守卫之一（Python 层；Java mergeStatus + SQL WHERE 是另外两层）
- 启动恢复绕过终态校验，直接 UPDATE（stale 的不会是终态，但防御性编程）
"""
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = frozenset({"COMPLETED", "FAILED"})


@dataclass
class JobRecord:
    job_id: str
    tenant_id: str
    trace_id: str
    task: str
    context: str
    research_type: str
    data_domain: str
    config_file_name: str
    status: str
    report_summary: str | None = None
    report_uri: str | None = None
    error_msg: str | None = None
    created_at: str = ""
    updated_at: str = ""
    started_at: str | None = None
    completed_at: str | None = None


_SCHEMA = """
CREATE TABLE IF NOT EXISTS research_jobs (
    job_id           TEXT PRIMARY KEY,
    tenant_id        TEXT NOT NULL DEFAULT 'default',
    trace_id         TEXT,
    task             TEXT NOT NULL,
    context          TEXT,
    research_type    TEXT,
    data_domain      TEXT,
    config_file_name TEXT,
    status           TEXT NOT NULL,
    report_summary   TEXT,
    report_uri       TEXT,
    error_msg        TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    started_at       TEXT,
    completed_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_status        ON research_jobs(status);
CREATE INDEX IF NOT EXISTS idx_trace_id      ON research_jobs(trace_id);
CREATE INDEX IF NOT EXISTS idx_tenant_status ON research_jobs(tenant_id, status);
"""


class JobStore:
    def __init__(self, db_path: str = "server/rest/research_jobs.db"):
        self.db_path = db_path
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.executescript(_SCHEMA)

    def create(self, rec: JobRecord) -> bool:
        with self._conn() as c:
            try:
                c.execute(
                    """INSERT INTO research_jobs
                       (job_id, tenant_id, trace_id, task, context,
                        research_type, data_domain, config_file_name, status,
                        created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (rec.job_id, rec.tenant_id, rec.trace_id, rec.task, rec.context,
                     rec.research_type, rec.data_domain, rec.config_file_name, rec.status,
                     rec.created_at, rec.updated_at),
                )
                return True
            except sqlite3.IntegrityError:
                return False  # duplicate job_id

    def get(self, job_id: str) -> JobRecord | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM research_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        return self._row_to_record(row) if row else None

    def list_by_status_in(self, statuses: Iterable[str]) -> list[JobRecord]:
        statuses = list(statuses)
        if not statuses:
            return []
        placeholders = ",".join("?" * len(statuses))
        with self._conn() as c:
            rows = c.execute(
                f"SELECT * FROM research_jobs WHERE status IN ({placeholders})",
                statuses,
            ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def update(
        self,
        job_id: str,
        status: str | None = None,
        report_summary: str | None = None,
        report_uri: str | None = None,
        error_msg: str | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
    ) -> bool:
        """更新 job 状态/字段。终态不可变守卫：若已终态且试图翻转状态，拒绝。

        Returns:
            True 表示更新成功；False 表示被终态守卫拒绝。
        """
        # 终态守卫：只拒绝"终态 → 不同终态"的翻转
        if status is not None:
            current = self.get(job_id)
            if (
                current
                and current.status in TERMINAL_STATUSES
                and status != current.status
            ):
                logger.warning(
                    "reject status flip job=%s %s -> %s",
                    job_id, current.status, status,
                )
                return False

        # 构造 SET 子句（只更新非 None 的字段）
        sets: list[str] = []
        params: list = []
        if status is not None:
            sets.append("status = ?")
            params.append(status)
        if report_summary is not None:
            sets.append("report_summary = ?")
            params.append(report_summary)
        if report_uri is not None:
            sets.append("report_uri = ?")
            params.append(report_uri)
        if error_msg is not None:
            sets.append("error_msg = ?")
            params.append(error_msg)
        if started_at is not None:
            sets.append("started_at = ?")
            params.append(started_at)
        if completed_at is not None:
            sets.append("completed_at = ?")
            params.append(completed_at)
        if not sets:
            return True  # nothing to update

        sets.append("updated_at = ?")
        params.append(datetime.now(timezone.utc).isoformat())
        params.append(job_id)

        # SQL 级终态守卫（防多实例并发）
        sql = (
            f"UPDATE research_jobs SET {', '.join(sets)} "
            f"WHERE job_id = ? AND status NOT IN ('COMPLETED', 'FAILED')"
        )
        # 注意：同终态更新（status==current.status）允许通过，
        # 但 SQL WHERE 会拦——这是个已知 trade-off：
        # 我们在 Python 层已保证了不会反向翻转，SQL 层做最后一道兜底
        # 对"同终态业务字段更新"场景，由 _do_update_terminal_bypass 处理
        with self._conn() as c:
            cur = c.execute(sql, params)
            if cur.rowcount == 0 and status is None:
                # 纯业务字段更新但记录已终态 → 走 bypass 路径
                return self._update_bypass_terminal(job_id, sets[:-1], params[:-1])
            return cur.rowcount > 0 or status is None

    def _update_bypass_terminal(self, job_id: str, sets: list[str], params: list) -> bool:
        """允许在终态记录上更新业务字段（report_summary 等）"""
        if not sets:
            return True
        params.append(job_id)
        sql = f"UPDATE research_jobs SET {', '.join(sets)} WHERE job_id = ?"
        with self._conn() as c:
            c.execute(sql, params)
        return True

    def recover_stale_jobs(self) -> int:
        """spec §7.9 启动恢复：把所有 PENDING/RUNNING 标 FAILED。

        绕过终态守卫（stale 的不会是终态，但显式标记）。
        Returns: 恢复的记录数
        """
        stale = self.list_by_status_in(["PENDING", "RUNNING"])
        now = datetime.now(timezone.utc).isoformat()
        for rec in stale:
            with self._conn() as c:
                c.execute(
                    """UPDATE research_jobs
                       SET status='FAILED',
                           error_msg='runner restarted (process crashed or restarted)',
                           completed_at=?,
                           updated_at=?
                       WHERE job_id=?""",
                    (now, now, rec.job_id),
                )
            logger.warning(
                "recovered stale job %s", rec.job_id,
                extra={"trace_id": rec.trace_id},
            )
        return len(stale)

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> JobRecord:
        return JobRecord(
            job_id=row["job_id"],
            tenant_id=row["tenant_id"],
            trace_id=row["trace_id"],
            task=row["task"],
            context=row["context"],
            research_type=row["research_type"],
            data_domain=row["data_domain"],
            config_file_name=row["config_file_name"],
            status=row["status"],
            report_summary=row["report_summary"],
            report_uri=row["report_uri"],
            error_msg=row["error_msg"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
        )
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest server/tests/rest/test_job_store.py -v`

预期：8 passed

- [ ] **步骤 5：Commit**

```bash
git add server/rest/job_store.py server/tests/rest/test_job_store.py
git commit -m "feat(research): add SQLite JobStore with terminal-immutability + startup recovery"
```

---

## 任务 4：Pydantic 模型 + Service Token dependency

**文件：**
- 创建：`server/rest/models.py`
- 创建：`server/rest/deps.py`
- 测试：`server/tests/rest/test_deps.py`

**spec 出处：** §4.1（REST 契约）、§7.10（service token）

- [ ] **步骤 1：编写失败的测试**

```python
# server/tests/rest/test_deps.py
import os
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from server.rest.deps import verify_service_token


class TestVerifyServiceToken:
    def test_valid_token_passes(self, monkeypatch):
        monkeypatch.setenv("RESEARCH_SERVICE_TOKEN", "secret123")
        # 应该不抛异常
        assert verify_service_token(authorization="Bearer secret123") is True

    def test_invalid_token_raises_401(self, monkeypatch):
        monkeypatch.setenv("RESEARCH_SERVICE_TOKEN", "secret123")
        with pytest.raises(HTTPException) as exc:
            verify_service_token(authorization="Bearer wrong")
        assert exc.value.status_code == 401

    def test_missing_header_raises_401(self, monkeypatch):
        monkeypatch.setenv("RESEARCH_SERVICE_TOKEN", "secret123")
        with pytest.raises(HTTPException) as exc:
            verify_service_token(authorization=None)
        assert exc.value.status_code == 401

    def test_no_token_configured_raises_500(self, monkeypatch):
        monkeypatch.delenv("RESEARCH_SERVICE_TOKEN", raising=False)
        with pytest.raises(HTTPException) as exc:
            verify_service_token(authorization="Bearer x")
        # 没配置 token = 配置错误，应该是 500 而不是 401
        assert exc.value.status_code == 500
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest server/tests/rest/test_deps.py -v`

预期：FAIL，`ModuleNotFoundError`

- [ ] **步骤 3：编写实现代码**

```python
# server/rest/models.py
"""Pydantic 请求/响应模型（spec §4.1 REST 契约）"""
from pydantic import BaseModel, Field
from typing import Literal


class CreateJobRequest(BaseModel):
    job_id: str
    trace_id: str = ""
    tenant_id: str = "default"
    task: str
    context: str = ""
    config_file_name: str | None = None
    retrieval_mode: str = "hybrid"
    length_budget: int = 900


class CreateJobResponse(BaseModel):
    job_id: str
    status: Literal["PENDING"] = "PENDING"


class JobStatusResponse(BaseModel):
    job_id: str
    tenant_id: str
    trace_id: str | None = None
    research_type: str | None = None
    data_domain: str | None = None
    status: Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]
    report_summary: str | None = None
    report_full: str | None = None
    report_uri: str | None = None
    error_msg: str | None = None
    created_at: str
    updated_at: str
    started_at: str | None = None
    completed_at: str | None = None
```

```python
# server/rest/deps.py
"""FastAPI dependencies（spec §7.10 service token）"""
import os
from fastapi import Header, HTTPException


def verify_service_token(authorization: str | None = Header(default=None)) -> bool:
    """验证调用方持有正确的 service token。

    spec §7.10：独立 token，不复用 SuperSonic user JWT。
    SuperSonic JWT payload 含密码哈希，跨服务传递会泄漏。
    """
    expected_token = os.getenv("RESEARCH_SERVICE_TOKEN", "")
    if not expected_token:
        raise HTTPException(
            status_code=500,
            detail="RESEARCH_SERVICE_TOKEN not configured",
        )

    expected = f"Bearer {expected_token}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="invalid service token")
    return True
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest server/tests/rest/test_deps.py -v`

预期：4 passed

- [ ] **步骤 5：Commit**

```bash
git add server/rest/models.py server/rest/deps.py server/tests/rest/test_deps.py
git commit -m "feat(research): add Pydantic models and service-token dependency"
```

---

## 任务 5：Prompt 模板文件（financial_analyst / academic / default + 4 个 domain 片段）

**文件：**
- 创建：`server/rest/research_prompts/financial_analyst.md`
- 创建：`server/rest/research_prompts/academic.md`
- 创建：`server/rest/research_prompts/default.md`
- 创建：`server/rest/research_prompts/domains/_template.md`
- 创建：`server/rest/research_prompts/domains/corporate_finance.md`
- 创建：`server/rest/research_prompts/domains/macroeconomy.md`
- 创建：`server/rest/research_prompts/domains/green_economy.md`
- 创建：`server/rest/research_prompts/domains/industry_analysis.md`

**spec 出处：** §7.5（所有 prompt 内容已定稿）

**说明：** 这些是纯文本文件，不是代码。无单测，由任务 6 的 IntentClassifier 扫描测试覆盖。

- [ ] **步骤 1：创建 `financial_analyst.md`**

内容：直接复制 spec §7.5 中 `financial_analyst.md` 章节的 markdown 代码块内容（从 "你是一名**金融分析师**" 开始，到 "- ❌ 对推测性结论不标注置信度" 结束）。

- [ ] **步骤 2：创建 `academic.md`**

内容：直接复制 spec §7.5 `academic.md` 章节的内容（从 "你正在开展**学术研究**" 开始）。

- [ ] **步骤 3：创建 `default.md`**

内容：直接复制 spec §7.5 `default.md` 章节的内容（从 "你正在开展**深度研究**" 开始）。

- [ ] **步骤 4：创建 `domains/_template.md`**

内容：直接复制 spec §7.5 `_template.md` 的完整内容（含 frontmatter 规范和"新增步骤"）。

- [ ] **步骤 5：创建 4 个 domain 片段**

按 spec §7.5 的示例创建 `corporate_finance.md` / `macroeconomy.md` / `green_economy.md` / `industry_analysis.md`。

每个文件必须以下面的 frontmatter 开头（spec §7.4 frontmatter 规范）：

```markdown
---
name: <domain_name>                    # 必填，与文件名一致
description: <一句话描述>              # 必填
trigger_keywords: [<关键词列表>]       # 可选
priority: <整数>                       # 可选
---

（正文内容从 spec §7.5 对应 domain 片段复制）
```

参考 priority 取值（控制扫描后注入 prompt 的顺序）：
- `corporate_finance`: priority=30
- `macroeconomy`: priority=25
- `green_economy`: priority=20
- `industry_analysis`: priority=15

- [ ] **步骤 6：Commit**

```bash
git add server/rest/research_prompts/
git commit -m "feat(research): add prompt templates and pluggable domain snippets"
```

---

## 任务 6：IntentClassifier（含 frontmatter 扫描）

**文件：**
- 创建：`server/rest/intent.py`
- 测试：`server/tests/rest/test_intent.py`

**spec 出处：** §7.4（IntentClassifier + DomainMeta + `_scan_domains`）

**前置依赖：** 任务 5 完成（domains/*.md 文件存在）

- [ ] **步骤 1：编写失败的测试**

```python
# server/tests/rest/test_intent.py
import pytest
from pathlib import Path
from server.rest.intent import (
    IntentClassifier,
    DomainMeta,
    _scan_domains,
    _parse_frontmatter,
)


class FakeLLMClient:
    def __init__(self, response: str):
        self.response = response
        self.calls = []

    async def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self.response


class TestParseFrontmatter:
    def test_parses_basic_frontmatter(self, tmp_path: Path):
        md = tmp_path / "x.md"
        md.write_text(
            "---\n"
            "name: green_economy\n"
            "description: 碳排放/ESG\n"
            "trigger_keywords: [碳, ESG, 绿色]\n"
            "priority: 20\n"
            "---\n"
            "\n# Body",
            encoding="utf-8",
        )
        meta = _parse_frontmatter(md)
        assert meta is not None
        assert meta.name == "green_economy"
        assert meta.description == "碳排放/ESG"
        assert meta.trigger_keywords == ("碳", "ESG", "绿色")
        assert meta.priority == 20

    def test_missing_frontmatter_returns_none(self, tmp_path: Path):
        md = tmp_path / "x.md"
        md.write_text("just body, no frontmatter", encoding="utf-8")
        assert _parse_frontmatter(md) is None

    def test_no_priority_defaults_to_zero(self, tmp_path: Path):
        md = tmp_path / "x.md"
        md.write_text(
            "---\nname: x\ndescription: y\n---\nbody",
            encoding="utf-8",
        )
        meta = _parse_frontmatter(md)
        assert meta.priority == 0


class TestScanDomains:
    def test_scans_real_domains_directory(self):
        """扫描真实的 research_prompts/domains/ 目录"""
        domains = _scan_domains()
        # 应该扫到 spec 定义的核心 domain
        names = set(domains.keys())
        assert "corporate_finance" in names
        assert "macroeconomy" in names
        assert "green_economy" in names
        assert "industry_analysis" in names

    def test_skips_underscore_files(self, tmp_path: Path):
        """以 _ 开头的文件被跳过"""
        (tmp_path / "_template.md").write_text(
            "---\nname: template\ndescription: x\n---\n",
            encoding="utf-8",
        )
        (tmp_path / "real.md").write_text(
            "---\nname: real\ndescription: y\n---\n",
            encoding="utf-8",
        )
        # 模拟 _scan_domains 用 tmp_path（通过 monkeypatch DOMAIN_DIR）
        import server.rest.intent as intent_mod
        original = intent_mod.DOMAIN_DIR
        intent_mod.DOMAIN_DIR = tmp_path
        try:
            intent_mod._scan_domains.cache_clear()
            domains = intent_mod._scan_domains()
        finally:
            intent_mod.DOMAIN_DIR = original
            intent_mod._scan_domains.cache_clear()

        assert "real" in domains
        assert "template" not in domains

    def test_priority_orders_domains(self):
        """priority 高的 domain 先注入"""
        domains = _scan_domains()
        names = list(domains.keys())
        # corporate_finance priority=30 应该在 green_economy priority=20 前
        assert names.index("corporate_finance") < names.index("green_economy")


class TestIntentClassifier:
    @pytest.mark.asyncio
    async def test_classify_parses_json_response(self):
        client = FakeLLMClient('{"research_type": "financial_analyst", "data_domain": "green_economy"}')
        clf = IntentClassifier(client)
        rtype, ddomain = await clf.classify("比亚迪 2024 碳排放", "上下文")
        assert rtype == "financial_analyst"
        assert ddomain == "green_economy"

    @pytest.mark.asyncio
    async def test_classify_default_forces_unknown_domain(self):
        client = FakeLLMClient('{"research_type": "default", "data_domain": "green_economy"}')
        clf = IntentClassifier(client)
        rtype, ddomain = await clf.classify("随便", "")
        assert rtype == "default"
        # default type 强制 unknown domain
        assert ddomain == "unknown"

    @pytest.mark.asyncio
    async def test_classify_invalid_json_falls_back(self):
        client = FakeLLMClient("not json at all")
        clf = IntentClassifier(client)
        rtype, ddomain = await clf.classify("x", "")
        assert rtype == "default"
        assert ddomain == "unknown"

    @pytest.mark.asyncio
    async def test_classify_unknown_domain_falls_back(self):
        client = FakeLLMClient('{"research_type": "financial_analyst", "data_domain": "nonexistent"}')
        clf = IntentClassifier(client)
        rtype, ddomain = await clf.classify("x", "")
        assert rtype == "financial_analyst"
        assert ddomain == "unknown"  # nonexistent 不在 VALID_DOMAINS

    @pytest.mark.asyncio
    async def test_prompt_includes_scanned_domains(self):
        """prompt 应该包含扫描出来的 domain 描述"""
        client = FakeLLMClient('{"research_type": "default", "data_domain": "unknown"}')
        clf = IntentClassifier(client)
        await clf.classify("test", "")
        assert len(client.calls) > 0
        prompt = client.calls[0]
        # prompt 应该提到 green_economy
        assert "green_economy" in prompt
        assert "corporate_finance" in prompt
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest server/tests/rest/test_intent.py -v`

预期：FAIL，`ModuleNotFoundError`

- [ ] **步骤 3：编写实现代码**

```python
# server/rest/intent.py
"""意图分类器 + 数据领域扫描（spec §7.4）

核心设计：零代码扩展。
IntentClassifier 启动时扫描 domains/*.md frontmatter，自动构建 VALID_DOMAINS 和 PROMPT 取值清单。
新增数据域 = 在 domains/ 目录加一个带 frontmatter 的 .md 文件，零代码改动。
"""
import json
import logging
import pathlib
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import tuple  # noqa: F401 - py3.12 兼容

logger = logging.getLogger(__name__)

DOMAIN_DIR = pathlib.Path(__file__).parent / "research_prompts" / "domains"


@dataclass(frozen=True)
class DomainMeta:
    name: str
    description: str
    trigger_keywords: tuple[str, ...] = ()
    priority: int = 0

    def prompt_line(self) -> str:
        """生成 PROMPT 中的取值说明行"""
        keywords = "/".join(self.trigger_keywords[:3]) if self.trigger_keywords else ""
        suffix = f"（关键词：{keywords}）" if keywords else ""
        return f"- {self.name}：{self.description}{suffix}"


@lru_cache(maxsize=1)
def _scan_domains() -> dict[str, DomainMeta]:
    """启动时扫描 domains/ 目录，自动加载所有 domain 元数据。

    新增数据域 = 在 domains/ 目录加一个带 frontmatter 的 .md 文件。
    零代码改动，重启即生效（Demo 期不做热加载）。
    """
    domains: dict[str, DomainMeta] = {}
    if not DOMAIN_DIR.exists():
        logger.warning("DOMAIN_DIR not found: %s", DOMAIN_DIR)
        return domains

    for md_file in sorted(DOMAIN_DIR.glob("*.md")):
        if md_file.name.startswith("_"):
            continue  # 跳过 _template.md 等文档文件
        meta = _parse_frontmatter(md_file)
        if meta and meta.name:
            domains[meta.name] = meta

    # 按 priority 降序（高优先级先注入 prompt）
    return dict(sorted(domains.items(), key=lambda x: -x[1].priority))


def _parse_frontmatter(path: pathlib.Path) -> DomainMeta | None:
    """解析 frontmatter（YAML between --- and ---）。

    使用 stdlib 简单解析，不引入 PyYAML 依赖。
    支持：str / [list]。
    """
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return None

    frontmatter: dict = {}
    for line in match.group(1).split("\n"):
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if v.startswith("[") and v.endswith("]"):
            v = tuple(
                x.strip().strip('"').strip("'")
                for x in v[1:-1].split(",")
                if x.strip()
            )
        frontmatter[k] = v

    try:
        priority = int(frontmatter.get("priority", 0))
    except (ValueError, TypeError):
        priority = 0

    return DomainMeta(
        name=frontmatter.get("name", path.stem),
        description=frontmatter.get("description", ""),
        trigger_keywords=tuple(frontmatter.get("trigger_keywords", ())),
        priority=priority,
    )


class IntentClassifier:
    """研究任务路由分类器（spec §7.4）

    启动时扫描 domains/ 目录自动加载领域清单，新增数据域零代码改动。
    """

    PROMPT_TEMPLATE = """判断研究任务的类型和数据域，只返回一行 JSON：
{{
  "research_type": "financial_analyst" | "academic" | "default",
  "data_domain": {domain_options}
}}

分类规则：
- research_type=financial_analyst 时，data_domain 必须明确（除 unknown 外）
- research_type=academic 时，data_domain 可选（辅助文献检索策略）
- research_type=default 时，data_domain 必为 unknown

data_domain 取值含义：
{domain_list}
- unknown：无法识别

任务：{task}
上下文：{context_head}

JSON："""

    VALID_TYPES = frozenset({"financial_analyst", "academic", "default"})

    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.domains = _scan_domains()
        self.VALID_DOMAINS = frozenset(self.domains.keys()) | {"unknown"}
        logger.info(
            "IntentClassifier loaded %d domains: %s",
            len(self.domains),
            list(self.domains.keys()),
        )

    def _build_prompt(self, task: str, context: str) -> str:
        domain_list = "\n".join(d.prompt_line() for d in self.domains.values())
        domain_options = " | ".join(f'"{d}"' for d in self.VALID_DOMAINS)
        return self.PROMPT_TEMPLATE.format(
            domain_options=domain_options,
            domain_list=domain_list,
            task=task,
            context_head=context[:500],
        )

    async def classify(self, task: str, context: str) -> tuple[str, str]:
        """返回 (research_type, data_domain)；失败统一 fallback ("default", "unknown")"""
        try:
            prompt = self._build_prompt(task, context)
            resp = await self.llm_client.complete(prompt)
            data = json.loads(resp.strip())
            rtype = data.get("research_type", "default")
            ddomain = data.get("data_domain", "unknown")
            rtype = rtype if rtype in self.VALID_TYPES else "default"
            ddomain = ddomain if ddomain in self.VALID_DOMAINS else "unknown"
            if rtype == "default":
                ddomain = "unknown"
            return rtype, ddomain
        except Exception as e:
            logger.warning("classify failed, falling back: %s", e)
            return "default", "unknown"
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest server/tests/rest/test_intent.py -v`

预期：8 passed

- [ ] **步骤 5：Commit**

```bash
git add server/rest/intent.py server/tests/rest/test_intent.py
git commit -m "feat(research): add IntentClassifier with dynamic domain scanning"
```

---

## 任务 7：ResearchDirective（拼核心 prompt + 领域片段）

**文件：**
- 创建：`server/rest/research_directive.py`
- 测试：`server/tests/rest/test_research_directive.py`

**spec 出处：** §7.5（ResearchDirective 实现）

**前置依赖：** 任务 5（prompt 模板文件存在）

- [ ] **步骤 1：编写失败的测试**

```python
# server/tests/rest/test_research_directive.py
import pytest
from server.rest.research_directive import ResearchDirective


@pytest.fixture
def directive() -> ResearchDirective:
    return ResearchDirective()


class TestResearchDirective:
    def test_financial_analyst_loads_core_template(self, directive: ResearchDirective):
        result = directive.compose_task(
            research_type="financial_analyst",
            data_domain="unknown",
            user_task="分析比亚迪",
            context="上下文",
            length_budget=900,
        )
        # 应该包含核心框架关键词
        assert "金融分析师" in result
        assert "四步法" in result
        # 应该包含 user_task
        assert "分析比亚迪" in result
        # 应该包含 length_budget
        assert "900" in result
        # 应该被 research_directive 标签包裹
        assert "<research_directive>" in result
        assert "</research_directive>" in result

    def test_financial_analyst_with_domain_appends_snippet(self, directive: ResearchDirective):
        result = directive.compose_task(
            research_type="financial_analyst",
            data_domain="green_economy",
            user_task="x",
            context="y",
            length_budget=500,
        )
        # 应该包含领域片段标题
        assert "数据领域：green_economy" in result
        # 应该包含 green_economy.md 的内容关键词
        assert "碳" in result or "ESG" in result

    def test_financial_analyst_unknown_domain_no_snippet(self, directive: ResearchDirective):
        result = directive.compose_task(
            research_type="financial_analyst",
            data_domain="unknown",
            user_task="x",
            context="y",
            length_budget=500,
        )
        # unknown 不拼领域片段
        assert "数据领域：" not in result

    def test_academic_does_not_append_domain_snippet(self, directive: ResearchDirective):
        """spec §7.4：只有 financial_analyst 拼 domain 片段"""
        result = directive.compose_task(
            research_type="academic",
            data_domain="social_science",
            user_task="x",
            context="y",
            length_budget=500,
        )
        assert "学术研究" in result
        # academic 即使有 data_domain 也不拼片段（spec 组合规则）
        assert "数据领域：social_science" not in result

    def test_default_loads_default_template(self, directive: ResearchDirective):
        result = directive.compose_task(
            research_type="default",
            data_domain="unknown",
            user_task="x",
            context="y",
            length_budget=500,
        )
        assert "深度研究" in result

    def test_unknown_research_type_falls_back_to_default(self, directive: ResearchDirective):
        result = directive.compose_task(
            research_type="nonexistent",
            data_domain="unknown",
            user_task="x",
            context="y",
            length_budget=500,
        )
        # fallback 到 default.md
        assert "深度研究" in result
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest server/tests/rest/test_research_directive.py -v`

预期：FAIL，`ModuleNotFoundError`

- [ ] **步骤 3：编写实现代码**

```python
# server/rest/research_directive.py
"""研究指导 prompt 拼接（spec §7.5）

拼接逻辑：
1. 加载核心模板（按 research_type）：financial_analyst/academic/default
2. 如果 research_type == financial_analyst 且 data_domain 有对应片段，拼接领域片段
3. 包裹在 <research_directive> 标签内
"""
import logging
import pathlib
from functools import lru_cache

logger = logging.getLogger(__name__)

PROMPT_DIR = pathlib.Path(__file__).parent / "research_prompts"
DOMAIN_DIR = PROMPT_DIR / "domains"


@lru_cache(maxsize=8)
def _load_template(type_name: str) -> str:
    """加载核心 prompt 模板，失败 fallback default.md"""
    path = PROMPT_DIR / f"{type_name}.md"
    if not path.exists():
        logger.warning("template not found: %s, falling back to default", path)
        path = PROMPT_DIR / "default.md"
    return path.read_text(encoding="utf-8").strip()


@lru_cache(maxsize=16)
def _load_domain_template(domain_name: str) -> str | None:
    """加载领域片段；不存在返回 None（不拼）

    注意：返回值含 frontmatter，调用方需自己剥离（或用 _load_domain_body）。
    """
    if domain_name in ("", "unknown", None):
        return None
    path = DOMAIN_DIR / f"{domain_name}.md"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip()


@lru_cache(maxsize=16)
def _load_domain_body(domain_name: str) -> str | None:
    """加载领域片段正文（剥离 frontmatter）"""
    raw = _load_domain_template(domain_name)
    if raw is None:
        return None
    # 剥离 frontmatter
    import re
    match = re.match(r"^---\n.*?\n---\n*", raw, re.DOTALL)
    if match:
        return raw[match.end():].strip()
    return raw


class ResearchDirective:
    """根据 (research_type, data_domain) 产出研究指导 prompt

    spec §7.5 拼接逻辑：
    - 核心模板（按 research_type）
    - 领域片段（仅 financial_analyst + data_domain != unknown 时拼接）
    - 包裹在 <research_directive> 标签内
    """

    def build_directive(
        self,
        research_type: str,
        data_domain: str = "unknown",
    ) -> str:
        core = _load_template(research_type)

        domain_section = ""
        if research_type == "financial_analyst":
            domain_body = _load_domain_body(data_domain)
            if domain_body:
                domain_section = f"\n\n## 数据领域：{data_domain}\n{domain_body}"

        return f"<research_directive>\n{core}{domain_section}\n</research_directive>"

    def compose_task(
        self,
        research_type: str,
        data_domain: str,
        user_task: str,
        context: str,
        length_budget: int,
    ) -> str:
        directive = self.build_directive(research_type, data_domain)
        return (
            f"{directive}\n\n"
            f"## 研究任务\n{user_task}\n\n"
            f"## Context\n{context}\n\n"
            f"## 输出长度\n请在 {length_budget} 字以内完成报告。"
        )
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest server/tests/rest/test_research_directive.py -v`

预期：6 passed

- [ ] **步骤 5：Commit**

```bash
git add server/rest/research_directive.py server/tests/rest/test_research_directive.py
git commit -m "feat(research): add ResearchDirective with pluggable domain snippets"
```

---

## 任务 8：QueryRewriter（按 type 分发，default 加约束）

**文件：**
- 创建：`server/rest/query_rewriter.py`
- 测试：`server/tests/rest/test_query_rewriter.py`

**spec 出处：** §7.6（QueryRewriter 按 type 分发）

- [ ] **步骤 1：编写失败的测试**

```python
# server/tests/rest/test_query_rewriter.py
import pytest
from server.rest.query_rewriter import QueryRewriter


@pytest.fixture
def rewriter() -> QueryRewriter:
    return QueryRewriter()


class TestQueryRewriter:
    @pytest.mark.asyncio
    async def test_default_prepends_constraint(self, rewriter: QueryRewriter):
        result = await rewriter.rewrite("分析下 GDP", "default")
        assert "分析下 GDP" in result
        assert "归因分析" in result
        assert "[已验证]" in result or "证据强度" in result

    @pytest.mark.asyncio
    async def test_financial_analyst_returns_unchanged(self, rewriter: QueryRewriter):
        original = "比亚迪 2024 净利润"
        result = await rewriter.rewrite(original, "financial_analyst")
        assert result == original

    @pytest.mark.asyncio
    async def test_academic_returns_unchanged(self, rewriter: QueryRewriter):
        original = "关于行为科学的研究"
        result = await rewriter.rewrite(original, "academic")
        assert result == original
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest server/tests/rest/test_query_rewriter.py -v`

预期：FAIL

- [ ] **步骤 3：编写实现代码**

```python
# server/rest/query_rewriter.py
"""Query Rewriter（spec §7.6）

设计依据：
- financial_analyst / academic 有专门 prompt 模板指导，不改 query
- default 无专门模板，需要 prepend 通用归因约束

Demo 期不做 LLM 改写（硬编码约束），避免增加延迟和失败面。
"""


class QueryRewriter:
    DEFAULT_CONSTRAINT = (
        "\n\n## 通用研究约束\n"
        "请对查询数据做归因分析：\n"
        "1. 数据描述（核心数字 + 横向锚定）\n"
        "2. 归因分析（驱动因素 + 证据强度）\n"
        "3. 预测与情景（短期 / 中期 + base / bull / bear）\n"
        "4. 不确定性与风险（含反面证据）\n"
        "证据强度标注：[已验证] / [推断] / [推测]。"
    )

    async def rewrite(self, task: str, research_type: str) -> str:
        """按 research_type 分发：default 加约束；其他原样返回。"""
        if research_type == "default":
            return task + self.DEFAULT_CONSTRAINT
        return task
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest server/tests/rest/test_query_rewriter.py -v`

预期：3 passed

- [ ] **步骤 5：Commit**

```bash
git add server/rest/query_rewriter.py server/tests/rest/test_query_rewriter.py
git commit -m "feat(research): add QueryRewriter with type-based dispatch"
```

---

## 任务 9：logging_config（trace_id filter + research logger）

**文件：**
- 创建：`server/rest/logging_config.py`
- 测试：`server/tests/rest/test_logging_config.py`

**spec 出处：** §9.3（Python logging 配置）

- [ ] **步骤 1：编写失败的测试**

```python
# server/tests/rest/test_logging_config.py
import logging
import pytest
from server.rest.logging_config import (
    TraceIdFilter,
    set_trace_id,
    get_trace_id,
    clear_trace_id,
    configure_research_logging,
)


class TestTraceIdContext:
    def test_set_and_get_trace_id(self):
        set_trace_id("supersonic_abc")
        assert get_trace_id() == "supersonic_abc"
        clear_trace_id()

    def test_get_without_set_returns_empty(self):
        clear_trace_id()
        assert get_trace_id() == ""

    def test_clear_removes_trace_id(self):
        set_trace_id("supersonic_xyz")
        clear_trace_id()
        assert get_trace_id() == ""


class TestTraceIdFilter:
    def test_filter_injects_trace_id_into_record(self):
        import os
        # 先设环境变量默认值
        f = TraceIdFilter()
        rec = logging.LogRecord(
            name="x", level=logging.INFO, pathname="", lineno=0,
            msg="hello", args=(), exc_info=None,
        )
        set_trace_id("supersonic_test")
        result = f.filter(rec)
        assert result is True
        assert getattr(rec, "trace_id", "") == "supersonic_test"
        clear_trace_id()


class TestConfigureResearchLogging:
    def test_configures_logger_without_error(self, tmp_path, monkeypatch):
        # 重定向日志文件到临时路径
        monkeypatch.chdir(tmp_path)
        configure_research_logging()
        logger = logging.getLogger("server.rest")
        # 应该至少有一个 handler
        assert len(logger.handlers) >= 1
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest server/tests/rest/test_logging_config.py -v`

预期：FAIL

- [ ] **步骤 3：编写实现代码**

```python
# server/rest/logging_config.py
"""Python 侧 logging 配置（spec §9.3）

- trace_id 通过 contextvar 传递（FastAPI middleware 注入）
- logging filter 把 trace_id 注入到每条 LogRecord
- 独立 research.log 文件，与现有 TaskTracer JSON 互补
"""
import logging
import logging.config
import os
import pathlib
from contextvars import ContextVar

# trace_id contextvar（由 FastAPI middleware 在请求入口设置）
_TRACE_ID: ContextVar[str] = ContextVar("trace_id", default="")

LOG_DIR = pathlib.Path("logs")
LOG_FILE = LOG_DIR / "research.log"


def set_trace_id(trace_id: str) -> None:
    _TRACE_ID.set(trace_id)


def get_trace_id() -> str:
    return _TRACE_ID.get()


def clear_trace_id() -> None:
    _TRACE_ID.set("")


class TraceIdFilter(logging.Filter):
    """把 contextvar 中的 trace_id 注入到 LogRecord"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id()
        return True


def configure_research_logging() -> None:
    """配置 server.rest 命名空间的 logger（spec §9.3）"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "trace_id": {
                "()": lambda: TraceIdFilter(),
            },
        },
        "formatters": {
            "research": {
                "format": "[%(asctime)s] [%(name)s] [%(levelname)s] "
                          "[trace_id=%(trace_id)s] %(message)s",
            },
        },
        "handlers": {
            "research": {
                "class": "logging.FileHandler",
                "filename": str(LOG_FILE),
                "formatter": "research",
                "filters": ["trace_id"],
                "encoding": "utf-8",
            },
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "research",
                "filters": ["trace_id"],
            },
        },
        "loggers": {
            "server.rest": {
                "handlers": ["research", "console"],
                "level": os.getenv("RESEARCH_LOG_LEVEL", "INFO"),
                "propagate": False,
            },
        },
    }
    logging.config.dictConfig(LOGGING_CONFIG)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest server/tests/rest/test_logging_config.py -v`

预期：4 passed

- [ ] **步骤 5：Commit**

```bash
git add server/rest/logging_config.py server/tests/rest/test_logging_config.py
git commit -m "feat(research): add trace_id logging filter and research logger"
```

---

## 任务 10：pipeline_timeout（asyncio.wait_for 包装）

**文件：**
- 创建：`server/rest/pipeline_timeout.py`
- 测试：`server/tests/rest/test_pipeline_timeout.py`

**spec 出处：** §5.8（pipeline_timeout.py 实现）、§4.4 决策 #5（Python 14min 硬超时）

- [ ] **步骤 1：编写失败的测试**

```python
# server/tests/rest/test_pipeline_timeout.py
import asyncio
import pytest
from server.rest.pipeline_timeout import PipelineTimeoutError, run_with_timeout


class TestRunWithTimeout:
    @pytest.mark.asyncio
    async def test_completes_within_timeout(self):
        async def quick():
            await asyncio.sleep(0.01)
            return "done"

        result = await run_with_timeout(quick(), timeout_s=1, job_id="j1")
        assert result == "done"

    @pytest.mark.asyncio
    async def test_raises_pipeline_timeout_error_on_expiry(self):
        async def slow():
            await asyncio.sleep(10)
            return "should not reach"

        with pytest.raises(PipelineTimeoutError) as exc:
            await run_with_timeout(slow(), timeout_s=0.05, job_id="j_timeout")
        assert "j_timeout" in str(exc.value)

    @pytest.mark.asyncio
    async def test_cancels_underlying_task_on_timeout(self):
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def slow():
            started.set()
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                cancelled.set()
                raise

        with pytest.raises(PipelineTimeoutError):
            await run_with_timeout(slow(), timeout_s=0.05, job_id="j")
        assert started.is_set()
        # 给取消一点时间传播
        await asyncio.sleep(0.05)
        assert cancelled.is_set()

    @pytest.mark.asyncio
    async def test_propagates_exception_from_coroutine(self):
        async def boom():
            raise ValueError("pipeline crashed")

        with pytest.raises(ValueError, match="pipeline crashed"):
            await run_with_timeout(boom(), timeout_s=1, job_id="j")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest server/tests/rest/test_pipeline_timeout.py -v`

预期：FAIL

- [ ] **步骤 3：编写实现代码**

```python
# server/rest/pipeline_timeout.py
"""Pipeline 硬超时包装（spec §5.8 / §4.4 决策 #5）

Python asyncio.wait_for 14 分钟硬超时是权威超时；
Java 15 分钟仅作兜底（Python 进程崩溃 / 网络分区等）。
"""
import asyncio
from typing import Awaitable, TypeVar

T = TypeVar("T")


class PipelineTimeoutError(Exception):
    """Pipeline 硬超时，Python 侧权威超时信号"""


async def run_with_timeout(
    coro: Awaitable[T],
    timeout_s: int,
    job_id: str,
) -> T:
    """运行 coroutine，超时则取消并抛 PipelineTimeoutError。

    Args:
        coro: 待执行的 coroutine（通常是 execute_task_pipeline(...)）
        timeout_s: 超时秒数
        job_id: 用于错误消息追踪

    Returns:
        coroutine 的返回值

    Raises:
        PipelineTimeoutError: 超时
        Exception: coroutine 自身抛的任何异常（透传）
    """
    task = asyncio.ensure_future(coro)
    try:
        return await asyncio.wait_for(task, timeout=timeout_s)
    except asyncio.TimeoutError:
        task.cancel()
        try:
            await task  # 让 cleanup 完成
        except (asyncio.CancelledError, Exception):
            pass
        raise PipelineTimeoutError(f"{job_id} exceeded {timeout_s}s")
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest server/tests/rest/test_pipeline_timeout.py -v`

预期：4 passed

- [ ] **步骤 5：Commit**

```bash
git add server/rest/pipeline_timeout.py server/tests/rest/test_pipeline_timeout.py
git commit -m "feat(research): add asyncio.wait_for hard-timeout wrapper"
```

---

## 任务 11：config_loader（从 StreamingTaskRunner 提升为模块级）

**文件：**
- 创建：`server/rest/config_loader.py`
- 修改：`server/bridge/runner.py`（提取 `_compose_config` 为模块级函数并 import）

**spec 出处：** 评审 #2 修复（spec §6 评审对照表）

**背景：** 评审指出 `server/bridge/config_loader.py` 在仓库不存在；`compose_config` 实际是 `StreamingTaskRunner._compose_config` 的私有方法。要让 pipeline_adapter 复用，需要把它提升为模块级函数。

- [ ] **步骤 1：阅读 runner.py 现有 _compose_config 实现**

运行：`grep -n "_compose_config\|create_pipeline_components\|hydra" server/bridge/runner.py`

记录：
- `_compose_config` 的实际签名和实现
- 它依赖的 import（`hydra`、`dotenv` 等）
- `create_pipeline_components` 是否也在 runner.py 还是已经在 pipeline.py

- [ ] **步骤 2：编写测试（验证新模块 API）**

```python
# server/tests/rest/test_config_loader.py
import pytest
from server.rest.config_loader import compose_config, create_pipeline_components


class TestConfigLoader:
    def test_compose_config_returns_dict_config(self):
        """spec §7.8 pipeline_adapter 调用 compose_config 获取 cfg"""
        cfg = compose_config(
            config_file_name="agent_llm_gpt5",
            overrides=[],
        )
        # 应该返回 OmegaConf DictConfig（或 dict）
        assert cfg is not None
        # 应该包含 main_agent 配置
        assert hasattr(cfg, "main_agent") or "main_agent" in cfg

    def test_create_pipeline_components_returns_tuple(self):
        """spec §7.8：components = create_pipeline_components(cfg);
        components[0]=main_tm, [1]=sub_tms, [2]=formatter"""
        cfg = compose_config("agent_llm_gpt5", [])
        components = create_pipeline_components(cfg)
        assert isinstance(components, tuple) or isinstance(components, list)
        assert len(components) == 3
```

**注意：** 这两个测试需要真实加载 Hydra 配置，可能比较慢。标记为 `@pytest.mark.slow` 并在 CI 单独跑。如果 Demo 期 Hydra 配置环境不具备，可以 `@pytest.mark.skip(reason="requires hydra config env")`。

- [ ] **步骤 3：抽取 compose_config 和 create_pipeline_components 到 config_loader.py**

```python
# server/rest/config_loader.py
"""Pipeline 配置组装（从 StreamingTaskRunner 提升的模块级函数）

spec §7.8 pipeline_adapter 通过这里组装 Hydra config，
而不是依赖 server/bridge/runner.py 的私有方法。
"""
import pathlib
import dotenv
from hydra import compose, initialize_config_dir
from omegaconf import DictConfig

# 复用 miro-flow 现有的 config 入口
CONFIG_DIR = pathlib.Path(__file__).parent.parent.parent / "config"


def compose_config(
    config_file_name: str = "agent_llm_gpt5",
    overrides: list[str] | None = None,
) -> DictConfig:
    """组装 Hydra config。

    Args:
        config_file_name: config/ 目录下的 yaml 文件名（不含 .yaml 后缀）
        overrides: Hydra override 列表

    Returns:
        DictConfig 对象
    """
    dotenv.load_dotenv()
    overrides = overrides or []
    with initialize_config_dir(config_dir=str(CONFIG_DIR), version_base=None):
        return compose(config_name=config_file_name, overrides=overrides)


def create_pipeline_components(cfg: DictConfig):
    """创建 pipeline 组件（main tool manager / sub tool managers / output formatter）

    Returns: (main_agent_tool_manager, sub_agent_tool_managers, output_formatter)
    """
    # 复用 src/core/pipeline.py 的工厂函数（不要重写）
    from src.core.pipeline import create_pipeline_components as _factory
    return _factory(cfg)
```

**修改 runner.py**：把现有的 `_compose_config` 方法改为调用新模块：

```python
# server/bridge/runner.py - 原有 _compose_config 方法替换
# 旧代码：
#   def _compose_config(self, ...):
#       dotenv.load_dotenv()
#       with hydra.initialize_config_dir(...):
#           return hydra.compose(...)
#
# 新代码：
from server.rest.config_loader import compose_config as _compose_config_module

# 保留 _compose_config 作为方法（向后兼容），但内部委托
def _compose_config(self, config_file_name: str, overrides: list[str]) -> DictConfig:
    return _compose_config_module(config_file_name, overrides)
```

**注意：** 如果 `src/core/pipeline.py` 的 `create_pipeline_components` 已经是模块级函数，直接 re-export 即可；不要重写。

- [ ] **步骤 4：运行测试验证**

运行：`python -m pytest server/tests/rest/test_config_loader.py -v`

预期：2 passed 或 skipped（视 Hydra 环境而定）

同时验证 runner.py 没有被破坏：

运行：`python -m pytest server/tests/ -v -k "runner or streaming"`

- [ ] **步骤 5：Commit**

```bash
git add server/rest/config_loader.py server/tests/rest/test_config_loader.py server/bridge/runner.py
git commit -m "refactor(research): lift compose_config to module-level for reuse"
```

---

## 任务 12：pipeline_adapter（编排器，整合所有组件）

**文件：**
- 创建：`server/rest/pipeline_adapter.py`
- 测试：`server/tests/rest/test_pipeline_adapter.py`

**spec 出处：** §7.8（完整实现）

**前置依赖：** 任务 1-11 全部完成

- [ ] **步骤 1：编写失败的测试**

```python
# server/tests/rest/test_pipeline_adapter.py
import asyncio
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from server.rest.pipeline_adapter import run_pipeline_async, PIPELINE_HARD_TIMEOUT_S
from server.rest.job_store import JobStore, JobRecord
from server.rest.pipeline_timeout import PipelineTimeoutError


@pytest.fixture
def store(tmp_path) -> JobStore:
    return JobStore(db_path=str(tmp_path / "test.db"))


@pytest.fixture
def job_rec(store: JobStore) -> JobRecord:
    now = datetime.now(timezone.utc).isoformat()
    rec = JobRecord(
        job_id="j1", tenant_id="default", trace_id="t1",
        task="test task", context="ctx",
        research_type="default", data_domain="unknown",
        config_file_name="agent_llm_gpt5",
        status="PENDING", created_at=now, updated_at=now,
    )
    store.create(rec)
    return rec


class TestRunPipelineAsync:
    @pytest.mark.asyncio
    async def test_skips_if_already_terminal(self, store: JobStore, job_rec: JobRecord):
        """幂等守卫：已终态直接 skip"""
        store.update(job_rec.job_id, status="FAILED", error_msg="prev failure")

        with patch("server.rest.pipeline_adapter.execute_task_pipeline") as mock_pipe:
            await run_pipeline_async(
                job_id=job_rec.job_id, task="t", context="c",
                research_type="default", data_domain="unknown",
                config_name="agent_llm_gpt5", trace_id="t1",
                tenant_id="default", length_budget=900,
                job_store=store, llm_client=MagicMock(),
            )
        # pipeline 不应该被调用
        mock_pipe.assert_not_called()

    @pytest.mark.asyncio
    async def test_success_marks_completed(self, store: JobStore, job_rec: JobRecord):
        """正常完成：状态 COMPLETED + report_summary + report_uri"""
        with patch("server.rest.pipeline_adapter.execute_task_pipeline", new=AsyncMock(return_value=("final answer", "boxed", Path("/tmp/log.json")))), \
             patch("server.rest.pipeline_adapter.compose_config", return_value={"main_agent": {"model": "gpt-5"}}), \
             patch("server.rest.pipeline_adapter.create_pipeline_components", return_value=(MagicMock(), {}, MagicMock())):
            await run_pipeline_async(
                job_id=job_rec.job_id, task="t", context="c",
                research_type="default", data_domain="unknown",
                config_name="agent_llm_gpt5", trace_id="t1",
                tenant_id="default", length_budget=100,
                job_store=store, llm_client=MagicMock(),
            )

        rec = store.get(job_rec.job_id)
        assert rec.status == "COMPLETED"
        assert rec.report_summary is not None
        assert rec.report_uri is not None
        assert rec.completed_at is not None

    @pytest.mark.asyncio
    async def test_timeout_marks_failed(self, store: JobStore, job_rec: JobRecord):
        """PipelineTimeoutError → 状态 FAILED + python hard timeout"""

        async def slow_pipe(**kwargs):
            await asyncio.sleep(10)
            return "never"

        with patch("server.rest.pipeline_adapter.execute_task_pipeline", new=AsyncMock(side_effect=slow_pipe)), \
             patch("server.rest.pipeline_adapter.compose_config", return_value={"main_agent": {}}), \
             patch("server.rest.pipeline_adapter.create_pipeline_components", return_value=(MagicMock(), {}, MagicMock())), \
             patch("server.rest.pipeline_adapter.PIPELINE_HARD_TIMEOUT_S", 0.05):
            await run_pipeline_async(
                job_id=job_rec.job_id, task="t", context="c",
                research_type="default", data_domain="unknown",
                config_name="agent_llm_gpt5", trace_id="t1",
                tenant_id="default", length_budget=100,
                job_store=store, llm_client=MagicMock(),
            )

        rec = store.get(job_rec.job_id)
        assert rec.status == "FAILED"
        assert "timeout" in (rec.error_msg or "").lower()

    @pytest.mark.asyncio
    async def test_exception_marks_failed(self, store: JobStore, job_rec: JobRecord):
        """其他异常 → 状态 FAILED + error_msg"""
        with patch("server.rest.pipeline_adapter.execute_task_pipeline", new=AsyncMock(side_effect=ValueError("LLM crashed"))), \
             patch("server.rest.pipeline_adapter.compose_config", return_value={"main_agent": {}}), \
             patch("server.rest.pipeline_adapter.create_pipeline_components", return_value=(MagicMock(), {}, MagicMock())):
            await run_pipeline_async(
                job_id=job_rec.job_id, task="t", context="c",
                research_type="default", data_domain="unknown",
                config_name="agent_llm_gpt5", trace_id="t1",
                tenant_id="default", length_budget=100,
                job_store=store, llm_client=MagicMock(),
            )

        rec = store.get(job_rec.job_id)
        assert rec.status == "FAILED"
        assert "ValueError" in (rec.error_msg or "")
        assert "LLM crashed" in (rec.error_msg or "")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest server/tests/rest/test_pipeline_adapter.py -v`

预期：FAIL，`ModuleNotFoundError`

- [ ] **步骤 3：编写实现代码**

```python
# server/rest/pipeline_adapter.py
"""Pipeline 编排器（spec §7.8）

职责：
- 串联 QueryRewriter → ResearchDirective → execute_task_pipeline → length control → ReportStore → JobStore.update
- 幂等守卫（已终态直接 skip）
- 硬超时包装（asyncio.wait_for 14min）
- 异常分类（PipelineTimeoutError / CancelledError / 其他 Exception）

不直接调 LLM、不直接读写 SQLite、不直接拼 prompt——这些由专门的组件负责。
"""
import asyncio
import logging
import pathlib
from datetime import datetime, timezone

from .config_loader import compose_config, create_pipeline_components
from .job_store import JobStore, TERMINAL_STATUSES
from .length_control import enforce_length_budget
from .logging_config import set_trace_id
from .pipeline_timeout import PipelineTimeoutError, run_with_timeout
from .query_rewriter import QueryRewriter
from .report_store import FileSystemReportStore
from .research_directive import ResearchDirective
from src.core.pipeline import execute_task_pipeline

logger = logging.getLogger(__name__)

# 全局单例（Demo 期足够；未来可改 dependency injection）
_report_store = FileSystemReportStore()
_directive = ResearchDirective()
_rewriter = QueryRewriter()

# spec §4.4 决策 #5：Python 14min 硬超时（必须早于 Java 15min 兜底）
PIPELINE_HARD_TIMEOUT_S = 14 * 60


async def run_pipeline_async(
    job_id: str,
    task: str,
    context: str,
    research_type: str,
    data_domain: str,
    config_name: str,
    trace_id: str,
    tenant_id: str,
    length_budget: int,
    job_store: JobStore,
    llm_client,
):
    """执行 pipeline 并更新 job 状态。

    幂等守卫：若 Job 已终态（如启动恢复标过 FAILED），直接返回。
    """
    set_trace_id(trace_id)

    # 幂等守卫：已终态直接 skip
    current = job_store.get(job_id)
    if current and current.status in TERMINAL_STATUSES:
        logger.warning(
            "job %s already terminal (%s), skip",
            job_id, current.status,
        )
        return

    # 标记 RUNNING
    job_store.update(
        job_id,
        status="RUNNING",
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    try:
        # 1. QueryRewriter：default 加通用约束，其他原样
        rewritten_task = await _rewriter.rewrite(task, research_type)

        # 2. ResearchDirective：拼核心 prompt + 领域片段
        full_task = _directive.compose_task(
            research_type=research_type,
            data_domain=data_domain,
            user_task=rewritten_task,
            context=context,
            length_budget=length_budget,
        )

        # 3. 组装 Hydra config 和 components
        cfg = compose_config(config_name, [])
        components = create_pipeline_components(cfg)

        # 4. 执行 pipeline（硬超时包装）
        final_answer, boxed_answer, log_path = await run_with_timeout(
            execute_task_pipeline(
                cfg=cfg,
                task_name=job_id,
                task_id=job_id,
                task_description=full_task,
                task_file_name=None,
                main_agent_tool_manager=components[0],
                sub_agent_tool_managers=components[1],
                output_formatter=components[2],
                log_path=pathlib.Path("logs") / f"{job_id}.json",
                ground_truth=None,
                metadata={
                    "trace_id": trace_id,
                    "source": "rest_api",
                    "research_type": research_type,
                    "data_domain": data_domain,
                },
                event_sink=None,
                human_interaction=None,
            ),
            timeout_s=PIPELINE_HARD_TIMEOUT_S,
            job_id=job_id,
        )

        # 5. 长度控制
        summary = enforce_length_budget(final_answer, budget=length_budget)

        # 6. 写报告 JSON
        report_uri = _report_store.save(job_id, tenant_id, {
            "job_id": job_id,
            "trace_id": trace_id,
            "task": task,
            "research_type": research_type,
            "data_domain": data_domain,
            "rewritten_task": rewritten_task if rewritten_task != task else None,
            "report_markdown": final_answer,
            "boxed_answer": boxed_answer,
            "metadata": {
                "config_file_name": config_name,
                "model_used": _extract_model_name(cfg),
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })

        # 7. SQLite 更新（终态不可变守卫在 JobStore.update 内）
        job_store.update(
            job_id,
            status="COMPLETED",
            report_summary=summary,
            report_uri=report_uri,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.info("job %s completed type=%s domain=%s",
                    job_id, research_type, data_domain)

    except PipelineTimeoutError:
        job_store.update(
            job_id,
            status="FAILED",
            error_msg=f"python hard timeout after {PIPELINE_HARD_TIMEOUT_S}s",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.warning("job %s timeout", job_id)

    except asyncio.CancelledError:
        # 不覆盖已终态状态（启动恢复路径触发）
        current = job_store.get(job_id)
        if not current or current.status not in TERMINAL_STATUSES:
            job_store.update(
                job_id,
                status="FAILED",
                error_msg="task cancelled",
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
        raise  # propagate

    except Exception as e:
        job_store.update(
            job_id,
            status="FAILED",
            error_msg=f"{type(e).__name__}: {str(e)[:500]}",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.exception("job %s failed", job_id)


def _extract_model_name(cfg) -> str:
    """从 Hydra cfg 提取模型名（兼容 dict 和 DictConfig）"""
    try:
        return cfg.get("main_agent", {}).get("model", "unknown")
    except (AttributeError, TypeError):
        return "unknown"
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest server/tests/rest/test_pipeline_adapter.py -v`

预期：4 passed

- [ ] **步骤 5：Commit**

```bash
git add server/rest/pipeline_adapter.py server/tests/rest/test_pipeline_adapter.py
git commit -m "feat(research): add pipeline_adapter orchestrator with idempotency + timeout"
```

---

## 任务 13：FastAPI routes + app.py 集成 + 启动恢复

**文件：**
- 创建：`server/rest/routes.py`
- 创建：`server/rest/__init__.py`
- 创建：`server/tests/rest/conftest.py`
- 创建：`server/tests/rest/test_routes.py`
- 修改：`server/app.py`（挂载 router + startup 事件 + trace_id middleware）

**spec 出处：** §4.1（REST 契约）、§5.0（数据流图）、§7.9（启动恢复）

**前置依赖：** 任务 1-12 全部完成

- [ ] **步骤 1：编写 conftest.py 提供测试 fixtures**

```python
# server/tests/rest/conftest.py
import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from server.rest.job_store import JobStore


@pytest.fixture
def tmp_db(tmp_path: Path) -> str:
    return str(tmp_path / "test_research.db")


@pytest.fixture
def job_store(tmp_db: str) -> JobStore:
    return JobStore(db_path=tmp_db)


@pytest.fixture
def mock_llm_client():
    """mock IntentClassifier 用的 LLM client"""
    from unittest.mock import AsyncMock
    client = AsyncMock()
    client.complete = AsyncMock(return_value='{"research_type": "default", "data_domain": "unknown"}')
    return client


@pytest.fixture
def client(monkeypatch, tmp_db, mock_llm_client, job_store):
    """TestClient with mocked LLM and isolated DB"""
    monkeypatch.setenv("RESEARCH_SERVICE_TOKEN", "test-token")
    monkeypatch.setenv("RESEARCH_DB_PATH", tmp_db)

    # 在 import routes 前替换全局 job_store
    import server.rest.routes as routes_mod
    routes_mod._job_store = job_store
    routes_mod._intent_classifier.llm_client = mock_llm_client

    # mock pipeline 不实际跑
    async def _fake_pipeline(**kwargs):
        return ("mock report content", "boxed", None)
    monkeypatch.setattr(
        "server.rest.pipeline_adapter.run_pipeline_async",
        _fake_pipeline,
    )

    from server.app import app
    return TestClient(app)
```

- [ ] **步骤 2：编写失败的测试**

```python
# server/tests/rest/test_routes.py
import pytest
from fastapi.testclient import TestClient


class TestCreateJob:
    def test_returns_202_with_pending_status(self, client: TestClient):
        """spec §4.1：POST 立即返回 202 + PENDING"""
        resp = client.post(
            "/v1/research/jobs",
            json={
                "job_id": "test-j1",
                "task": "分析比亚迪",
                "context": "上下文",
            },
            headers={"Authorization": "Bearer test-token"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["job_id"] == "test-j1"
        assert data["status"] == "PENDING"

    def test_missing_auth_returns_401(self, client: TestClient):
        resp = client.post(
            "/v1/research/jobs",
            json={"job_id": "x", "task": "y"},
        )
        assert resp.status_code == 401

    def test_wrong_auth_returns_401(self, client: TestClient):
        resp = client.post(
            "/v1/research/jobs",
            json={"job_id": "x", "task": "y"},
            headers={"Authorization": "Bearer wrong"},
        )
        assert resp.status_code == 401

    def test_missing_task_returns_422(self, client: TestClient):
        """task 是必填字段"""
        resp = client.post(
            "/v1/research/jobs",
            json={"job_id": "x"},  # 缺 task
            headers={"Authorization": "Bearer test-token"},
        )
        assert resp.status_code == 422


class TestGetJob:
    def test_returns_status_after_create(self, client: TestClient):
        # 先创建
        client.post(
            "/v1/research/jobs",
            json={"job_id": "test-j2", "task": "x"},
            headers={"Authorization": "Bearer test-token"},
        )
        # 查询
        resp = client.get(
            "/v1/research/jobs/test-j2",
            headers={"Authorization": "Bearer test-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == "test-j2"
        assert data["status"] in ("PENDING", "RUNNING")

    def test_missing_job_returns_404(self, client: TestClient):
        resp = client.get(
            "/v1/research/jobs/nonexistent",
            headers={"Authorization": "Bearer test-token"},
        )
        assert resp.status_code == 404

    def test_missing_auth_returns_401(self, client: TestClient):
        resp = client.get("/v1/research/jobs/x")
        assert resp.status_code == 401
```

- [ ] **步骤 3：运行测试验证失败**

运行：`python -m pytest server/tests/rest/test_routes.py -v`

预期：FAIL，可能是因为 routes.py 还没创建 / app.py 没挂载

- [ ] **步骤 4：编写 routes.py**

```python
# server/rest/routes.py
"""FastAPI REST routes：POST/GET /v1/research/jobs（spec §4.1 / §5.0）"""
import logging
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException

from .deps import verify_service_token
from .models import CreateJobRequest, CreateJobResponse, JobStatusResponse
from .job_store import JobStore
from .intent import IntentClassifier

logger = logging.getLogger(__name__)

router = APIRouter()

# 全局单例（Demo 期；未来可改 dependency injection）
# 注意：这些会在 app.py 启动时被设置
_job_store: JobStore | None = None
_intent_classifier: IntentClassifier | None = None

TYPE_TO_CONFIG = {
    "financial_analyst": "agent_llm_gpt5",
    "academic": "agent_llm_gpt5",
    "default": "agent_llm_gpt5",
}


def set_dependencies(job_store: JobStore, classifier: IntentClassifier) -> None:
    """由 app.py 启动时调用，注入依赖"""
    global _job_store, _intent_classifier
    _job_store = job_store
    _intent_classifier = classifier


@router.post(
    "/v1/research/jobs",
    status_code=202,
    response_model=CreateJobResponse,
    dependencies=[Depends(verify_service_token)],
)
async def create_job(req: CreateJobRequest, bg: BackgroundTasks):
    """spec §5.0 同步路径：分类 + 写 PENDING + 派发 + 立即 202"""
    assert _job_store is not None
    assert _intent_classifier is not None

    # 1. IntentClassifier 分类
    research_type, data_domain = await _intent_classifier.classify(req.task, req.context)
    config_name = TYPE_TO_CONFIG.get(research_type, "agent_llm_gpt5")

    # 2. 写 SQLite PENDING
    from datetime import datetime, timezone
    from .job_store import JobRecord
    now = datetime.now(timezone.utc).isoformat()
    rec = JobRecord(
        job_id=req.job_id,
        tenant_id=req.tenant_id or "default",
        trace_id=req.trace_id,
        task=req.task,
        context=req.context,
        research_type=research_type,
        data_domain=data_domain,
        config_file_name=config_name,
        status="PENDING",
        created_at=now,
        updated_at=now,
    )
    if not _job_store.create(rec):
        raise HTTPException(status_code=409, detail="job_id already exists")

    # 3. 派发后台任务（不阻塞响应）
    bg.add_task(_dispatch_pipeline, req, research_type, data_domain, config_name)

    # 4. 立即返回 202
    return CreateJobResponse(job_id=req.job_id, status="PENDING")


async def _dispatch_pipeline(
    req: CreateJobRequest,
    research_type: str,
    data_domain: str,
    config_name: str,
) -> None:
    """后台 dispatcher（spec §5.0 异步路径）"""
    from .pipeline_adapter import run_pipeline_async
    # llm_client 由 app.py 通过 set_dependencies 设置
    llm_client = getattr(_intent_classifier, "llm_client", None)
    try:
        await run_pipeline_async(
            job_id=req.job_id,
            task=req.task,
            context=req.context,
            research_type=research_type,
            data_domain=data_domain,
            config_name=config_name,
            trace_id=req.trace_id,
            tenant_id=req.tenant_id or "default",
            length_budget=req.length_budget,
            job_store=_job_store,
            llm_client=llm_client,
        )
    except Exception:
        logger.exception("pipeline dispatch failed for job %s", req.job_id)


@router.get(
    "/v1/research/jobs/{job_id}",
    response_model=JobStatusResponse,
    dependencies=[Depends(verify_service_token)],
)
async def get_job(job_id: str):
    """spec §4.1：GET 返回当前状态"""
    assert _job_store is not None
    rec = _job_store.get(job_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="job not found")

    return JobStatusResponse(
        job_id=rec.job_id,
        tenant_id=rec.tenant_id,
        trace_id=rec.trace_id,
        research_type=rec.research_type,
        data_domain=rec.data_domain,
        status=rec.status,
        report_summary=rec.report_summary,
        report_uri=rec.report_uri,
        error_msg=rec.error_msg,
        created_at=rec.created_at,
        updated_at=rec.updated_at,
        started_at=rec.started_at,
        completed_at=rec.completed_at,
    )
```

```python
# server/rest/__init__.py
# 空文件，标记为 Python 包
```

- [ ] **步骤 5：修改 app.py 挂载 router + startup 事件**

读取现有 `server/app.py`，找到合适位置加入：

```python
# server/app.py 新增（在现有 imports 后）
import os
from server.rest.routes import router as research_router, set_dependencies
from server.rest.job_store import JobStore
from server.rest.intent import IntentClassifier
from server.rest.logging_config import configure_research_logging, set_trace_id
from contextvars import ContextVar

# 初始化 logging
configure_research_logging()

# 初始化 JobStore（路径可通过环境变量配置）
_DB_PATH = os.getenv("RESEARCH_DB_PATH", "server/rest/research_jobs.db")
_job_store = JobStore(db_path=_DB_PATH)

# 初始化 IntentClassifier（llm_client 延迟注入）
# 注意：实际 LLM client 由现有 src/llm 模块提供，启动时创建
# Demo 期这里先用 None，app startup 时通过 set_dependencies 注入
_llm_client = None  # 由 src/llm 的实际工厂函数创建（启动时初始化，见下方说明）
_intent_classifier = IntentClassifier(_llm_client) if _llm_client else None

# 注入依赖
if _intent_classifier:
    set_dependencies(_job_store, _intent_classifier)

# 挂载 router
app.include_router(research_router)


@app.middleware("http")
async def trace_id_middleware(request, call_next):
    """spec §9.2：从 X-Trace-Id header 注入 contextvar"""
    trace_id = request.headers.get("X-Trace-Id", "")
    if trace_id:
        set_trace_id(trace_id)
    response = await call_next(request)
    if trace_id:
        response.headers["X-Trace-Id"] = trace_id
    return response


@app.on_event("startup")
async def startup_recovery():
    """spec §7.9：启动时恢复 stale jobs"""
    recovered = _job_store.recover_stale_jobs()
    if recovered > 0:
        import logging
        logging.getLogger(__name__).info(
            "startup recovery: marked %d stale jobs as FAILED", recovered,
        )
```

**注意：** `_llm_client` 的实际初始化依赖 `src/llm` 模块的工厂函数。Demo 启动前需要找到现有代码中如何创建 LLM 客户端（参考 `server/bridge/runner.py` 怎么做的）并复用。如果暂时找不到，可以让 IntentClassifier 也接受 mock client（仅测试用）。

- [ ] **步骤 6：运行测试验证通过**

运行：`python -m pytest server/tests/rest/test_routes.py -v`

预期：6 passed

- [ ] **步骤 7：运行所有 Python 测试确认没有回归**

运行：`python -m pytest server/tests/rest/ -v`

预期：所有测试通过

- [ ] **步骤 8：Commit**

```bash
git add server/rest/routes.py server/rest/__init__.py server/tests/rest/conftest.py server/tests/rest/test_routes.py server/app.py
git commit -m "feat(research): add FastAPI routes with startup recovery and trace_id middleware"
```

---

## 任务 14：端到端验证（手工 curl + 启动 Python 服务）

**文件：** 无新增文件，只验证

**spec 出处：** §9.4 集成测试（Python FastAPI TestClient）

**目标：** 在本机启动 Python 服务，用 curl 验证完整流程能跑通（不要求真实 LLM 调用，但 SQLite + 报告文件落盘要正常）。

- [ ] **步骤 1：配置环境变量**

```bash
cd /Users/yourton_ma/workspace/agent_project/research-agent/miro-flow-solution

# 在 .env 中加入（如果没有）
cat >> .env <<EOF
RESEARCH_SERVICE_TOKEN=dev-token-please-change
RESEARCH_DB_PATH=server/rest/research_jobs.db
EOF

source .env  # 或重新打开 shell
```

- [ ] **步骤 2：启动 Python 服务**

```bash
# 使用 uvicorn 启动（参考现有 docker-compose 或 server/main.py）
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

预期：看到 startup 日志，包含 "startup recovery: marked N stale jobs as FAILED"（首次启动应为 0）。

- [ ] **步骤 3：验证 POST 创建 job**

```bash
curl -X POST http://localhost:8000/v1/research/jobs \
  -H "Authorization: Bearer dev-token-please-change" \
  -H "X-Trace-Id: test-trace-001" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "e2e-test-001",
    "task": "分析比亚迪 2024 年净利润",
    "context": "净利润 300 亿，同比 +35%",
    "trace_id": "test-trace-001"
  }'
```

预期：HTTP 202，返回 `{"job_id": "e2e-test-001", "status": "PENDING"}`

- [ ] **步骤 4：验证 GET 查询状态**

```bash
curl http://localhost:8000/v1/research/jobs/e2e-test-001 \
  -H "Authorization: Bearer dev-token-please-change"
```

预期：HTTP 200，返回包含 status / research_type / data_domain 字段的 JSON。

- [ ] **步骤 5：验证 401（token 错）**

```bash
curl -X POST http://localhost:8000/v1/research/jobs \
  -H "Authorization: Bearer wrong-token" \
  -H "Content-Type: application/json" \
  -d '{"job_id": "x", "task": "y"}'
```

预期：HTTP 401

- [ ] **步骤 6：验证启动恢复**

```bash
# 1. 杀掉 Python 进程（Ctrl+C）
# 2. 直接在 SQLite 里手动造一个 RUNNING 状态的 job（模拟崩溃）
sqlite3 server/rest/research_jobs.db "INSERT INTO research_jobs (job_id, tenant_id, task, status, created_at, updated_at) VALUES ('stale-job', 'default', 'test', 'RUNNING', datetime('now'), datetime('now'));"

# 3. 重启 Python 服务
uvicorn server.main:app --host 0.0.0.0 --port 8000

# 4. 看启动日志：应该有 "recovered stale job stale-job"
# 5. 查询确认
curl http://localhost:8000/v1/research/jobs/stale-job \
  -H "Authorization: Bearer dev-token-please-change"
```

预期：status 为 FAILED，error_msg 包含 "runner restarted"。

- [ ] **步骤 7：验证 SQLite 落盘**

```bash
sqlite3 server/rest/research_jobs.db "SELECT job_id, status, research_type, data_domain FROM research_jobs;"
```

预期：看到测试创建的 job 记录，字段齐全。

- [ ] **步骤 8：验证报告 JSON 文件（如果有真实完成的 job）**

```bash
ls -la outputs/default/research_jobs/
# 如果有 COMPLETED 的 job，应该看到对应 JSON 文件
cat outputs/default/research_jobs/<job_id>.json | python -m json.tool
```

**注意：** 真实 LLM 完成需要 API key 配置好。如果没有，这一步可跳过，留待 Java + 前端联调时再验证。

- [ ] **步骤 9：清理测试数据并记录验证结果**

```bash
# 删除测试 DB（下次启动会自动重建）
rm -f server/rest/research_jobs.db
# 删除测试报告
rm -rf outputs/default/research_jobs/
```

在 commit message 里记录验证结果。

- [ ] **步骤 10：Commit（Phase 1 完成标志）**

```bash
git add -A
git commit -m "test(research): phase 1 e2e verification - POST/GET/startup recovery all pass"
```

---

## Phase 1 完成检查清单

- [ ] 14 个任务全部 commit
- [ ] `python -m pytest server/tests/rest/ -v` 全部通过（预期 ~40 个测试）
- [ ] 手工 curl 验证：POST 202 / GET 200 / 401 / 启动恢复 都正常
- [ ] SQLite 表结构创建成功
- [ ] `outputs/default/research_jobs/` 目录可写
- [ ] 日志带 trace_id
- [ ] IntentClassifier 扫描到至少 4 个 domain（corporate_finance/macroeconomy/green_economy/industry_analysis）
- [ ] 没有 lint 错误（`ruff check server/rest/` 或项目用的 linter）

## 已知遗留（Phase 2/3 处理）

- LLM client 真实初始化：需要从 `src/llm` 工厂创建，Demo 期可先 mock
- Java 侧实现：Phase 2
- 前端 SSE 实现：Phase 3
- 真实 LLM 完成的端到端报告验证：Phase 3 联调时

## 评审修复项进度

本 Phase 已覆盖评审报告中以下项（详见 spec §9.1.1）：
- ✅ #6 Java 单边超时与 Python 状态分叉（任务 10 + 任务 12）
- ✅ #18 错误矩阵与实现矛盾（任务 12 异常分类）
- 部分 #2 pipeline 适配层依赖真实模块（任务 11 提升了 `compose_config`）

未覆盖（Phase 2 Java 侧处理）：
- #4 IDOR + SSE 资源耗尽
- #10 `include_full` 恒 true
- #11 SSE 推送大字段
- #14 SSE 终态不 complete
