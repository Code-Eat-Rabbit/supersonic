# 深度研究集成面试文档 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 新建 `docs/resume/interview/深度研究/02-集成设计-面试文档.md`（约 500–700 行），把实施规格改写成可答辩的面试文档：先链路后淘汰，再讲一致性 / 容错 / 权限 / 可观测，最后写不足与演进。

**架构：** 单文件 Markdown。叙事按已上线集成讲，细节对齐 `02-集成设计.md`；不声称 Java 网关类已合进 SuperSonic 开源主仓。Compose 同网络是部署，不是前端直连。题纲逐题附录首版不写。

**技术栈：** Markdown；代码摘录对齐实施规格（标注来源）；不改 Java / Python 功能代码。

**规格：** [`docs/superpowers/specs/2026-09-03-research-integration-interview-doc-design.md`](../specs/2026-09-03-research-integration-interview-doc-design.md)

**本计划不含业务代码改动。** 每个任务的「测试」是核对命令（`test` / `grep` / `wc`），不是 pytest。

---

## 文件结构

| 文件 | 动作 | 职责 |
|------|------|------|
| `docs/resume/interview/深度研究/02-集成设计-面试文档.md` | 创建 | 唯一主交付 |
| `docs/resume/interview/深度研究/01-通用问答.md` | 修改分册索引一行 | 集成主题同时链面试版 |
| `docs/resume/interview/面试题纲.md` | 修改 § 三导语一行 | 实施规格 + 面试版并列 |
| `docs/resume/interview/深度研究/02-集成设计.md` | 只读 | 接口路径、状态机、14/15 分钟、代码摘录来源 |
| `docs/resume/interview/智能问数/02-SchemaMapper.md` | 只读 | 故事体例；第 2 节不要抄它的「先淘汰后答案」 |

一起变更的文件：主文档四节是同一叙事，必须按任务 1→4 顺序追加，不能并行写互相矛盾的口径。

---

## 口径锁（全任务共用，禁止改数字或发明组件）

| 项 | 必须写成 |
|----|----------|
| 问数耗时 | 约 15 秒（端到端）；描述性解读 &lt;2s |
| 研究耗时 | 数分钟级；产品侧临时建议 11 分钟（`01`，`n=3`，非正式 SLA） |
| 工程超时 | Python `asyncio.wait_for` **14 分钟**是执行权威；Java **15 分钟**只兜底崩溃/分区 |
| Scheduler | `fixedDelay` **2 秒** |
| 前端 API | `POST /api/chat/research/query/{queryId}`；`GET /api/chat/research/{jobId}`；`GET /api/chat/research/{jobId}/stream` |
| Python API | `POST /v1/research/jobs` → 202；`GET /v1/research/jobs/{job_id}` |
| Compose | 示例 `PYTHON_BASE_URL=http://research-agent:8000`；Python 不对外暴露 |
| 失败率 | **整篇不得出现**任何失败率百分比或「连点三次」用户行为数字 |
| 禁止组件 | Nginx 研究网关、Kafka、共享 DB、gRPC、前端直连 Python |

代码摘录必须标明「对齐实施规格 `02-集成设计.md`」，不要写成 SuperSonic 主仓已合并路径，除非摘的是现有 `textSummary` 区域这种问数 UI。

---

### 任务 1：创建文件 — 文首 + §1 背景

**文件：**
- 创建：`docs/resume/interview/深度研究/02-集成设计-面试文档.md`

- [ ] **步骤 1：确认目标文件尚不存在**

运行：

```bash
cd /Users/yourton_ma/workspace/supersonic
test ! -e docs/resume/interview/深度研究/02-集成设计-面试文档.md && echo ABSENT || echo EXISTS
```

预期：`ABSENT`。若 `EXISTS`，停下来先读现有文件，不要覆盖未纳入本计划的内容。

- [ ] **步骤 2：写入文首与 §1（一次性写完整段，不要留空标题）**

将下列内容写入 `docs/resume/interview/深度研究/02-集成设计-面试文档.md`：

```markdown
# 问数结果深度研究 — 集成设计（面试版）

> 本文是面试准备文档，不是实施说明书。
> 实施规格（类、表、完整代码、失败矩阵）：[`02-集成设计.md`](./02-集成设计.md)
> 指标 / GAIA / 耗时口径：[`01-通用问答.md`](./01-通用问答.md)
> 编排 / Hybrid / 工程化：[`03-Main-Sub-Agent编排.md`](./03-Main-Sub-Agent编排.md) · [`04-Hybrid-Search-MCP.md`](./04-Hybrid-Search-MCP.md) · [`05-工程化能力.md`](./05-工程化能力.md)
> 题纲：[`../面试题纲.md`](../面试题纲.md) § 三 B4–B6、C7–C9、D10–D12（本文不逐题作答）
> **诚实口径：** 按实施规格接到问数产品并上线来讲。不把这些 Java 网关类说成已经合进 SuperSonic 开源主仓；代码摘录对齐规格，不是开源主仓路径。

---

## 1. 背景：深度研究不能挡问数

开场第一句：

> 问数主链路还是 Java，大约 15 秒出描述性解读。深度研究是可选的 Python 微服务，典型要数分钟。用户只传当前 `queryId`，Java 网关鉴权、拼 context、创建异步 Job，立刻返回；前端用 SSE 订 Java 等终态。失败或超时静默留下 `textSummary`，不挡查数。两个服务打成镜像，Compose 同一网络，Python 不对外暴露。

要解的不是「怎么把 FastAPI 跑起来」，而是一条产品契约：**研究可以失败，问数结果必须还在；研究可以很慢，Chat 线程不能跟着慢。**

| 矛盾 | 面试怎么说 |
|------|------------|
| 时延差两个数量级 | 问数秒级（约 15 秒端到端，描述性解读 &lt;2s），研究数分钟。不能在 execute 线程里同步等。产品侧超时临时建议 11 分钟，来自 `01` 的 `n=3` 下界，不是正式 SLA。 |
| 职责不同 | Java 有登录用户、权限、`ChatQueryDO`（原问题 / `textResult` / `textSummary`）。Python 有 Agent、MCP、检索生态。 |
| 失败不能污染主结果 | 深度研究挂了，用户至少还能看表格和描述性解读。 |
| 部署 ≠ 网关 | Compose 同网络只解决服务发现和内网隔离。拼 context、鉴权、配额仍然必须走 Java。 |

IntentClassifier 的 prompt、报告换仓、13 种失败逐条，都不在本节展开。先把契约钉死，机制放到 §2 / §3。
```

- [ ] **步骤 3：核对 §1 必含句**

运行：

```bash
f=docs/resume/interview/深度研究/02-集成设计-面试文档.md
grep -q 'queryId' "$f" && grep -q 'textSummary' "$f" && grep -q 'Compose' "$f" && grep -q '不对外暴露' "$f" && grep -q '不能挡问数' "$f" && echo OK || echo FAIL
```

预期：`OK`

- [ ] **步骤 4：Commit**

```bash
git add docs/resume/interview/深度研究/02-集成设计-面试文档.md
git commit -m "$(cat <<'EOF'
docs(interview/深度研究): 新增集成面试文档文首与背景

EOF
)"
```

---

### 任务 2：追加 §2 端到端集成（先链路，后淘汰）

**文件：**
- 修改：`docs/resume/interview/深度研究/02-集成设计-面试文档.md`（追加，不改 §1 契约句）

- [ ] **步骤 1：在文件末尾追加 §2，必须先 2.1 拓扑 → 2.2 四段链路（含代码）→ 2.3 淘汰表**

追加内容如下。代码块保持短；注释写明对齐实施规格。

````markdown
## 2. 端到端：Java 网关怎么接到 Python

### 2.1 先建立心智模型

Java 是问数产品的网关，Python 是研究运行时。浏览器只跟 Java 说话。两个进程各自一个 Dockerfile，放进同一个 Compose 网络；Java 用服务名访问 Python，例如 `PYTHON_BASE_URL=http://research-agent:8000`。对外只暴露 Java（和前端）。**同网络不是前端直连**：浏览器进不了容器 DNS，也不该拿到研究服务的地址。

```
用户点「深度研究」
  → 前端只 POST queryId 给 Java
  → Java 鉴权 / 拼 task+context / 落 PENDING / 立刻回 jobId
  → Java 内网异步 POST Python（Bearer service token + X-Trace-Id）
  → Python 验 token、分类、落 SQLite、202，后台跑 pipeline
  → 前端 SSE 订 Java；Java 每 2s 拉 Python，状态变了再推前端
  → COMPLETED 展示报告；FAILED 组件 return null，留下 textSummary
```

两条回传通道必须拆开讲：

| 方向 | 机制 | 为什么这样拆 |
|------|------|--------------|
| Python 状态 → Java 表 | Java `@Scheduled` 每 2 秒拉一次 | 频率固定，和打开页面的人数无关 |
| Java 表 → 前端 | SSE 推状态；首屏 / 重连先 GET | 用户不用 500ms 轮询研究接口 |

### 2.2 四段链路

#### （1）前端：只传 `queryId`，失败不渲染

挂在现有 `textSummary` 下方。没有描述性解读就不给按钮——深度研究是解读之后的可选项，不是第二条问数。

```tsx
{/* 对齐实施规格 02-集成设计.md §5.2；不是 SuperSonic 开源主仓已合并代码 */}
{data.textSummary && data.researchFeature?.enabled && (
    <ResearchItem
        queryId={data.queryId}
        researchFeature={data.researchFeature}
    />
)}
```

点击只打 `POST /api/chat/research/query/{queryId}`。`FAILED` 时组件直接不画，表格和 `textSummary` 还在。

```tsx
{/* 对齐实施规格 §5.5 */}
const handleStart = async () => {
    const res = await createResearchJob(queryId);
    setJobId(res.jobId);
};

if (status === 'FAILED') {
    return null;
}
```

SSE 细节口述即可：先 GET 当前状态，已终态就不再订；否则订 `/api/chat/research/{jobId}/stream`，收到终态关闭，`onerror` 3 秒重连。页面刷新靠 `researchFeature.runningJobId` 续订。`textSummary` 那条 500ms 轮询保持不动，两条状态通道互不干扰。

#### （2）Java 创建：鉴权、拼 context、立刻返回

`createResearch` 做完这些事才返回，**不等 pipeline**：

1. 校验 `queryId` 属于当前用户（admin 放行）
2. 确认已有 `textSummary`
3. 功能开关 + 日配额 + 并发
4. 从 `ChatQueryDO` 截断拼 `task`（原问题）+ `context`（结果和解读，Demo ≤ 4000 字）
5. Java 生成 `jobId`（UUID），带上 MDC 里的 `traceId`
6. 写本地任务表 `PENDING`
7. `@Async` POST Python，响应已经是 `{jobId, PENDING}`

```java
// 对齐实施规格 §6.3.2，主干；省略 DTO / Mapper
public CreateJobResponse createResearch(User user, Long queryId) {
    ChatQueryDO query = chatQueryService.getChatQuery(queryId);
    if (query == null || StringUtils.isEmpty(query.getTextSummary())) {
        throw new ResearchBadRequestException("查询结果不存在或无描述性解读");
    }
    permissionChecker.check(user);

    String task = query.getQuestion();
    String context = buildContext(query);
    String jobId = UUID.randomUUID().toString();
    String traceId = TraceIdUtil.getTraceId();

    jobMapper.insert(pendingJob(jobId, queryId, user, task, traceId));
    pythonClient.createJobAsync(jobId, traceId, task, context);
    return new CreateJobResponse(jobId, "PENDING");
}
```

Python 当时挂了：创建接口仍然 200，只打 warn，交给 Scheduler 超时收尸，**不把 Chat execute 变成 504**。

#### （3）Python 接单：验 token，立刻 202

`POST /v1/research/jobs`。FastAPI dependency 验独立 service token，失败 401。同步路径只做：IntentClassifier 一次 LLM → SQLite `PENDING` → `BackgroundTasks` 丢给 `run_pipeline_async` → **202**。`job_id` 用 Java 传来的，不自己发号。

```python
# 对齐实施规格 §7.10
@router.post("/v1/research/jobs", status_code=202,
             dependencies=[Depends(verify_service_token)])
async def create_job(req: CreateJobRequest, bg: BackgroundTasks):
    research_type, data_domain = await intent_classifier.classify(req.task, req.context)
    job_store.create(job_id=req.job_id, ..., status="PENDING")
    bg.add_task(run_pipeline_async, ...)
    return {"job_id": req.job_id, "status": "PENDING"}
```

分类失败 fallback `default`，任务继续跑，不把「没分对类型」升级成用户失败。真正执行在后台：`asyncio.wait_for(execute_task_pipeline, 14min)`，写报告文件，SQLite 标 `COMPLETED` / `FAILED`。Main–Sub 怎么拆任务见 [`03`](./03-Main-Sub-Agent编排.md)，这里只看到 HTTP。

#### （4）回传：2 秒拉 + SSE 推

Java 扫本地 `PENDING` / `RUNNING`，对每条 `GET /v1/research/jobs/{jobId}`（默认不带全文；变 `COMPLETED` 再拉一次 `include_full`）。状态变化写入 Java 表并推 SSE。

```java
// 对齐实施规格 §6.3.5，只留分支
@Scheduled(fixedDelayString = "${research.sync-interval-ms:2000}")
public void syncRunningJobs() {
    for (ResearchJobDO job : active) {
        if (isTimeout(job, timeoutMinutes)) {          // 15min 兜底
            flipToFailed(job, "java-side timeout");
            continue;
        }
        try {
            PythonJobStatus p = pythonClient.getStatus(job.getJobId(), false);
            mergeStatus(job, p);                       // 终态拒绝翻转
        } catch (HttpClientErrorException.NotFound e) {
            flipToFailed(job, "python job not found"); // 真孤儿
        } catch (Exception e) {
            log.debug("skip this round");              // 抖动，下次再试
        }
    }
}
```

### 2.3 为什么不选别的

读完链路再看对照才有意义。

| 淘汰 | 对上链路里哪一步 | 为什么不行 |
|------|------------------|------------|
| execute 线程同步 POST 并阻塞 | Java 立刻回 `jobId` | 研究数分钟，占死 Chat 线程和 Tomcat 池；超时只能 504，主结果一起糊 |
| 前端直连 Python | 只 POST `queryId` | 浏览器进不了 Compose 内网；Python 没有用户体系，拼不了 `ChatQueryDO`，也做不了配额 / 越权 |
| 前端 500ms 轮询当唯一通道 | SSE + 定时拉拆两截 | 用户数和 Java→Python 流量绑死，研究服务被打成查询服务 |
| Python 回调 Java / 上 MQ | Java 每 2s 拉 | 还要给 Python 配 Java 入站鉴权、死信、乱序；当前任务量不值（回调是 §4 的演进，不是现在的方案） |
| 转传 SuperSonic 用户 JWT | 独立 service token | payload 含密码哈希；密钥耦合；user token 和 service token 语义不是一回事 |

金句：**同步会挡主链路，直连会穿权限，用户轮询会把内网打满。所以 Java 做网关、Job 异步、状态用「定时拉 + SSE 推」拆成两截；Compose 只是把这两截放进同一内网。**

三条配套约束，不另开章：

1. `jobId` 由 Java 生成，Python 不自创 id
2. Java 只传 `task + context`，研究类型由 Python IntentClassifier 判——加新类型不动协议
3. Python 只验 service token，不知道 SuperSonic 用户是谁
````

注意：上面外层是计划用的四反引号围栏；写入目标文件时，内部代码块用普通三反引号，章节标题是 `## 2.` 不是四级标题。

- [ ] **步骤 2：核对 §2 结构与禁句**

运行：

```bash
f=docs/resume/interview/深度研究/02-集成设计-面试文档.md
grep -n '^## 2\.' "$f"
grep -q 'research-agent:8000' "$f" && grep -q '同网络不是前端直连\|同网络 ≠ 前端直连\|同网络不是前端直连' "$f" || grep -q '不是前端直连' "$f"
grep -q 'createResearch' "$f" && grep -q 'status_code=202' "$f" && grep -q 'syncRunningJobs' "$f"
grep -q 'execute 线程同步\|同步 POST' "$f"
grep -q 'Kafka\|gRPC' "$f" && echo FORBIDDEN || echo NO_FORBIDDEN_MQ
```

预期：存在 `## 2.`；含 Compose 示例与「不是前端直连」；含三段代码关键词；含淘汰表；`NO_FORBIDDEN_MQ`（正文可以在淘汰表里写「上 MQ」，但不得写成已采用 gRPC/Kafka）。

更严的禁句：

```bash
grep -E '已合进 SuperSonic 开源|前端直连 Python 已上线' "$f" && echo FAIL || echo OK_HONEST
```

预期：`OK_HONEST`

- [ ] **步骤 3：Commit**

```bash
git add docs/resume/interview/深度研究/02-集成设计-面试文档.md
git commit -m "$(cat <<'EOF'
docs(interview/深度研究): 写集成面试文档端到端链路与方案淘汰

EOF
)"
```

---

### 任务 3：追加 §3 四个后端问题

**文件：**
- 修改：`docs/resume/interview/深度研究/02-集成设计-面试文档.md`

- [ ] **步骤 1：追加 §3，四个小节标题必须是 3.1 一致性、3.2 容错、3.3 权限、3.4 可观测**

追加：

```markdown
## 3. 后端怎么保证：一致、容错、权限、可观测

两个独立进程、两套存储、没有分布式事务。面试要答的不是「用了 SSE」，而是**权威在哪、失败时谁让步**。

### 3.1 状态怎么一致

结论：不搞 2PC，也不共享问数业务库。执行态以 Python 为准，用户可见态以 Java 表为准。Java 用 2 秒拉取做最终一致；用「终态不可变」避免双写打架。

| 事实来源 | 存什么 | 谁写 |
|----------|--------|------|
| Python SQLite | 任务跑到哪、报告 URI | 只有 Python |
| Java 任务表 | 给前端看的状态、报告摘要、审计 | Java 合并 Python 回包 |

为什么不共享库：问数库是业务库，研究进程不该碰用户表；Python 挂了不能把 Chat 库一起拖死。

为什么是拉不是推：研究任务少，固定频率拉就能跟上；推还要让 Python 持有 Java 的鉴权，Demo 不值（主动回调放到 §4）。

真正会炸的坑是**双写终态**：Java 等了 15 分钟标 `FAILED` 并推 SSE，Python 稍后跑完又标 `COMPLETED`，刷新页面报告又冒出来。修法两条一起上：

- Python `asyncio.wait_for` **14 分钟**是超时权威，到期必进 `FAILED`，避免研究进程无限制烧 token
- Java **15 分钟**只兜底进程崩溃 / 网络分区
- `COMPLETED` / `FAILED` 一旦写入，Python `job_store.update` 和 Java `mergeStatus` 都拒绝再改

重启一致性：Python 起来扫残留 `PENDING` / `RUNNING`，标 `FAILED`（`runner restarted`）。Java 下一次 2 秒拉取就能感知，用户从空等 15 分钟变成秒级静默回退。当前**不**做重启后续跑——评测续跑和业务会话续跑不是一回事，见 [`05`](./05-工程化能力.md)。

超时时钟看 `started_at`（进入 `RUNNING` 的时间）；还没跑起来才退回 `created_at`，避免把排队时间算进研究超时。

金句：`jobId` 由 Java 发号，两边从第一毫秒就指同一条任务；之后只允许 `PENDING → RUNNING → 终态`，终态是单向门。

### 3.2 容错和降级

结论：分层。产品层失败要静默、不挡问数；同步层要区分假失败和真失败；Agent 内部失败尽量降级，不要每次工具抖动都拆掉按钮。

| 层 | 失败长什么样 | 策略 |
|----|--------------|------|
| 产品（用户看见的） | 没报告，或工程超时 | 组件 `return null`，留下 `textSummary` |
| 同步（Java↔Python） | HTTP 超时、404、进程重启 | 抖动跳过本轮；404 与硬超时才 `FAILED` |
| Agent 内部 | 某次 MCP 挂了 | 工具降级链，见 [`04`](./04-Hybrid-Search-MCP.md)；不等于产品失败 |

假失败 vs 真失败：某次 GET Python 超时，多半是抖动，立刻 `FAILED` 会把还在跑的任务杀死（token 已经花了）。Python 明确 404（库被清、孤儿记录）才是真失败。

有一类失败其实是降级成功：IntentClassifier 挂了 → fallback `default`，任务继续。不要把它讲成「分类一错用户就看不到研究」。

超时是预算不是 SLA：14 / 15 分钟防假死。产品侧 11 分钟临时建议只来自 `01` 的 `n=3` 样本，不能对外说成 P95。

SSE 断了不是任务断了：3 秒重连；先 GET 再订，避免漏终态。任务在 Java / Python 两边继续跑。

金句：MCP 失败可以换工具，产品失败只有一种——用户拿不到深度报告。前者见 `04`，后者必须静默回退。

### 3.3 权限怎么做

结论：鉴权在网关一次做完。Python 是零信任内网服务：只认 service token，不认用户。Docker 同网络是网络层隔离，**不能替代**应用层鉴权。

三道闸按调用顺序：

1. **功能开关**：`isAdmin` + 白名单。过不了根本不建 Job。
2. **配额与并发**：今日次数、是否已有 `RUNNING`。规则运行时算，**不落权限表**；表里的 `created_by` 只做审计和聚合。
3. **资源归属（防 IDOR）**：`queryId` / `jobId` 是不是这个人的。不存在和不是本人统一 **404**，不给 403 去泄露「这个 UUID 存在」。SSE 注册前也要过，防止用随机 id 把 emitter 打满。

和 Python 的边界：浏览器拿不到 Python 地址；Java→Python 带独立 service token，**不转传** SuperSonic JWT（payload 有密码哈希，密钥还会耦合）。即便有人进了内网，没有 token 仍是 401——网络隔离是纵深，token 才是服务身份。

不选的方案：把 `userId` 传进 Python 做行级权限。那等于把用户体系复制一份，权限规则一改要改两个服务；研究进程也不该看见谁是谁。

金句：Java 管「谁能发起、谁能看」；Python 管「怎么研究」。权限信息不进研究库。

### 3.4 可观测性怎么做

结论：跨两个进程排障，靠同一条 `traceId` 把「用户可见态 / 服务日志 / Agent 内部轨迹」串起来，而不是上一套完整分布式追踪。

| 层 | 记什么 | 什么时候用 |
|----|--------|------------|
| Java 任务表 | `jobId`、状态、`error_msg`、`created_by` | 先看用户看到了什么，卡在 `PENDING` 还是 `FAILED` |
| 结构化日志 | Java logback MDC + Python logging；`X-Trace-Id` 注入 contextvar | 用 `traceId` 把网关耗时、401/404、Scheduler 跳过抖动串成一条链 |
| TaskTracer JSON | 每轮 tool / Sub 的 message history | 确认是集成挂了还是 Agent 跑飞了；细节见 [`05`](./05-工程化能力.md) |

创建 Job 时 Java 把现成 MDC `traceId` 放进 header 和表字段。Scheduler 状态变化打 info（`jobId` + 新旧状态）；抖动走 debug，避免把重试刷成事故。

产品对用户静默，对日志不静默：`FAILED` 一定有 `error_msg` + `traceId`，否则无法复盘。Kibana Dashboard、Prometheus 指标名、Jaeger 不是当前集成的最小可观测，放到「如果重新做」口头补充即可。

金句：先查表看终态，再 grep `traceId` 看跨服务，最后才打开 TaskTracer 看 Agent。
```

- [ ] **步骤 2：核对四块都在，且没有失败率数字、没有「正式 SLA」断言**

运行：

```bash
f=docs/resume/interview/深度研究/02-集成设计-面试文档.md
grep -q '### 3.1' "$f" && grep -q '### 3.2' "$f" && grep -q '### 3.3' "$f" && grep -q '### 3.4' "$f" && echo HEADS_OK
grep -q '终态不可变\|终态是单向门' "$f" && grep -q 'IntentClassifier' "$f" && grep -q '统一 \*\*404\*\*\|统一 404' "$f" && grep -q 'X-Trace-Id' "$f" && echo CONTENT_OK
grep -E '失败率 [0-9]|回退率 [0-9]|正式 SLA|正式 P95' "$f" && echo BAD_METRIC || echo METRIC_OK
```

预期：`HEADS_OK`、`CONTENT_OK`、`METRIC_OK`。允许出现「非正式 SLA」「不是正式 P95」。

- [ ] **步骤 3：Commit**

```bash
git add docs/resume/interview/深度研究/02-集成设计-面试文档.md
git commit -m "$(cat <<'EOF'
docs(interview/深度研究): 写集成面试文档一致性容错权限与可观测

EOF
)"
```

---

### 任务 4：追加 §4 不足与演进

**文件：**
- 修改：`docs/resume/interview/深度研究/02-集成设计-面试文档.md`

- [ ] **步骤 1：追加 §4。本节不得出现可讲/不可讲对照表，不得出现题纲 B4 逐题答法。**

```markdown
## 4. 当前不足与未来演进

短板都承认：是单机 Demo 的存储和同步，不是网关边界画错了。演进优先换实现，不改 Java↔Python 契约。

**现在短在哪**

1. **最终一致有最多约 2 秒的可见延迟。** Python 假死时要等到 Java 15 分钟兜底，当前没有回调。
2. **Python 侧 SQLite + 本地文件报告。** 进程重启是标失败，不是接着跑；单副本，没有 HA。
3. **路由协议就绪、实现未分化。** 三类 `research_type` 仍落到同一套 agent config。
4. **权限是内测模型。** admin + 白名单 + 配额，没有权限表，没有订阅计费。
5. **产品漏斗没有埋点。** 失败率、再次触发率说不出来——无埋点不编数字，和 [`01`](./01-通用问答.md) 一致。
6. **没有取消、没有业务会话续跑。** 规格里的 YAGNI；评测 attempt 续跑不要拿来冒充业务续跑。

**下一步按这个顺序**

| 优先级 | 做什么 | 为什么现在能演进 |
|--------|--------|------------------|
| 1 | 同步改为 Python 回调 + Java 定时拉兜底 | 协议不用改，只加一条 Java 入站；解决 2 秒延迟和假死空等 |
| 2 | ReportStore / JobStore 换可持久化存储 | `report_uri`、`tenant_id` 已在协议里 |
| 3 | 按类型真正分 config；新领域只加 markdown | Java 本来就不传 `research_type` |
| 4 | 权限表 / 配额产品化 | 只换 checker，Python 协议不动 |
| 5 | 失败与耗时打点后再谈 SLA | 先有埋点，才有失败率 |

近期不做：断点续传、任务级 WebClient 重构、上完整 APM。被问「如果重新做」可以提，不当成已经排期。
```

- [ ] **步骤 2：核对 §4 六条不足和演进表五级都在；确认全文仍无 `## 5.`**

运行：

```bash
f=docs/resume/interview/深度研究/02-集成设计-面试文档.md
grep -q '^## 4\.' "$f" && grep -q 'SQLite' "$f" && grep -q 'YAGNI\|没有取消' "$f"
grep -q 'Python 回调' "$f"
grep '^## 5\.' "$f" && echo HAS_SEC5 || echo NO_SEC5
```

预期：`NO_SEC5`

- [ ] **步骤 3：Commit**

```bash
git add docs/resume/interview/深度研究/02-集成设计-面试文档.md
git commit -m "$(cat <<'EOF'
docs(interview/深度研究): 写集成面试文档不足与演进

EOF
)"
```

---

### 任务 5：交叉链接（01 分册索引 + 题纲导语）

**文件：**
- 修改：`docs/resume/interview/深度研究/01-通用问答.md` 约第 237 行
- 修改：`docs/resume/interview/面试题纲.md` 约第 200 行

规格写明 01 索引更新不阻塞主交付；本任务仍然做，因为只改两行，避免读者只链到 2900 行实施规格。

- [ ] **步骤 1：改 `01` 分册索引「集成」那一行**

将：

```markdown
| Java↔Python、触发、静默回退、Job | [`02-集成设计.md`](./02-集成设计.md) | B4–B6、C7–C9、D10–D12 |
```

改成：

```markdown
| Java↔Python、触发、静默回退、Job | 面试版 [`02-集成设计-面试文档.md`](./02-集成设计-面试文档.md)；实施规格 [`02-集成设计.md`](./02-集成设计.md) | B4–B6、C7–C9、D10–D12 |
```

同步把文首「专题详解」里集成那条改成先链面试版、规格作括号补充：

```markdown
> - 集成契约 / 触发与回退 → [`02-集成设计-面试文档.md`](./02-集成设计-面试文档.md)（实施规格：[`02-集成设计.md`](./02-集成设计.md)）
```

- [ ] **步骤 2：改题纲 § 三导语**

将：

```markdown
> 集成设计：[`深度研究/02-集成设计.md`](./深度研究/02-集成设计.md)
```

改成：

```markdown
> 集成设计（面试）：[`深度研究/02-集成设计-面试文档.md`](./深度研究/02-集成设计-面试文档.md)  
> 实施规格：[`深度研究/02-集成设计.md`](./深度研究/02-集成设计.md)
```

宽问「第一句答题」不要改——那是 `01` 的指标口径，不是本文的开场句。

- [ ] **步骤 3：核对链接文件都存在**

运行：

```bash
test -f docs/resume/interview/深度研究/02-集成设计-面试文档.md && \
test -f docs/resume/interview/深度研究/02-集成设计.md && \
grep -q '02-集成设计-面试文档.md' docs/resume/interview/深度研究/01-通用问答.md && \
grep -q '02-集成设计-面试文档.md' docs/resume/interview/面试题纲.md && echo LINKS_OK
```

预期：`LINKS_OK`

- [ ] **步骤 4：Commit**

```bash
git add docs/resume/interview/深度研究/01-通用问答.md docs/resume/interview/面试题纲.md
git commit -m "$(cat <<'EOF'
docs(interview/深度研究): 分册索引与题纲改链到集成面试文档

EOF
)"
```

---

### 任务 6：规格验收 + 篇幅

**文件：**
- 只读核对：`docs/resume/interview/深度研究/02-集成设计-面试文档.md`
- 只读：`docs/superpowers/specs/2026-09-03-research-integration-interview-doc-design.md` §8

- [ ] **步骤 1：篇幅**

运行：

```bash
wc -l docs/resume/interview/深度研究/02-集成设计-面试文档.md
```

预期：行数在 **500–700**。若 &lt;500：§2 四段链路或 §3 四问写得过瘦，补故事（双写终态、404 vs 抖动）而不是贴类清单。若 &gt;700：删完整 hook、DDL、13 种失败表、IntentClassifier prompt。允许 480–720 的小幅越界，但 800+ 必须砍。

- [ ] **步骤 2：验收清单（规格 §8）**

运行：

```bash
f=docs/resume/interview/深度研究/02-集成设计-面试文档.md
echo "---- sections ----"
grep -n '^## ' "$f"
echo "---- forbidden dumps ----"
grep -E 'CREATE TABLE s2_chat_research_job|ResearchJobController.java|13 种失败|失败点.Python 状态' "$f" && echo HAS_DUMP || echo NO_DUMP
echo "---- required ----"
grep -q '01-通用问答.md' "$f" && grep -q '03-Main-Sub-Agent编排.md' "$f" && grep -q '04-Hybrid-Search-MCP.md' "$f" && grep -q '05-工程化能力.md' "$f" && grep -q '02-集成设计.md' "$f" && echo REFS_OK
grep -q '14 分钟' "$f" && grep -q '15 分钟' "$f" && grep -q '11 分钟' "$f" && echo TIMEOUTS_OK
```

预期：

- 仅有 `## 1.` … `## 4.`，没有 `## 5.`
- `NO_DUMP`
- `REFS_OK`
- `TIMEOUTS_OK`（11 / 14 / 15 都出现，且 11 分钟附近有「临时建议」或 `n=3` 或「非正式」字样）

```bash
grep -n '11 分钟' docs/resume/interview/深度研究/02-集成设计-面试文档.md
```

该行必须同时能解释它不是工程硬超时。

- [ ] **步骤 3：若步骤 1 或 2 失败，就地改主文档并再跑一遍，然后单独 commit**

```bash
git add docs/resume/interview/深度研究/02-集成设计-面试文档.md
git commit -m "$(cat <<'EOF'
docs(interview/深度研究): 按验收收束集成面试文档篇幅与口径

EOF
)"
```

若已通过且无改动，不要空 commit。

---

## 自检（写计划的人执行，不是实现任务）

**规格覆盖：**

| 规格章节 | 对应任务 |
|----------|----------|
| §5.1 文首 | 任务 1 |
| §5.2 §1 背景 | 任务 1 |
| §5.3 §2 链路 + 淘汰 | 任务 2 |
| §5.4 §3 四问 | 任务 3 |
| §5.5 §4 不足演进 | 任务 4 |
| §6 交叉引用 / 超时分工 | 任务 2–4 正文 + 任务 6 核对 |
| §8 验收 | 任务 6 |
| §8 可选 01 索引 | 任务 5（已纳入，不只是可选口头） |
| 非目标：无题纲逐题附录 | 任务 4 步骤 2 查无 `## 5.`；任务 5 不改宽问第一句 |

**占位符：** 计划内步骤都是可粘贴正文或可运行命令，无「补充细节」「适当展开」。

**名称一致：** 全文使用 `jobId`（Java / 前端）与 Python JSON `job_id` 并存时，按所在代码块语言区分；状态枚举 `PENDING` / `RUNNING` / `COMPLETED` / `FAILED`；服务名示例 `research-agent:8000`。
