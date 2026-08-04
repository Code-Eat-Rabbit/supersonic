# 深度研究功能集成设计（SuperSonic × miro-flow-solution）

> 目标：在 SuperSonic 问数成功并完成描述性解读后，引导用户触发 Python 深度研究 Agent（miro-flow-solution），产出归因报告并回挂到当前 `queryId`。
> 输入文档：`docs/resume/interview/三、深度研究-面试准备.md` 的 B5 / C9 章节。
> 状态：设计定稿，待编写实现计划（writing-plans 阶段）。
> 协议契约原则：**协议先就绪、实现可渐进**——Demo 阶段每项只做最小实现，但字段和抽象接口先留好，未来演进无损。

---

## 1. 项目背景

### 1.1 B5 文档描述的产品形态

- 用户问数成功并完成描述性解读后，结果区展示「想要对结果做深度研究吗？」
- 用户点击 = 启动深度研究，前端只传当前 `queryId`
- Java 按该 `queryId` 取出原问题、`textResult`/`textSummary`、维度/指标，截断后拼成 `task + context`
- Java `POST` Python `/v1/research/jobs`，立即 `202` 返回 `jobId`，**不**在 execute 线程同步等待
- 前端轮询/订阅 Java 取终态；成功写入短报告字段；失败静默保留 `textSummary`

### 1.2 双方代码现状落差

| 维度 | 现状 | 差距 |
|------|------|------|
| Python 任务执行通道 | 仅 WebSocket `/ws`（session 1:1 task，纯内存） | 需新增 REST `/v1/research/jobs` 异步 job 契约 |
| Python 任务状态持久化 | 无（仅 TaskTracer JSON 日志，无 load 入口） | 需新增 SQLite job store + 启动恢复 |
| Java 异步 job 框架 | 无（仅 textSummary 伪流式轮询） | 需新建 `s2_chat_research_job` 表 + 网关层 |
| 前端轮询/推送 | ChatItem 500ms 轮询 `getExecuteSummary` | 新增 SSE 推送通道 |
| traceId | Java MDC + LogInterceptor，链路完整 | 需 HTTP header 透传到 Python |

### 1.3 实现目标

**端到端跑通 Demo**：Java 网关 + Python REST + 前端 SSE，三个本地进程能从点击按钮看到深度报告产出。

---

## 2. 范围与边界

### 2.1 Demo 范围内必做

- Python 新增 REST `/v1/research/jobs`（POST 创建 + GET 查询）
- Python SQLite job store + 启动恢复
- Python IntentClassifier（1 次 LLM 调用 + fallback）
- Python 长度控制（句子边界截断）
- Python FileSystemReportStore（JSON 文件存储）
- Python Service Token 验证（独立 token，不复用 SuperSonic JWT）
- Java 新建 `s2_chat_research_job` 表 + 12 个新文件
- Java `@Scheduled` 2s 同步 + SSE 推送
- Java 权限校验（JWT `isAdmin` + 白名单 + 配额）
- 前端 SSE 订阅 hook + ResearchItem 组件
- traceId HTTP header 透传

### 2.2 演进路径（协议就绪，实现延后）

- 路由多 config 差异化（Demo 三类 type 都 fallback 到 `agent_llm_gpt5`）
- ReportStore 换 MongoDB / PostgreSQL JSONB
- 多租户隔离逻辑（WHERE 过滤 + 配额）
- 权限表 `s2_research_permission` + 订阅/计费
- SSE 推拉结合（Python 回调 + Java 定时轮询兜底）
- ELK / Prometheus / Jaeger 接入

### 2.3 明确不做（YAGNI）

- 断点续传（message_history 持久化 + resume_from_turn）
- 任务取消接口、任务列表查询接口
- 任务级 reactive 实现（WebClient）
- ELK / Prometheus / 分布式追踪
- 负载测试、chaos engineering
- E2E 自动化（手工跑通即可）

---

## 3. 整体架构

### 3.1 数据流总览

```
[用户] 在 ChatItem 结果区点击"深度研究"
   │
   ▼  POST /api/chat/research/query/{queryId}        (前端 → Java)
[Java 网关]
   - UserHolder.findUser() 拿当前用户
   - permissionChecker.check(user)  ← 权限+配额+并发
   - 从 ChatQueryDO 取 question + textResult + textSummary + 维度/指标
   - 截断拼成 task + context
   - 生成 jobId = UUID，拿 traceId
   - 写 s2_chat_research_job(PENDING)
   - @Async 调 Python（带 Authorization + X-Trace-Id header）
   - 返回 {jobId, status:PENDING}
   │
   │                                              ────►  [Python miro-flow]
   │                                                     FastAPI dependency 验 service token
   │                                                     IntentClassifier 分类（1 次 LLM 调用）
   │                                                     TypeToConfig 映射
   │                                                     写 SQLite(PENDING)
   │                                                     asyncio.create_task 执行 pipeline
   │                                                     立即返回 202 + job_id
   │
   ▼  EventSource 订阅 /api/chat/research/{jobId}/stream
[前端]                                          [Python pipeline 运行]
   - 先 GET 当前状态                                - execute_task_pipeline
   - 终态则关闭                                     - 长度控制（句子边界截断）
   - 订阅 SSE                                       - 写 outputs/{tenant}/research_jobs/{job_id}.json
   - onerror 3 秒重连                               - 更新 SQLite(COMPLETED)
                                                       │
[Java @Scheduled fixedDelay=2000]                       │
   - 扫 s2_chat_research_job WHERE status IN (PENDING, RUNNING)
   - 对每条记录 GET /v1/research/jobs/{jobId}
   - 状态变化 → 更新本地表 + 推 SSE
   - 超时（15min）→ 标 FAILED
```

### 3.2 两个独立方向（关键澄清）

| 方向 | 机制 | 频率 |
|------|------|------|
| Python 状态 → Java 表 | Java `@Scheduled` 主动拉 Python | 每 2 秒 |
| Java 表 → 前端 UI | Java SSE 推送 + GET fallback（首次/重连） | 事件驱动 |

**关键设计**：Java→Python 流量与前端用户数解耦。100 个用户同时轮询，Java 仍然每 2 秒一次固定频率向 Python 发请求。

---

## 4. 跨服务契约

### 4.1 REST 契约（Java ↔ Python · 内部）

**POST `/v1/research/jobs`**（Python 新增）

Headers:
```
Authorization: Bearer <RESEARCH_SERVICE_TOKEN>
X-Trace-Id: supersonic_<UUID>
Content-Type: application/json
```

Request body:
```json
{
  "job_id": "uuid-由-Java-生成",
  "trace_id": "supersonic_xxx",
  "tenant_id": "default",
  "task": "用户原问题（来自 ChatQueryDO.question）",
  "context": "截断后的 textResult/textSummary + 维度/指标",
  "config_file_name": null,
  "retrieval_mode": "hybrid",
  "length_budget": 900
}
```

Response 202:
```json
{ "job_id": "...", "status": "PENDING" }
```

**GET `/v1/research/jobs/{job_id}`**（Python 新增）

Response 200:
```json
{
  "job_id": "...",
  "tenant_id": "default",
  "trace_id": "...",
  "research_type": "industry",
  "status": "PENDING | RUNNING | COMPLETED | FAILED",
  "report_summary": "...",
  "report_uri": "fs://outputs/default/research_jobs/{job_id}.json",
  "error_msg": "...",
  "created_at": "...",
  "updated_at": "...",
  "started_at": "...",
  "completed_at": "..."
}
```

Query 参数 `?include_full=true`：按需读取完整报告 JSON 文件并返回 `report_full` 字段（Java 在 COMPLETED 时拉一次）。

### 4.2 REST 契约（前端 ↔ Java · 外部）

| 方法 | 路径 | 响应 |
|------|------|------|
| POST | `/api/chat/research/query/{queryId}` | `200 {jobId, status:PENDING}` / `400`（无 textSummary）/ `403`（无权限）/ `429`（配额）/ `409`（并发） |
| GET | `/api/chat/research/{jobId}` | `200 {jobId, queryId, status, reportSummary?, reportFull?, errorMsg?}` |
| GET | `/api/chat/research/{jobId}/stream` | `SseEmitter`（`text/event-stream`，状态变化推送） |

### 4.3 状态机

```
            ┌──────────────────────────────────────┐
            │                                      │
PENDING ──► RUNNING ──► COMPLETED                  │
   │           │                                  │
   │           └──► FAILED（Python 异常 / 超时）   │
   │                                              │
   └──► FAILED（Python 启动恢复扫到 RUNNING）◄────┘
```

**状态迁移规则**：

| 迁移 | 触发时机 | 实现位置 |
|------|----------|----------|
| → PENDING | POST `/v1/research/jobs` 收到请求 | `routes.py` create_job |
| → RUNNING | `run_pipeline_async` 开始执行 | `pipeline_adapter.py` 入口 |
| → COMPLETED | `execute_task_pipeline` 正常返回（含 max_turns 到顶但有 final summary） | `pipeline_adapter.py` try 块末尾 |
| → FAILED | pipeline 抛异常 / Python 启动恢复扫到 / Java 15min 超时 | `pipeline_adapter.py` except / `recover_stale_jobs` / `ResearchSyncScheduler` |

### 4.4 关键设计决策（5 条）

1. **jobId 由 Java 生成**（UUID）——Java 控制命名空间，Python 不自创 task_id
2. **traceId 从 Java MDC 透传到 Python**——HTTP header `X-Trace-Id`，便于事后排查
3. **路由由 Python 全权决策**——IntentClassifier 判断类型，Java 只传 `task + context`，不感知业务
4. **前端永远不直连 Python**——所有调用过 Java 网关
5. **超时统一在 Java 侧**——Java 启动 job 记录 `started_at`，15 分钟仍 PENDING/RUNNING 则 Java 主动标 FAILED

---

## 5. Python 侧设计

### 5.1 文件结构（新增/修改）

```
miro-flow-solution/
└── server/
    ├── app.py                              [修改] 挂载 REST router + startup 事件 + trace_id middleware
    ├── rest/                               [新增目录]
    │   ├── __init__.py
    │   ├── routes.py                       [新增] FastAPI router: POST/GET /v1/research/jobs
    │   ├── models.py                       [新增] Pydantic 请求/响应模型
    │   ├── deps.py                         [新增] FastAPI dependency: verify_service_token
    │   ├── job_store.py                    [新增] SQLite 持久化 + 启动恢复
    │   ├── intent.py                       [新增] IntentClassifier
    │   ├── length_control.py               [新增] 句子边界截断
    │   ├── report_store.py                 [新增] ReportStore Protocol + FileSystemReportStore
    │   ├── logging_config.py               [新增] trace_id filter + research logger
    │   └── pipeline_adapter.py             [新增] run_pipeline_async 包装 execute_task_pipeline
    └── bridge/runner.py                    [不动] WebSocket 路径仍用 StreamingTaskRunner
```

**WebSocket `/ws` 完全不动**——原 miro-flow Next.js 前端继续用。REST 是新增并列路径，两条路径最终都调用 `execute_task_pipeline()`。

### 5.2 SQLite Schema

文件位置：`server/rest/research_jobs.db`（SQLite 单文件，不引入 DB 进程）。

```sql
CREATE TABLE IF NOT EXISTS research_jobs (
    job_id           TEXT PRIMARY KEY,          -- Java 生成的 UUID
    tenant_id        TEXT NOT NULL DEFAULT 'default',
    trace_id         TEXT,                       -- 透传 SuperSonic traceId
    task             TEXT NOT NULL,             -- 原始用户问题
    context          TEXT,                       -- Java 截断后的查询结果+维度
    research_type    TEXT,                       -- IntentClassifier 输出: industry/academic/default
    config_file_name TEXT,                       -- 实际使用的 Hydra config
    status           TEXT NOT NULL,             -- PENDING/RUNNING/COMPLETED/FAILED
    report_summary   TEXT,                       -- 截断版（≤ length_budget），高频查询返回
    report_uri       TEXT,                       -- 完整报告 URI（如 fs://outputs/.../job.json）
    error_msg        TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    started_at       TEXT,
    completed_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_status        ON research_jobs(status);
CREATE INDEX IF NOT EXISTS idx_trace_id      ON research_jobs(trace_id);
CREATE INDEX IF NOT EXISTS idx_tenant_status ON research_jobs(tenant_id, status);
```

**关键设计**：不存完整报告大字段（`report_full`）——存路径索引 `report_uri`，避免高频状态查询读 overflow pages。

### 5.3 ReportStore 抽象（演进锚点 #1）

```python
# server/rest/report_store.py
from pathlib import Path
import json
from typing import Protocol

class ReportStore(Protocol):
    def save(self, job_id: str, tenant_id: str, payload: dict) -> str: ...
    def get(self, job_id: str, tenant_id: str = "default") -> dict | None: ...
    def delete(self, job_id: str, tenant_id: str = "default") -> None: ...

class FileSystemReportStore:
    """当前实现：JSON 文件存到 outputs/{tenant_id}/research_jobs/{job_id}.json

    设计动机：
    - JSON 含结构化字段（report_markdown + boxed_answer + metadata），未来迁移 MongoDB/PostgreSQL JSONB 格式不变
    - 按 tenant 分目录，未来多租户自然隔离
    - 开发者可直接打开 JSON 文件调试
    """

    def __init__(self, base_dir: str = "outputs"):
        self.base_dir = Path(base_dir)

    def _path_for(self, tenant_id: str, job_id: str) -> Path:
        return self.base_dir / tenant_id / "research_jobs" / f"{job_id}.json"

    def save(self, job_id: str, tenant_id: str, payload: dict) -> str:
        path = self._path_for(tenant_id, job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8"
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

**报告 JSON 结构**：

```json
{
  "job_id": "uuid",
  "trace_id": "supersonic_xxx",
  "task": "...",
  "research_type": "industry",
  "report_markdown": "...",          // 完整报告 Markdown 文本
  "boxed_answer": "...",             // pipeline 已有的结构化答案
  "metadata": {                       // 可扩展元数据，加键不破坏 schema
    "word_count": 5234,
    "model_used": "gpt-5",
    "config_file_name": "agent_llm_gpt5",
    "turn_count": 12
  },
  "created_at": "2026-08-04T...",
  "completed_at": "2026-08-04T..."
}
```

### 5.4 IntentClassifier（路由 · 演进锚点 #2）

```python
# server/rest/intent.py
TYPE_TO_CONFIG = {
    "industry": "agent_llm_gpt5",      # Demo: fallback 到通用 config
    "academic": "agent_llm_gpt5",      # Demo: fallback 到通用 config
    "default":  "agent_llm_gpt5",
}

class IntentClassifier:
    PROMPT = """判断以下研究任务的类型，只返回一个词：
- industry（行业研究/财报/市场分析）
- academic（学术研究/文献/方法论）
- default（无法明确分类）

任务：{task}
上下文：{context_head}

类型："""

    def __init__(self, llm_client):
        self.llm_client = llm_client

    async def classify(self, task: str, context: str) -> str:
        try:
            resp = await self.llm_client.complete(
                self.PROMPT.format(task=task, context_head=context[:500])
            )
            t = resp.strip().lower()
            return t if t in TYPE_TO_CONFIG else "default"
        except Exception:
            return "default"   # 失败 fallback
```

### 5.5 长度控制（三层级联）

```python
# server/rest/length_control.py
import re

SENTENCE_BOUNDARY = re.compile(r'(?<=[。！？\n])')

def enforce_length_budget(report: str, budget: int = 900) -> str:
    """句子边界感知截断

    设计原则：
    - Prompt 软引导（task description 内已要求 length_budget 字数）
    - 产出后硬兜底（此处）：按句子边界截断，不破坏内容
    - 允许 20% 浮动，避免勉强
    """
    if len(report) <= int(budget * 1.2):
        return report

    parts = SENTENCE_BOUNDARY.split(report)
    result, total = [], 0
    for p in parts:
        if total + len(p) > budget:
            break
        result.append(p)
        total += len(p)

    summary = "".join(result).rstrip()
    if len(summary) < len(report):
        summary += "\n\n…（已省略部分细节，完整报告见 report_full）"
    return summary
```

### 5.6 pipeline_adapter.py · 异步执行包装

```python
# server/rest/pipeline_adapter.py
import logging
from datetime import datetime, timezone
from .job_store import JobStore
from .report_store import FileSystemReportStore
from .length_control import enforce_length_budget
from ..bridge.config_loader import compose_config, create_pipeline_components
from src.core.pipeline import execute_task_pipeline

logger = logging.getLogger("server.rest.pipeline_adapter")
report_store = FileSystemReportStore()

async def run_pipeline_async(
    job_id: str, task: str, context: str,
    config_name: str, trace_id: str,
    tenant_id: str, length_budget: int,
    job_store: JobStore, llm_client,
):
    try:
        # trace_id 写 contextvar，Python logging 带上
        from .logging_config import set_trace_id
        set_trace_id(trace_id)

        job_store.update(job_id,
            status="RUNNING",
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        # 组装完整 task description（含长度软引导）
        full_task = (
            f"{task}\n\n## Context\n{context}\n\n## 要求\n"
            f"请产出 {length_budget} 字以内的深度研究报告。"
        )

        # 调用现有 execute_task_pipeline
        cfg = compose_config(config_name)
        components = create_pipeline_components(cfg)
        final_answer, boxed_answer, log_path = await execute_task_pipeline(
            cfg=cfg,
            task_name=job_id,
            task_id=job_id,
            task_description=full_task,
            task_file_name=None,
            main_agent_tool_manager=components[0],
            sub_agent_tool_managers=components[1],
            output_formatter=components[2],
            log_path=pathlib.Path("logs") / f"{job_id}.json",   # 与现有 TaskTracer 日志目录一致
            metadata={"trace_id": trace_id, "source": "rest_api"},
        )

        # 长度控制：句子边界截断
        summary = enforce_length_budget(final_answer, budget=length_budget)

        # 完整报告写 JSON 文件
        report_uri = report_store.save(job_id, tenant_id, {
            "job_id": job_id,
            "trace_id": trace_id,
            "task": task,
            "report_markdown": final_answer,
            "boxed_answer": boxed_answer,
            "metadata": {
                "config_file_name": config_name,
                "model_used": cfg.get("main_agent", {}).get("model", "unknown"),
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })

        # SQLite 只存 summary + URI
        job_store.update(job_id,
            status="COMPLETED",
            report_summary=summary,
            report_uri=report_uri,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.info(f"job {job_id} completed", extra={"trace_id": trace_id})

    except Exception as e:
        import traceback
        job_store.update(job_id,
            status="FAILED",
            error_msg=f"{type(e).__name__}: {str(e)[:500]}",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.exception(f"job {job_id} failed", extra={"trace_id": trace_id})
```

### 5.7 启动恢复

```python
# server/rest/job_store.py
from datetime import datetime, timezone

class JobStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_schema()

    def recover_stale_jobs(self):
        """启动时调用：把所有 PENDING/RUNNING 标 FAILED"""
        stale = self.list_by_status_in(["PENDING", "RUNNING"])
        for job in stale:
            self.update(job.job_id,
                status="FAILED",
                error_msg="runner restarted (process crashed or restarted)",
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
            logger.warning(
                f"recovered stale job {job.job_id}",
                extra={"trace_id": job.trace_id},
            )
```

```python
# server/app.py 修改
@app.on_event("startup")
async def startup_recovery():
    job_store.recover_stale_jobs()
    logger.info("startup recovery completed")
```

### 5.8 Service Token 验证（独立 token，不复用 SuperSonic JWT）

**为什么独立 token**：
- SuperSonic JWT payload 含 `token_user_password` 字段（密码哈希），跨服务传递会泄漏
- Python 不应该知道 SuperSonic 的 JWT secret，两个服务绑死违反边界
- user token 代表"用户操作"，service token 代表"服务调用"——身份语义不同

```python
# server/rest/deps.py
import os
from fastapi import Header, HTTPException

SERVICE_TOKEN = os.getenv("RESEARCH_SERVICE_TOKEN", "")

async def verify_service_token(authorization: str = Header(...)) -> bool:
    expected = f"Bearer {SERVICE_TOKEN}"
    if authorization != expected:
        raise HTTPException(401, "invalid service token")
    return True
```

```python
# server/rest/routes.py
from fastapi import APIRouter, Depends, BackgroundTasks
from .deps import verify_service_token

router = APIRouter()

@router.post(
    "/v1/research/jobs",
    status_code=202,
    dependencies=[Depends(verify_service_token)],
)
async def create_job(req: CreateJobRequest, bg: BackgroundTasks):
    research_type = await intent_classifier.classify(req.task, req.context)
    config_name = TYPE_TO_CONFIG.get(research_type, "agent_llm_gpt5")

    job_store.create(
        job_id=req.job_id,
        tenant_id=req.tenant_id or "default",
        trace_id=req.trace_id,
        task=req.task,
        context=req.context,
        research_type=research_type,
        config_file_name=config_name,
        status="PENDING",
    )

    bg.add_task(run_pipeline_async, ...)

    return {"job_id": req.job_id, "status": "PENDING"}
```

### 5.9 多租户字段（演进锚点 #3）

- `tenant_id` 进 SQLite schema 和 REST 协议，缺省 `"default"`
- Demo 不实现隔离逻辑（按 `job_id` 主键查天然隔离）
- ReportStore 按 tenant 分目录（当前所有文件落 `outputs/default/research_jobs/`）
- 未来加列表接口时补 `WHERE tenant_id = ?` 过滤

### 5.10 Python 侧不做的事

- 断点续传（message_history 持久化）
- message_history 加载/恢复路径
- 任务取消接口、任务列表查询接口
- IntentClassifier accuracy 评估（fallback 容忍错分）

---

## 6. Java 侧设计

### 6.1 文件结构（新增/修改）

```
chat/server/src/main/java/com/tencent/supersonic/chat/server/
└── research/                                          [新增包]
    ├── ResearchJobController.java                     [新增] REST 入口
    ├── ResearchJobService.java                        [新增] 业务接口
    ├── ResearchJobServiceImpl.java                    [新增] 业务实现
    ├── ResearchPermissionChecker.java                 [新增] 权限+配额+并发校验
    ├── PythonResearchClient.java                      [新增] 调 Python REST
    ├── ResearchSseRegistry.java                       [新增] SSE emitter 管理
    ├── ResearchSyncScheduler.java                     [新增] @Scheduled 同步任务
    ├── ResearchExceptionHandler.java                  [新增] 403/429/409 映射
    ├── dto/
    │   ├── CreateJobRequest.java
    │   ├── CreateJobResponse.java
    │   ├── JobStatusResponse.java
    │   ├── ResearchFeature.java
    │   └── PythonJobStatus.java
    └── persistence/
        ├── ResearchJobMapper.java                     [新增] MyBatis-Plus Mapper
        ├── ResearchJobMapper.xml
        └── ResearchJobDO.java

chat/server/src/main/resources/db/migration/
└── V20260804__create_research_job.sql                 [新增] 表结构

launchers/standalone/src/main/resources/
└── application.yml                                    [修改] 加 research.* 配置
```

**修改现有文件**：
- `ChatQueryController.java` 或 `ChatQueryService` 实现：在 execute 响应里附加 `researchFeature`

**总计：12 个新文件，2 处修改，1 处 SQL**。

### 6.2 数据表 `s2_chat_research_job`

```sql
-- chat/server/src/main/resources/db/migration/V20260804__create_research_job.sql
CREATE TABLE s2_chat_research_job (
    job_id          VARCHAR(64) PRIMARY KEY,
    query_id        BIGINT NOT NULL,
    tenant_id       VARCHAR(64) NOT NULL DEFAULT 'default',
    trace_id        VARCHAR(128),
    created_by      BIGINT NOT NULL,                  -- 审计：哪个用户触发
    agent_id        INTEGER,
    task            TEXT,                              -- Java 组装后传给 Python 的
    python_status   VARCHAR(16),                      -- PENDING/RUNNING/COMPLETED/FAILED
    report_summary  TEXT,
    report_full     TEXT,
    error_msg       TEXT,
    created_at      TIMESTAMP NOT NULL,
    started_at      TIMESTAMP,
    completed_at    TIMESTAMP,
    INDEX idx_query_id (query_id),
    INDEX idx_created_by_status (created_by, python_status),   -- 配额+并发统计
    INDEX idx_python_status (python_status)                     -- @Scheduler 扫 RUNNING
) COMMENT '深度研究任务';
```

**重要原则**：表里**不存权限规则**——权限是运行时判断（基于 user 对象 + 配置）。表只存审计数据。

### 6.3 五个核心组件

#### 6.3.1 `ResearchJobController` · REST 入口

```java
@RestController
@RequestMapping("/api/chat/research")
public class ResearchJobController {

    @Autowired private ResearchJobService service;
    @Autowired private ResearchSseRegistry sseRegistry;

    @PostMapping("/query/{queryId}")
    public Result<CreateJobResponse> createResearch(
            @PathVariable Long queryId,
            HttpServletRequest request) {
        User user = UserHolder.findUser(request, null);
        return Result.success(service.createResearch(user, queryId));
    }

    @GetMapping("/{jobId}")
    public Result<JobStatusResponse> getStatus(@PathVariable String jobId) {
        return Result.success(service.getStatus(jobId));
    }

    @GetMapping(
        value = "/{jobId}/stream",
        produces = MediaType.TEXT_EVENT_STREAM_VALUE
    )
    public SseEmitter streamStatus(@PathVariable String jobId) {
        return sseRegistry.register(jobId);
    }
}
```

#### 6.3.2 `ResearchJobServiceImpl` · 业务流程

```java
@Service
public class ResearchJobServiceImpl implements ResearchJobService {

    @Autowired private ChatQueryService chatQueryService;
    @Autowired private ResearchPermissionChecker permissionChecker;
    @Autowired private PythonResearchClient pythonClient;
    @Autowired private ResearchJobMapper jobMapper;
    @Autowired private ResearchSseRegistry sseRegistry;

    @Override
    public CreateJobResponse createResearch(User user, Long queryId) {
        // 1. 取 ChatQueryDO（复用现有 API）
        ChatQueryDO query = chatQueryService.getChatQuery(queryId);
        if (query == null || StringUtils.isEmpty(query.getTextSummary())) {
            throw new ResearchBadRequestException(
                "查询结果不存在或无描述性解读");
        }

        // 2. 权限 + 配额 + 并发校验
        permissionChecker.check(user);

        // 3. 组装 task + context（截断到 ≤ 4000 字）
        String task = query.getQuestion();
        String context = buildContext(query);

        // 4. 生成 jobId + 拿 traceId
        String jobId = UUID.randomUUID().toString();
        String traceId = TraceIdUtil.getTraceId();

        // 5. 写 Java 表（PENDING）
        ResearchJobDO job = new ResearchJobDO();
        job.setJobId(jobId);
        job.setQueryId(queryId);
        job.setTenantId("default");
        job.setTraceId(traceId);
        job.setCreatedBy(user.getId());
        job.setAgentId(query.getAgentId());
        job.setTask(task);
        job.setPythonStatus("PENDING");
        job.setCreatedAt(new Date());
        jobMapper.insert(job);

        // 6. 异步调 Python（不阻塞响应）
        pythonClient.createJobAsync(jobId, traceId, task, context);

        return new CreateJobResponse(jobId, "PENDING");
    }

    private String buildContext(ChatQueryDO query) {
        // textResult + textSummary + 维度 + 指标，总长度 ≤ 4000 字
        StringBuilder sb = new StringBuilder();
        if (query.getTextResult() != null) {
            sb.append("## 查询结果\n").append(truncate(query.getTextResult(), 2000)).append("\n\n");
        }
        if (query.getTextSummary() != null) {
            sb.append("## 描述性解读\n").append(truncate(query.getTextSummary(), 1000)).append("\n\n");
        }
        // Demo 范围内只取 textResult + textSummary；维度/指标列表留作扩展
        // 未来从 ParseContext.getParsedS2SQL() 提取 metrics/dimensions 字段追加到 context
        return sb.toString();
    }
}
```

#### 6.3.3 `ResearchPermissionChecker` · 权限校验

```java
@Component
public class ResearchPermissionChecker {

    @Value("${research.enabled-admin-only:true}")
    private boolean adminOnly;

    @Value("${research.enabled-users:}")
    private Set<String> whitelist;

    @Value("${research.daily-quota:10}")
    private int dailyQuota;

    @Value("${research.max-concurrent-per-user:1}")
    private int maxConcurrent;

    @Autowired private ResearchJobMapper jobMapper;

    public void check(User user) {
        // 1. 功能权限（内测期：admin OR 白名单）
        boolean permitted = false;
        if (adminOnly && Integer.valueOf(1).equals(user.getIsAdmin())) {
            permitted = true;
        }
        if (whitelist.contains(user.getName())) {
            permitted = true;
        }
        if (!permitted) {
            throw new ResearchPermissionException(
                "深度研究功能内测中，仅对管理员开放");
        }

        // 2. 配额（每用户每日）
        int todayCount = jobMapper.countByUserAndDate(user.getId(), today());
        if (todayCount >= dailyQuota) {
            throw new ResearchQuotaExceededException("今日深度研究次数已用完");
        }

        // 3. 并发（每用户 max_concurrent 个 RUNNING）
        int runningCount = jobMapper.countByUserAndStatus(user.getId(), "RUNNING");
        if (runningCount >= maxConcurrent) {
            throw new ResearchConcurrentException("已有深度研究进行中");
        }
    }

    public boolean isPermitted(User user) {
        // 轻量判断（不抛异常），用于 queryResult.researchFeature.enabled
        if (adminOnly && Integer.valueOf(1).equals(user.getIsAdmin())) return true;
        return whitelist.contains(user.getName());
    }

    public int remainingQuota(User user) {
        return Math.max(0, dailyQuota - jobMapper.countByUserAndDate(user.getId(), today()));
    }
}
```

#### 6.3.4 `PythonResearchClient` · 调 Python REST

```java
@Component
public class PythonResearchClient {

    @Value("${research.python-base-url}")
    private String baseUrl;

    @Value("${research.service-token}")
    private String serviceToken;

    @Autowired @Qualifier("researchExecutor")
    private ThreadPoolExecutorMdcWrapper executor;

    @Async("researchExecutor")
    public void createJobAsync(String jobId, String traceId,
                                String task, String context) {
        CreateJobRequest req = new CreateJobRequest();
        req.setJob_id(jobId);
        req.setTrace_id(traceId);
        req.setTenant_id("default");
        req.setTask(task);
        req.setContext(context);
        req.setLength_budget(900);
        req.setRetrieval_mode("hybrid");

        HttpHeaders headers = new HttpHeaders();
        headers.setBearerAuth(serviceToken);
        headers.set("X-Trace-Id", traceId);
        headers.setContentType(MediaType.APPLICATION_JSON);

        try {
            new RestTemplate().postForEntity(
                baseUrl + "/v1/research/jobs",
                new HttpEntity<>(req, headers),
                String.class
            );
            // 202 + PENDING 即成功
        } catch (Exception e) {
            // 网络异常：让 @Scheduler 在超时后标 FAILED
            log.warn("[research] createJob HTTP failed, jobId={}", jobId, e);
        }
    }

    public PythonJobStatus getStatus(String jobId, boolean includeFull) {
        String url = baseUrl + "/v1/research/jobs/" + jobId;
        if (includeFull) url += "?include_full=true";

        HttpHeaders headers = new HttpHeaders();
        headers.setBearerAuth(serviceToken);
        // traceId 由 MDC 自动透传（如果 RestTemplate 配了 MDC interceptor）

        ResponseEntity<PythonJobStatus> resp = new RestTemplate().exchange(
            url, HttpMethod.GET,
            new HttpEntity<>(headers),
            PythonJobStatus.class
        );
        return resp.getBody();
    }
}
```

#### 6.3.5 `ResearchSyncScheduler` · @Scheduled 同步（核心）

```java
@Component
public class ResearchSyncScheduler {

    private static final Logger log = LoggerFactory.getLogger(ResearchSyncScheduler.class);

    @Value("${research.timeout-minutes:15}")
    private int timeoutMinutes;

    @Autowired private ResearchJobMapper mapper;
    @Autowired private PythonResearchClient pythonClient;
    @Autowired private ResearchSseRegistry sseRegistry;

    @Scheduled(fixedDelayString = "${research.sync-interval-ms:2000}")
    public void syncRunningJobs() {
        List<ResearchJobDO> running = mapper.selectByStatusIn(
            Arrays.asList("PENDING", "RUNNING"));

        for (ResearchJobDO job : running) {
            String oldStatus = job.getPythonStatus();

            // 超时兜底
            if (isTimeout(job, timeoutMinutes)) {
                job.setPythonStatus("FAILED");
                job.setErrorMsg("java-side timeout after " + timeoutMinutes + " min");
                job.setCompletedAt(new Date());
                mapper.updateById(job);
                sseRegistry.send(job.getJobId(), buildEvent(job));
                log.warn("[research] timeout jobId={} traceId={}",
                    job.getJobId(), job.getTraceId());
                continue;
            }

            try {
                // 拉取 Python 状态（COMPLETED 时拉 full）
                boolean includeFull = "COMPLETED".equals(oldStatus) == false;
                PythonJobStatus p = pythonClient.getStatus(job.getJobId(), includeFull);

                // 状态变化才更新 + 推送
                if (!oldStatus.equals(p.getStatus())) {
                    mergeStatus(job, p);
                    mapper.updateById(job);
                    sseRegistry.send(job.getJobId(), buildEvent(job));
                    log.info("[research] status change jobId={} {} -> {}",
                        job.getJobId(), oldStatus, p.getStatus());
                }
            } catch (Exception e) {
                // 网络抖动：跳过本次，下次再试
                log.debug("[research] sync failed jobId={} will retry: {}",
                    job.getJobId(), e.getMessage());
            }
        }
    }

    private boolean isTimeout(ResearchJobDO job, int minutes) {
        long elapsed = System.currentTimeMillis() - job.getCreatedAt().getTime();
        return elapsed > minutes * 60_000L;
    }
}
```

### 6.4 `ResearchSseRegistry` · SSE 推送

```java
@Component
public class ResearchSseRegistry {

    @Autowired private ResearchJobMapper mapper;

    private final Map<String, List<SseEmitter>> emitters = new ConcurrentHashMap<>();

    public SseEmitter register(String jobId) {
        SseEmitter emitter = new SseEmitter(0L);   // 不超时
        emitters.computeIfAbsent(jobId, k -> new CopyOnWriteArrayList<>())
                .add(emitter);

        emitter.onCompletion(() -> remove(jobId, emitter));
        emitter.onTimeout(() -> remove(jobId, emitter));
        emitter.onError(e -> remove(jobId, emitter));

        // 首次连接立即推当前状态（避免新连接看不到状态）
        ResearchJobDO current = mapper.selectById(jobId);
        if (current != null) {
            try {
                emitter.send(SseEmitter.event().data(buildEvent(current)));
            } catch (IOException ignored) {}
        }
        return emitter;
    }

    public void send(String jobId, Object event) {
        List<SseEmitter> list = emitters.get(jobId);
        if (list == null) return;   // 无人订阅，丢弃（表已更新，前端重连会拉到最新）
        for (SseEmitter e : list) {
            try {
                e.send(SseEmitter.event().data(event));
            } catch (IOException ex) {
                remove(jobId, e);
            }
        }
    }

    private void remove(String jobId, SseEmitter emitter) {
        emitters.computeIfPresent(jobId, (k, v) -> {
            v.remove(emitter);
            return v.isEmpty() ? null : v;
        });
    }

    private JobStatusResponse buildEvent(ResearchJobDO job) {
        // 构造 SSE 推送的 payload
        return new JobStatusResponse(
            job.getJobId(), job.getQueryId(),
            job.getPythonStatus(),
            job.getReportSummary(), job.getReportFull(),
            job.getErrorMsg()
        );
    }
}
```

### 6.5 与现有 `ChatQueryController` 集成

在 queryResult 或 getExecuteSummary 响应里附加 `researchFeature`（不调用独立权限接口）：

```java
// 修改 ChatQueryController.queryData 或 ChatQueryService.queryData（具体位置实现阶段确认）
// 目标：前端拿到 queryResult 时能读到 researchFeature 字段
public Result<QueryData> queryData(...) {
    QueryData data = chatQueryService.queryData(...);

    // 新增：附加 researchFeature
    User user = UserHolder.findUser(request, null);
    data.setResearchFeature(buildResearchFeature(user, data.getQueryId()));

    return Result.success(data);
}

private ResearchFeature buildResearchFeature(User user, Long queryId) {
    ResearchFeature rf = new ResearchFeature();
    rf.setEnabled(permissionChecker.isPermitted(user));
    rf.setRemainingToday(permissionChecker.remainingQuota(user));

    ResearchJobDO runningJob = jobMapper.findRunningByQueryId(queryId);
    rf.setRunningJobId(runningJob != null ? runningJob.getJobId() : null);

    return rf;
}
```

### 6.6 配置项（`application.yml`）

```yaml
research:
  python-base-url: http://localhost:8000
  service-token: ${RESEARCH_SERVICE_TOKEN:dev-default-token-please-change}

  # 权限（内测期）
  enabled-admin-only: true
  enabled-users: ""                                  # 逗号分隔用户名

  # 配额
  daily-quota: 10
  max-concurrent-per-user: 1

  # 同步
  sync-interval-ms: 2000
  timeout-minutes: 15

  # 字数预算
  length-budget: 900

spring:
  mvc:
    async:
      request-timeout: -1                             # SSE 不超时
```

### 6.7 异常映射

```java
@RestControllerAdvice
public class ResearchExceptionHandler {

    @ExceptionHandler(ResearchPermissionException.class)
    public ResponseEntity<ErrorBody> handle403(ResearchPermissionException e) {
        return ResponseEntity.status(403)
            .body(new ErrorBody("RESEARCH_FORBIDDEN", e.getMessage()));
    }

    @ExceptionHandler(ResearchQuotaExceededException.class)
    public ResponseEntity<ErrorBody> handle429(ResearchQuotaExceededException e) {
        return ResponseEntity.status(429)
            .body(new ErrorBody("RESEARCH_QUOTA_EXCEEDED", e.getMessage()));
    }

    @ExceptionHandler(ResearchConcurrentException.class)
    public ResponseEntity<ErrorBody> handle409(ResearchConcurrentException e) {
        return ResponseEntity.status(409)
            .body(new ErrorBody("RESEARCH_CONCURRENT", e.getMessage()));
    }
}
```

### 6.8 Java 侧不做的事

- 任务列表查询接口、任务取消接口
- 权限表 `s2_research_permission`（内测期 isAdmin + 白名单够用）
- `@AuthenticationIgnore`（复用 SuperSonic 现有认证）
- WebClient（RestTemplate 同步够用，Python 立即返回 202）

---

## 7. 前端设计

### 7.1 文件结构（新增/修改）

```
webapp/packages/chat-sdk/src/
├── components/
│   └── ChatItem/
│       ├── ExecuteItem.tsx                       [修改] 挂载 ResearchItem
│       └── ResearchItem/                         [新增目录]
│           ├── index.tsx                         [新增] 容器组件 + 状态机
│           ├── ResearchTrigger.tsx               [新增] 启动按钮
│           ├── ResearchProgress.tsx              [新增] 进行中 loading
│           ├── ResearchReport.tsx                [新增] 报告展示 + 折叠
│           └── styles.less                       [新增]
├── hooks/
│   └── useResearchJobStream.ts                   [新增] SSE 订阅 hook
└── service/
    └── index.ts                                  [修改] 加 3 个 research API
```

**总计：6 个新文件，2 处修改**。

### 7.2 ExecuteItem 集成位置

在 `ExecuteItem.tsx:154-159` 的 `textSummary` 区域下方挂载（最小侵入）：

```tsx
<div className={styles.executeItem}>
    {data.textSummary && (
        <div className={styles.textSummary}>
            <ReactMarkdown>{data.textSummary}</ReactMarkdown>
        </div>
    )}

    {renderByQueryMode(data)}   {/* 原有：表格/图表 */}

    {/* 新增：深度研究引导，只在有 textSummary 时显示 */}
    {data.textSummary && data.researchFeature?.enabled && (
        <ResearchItem
            queryId={data.queryId}
            researchFeature={data.researchFeature}
        />
    )}
</div>
```

### 7.3 ResearchItem 状态机

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   IDLE ──点击──► PENDING ──► RUNNING ──► COMPLETED          │
│                      │                  │                   │
│                      └──► FAILED ◄──────┘                   │
│                      (静默隐藏)                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘

UI 表现：
  IDLE       → "想要对结果做深度研究吗？" [启动按钮]
  PENDING    → loading + "正在准备..."（保留表格 + textSummary）
  RUNNING    → loading + "正在深度研究中，预计 3-10 分钟..."
  COMPLETED  → 在 textSummary 下方展示 report_summary + [查看完整报告]
  FAILED     → ✗ 不渲染任何东西（静默失败）
```

### 7.4 `useResearchJobStream` hook

```typescript
// hooks/useResearchJobStream.ts
import { useEffect, useState } from 'react';
import { getResearchStatus } from '../service';

export type JobStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';

export interface ResearchState {
    status: JobStatus | null;
    report: { summary: string; full?: string } | null;
    errorMsg: string | null;
}

export function useResearchJobStream(jobId: string | null): ResearchState {
    const [state, setState] = useState<ResearchState>({
        status: null, report: null, errorMsg: null,
    });

    useEffect(() => {
        if (!jobId) return;

        let eventSource: EventSource | null = null;
        let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
        let closed = false;

        const connect = async () => {
            if (closed) return;

            try {
                // 1. 先 GET 当前状态（避免 SSE 不推当前状态的问题）
                const current = await getResearchStatus(jobId);
                setState({
                    status: current.status,
                    report: current.reportSummary
                        ? { summary: current.reportSummary, full: current.reportFull }
                        : null,
                    errorMsg: current.errorMsg,
                });

                // 已终态：不订阅
                if (current.status === 'COMPLETED' || current.status === 'FAILED') {
                    return;
                }

                // 2. 订阅 SSE
                eventSource = new EventSource(`/api/chat/research/${jobId}/stream`);

                eventSource.onmessage = (e) => {
                    const data = JSON.parse(e.data);
                    setState({
                        status: data.status,
                        report: data.reportSummary
                            ? { summary: data.reportSummary, full: data.reportFull }
                            : null,
                        errorMsg: data.errorMsg,
                    });
                    if (data.status === 'COMPLETED' || data.status === 'FAILED') {
                        eventSource?.close();
                    }
                };

                eventSource.onerror = () => {
                    eventSource?.close();
                    if (!closed) {
                        reconnectTimer = setTimeout(connect, 3000);   // 3 秒重连
                    }
                };
            } catch (err) {
                if (!closed) {
                    reconnectTimer = setTimeout(connect, 3000);
                }
            }
        };

        connect();

        return () => {
            closed = true;
            eventSource?.close();
            if (reconnectTimer) clearTimeout(reconnectTimer);
        };
    }, [jobId]);

    return state;
}
```

### 7.5 ResearchItem 容器

```tsx
// components/ChatItem/ResearchItem/index.tsx
import { useState } from 'react';
import { useResearchJobStream } from '../../../hooks/useResearchJobStream';
import { createResearchJob } from '../../../service';
import ResearchTrigger from './ResearchTrigger';
import ResearchProgress from './ResearchProgress';
import ResearchReport from './ResearchReport';

interface Props {
    queryId: number;
    researchFeature: {
        enabled: boolean;
        remainingToday: number;
        runningJobId: string | null;
    };
}

export default function ResearchItem({ queryId, researchFeature }: Props) {
    // jobId 初始化：优先用 runningJobId（页面刷新后继续订阅）
    const [jobId, setJobId] = useState<string | null>(
        researchFeature.runningJobId
    );
    const { status, report, errorMsg } = useResearchJobStream(jobId);

    const handleStart = async () => {
        try {
            const res = await createResearchJob(queryId);
            setJobId(res.jobId);
        } catch (err) {
            // 静默失败（权限/配额/并发已在 service 层抛出）
            console.warn('[research] start failed', err);
        }
    };

    // ✗ FAILED：不渲染（静默保留 textSummary）
    if (status === 'FAILED') {
        return null;
    }

    // 进行中
    if (status === 'PENDING' || status === 'RUNNING') {
        return <ResearchProgress status={status} />;
    }

    // 完成
    if (status === 'COMPLETED' && report) {
        return (
            <ResearchReport
                summary={report.summary}
                fullReport={report.full}
            />
        );
    }

    // 默认：启动按钮
    return (
        <ResearchTrigger
            remainingToday={researchFeature.remainingToday}
            runningJobId={researchFeature.runningJobId}
            onStart={handleStart}
        />
    );
}
```

### 7.6 service 层 API

```typescript
// service/index.ts 增量
export const createResearchJob = async (queryId: number) => {
    const res = await request.post(`/api/chat/research/query/${queryId}`);
    return res.data;   // { jobId, status }
};

export const getResearchStatus = async (jobId: string) => {
    const res = await request.get(`/api/chat/research/${jobId}`);
    return res.data;   // { jobId, status, reportSummary?, reportFull?, errorMsg? }
};

// SSE 直接用 EventSource，不走 axios（浏览器原生 API）
```

### 7.7 关键交互细节

**场景 1：页面刷新后继续订阅**
- `queryResult.researchFeature.runningJobId` 不为 null（Java 表里 RUNNING job）
- ResearchItem 初始 jobId 即 `runningJobId`，自动续订 SSE
- 用户体验：刷新后看到"正在深度研究中..."

**场景 2：用户离开页面后回来**
- EventSource 在组件 mount 时重新建立
- `useResearchJobStream` 先 GET 拿当前状态，可能直接是 COMPLETED → 跳过 SSE 订阅

**场景 3：深度研究失败**
- SSE 收到 `{status: 'FAILED', errorMsg: '...'}`
- ResearchItem 返回 `null`，不渲染任何东西
- 用户只看到原表格 + textSummary
- 失败原因在浏览器 console + Java logback 日志里

**场景 4：Python 服务挂了**
- SSE 连接失败 → `onerror` → 3 秒重连
- 重连期间 UI 显示 RUNNING（保持上次状态）
- 如果 Python 一直不响应，Java @Scheduler 15 分钟后标 FAILED → 推送 → UI 静默隐藏

### 7.8 与现有轮询模式的关系

**两条独立的状态获取路径**：

| 数据 | 获取方式 | 管理者 |
|------|----------|--------|
| `textSummary`（描述性解读） | 500ms 轮询 `getExecuteSummary` | `ChatItem/index.tsx` 现有逻辑 |
| 深度研究状态 | SSE 推送 | `ResearchItem` + `useResearchJobStream` |

**互不干扰**：textSummary 轮询失败不影响深度研究 SSE；深度研究挂了不影响 textSummary 展示。

### 7.9 前端不做的事

- 取消按钮（Demo 范围）
- 进度条/百分比（PENDING/RUNNING 两态够）
- 历史报告列表
- 报告导出按钮
- 用户反馈/评分
- toast 提示（静默失败原则）

---

## 8. 权限控制（Java 侧实现）

### 8.1 设计原则

**权限完全在 Java，Python 不感知用户**：
- Python 只验证 service token（防内部直连）
- Python 不需要 user_id / agent_id / 权限规则

**层次划分**：

| 层 | 关心 | 不关心 |
|----|------|--------|
| Python | tenant + job 执行 | user、agent、权限规则 |
| Java | user（权限）+ agent（业务上下文）+ job（路由） | 报告内部内容 |

### 8.2 内测期实现（Demo 范围）

基于 SuperSonic JWT 自带的 `token_is_admin` 字段（`UserWithPassword.java:36-47`）+ application.yml 白名单：

```java
public void check(User user) {
    boolean permitted = false;
    if (adminOnly && Integer.valueOf(1).equals(user.getIsAdmin())) {
        permitted = true;
    }
    if (whitelist.contains(user.getName())) {
        permitted = true;
    }
    if (!permitted) {
        throw new ResearchPermissionException(
            "深度研究功能内测中，仅对管理员开放");
    }
    // ... 配额、并发校验
}
```

### 8.3 前端如何感知权限

**前端不主动查权限接口**——在 `queryResult` 或 `getExecuteSummary` 响应里顺带返回 `researchFeature`：

```typescript
interface ResearchFeature {
    enabled: boolean;          // 当前用户能否看到按钮
    remainingToday: number;    // 今日剩余次数
    runningJobId: string | null;  // null=无进行中
}
```

**按钮状态机**：

| `enabled` | `remainingToday` | `runningJobId` | 按钮状态 |
|-----------|------------------|----------------|----------|
| false | - | - | 不显示（或灰显"内测中"） |
| true | 0 | - | "今日已达上限" |
| true | >0 | 非 null | "查看进行中的研究" |
| true | >0 | null | "启动深度研究" ✓ 可点 |

### 8.4 演进路径

| 阶段 | 权限判断方式 | 改动 |
|------|-------------|------|
| **内测期（Demo）** | `isAdmin` + application.yml 白名单 | 当前方案 |
| **公测期** | 新建 `s2_research_permission` 表 | 加 1 张表 + 改 checker |
| **正式期** | 接订阅/计费系统（按 user_tier） | 改 checker，schema 不动 |
| **各阶段** | Python 协议**完全不变** | ✓ |

### 8.5 关键澄清：权限信息 vs 审计信息

| 类型 | 存哪 | 例子 |
|------|------|------|
| **权限信息**（运行时判断） | 不存表，运行时从 user 对象 + 配置读 | "alice 是 admin 吗？" |
| **审计信息**（事后追溯） | 存 `s2_chat_research_job.created_by` | "job X 是 alice 触发的" |
| **配额统计**（运行时聚合） | 不专门存，从审计表聚合 | "alice 今天用了几次？" |

**不存权限表**：内测阶段权限规则简单（isAdmin），存表是过度设计。

---

## 9. 错误处理 + 可观测性 + 测试

### 9.1 错误处理矩阵（10 种失败场景）

| # | 失败点 | Python 状态 | Java 响应 | 前端表现 |
|---|--------|------------|-----------|---------|
| 1 | Python 服务进程挂了 | 无响应 | GET 失败，保持 RUNNING；15min 超时标 FAILED | 继续 loading → 最终静默隐藏 |
| 2 | pipeline 抛异常 | FAILED + error_msg | 拉到 FAILED，更新表，推 SSE | return null（静默） |
| 3 | IntentClassifier 失败 | fallback `default` | 正常 RUNNING | 正常完成 |
| 4 | LLM 调用失败 | pipeline 抛异常 → FAILED | 同 #2 | 静默 |
| 5 | 报告文件写入失败 | pipeline 抛异常 → FAILED | 同 #2 | 静默 |
| 6 | SQLite 写入失败 | HTTP 500 | Java 标 FAILED + error_msg | 静默 |
| 7 | Java→Python 网络抖动 | - | GET 失败，下次 @Scheduled 重试 | 继续 loading（用户无感） |
| 8 | Service token 不匹配 | HTTP 401 | Java 标 FAILED + 严重告警 | 静默（但日志 ERROR） |
| 9 | Job 不存在 | HTTP 404 | Java 标 FAILED（清理孤儿记录） | 静默 |
| 10 | Python 重启过程中 | 启动时扫 RUNNING 标 FAILED | Java 拉到 FAILED，推 SSE | 静默 |

**核心原则**（对齐 B5）：
- 所有失败路径 → 前端 `return null`（保留 textSummary）
- 失败原因**永远**写日志（带 traceId）
- 不弹 toast、不重试请求、不覆盖 textSummary

### 9.2 traceId 完整链路

```
[Java 入口] TraceIdUtil.getTraceId()（从 MDC，或 LogInterceptor 生成）
    │
    ▼  HTTP header: X-Trace-Id: supersonic_<UUID>
[Python FastAPI middleware]
    │
    ▼  set_trace_id(...) → contextvar
[Python pipeline 执行]
    │
    ├── logging filter 带 trace_id
    ├── TaskTracer JSON 写 trace_id 字段
    └── ReportStore JSON 含 trace_id
    │
    ▼  HTTP response header: X-Trace-Id: <原值回传>
[Java 接收] 校验 traceId 一致性
    │
    ▼  写入 s2_chat_research_job.trace_id
[Java 日志] logback pattern `%X{traceId}` 自动带
```

**事后排查**（单条命令）：
```bash
grep "supersonic_abc123" \
    /path/to/supersonic/logs/s2-info.log \
    /path/to/supersonic/logs/s2-error.log \
    /path/to/miro-flow/logs/research.log \
    /path/to/miro-flow/logs/{job_id}.json
```

### 9.3 日志策略

**Java 侧**（复用现有 logback-spring.xml）：

| Appender | 文件 | 用途 | traceId |
|----------|------|------|---------|
| `fileInfoLog`（现有） | `logs/s2-info.log` | 全量 INFO | ✓ `%X{traceId}` |
| `fileErrorLog`（现有） | `logs/s2-error.log` | ERROR 级 | ✓ |
| `serviceLog`（现有） | `logs/serviceinfo.chat.log` | `com.tencent.supersonic` 包 | ✓ |

**Python 侧**（新增）：

```python
# server/rest/logging_config.py
LOGGING = {
    "version": 1,
    "filters": {
        "trace_id": {"()": "server.rest.logging.TraceIdFilter"},
    },
    "formatters": {
        "research": {
            "format": "[%(asctime)s] [%(name)s] [%(levelname)s] "
                      "[trace_id=%(trace_id)s] %(message)s"
        },
    },
    "handlers": {
        "research": {
            "class": "logging.FileHandler",
            "filename": "logs/research.log",
            "formatter": "research",
            "filters": ["trace_id"],
        },
    },
    "loggers": {
        "server.rest": {"handlers": ["research"], "level": "INFO"},
    },
}
```

**TaskTracer JSON**（现有，不动）：每次 LLM 调用前后写 `logs/{task_id}.json`，含完整 `message_history`——调试时直接打开看。

### 9.4 测试策略（三层）

#### 单元测试

**Java 侧（JUnit 5 + Mockito）**

| 测试类 | 覆盖点 |
|--------|--------|
| `ResearchPermissionCheckerTest` | isAdmin 通过、白名单通过、配额耗尽 429、并发限制 409、非 admin 无权限 403 |
| `ResearchJobServiceImplTest` | mock PythonClient，验证 jobId 生成、表插入、traceId 透传 |
| `ResearchSyncSchedulerTest` | mock Mapper + Client，验证状态变化触发推送、超时兜底、空跑 |
| `ResearchSseRegistryTest` | emitter 注册/移除/推送给多订阅者/无人订阅丢弃 |
| `PythonResearchClientTest` | mock RestTemplate，验证 header（Authorization + X-Trace-Id） |
| `ResearchExceptionHandlerTest` | 403/429/409 映射 |

**Python 侧（pytest）**

| 测试文件 | 覆盖点 |
|---------|--------|
| `test_intent.py` | IntentClassifier 三分类 + LLM 失败 fallback |
| `test_length_control.py` | 句子边界截断、20% 浮动、短报告不补全 |
| `test_job_store.py` | SQLite CRUD + 启动恢复（标 FAILED）+ 复合索引查询 |
| `test_report_store.py` | FileSystemReportStore save/get/delete + 按 tenant 分目录 |
| `test_routes.py` | FastAPI TestClient：POST 立即 202、GET 状态、service token 401 |
| `test_pipeline_adapter.py` | mock execute_task_pipeline，验证状态迁移 + 异常分支 |

**前端（Jest）**

| 测试文件 | 覆盖点 |
|---------|--------|
| `useResearchJobStream.test.ts` | mock EventSource，验证 GET 优先、终态自关闭、3 秒重连、组件卸载清理 |
| `ResearchItem.test.tsx` | 状态机渲染：IDLE/PENDING/RUNNING/COMPLETED/FAILED 各态 |
| `ResearchTrigger.test.tsx` | 配额耗尽禁用、已有 runningJobId 不显示按钮 |

#### 集成测试

**Java（`@SpringBootTest` + `MockMvc`）**：
```java
@SpringBootTest
class ResearchJobControllerIntegrationTest {
    @Test
    void createResearch_fullFlow() {
        // 1. 准备 ChatQueryDO（有 textSummary）
        // 2. mock PythonResearchClient（stub 立即返回 202）
        // 3. POST /api/chat/research/query/{queryId}
        // 4. 验证 s2_chat_research_job 表 PENDING 记录
        // 5. GET /api/chat/research/{jobId} 返回 PENDING
    }
}
```

**Python（`pytest` + `FastAPI TestClient`）**：
```python
def test_create_job_immediate_202(client, mock_llm):
    resp = client.post("/v1/research/jobs",
                       json={...},
                       headers={"Authorization": "Bearer test-token"})
    assert resp.status_code == 202
    assert resp.json()["status"] == "PENDING"
```

#### E2E 测试（可选，Demo 范围）

利用现有 `webapp/packages/supersonic-fe/` Puppeteer 环境，手工跑通即可，自动化留作演进项。

### 9.5 测试用例矩阵

| 场景 | Java 单测 | Python 单测 | 前端单测 | Java 集成 | Python 集成 |
|------|----------|------------|---------|----------|-------------|
| 正常启动 + 完成 | ✓ mock client | ✓ mock pipeline | ✓ COMPLETED 渲染 | ✓ stub Python | ✓ TestClient |
| 权限拒绝（403） | ✓ Checker | - | - | ✓ | - |
| 配额耗尽（429） | ✓ Checker | - | ✓ Trigger 禁用 | ✓ | - |
| 并发限制（409） | ✓ Checker | - | - | - | - |
| Python 异常 → FAILED | ✓ Scheduler | ✓ adapter except | ✓ return null | ✓ | - |
| Python 重启恢复 | - | ✓ recover_stale | - | - | ✓ startup event |
| SSE 断线重连 | ✓ Registry | - | ✓ hook 重连 | - | - |
| 报告超长 → 截断 | - | ✓ length_control | - | - | - |
| Service token 错 | - | ✓ routes 401 | - | - | ✓ |
| IntentClassifier 错 | - | ✓ fallback | - | - | - |

### 9.6 可观测性指标（Demo 简化）

**Demo 范围内可查的指标**（SQL 查 `s2_chat_research_job` 表）：

```sql
-- 今日成功/失败计数 by user
SELECT created_by, python_status, COUNT(*)
FROM s2_chat_research_job
WHERE created_at > CURDATE()
GROUP BY created_by, python_status;

-- 平均耗时（成功 job）
SELECT AVG(TIMESTAMPDIFF(SECOND, started_at, completed_at))
FROM s2_chat_research_job
WHERE python_status = 'COMPLETED';
```

**演进路径**（不在 Demo 范围）：
- 接 Prometheus + Grafana（计数器、直方图）
- 接 ELK（统一日志检索）
- 接 Jaeger/Zipkin（分布式追踪）

---

## 10. 三个演进锚点

整个设计的核心原则：**协议先就绪、实现可渐进**。三个关键演进锚点：

### 10.1 路由

- **协议就绪**：POST body 不传 research_type，Python 全权决策
- **当前实现**：IntentClassifier 1 次 LLM 调用，三类 type（industry/academic/default）都 fallback 到 `agent_llm_gpt5`
- **演进触发**：加新研究风格时
- **演进成本**：Python 加分类标签 + 新 Hydra config（不动协议、不动 Java、不动前端）

### 10.2 报告存储

- **协议就绪**：`report_uri` 字段通用（`fs://` / `mongo://` / `pg://`）
- **当前实现**：`FileSystemReportStore` 存 JSON 到 `outputs/{tenant}/research_jobs/{job_id}.json`
- **演进触发**：生产化部署时
- **演进成本**：换实现类（`MongoReportStore` / `PgJsonbReportStore`），序列化格式（JSON）不变，URI scheme 换掉

### 10.3 多租户

- **协议就绪**：`tenant_id` 进 schema 和 REST 协议，缺省 `"default"`
- **当前实现**：所有 job 属 `"default"`，不实现隔离逻辑（按 `job_id` 主键查天然隔离）
- **演进触发**：加列表查询接口或真实多租户部署时
- **演进成本**：Java 把 agentId 映射到 tenant_id；Python GET 加 `WHERE tenant_id = ?` 过滤；ReportStore 已按 tenant 分目录

**三者共同的设计原则**：Demo 阶段每项只做最小实现，但字段和抽象接口先留好，未来演进无损。

---

## 11. 文件清单与改动统计

### 11.1 Python 侧

| 类型 | 文件 | 说明 |
|------|------|------|
| 修改 | `server/app.py` | 挂载 REST router + startup 事件 + trace_id middleware |
| 新增 | `server/rest/__init__.py` | 包初始化 |
| 新增 | `server/rest/routes.py` | FastAPI router：POST/GET /v1/research/jobs |
| 新增 | `server/rest/models.py` | Pydantic 请求/响应模型 |
| 新增 | `server/rest/deps.py` | FastAPI dependency：verify_service_token |
| 新增 | `server/rest/job_store.py` | SQLite 持久化 + 启动恢复 |
| 新增 | `server/rest/intent.py` | IntentClassifier |
| 新增 | `server/rest/length_control.py` | 句子边界截断 |
| 新增 | `server/rest/report_store.py` | ReportStore Protocol + FileSystemReportStore |
| 新增 | `server/rest/logging_config.py` | trace_id filter + research logger |
| 新增 | `server/rest/pipeline_adapter.py` | run_pipeline_async 包装 execute_task_pipeline |
| 新增 | `server/rest/research_jobs.db` | SQLite 数据库（运行时生成） |

**总计：1 处修改，10 个新文件，1 个运行时数据库**。

### 11.2 Java 侧

| 类型 | 文件 | 说明 |
|------|------|------|
| 新增 | `chat/server/.../research/ResearchJobController.java` | REST Controller |
| 新增 | `chat/server/.../research/ResearchJobService.java` | 业务接口 |
| 新增 | `chat/server/.../research/ResearchJobServiceImpl.java` | 业务实现 |
| 新增 | `chat/server/.../research/ResearchPermissionChecker.java` | 权限校验 |
| 新增 | `chat/server/.../research/PythonResearchClient.java` | 调 Python REST |
| 新增 | `chat/server/.../research/ResearchSseRegistry.java` | SSE emitter 管理 |
| 新增 | `chat/server/.../research/ResearchSyncScheduler.java` | @Scheduled 同步 |
| 新增 | `chat/server/.../research/ResearchExceptionHandler.java` | 403/429/409 映射 |
| 新增 | `chat/server/.../research/dto/*.java` | 5 个 DTO |
| 新增 | `chat/server/.../research/persistence/*.java` + `.xml` | Mapper + DO |
| 新增 | `chat/server/src/main/resources/db/migration/V20260804__create_research_job.sql` | 表结构 |
| 修改 | `launchers/standalone/src/main/resources/application.yml` | 加 research.* 配置 |
| 修改 | `ChatQueryController.java` 或 `ChatQueryService` | 在 execute 响应附加 researchFeature |

**总计：12 个新文件，2 处修改，1 处 SQL**。

### 11.3 前端侧

| 类型 | 文件 | 说明 |
|------|------|------|
| 修改 | `webapp/packages/chat-sdk/src/components/ChatItem/ExecuteItem.tsx` | 挂载 ResearchItem |
| 修改 | `webapp/packages/chat-sdk/src/service/index.ts` | 加 3 个 research API |
| 新增 | `webapp/packages/chat-sdk/src/components/ChatItem/ResearchItem/index.tsx` | 容器组件 |
| 新增 | `webapp/packages/chat-sdk/src/components/ChatItem/ResearchItem/ResearchTrigger.tsx` | 启动按钮 |
| 新增 | `webapp/packages/chat-sdk/src/components/ChatItem/ResearchItem/ResearchProgress.tsx` | 进行中 loading |
| 新增 | `webapp/packages/chat-sdk/src/components/ChatItem/ResearchItem/ResearchReport.tsx` | 报告展示 |
| 新增 | `webapp/packages/chat-sdk/src/components/ChatItem/ResearchItem/styles.less` | 样式 |
| 新增 | `webapp/packages/chat-sdk/src/hooks/useResearchJobStream.ts` | SSE 订阅 hook |

**总计：6 个新文件，2 处修改**。

### 11.4 总计

- **Python**：10 个新文件 + 1 修改
- **Java**：12 个新文件 + 2 修改 + 1 SQL
- **前端**：6 个新文件 + 2 修改
- **合计**：28 个新文件，5 处修改，1 处 SQL

---

## 12. 面试讲解话术（整合）

### 12.1 整体架构

> "Java 是网关，Python 是研究中心。Java 负责权限、组装上下文、异步调度；Python 负责意图识别、执行 pipeline、产出报告。两个独立方向设计：Java→Python 用 @Scheduled 主动拉，流量与用户数解耦；Java→前端用 SSE 推送，避免无效轮询。"

### 12.2 三个演进锚点

> "协议先就绪、实现可渐进：
>
> 1. **路由**：Python IntentClassifier 全权分类，加新研究类型不动协议
> 2. **报告存储**：ReportStore Protocol 抽象，当前 FileSystemReportStore，未来换 MongoDB 或 PostgreSQL JSONB 不动协议
> 3. **多租户**：tenant_id 字段进 schema 和协议，当前 Demo 不实现隔离（按 jobId 主键查天然隔离），未来加列表接口时补 WHERE 过滤
>
> 三者共同的设计原则是 Demo 阶段每项只做最小实现，但字段和抽象接口先留好。"

### 12.3 权限边界

> "权限完全在 Java 网关——Python 不感知用户体系。Java 在 POST 之前做三层校验：功能开关（JWT 的 isAdmin 字段 + 白名单）、每日配额、并发数。校验通过才调 Python，并在 Authorization header 带 service token。
>
> **不复用 SuperSonic 的 user JWT**：payload 含密码哈希会泄漏给 Python，密钥耦合，语义错位（user token vs service token）。Python 侧 FastAPI dependency 验证独立 service token，不知道也不需要知道调用方是谁的用户体系。"

### 12.4 失败处理

> "失败的核心契约是'静默保留 textSummary'——10 种失败场景（Python 异常、Python 重启、网络抖动、配额耗尽、权限拒绝、token 错、SSE 断线等）全部走相同路径：前端 return null，不渲染任何东西；失败原因进日志（带 traceId）。
>
> Python 侧 SQLite job store + 启动恢复——进程重启时扫 RUNNING 标 FAILED，Java 下次轮询秒级感知，用户从等待 15 分钟降到秒级。Java 侧 15 分钟超时兜底防 Python 假死。"

### 12.5 可观测性

> "三层可观测性：
>
> 1. **结构化日志**：Java logback + Python logging，统一带 trace_id（HTTP header 透传），事后用单条 grep 命令串起完整调用链
> 2. **TaskTracer JSON**：Python 侧已有，每次 LLM 调用前后写完整 message_history 到文件，调试时直接打开看
> 3. **业务状态表**：Java `s2_chat_research_job` 是事实来源，任何状态机变化都落表
>
> 测试三层：单测（JUnit/pytest/Jest）+ 集成（SpringBootTest + FastAPI TestClient）+ E2E（Puppeteer，可选）。"

---

## 13. 后续步骤

1. **规格自检**（下一步）：占位符扫描、内部一致性、范围检查、模糊性检查
2. **用户审查书面规格**：等待用户对本文档的反馈
3. **过渡到实现**：调用 writing-plans 技能创建实现计划
