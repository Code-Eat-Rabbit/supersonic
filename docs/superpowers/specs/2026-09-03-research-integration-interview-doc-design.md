# 问数结果深度研究 · 集成设计面试文档 — 设计规格

> 日期：2026-09-03
> 状态：待用户审查
> 目标文件：`docs/resume/interview/深度研究/02-集成设计-面试文档.md`
> 实施规格（不取代）：`docs/resume/interview/深度研究/02-集成设计.md`
> 指标 / 开场口径：`docs/resume/interview/深度研究/01-通用问答.md`
> 题纲锚点：`docs/resume/interview/面试题纲.md` § 三 B4–B6、C7–C9、D10–D12（本文不写逐题附录）
> 体例参照：`docs/resume/interview/智能问数/02-SchemaMapper.md` 的故事性；第 2 节改为「先链路后淘汰」
> 复习标本：`miro-flow-solution` + SuperSonic 问数主链路（对齐工程细节；不宣称发明框架）

---

## 1. 背景与目标

### 1.1 问题

现有 `02-集成设计.md` 是实施规格：约 2900 行，含类清单、DDL、完整 hook 与 13 种失败矩阵。适合对照实现，不适合面试：

- 读不完，复杂代码把决策淹没。
- 缺少故事：困难、踩坑、方案权衡经不起拷打。
- 题纲要的是 Java↔Python 怎么接、为何不挡主链路、失败怎么回退，不是文件清单。

### 1.2 目标

1. 新建面试文档 `02-集成设计-面试文档.md`，按**已上线的集成**来讲（规格即上线口径；不声称这些 Java 类已合进 SuperSonic 开源主仓）。
2. 主线是产品契约：**深度研究不能挡问数**。技术决策都服务于这条契约。
3. 目标篇幅 **500–700 行**。代码只贴关键分支（创建 Job、202 返回、Scheduler 合并、FAILED 不渲染），不搬 13 个类和完整 hook。
4. 原 `02-集成设计.md` 保留为实施规格；`01` / `03` / `04` / `05` 的链接从面试文档指回规格或分册，不把编排 / Hybrid / 熔断写进本文。

### 1.3 非目标

- 不写题纲逐题附录（B/C/D 第一句表）。需要时以后再加，不进首版。
- 不改 SuperSonic / miro-flow-solution 功能代码。
- 不编造失败率、SLA、P95、用户「连点三次」行为数据。
- 不把 Compose 同网络写成前端直连 Python，也不用 Docker 替代 Java 网关。
- 不在本文展开 IntentClassifier prompt、domains 扫描全文、ReportStore 换仓实现、ELK Dashboard 配法、Jaeger。

---

## 2. 已确认决策

| 决策点 | 选择 |
|--------|------|
| 叙事主语 | 设计答辩体：把比赛原型接到问数产品时的集成设计；按已上线讲，细节对齐 `02-集成设计.md` |
| 调用链 | 浏览器只打 Java；Java 用 Compose 内网服务名访问 Python；Python 不对外暴露 |
| 部署 | 两个项目各自 Dockerfile，一个 Compose、同一 Docker 网络。这是部署拓扑，不是架构替代 |
| 文档骨架 | SchemaMapper 的故事性（背景 → 选型 → 后端问题 → 不足）；第 2 节改为先写清端到端，再写为什么不选别的 |
| 内容主线 | 产品契约：「深度研究不能挡问数」 |
| 后端三问 + 可观测 | 状态一致性、容错/降级、权限、可观测性，作为第 3 节四个并列方向 |
| 第 4 节 | 只写当前不足 + 未来演进 |
| 第 5 节题纲对照 | **首版不做** |
| 文件名 | `02-集成设计-面试文档.md`，与实施规格并存 |

---

## 3. 方案对比（记录）

### 3.1 叙事主语

| 方案 | 描述 | 结论 |
|------|------|------|
| A. 设计答辩体 | 按规格上线来讲，不把未合入开源主仓的类说成 SuperSonic 贡献 | **采用** |
| B. 实习落地体 | 只写 Data Agent 真实差异，SuperSonic 方案当对照 | 不采用：用户要求对齐 `02-集成设计.md` |
| C. 混合体 | 实习一套、SuperSonic 一套 | 不采用：两套口径容易混 |

### 3.2 调用链 vs 部署

| 方案 | 描述 | 结论 |
|------|------|------|
| A. Compose 只改部署 | 前端 → Java 网关 → 内网 Python | **采用** |
| B. 反向代理分流 research 到 Python | Java 不再做研究网关 | 不采用：`queryId` 拼装和鉴权无处放 |
| C. 前端直连 Python | 浏览器打 FastAPI | 不采用：进不了内网，且 Python 无用户体系 |

### 3.3 文档组织

| 方案 | 描述 | 结论 |
|------|------|------|
| 1. 产品契约主线 | 从「不能挡问数」收束异步、双通道、静默回退、Compose | **采用** |
| 2. 排障时间线主线 | 按事故顺序讲 | 踩坑收进第 3 节，不当整篇骨架 |
| 3. 边界主线 | Java vs Python 职责切章 | 不采用：产品追问会散 |

第 2 节内部顺序（用户修订）：**先详细写集成链路（可贴必要代码），再给淘汰理由**。不是 SchemaMapper 那种「先淘汰表、后亮答案」。

---

## 4. 交付物结构

文件：`docs/resume/interview/深度研究/02-集成设计-面试文档.md`

```
文首元信息
§1 文档定位 + 背景痛点
§2 端到端集成（链路 + 必要代码 + 方案淘汰）
§3 四个后端问题（一致性 / 容错 / 权限 / 可观测）
§4 当前不足与未来演进
```

不设 §5 题纲对照。文首用几行指向题纲 B/C/D 和 `01`，不逐题作答。

---

## 5. 各节规格

### 5.1 文首

- 说明本文是面试版；实施细节以 `02-集成设计.md` 为准。
- 链到 `01`（指标）、`03`–`05`（编排 / Hybrid / 工程化）。
- 一句话诚实口径：按该规格接到问数产品并上线；不把开源 SuperSonic 主仓当实现出处。

### 5.2 §1 背景痛点

开场第一句必须包含：Java 问数主链路、Python 可选深度研究、只传 `queryId`、异步 Job、SSE 订 Java、失败静默留 `textSummary`、Compose 同网络且 Python 不对外。

四对矛盾写成表，不展开机制：

| 矛盾 | 一句话 |
|------|--------|
| 时延 | 问数约 15 秒 vs 研究数分钟，不能在 execute 线程里等 |
| 职责 | Java 有用户 / 权限 / `ChatQueryDO`；Python 有 Agent 生态 |
| 失败 | 研究挂了，描述性解读必须还在 |
| 部署 ≠ 网关 | Compose 解决发现和隔离，不解决鉴权和拼 context |

不写：IntentClassifier 细节、13 种失败全文、类名清单。

### 5.3 §2 端到端集成

**2.1 心智模型 + 部署拓扑**

```
浏览器 ──POST queryId──► Java 网关 ──内网 POST──► Python
              │                         │
              │ 立刻 {jobId, PENDING}    │ 立刻 202，后台跑 pipeline
              ▼                         ▼
         SSE 订阅 Java            Java @Scheduled 每 2s 拉 Python
```

Compose：两个 Dockerfile、同一 network；Java 配置示例 `PYTHON_BASE_URL=http://research-agent:8000`（服务名以 Compose 为准）。对外只暴露 Java（及前端）。写明：同网络 ≠ 前端直连。

**2.2 四段链路（每段可贴必要代码）**

| 段 | 必须讲清 | 可贴的代码 | 不要贴 |
|----|----------|------------|--------|
| 前端 | `textSummary` 下方挂载；只传 `queryId`；`FAILED` 时 `return null` | `ExecuteItem` 挂载片段；`handleStart`；`status === 'FAILED'` 分支 | 完整 `useResearchJobStream`（约 80 行）可缩成「先 GET 再 SSE、终态关闭、3 秒重连」 |
| Java 创建 | 归属 / 配额 → `ChatQueryDO` 拼 `task+context` → Java 生成 `jobId` → 写表 PENDING → `@Async` POST Python → 立即返回 | `createResearch` 主干约 30 行 | 13 个类文件树、完整 DTO、DDL 全文 |
| Python 接单 | service token → IntentClassifier → SQLite PENDING → 后台 pipeline → 202 | `create_job` 同步路径骨架 | Main–Sub 循环（指 `03`）；`wait_for` 14 分钟只留一句 |
| 回传 | 两条通道拆开：Python→Java 表是定时拉；Java 表→前端是 SSE | Scheduler 循环骨架（超时兜底 / 404 立刻 FAILED / 抖动 skip / `mergeStatus` 拒终态翻转）+ SSE `onmessage` 终态关闭 | `ResearchSseRegistry` 全文 |

**2.3 方案淘汰（读完链路再看）**

每条回扣 2.2 已出现的环节：

| 淘汰 | 回扣 | 理由 |
|------|------|------|
| execute 线程同步等 Python | Java 立刻回 `jobId` | 占死 Chat 线程，主结果一起糊 |
| 前端直连 Python | 只 POST `queryId` | 拼不了 `ChatQueryDO`，进不了内网，无鉴权 |
| 前端 500ms 轮询当唯一通道 | SSE + 定时拉拆两截 | 用户数绑死 Java→Python 流量 |
| Python 回调 / MQ | Java 每 2s 拉 | Demo 任务量撑不起反向鉴权和死信（回调列为第 4 节演进，不当当前方案） |
| 转传用户 JWT | 独立 service token | 密码哈希泄漏、密钥耦合、语义错位 |

金句：同步挡主链路，直连穿权限，用户轮询打满内网；Compose 只解决发现和隔离。

配套三约束写在淘汰之后、不单独成章：`jobId` 由 Java 生成；路由由 Python 判；Python 只验 service token。

### 5.4 §3 四个后端问题

立场句：两个独立进程、两套存储、没有分布式事务。要答的是权威在哪、失败时谁让步。

**3.1 状态一致性**

- 结论：不搞 2PC、不共享业务库。执行态以 Python 为准，用户可见态以 Java 表为准；2 秒拉取做最终一致；终态不可变防双写。
- 必写故事：共享库为何不行 → 拉而非推 → Java 15 分钟 FAILED 与 Python 后到 COMPLETED 分叉 → Python 14 分钟硬超时是执行权威，Java 15 分钟只兜底崩溃/分区 → 重启扫残留标 FAILED → 超时时钟用 `started_at`，未启动才退 `created_at`。
- 金句：`jobId` 由 Java 发号；`PENDING → RUNNING → 终态` 是单向门。

**3.2 容错与降级**

三层表必须出现，且不可混用：

| 层 | 失败 | 策略 |
|----|------|------|
| 产品 | 没报告 / 超时 | 组件 `return null`，留下 `textSummary` |
| 同步 | HTTP 超时、404、进程重启 | 抖动跳过本轮；404 与硬超时才 FAILED |
| Agent 内部 | 某次 MCP 挂了 | 工具降级（指 `04`），不等于产品失败 |

必写取舍：创建 Job `@Async`，Python 当时挂了不把 Chat 变成 504；IntentClassifier 失败 fallback `default` 是降级成功；14/15 分钟是防假死，口径跟 `01`（`n=3`，非正式 SLA）；SSE 断了不是任务断了。

**3.3 权限**

- 结论：鉴权在网关一次做完。Python 零信任：只认 service token。同网络是纵深，不能替代应用层鉴权。
- 三道闸按调用顺序：功能开关（admin + 白名单）→ 配额与并发（规则不落权限表，`created_by` 只审计）→ 资源归属（不存在与非本人统一 404；SSE 注册前也校验）。
- 不选：把 `userId` 传进 Python 做行级权限。

**3.4 可观测性**

- 结论：靠同一条 `traceId` 串三层，不上完整 APM。
- 排障顺序：Java 任务表（用户可见态）→ 结构化日志（Java MDC + `X-Trace-Id` → Python contextvar）→ TaskTracer JSON（Agent 内部，细节在 `05`）。
- 产品对用户静默，对日志不静默：FAILED 必须有 `error_msg` + `traceId`。
- 不写 Kibana 配法、Prometheus 指标名、Jaeger。

JWT 误传收进 3.3；IntentClassifier fallback 收进 3.2。不另开事故故事。

### 5.5 §4 当前不足与未来演进

只答短板和下一步。可讲/不可讲表不在本节；需要时写进文首一句。

**不足（必须能当面认）**

1. 同步是最终一致，可见延迟约 2 秒；Python 假死要等 Java 15 分钟兜底，当前没有回调。
2. Python 侧 SQLite + 本地文件报告；重启是标失败，不是接着跑；单副本无 HA。
3. 路由协议就绪、实现未分化：三类 `research_type` 仍同一套 agent config。
4. 权限是内测模型：admin + 白名单 + 配额，无权限表、无订阅。
5. 无产品漏斗埋点，不报失败率（与 `01` 一致）。
6. 无取消、无业务会话续跑（YAGNI）。

**演进顺序（先不改契约）**

| 优先级 | 做什么 | 为何现在能演进 |
|--------|--------|----------------|
| 1 | Python 回调 + Java 定时拉兜底 | 协议不动，加 Java 入站 |
| 2 | ReportStore / JobStore 换可持久化存储 | `report_uri`、`tenant_id` 已在协议里 |
| 3 | 按类型分 config；新领域只加 markdown | Java 本来不传 `research_type` |
| 4 | 权限表 / 配额产品化 | 只换 checker，Python 协议不动 |
| 5 | 失败与耗时打点后再谈 SLA | 先有埋点才有失败率 |

近期不做：断点续传、任务级 WebClient 重构、完整 APM。可当「如果重新做」的口头补充，不当已排期。

金句：短板是单机 Demo 的存储和同步，不是网关边界画错；演进换实现、不改 Java↔Python 契约。

---

## 6. 口径与交叉引用

| 主题 | 本文 | 别处 |
|------|------|------|
| GAIA / 耗时 / Token / 开场宽问 | 不重写数字 | `01-通用问答.md` |
| Main–Sub 编排 | pipeline 只留一句 | `03-Main-Sub-Agent编排.md` |
| Hybrid / MCP 降级 | 产品失败 vs 工具失败分界 | `04-Hybrid-Search-MCP.md` |
| TaskTracer / 评测续跑 | 可观测第三层指针 | `05-工程化能力.md` |
| 类、表、完整代码、13 失败矩阵 | 不复制 | `02-集成设计.md` |

数字：问数端到端约 15 秒、描述性解读 &lt;2s、研究数分钟、Scheduler 2 秒。失败率不写。

超时不要混成一个数：`01` 的 11 分钟是 `n=3` 样本推出的**产品侧临时建议**，非正式 SLA；本文工程超时是 Python 硬超时 14 分钟 + Java 兜底 15 分钟。面试文档里两套都要出现时，必须写清分工。

---

## 7. 实现时的写作约束

- 简体中文；中英文与数字之间加空格（链接、术语按现有面试文档习惯）。
- 代码引用用项目既有围栏；面试文档里的代码是规格摘录，标明「对齐 `02-集成设计.md`」，不要假装是 SuperSonic 主仓路径下的已合并文件，除非摘的是现有问数代码（如 `textSummary` 区域）。
- 用户可见的接口路径、状态机、14/15 分钟、终态不可变、统一 404，必须与实施规格一致；若写作时发现规格内部矛盾，以实施规格 §4.4 七条决策和评审 #4/#6/#18 为准。
- 不引入规格里没有的组件（例如 Nginx 研究网关、Kafka、共享 DB）。

---

## 8. 验收

- [ ] 文件存在于 `docs/resume/interview/深度研究/02-集成设计-面试文档.md`
- [ ] 约 500–700 行；无类清单、无 DDL 全文、无 13 行失败矩阵
- [ ] 四节齐全，无题纲逐题附录
- [ ] §2 先链路后淘汰；含 Compose 同网络且明确不是前端直连
- [ ] §3 含一致性、容错、权限、可观测四块
- [ ] §4 只含不足与演进
- [ ] 不出现失败率数字；超时口径不写成正式 SLA
- [ ] `01` / `03`–`05` / 实施规格均有链接
- [ ] `01-通用问答.md` 分册索引若仍只链实施规格，实现时可加一条链到面试文档（可选，不阻塞）
