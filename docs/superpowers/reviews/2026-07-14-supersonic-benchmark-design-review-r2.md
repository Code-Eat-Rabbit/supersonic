# Review Round 2: SuperSonic 全面测评方案设计

> **Reviewer**: Claude Code | **日期**: 2026-07-14
> **文档**: `docs/superpowers/specs/2026-07-14-supersonic-benchmark-design.md` (v2)
> **范围**: 聚焦**维度二(数据量)**与**维度三(治理对比)**,基于 Java 代码深挖
> **结论**: **有条件通过 (Conditional Pass)** — v2 修复了第一轮的 B1-B3/M1-M4,方法论框架已扎实。但维度二/三的**若干技术假设被代码证伪**,治理层级的"变量隔离"设计存在**混淆变量(confounding variables)**,不修正会导致实验结果无法解释。

> ⚠️ **重要 — 读这份之前请先看 `2026-07-14-supersonic-benchmark-design-review-r2-supplement.md`**
> 本文件的 **B4(治理消融矩阵)** 已在 supplement 中**作废** —— 用户澄清维度二/三的真实意图是"Agent 规模最佳实践",不是治理消融。B5/B6/M5/M6/M7/M8 等事实修正仍成立。supplement 是当前权威方向。

---

## 总评

v2 版本质量显著提升:占位符 key、分层准确率、gold 标注方案、独立 Agent、指标拆层、定性假设都已落地。第一轮的 11 条 checklist 全部处理。

但本轮深挖 Java 代码后发现,**v2 对 SuperSonic 数据治理机制的理解有几处事实性错误**,而这些错误恰好集中在维度二/三的核心设计上。如果按当前 v2 实施,实验结果会出现"我改了 X,但 Y 也跟着变了"的混淆,无法得出干净的因果结论。

下面按严重程度分级。

---

## 🔴 Blocker 级问题(威胁实验效度)

### B4. 治理层级定义(§4.2)把"列名治理"和"映射机制治理"混为一谈 — 混淆变量

**问题**: v2 的 Level 0/1/2 定义同时改变了**多个独立维度**:

```
Level 0 → Level 1 → Level 2 同时改变了:
  ① 列名 (英文编码 → 中文别名 → 中文视图)
  ② 维度类型标注 (无 → categorical/time → 全标注)
  ③ Metric 定义 (无 → SUM/COUNT → 全定义)
  ④ 值映射 (原始编码 → 原始编码 → 解码视图)
  ⑤ 值级 Embedding (无 → 无 → BGE-small-zh)        ← B5 会证伪
  ⑥ 单字词补充 (无 → 无 → 高频分词子词)
  ⑦ EmbeddedMapper use-llm-enhance (无 → 无 → 启用)  ← B6 会证伪默认值
```

**代码核查**:
- `PromptHelper.java:105-198` 的 `buildSchemaStr()` 显示 LLM 实际看到的是:
  - `metric.getName()` (中文 name,非 bizName) — PromptHelper.java:112
  - `metric.getAlias()` — PromptHelper.java:113-117
  - `metric.getDescription()` (COMMENT) — PromptHelper.java:125-127
  - `metric.getDefaultAgg()` (AGGREGATE) — PromptHelper.java:128-131
  - dimension 同理:getName/alias/datatype/format/description — PromptHelper.java:136-158
  - **值**:`<fieldName='fieldValue'>` — PromptHelper.java:165-167
- **LLM 完全看不到** bizName / fieldName / 维度 type 枚举(只看人类可读描述)。

**这意味着**:
- 改变 ①(列名)实际是改变 LLM 看到的 `name` 字段 — 直接影响 LLM 理解。
- 改变 ②(维度 type 标注)对 LLM prompt **几乎无影响**(type 枚举不进 prompt,只影响 `PartitionTimeMapper`/`SchemaCorrector` 的规则路径)。
- 改变 ③(Metric 定义)同时改变 LLM 看到的 `AGGREGATE` 子句 + `AggCorrector` 的规则路径。
- 改变 ④(值映射)改变 LLM 看到的 `Values=[...]` 段 — 这是最显著的变量之一。

**所以 Level 0→1→2 不是一个干净的单变量实验,而是 7 个变量同时变**。如果 Level 2 准确率高于 Level 0,你无法归因到"哪个治理动作贡献最大"。

**建议**: 把 §4.2 改为**正交设计(orthogonal design)**,显式列出 7 个治理杠杆,然后构造**消融实验矩阵**而非简单三级:

| 实验组 | name 中文 | alias | description | agg | 值解码 | Embedding 增强 | LLM enhance |
|--------|----------|-------|-------------|-----|--------|----------------|-------------|
| L0-baseline | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| L1-name | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| L1-full | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| L2-values | ✓ | ✓ | ✓ | ✓ | ✓ | (见 B5) | (见 B6) |

这样面试时你能讲:"值解码贡献了 +X 个点,列名治理贡献了 +Y 个点"。比一句"Level 2 比 Level 0 好"专业一个量级。

---

### B5. "BGE-small-zh 手动生成值级 Embedding"在当前架构下不可行 — 技术假设错误

**位置**: §4.2 Level 2 最后一档 + §7 风险表"Embedding 生成耗时"

**代码核查**:
- `application-local.yaml:11-12`: `embedding-model.provider: in_process` — 用的是 **ONNX BERT**(S2OnnxEmbeddingModel),不是 BGE。
- `TextSegmentConvert.java:30-35`: 嵌入的是 `DataItem` 的多个字段组合(name + bizName + newName + defaultAgg + ...),**不是单一的 name**。
- `MetaEmbeddingTask` / `MetaEmbeddingListener` 是**唯一**的 embedding 写入路径,走的是**当前配置的 in_process 模型**,不接受外部预计算向量。

**问题**:
1. 你**无法用 BGE-small-zh 在外部生成向量然后注入** SuperSonic —— embedding 写入路径绑死了 `EmbeddingModel.embed()` 调用,没有"注入预计算向量"的 API。
2. 即使能注入,检索时仍用 in_process ONNX 模型做 query 端 embedding —— **query 和 document 必须用同一个模型**,否则向量空间不匹配,检索准确率会崩。
3. 想换 BGE-small-zh 必须**整个 embedding-model.provider 换掉**(改配置 + 提供 ONNX 文件),这是 SuperSonic 全局配置,**无法按 Dataset/Model 粒度切换**。

**这意味着 §4.2 的"Level 2 vs Level 1 用不同 embedding"这个对比在当前架构下做不到。**

**建议** 三选一:
1. **删掉"值级 BGE-small-zh"这一档**,承认 embedding 模型是全局常量,不作为治理变量。
2. **改成"是否触发 embedding 检索"对比**:通过控制 `Text2SQLType` (`ONLY_RULE` vs `LLM_OR_RULE`)和 `MapModeEnum`,让 Level 0/1 走纯规则、Level 2 走 embedding。这是干净且代码支持的变量。
3. **如果一定要换 embedding 模型**:作为**独立的第三个子实验**,单独跑一次"ONNX-BERT vs BGE-small-zh 全局切换"对比,与 Level 0/1/2 治理实验**分开跑**,避免混淆。

我推荐方案 2 —— 它既代码可行,又能讲出"语义检索 vs 规则匹配"的故事,比 embedding 模型本身的对比更有叙事价值。

---

### B6. `use-llm-enhance` 在 s2-config.yaml 中默认就是 true — 实验默认值与文档假设相反

**位置**: §4.2 Level 2 "EmbeddedMapper: use-llm-enhance 启用" — 隐含默认是 false

**代码核查**:
- `s2-config.yaml:45`: `s2.mapper.embedding.use-llm-enhance: true` — **项目默认配置就是 true**。
- `MapperConfig.java:61-63`: 代码层 fallback 是 `false`,但 `s2-config.yaml` 覆盖为 `true`。
- `EmbeddingMatchStrategy.java:75-88`: 开启后,**每次 embedding 检索都会调一次 LLM** 做二次过滤。

**问题**:
1. 这意味着**所有 Level 都默认走 LLM 二次过滤**(除非显式关闭)。如果 Level 0/1 没显式关,你以为是"纯 embedding 检索",实际是"embedding + LLM 过滤",变量没隔离。
2. **更严重**: `EmbeddingMatchStrategy.detectWithLLM()` 每次 embedding 检索都会调一次 LLM。维度二(数据量测试)的"映射延迟"指标会因此被 LLM 调用主导,**你测的不是"数据量对映射的影响",而是"LLM 二次过滤的延迟"**。这会让 §5.4 "映射延迟 = embedding 检索 vs LLM 生成分段计时" 的假设完全失效 —— 映射阶段本身就含 LLM 调用。

**建议**:
1. §4.2 显式声明每个 Level 的 `use-llm-enhance` 取值,Level 0/1 明确设为 `false`(否则不是"裸数据/基础治理")。
2. §5.4 映射延迟拆**三段**:
   - 纯 embedding 检索延迟(`use-llm-enhance=false` 时测)
   - LLM 二次过滤延迟(`use-llm-enhance=true` 时的增量)
   - NL2SQL 生成延迟
3. 在脚本里通过 SuperSonic 的参数 API(**不是**改 yaml 重启)动态切换 `s2.mapper.embedding.use-llm-enhance`,验证它是否支持 per-request 覆盖。若不支持 per-request,则需 per-Agent 不同配置 —— 需要确认 Agent 是否能携带 mapper 参数。

---

## 🟠 Major 级问题

### M5. 维度二/三的"映射成功率"指标定义模糊 — 应改用 `/api/semantic/query/chat/map` 而非 `query/search`

**位置**: §4.4 "映射层 / `query/search` API 成功率" + §5.4 "映射成功率 / `query/search` API 200 OK 比例"

**代码核查**:
- `/api/chat/query/search` (ChatQueryController.java:33) 调用 `chatQueryService.search()`,走的是**完整 parse 流程**的一部分,不是纯映射。
- `/api/semantic/query/chat/map` (ChatQueryApiController.java:38) 调用 `S2ChatLayerService.map()`,**只跑 SchemaMapper 链,不跑 LLM 生成** —— 返回 `MapResp { queryText, mapInfo }`。
- `SchemaMapInfo` 提供 `getMatchedDataSetIds()`、`getMatchedElements(dsId)` 等方法,可以精确统计映射到的元素数量、similarity 分布、是否 LLM matched。

**问题**:
1. v2 用 `query/search` 测"映射成功率",但 search 端点语义不清(可能含 parse),**映射与生成分不开**。
2. "200 OK 比例"是错误指标 —— SuperSonic 全局异常处理器(`RestExceptionHandler.java`)把所有异常包成 HTTP 200 + `code != 200`。所以映射失败也是 200,按"200 OK 比例"统计会得到 100%。
3. 正确的"映射成功率"应该看 `MapResp.mapInfo` 是否为空,或 matched elements 数量是否 > 0。

**建议**:
1. §4.4 / §5.4 改用 **`/api/semantic/query/chat/map`** 端点测纯映射能力。
2. 把"映射成功率"细化为:
   - **Dataset 命中率**: `mapInfo.getMatchedDataSetIds()` 含目标 dataset 的比例。
   - **元素召回率**: matched elements 中,目标元素(按 gold SQL 反推)占比。
   - **高置信命中率**: `similarity >= 0.9` 或 `isFullMatched()` 的元素占比。
3. 删掉"200 OK 比例"这个指标 —— 它在 SuperSonic 架构下永远是 100%,无信息量。

---

### M6. 维度二"LLM 生成延迟与数据量无关"假设需代码验证 — 存在反例

**位置**: §5.4 "SQL 生成延迟 / 由 LLM 主导,与数据量几乎无关"

**代码核查**:
- `PromptHelper.buildSchemaStr()` 把**所有 metrics 和 dimensions** 拼进 prompt(PromptHelper.java:108-158)。
- 数据量增长 → Model/Dataset 数量增长 → **schema 字符串变长 → prompt token 变长 → LLM 延迟增加**。

**问题**: LLM 看到的是 schema 不是行数据,这点 v2 说的对。但"schema 膨胀"会让 prompt 显著变长 —— 100 家公司 × 3 表 × N 维度,prompt 可能从 500 token 膨胀到 5000+ token,**LLM 延迟随 prompt 长度近似线性增长**。

所以严格说,数据量增长对 LLM 延迟的影响机制是**间接的、通过 schema 大小传导**,而非 v2 说的"几乎无关"。

**建议**:
1. §5.4 假设修正为:"数据量增长对 LLM 延迟的影响**主要通过 schema 膨胀间接传导**,而非行数。在 schema 元素数量 < 阈值时影响可忽略,超过后延迟随 prompt token 线性增长。"
2. 维度二测试时**额外记录 prompt token 数**,作为 schema 膨胀的代理变量,与延迟做相关性分析。
3. 如果发现延迟与 prompt token 强相关而与 dataset 数量弱相关,那是更精确的发现:"是 prompt 长度而非数据规模本身拖慢了 LLM"。

---

### M7. Gold 标注方案(§Gold 标注方案)缺少"跨 Level 一致性"约束

**位置**: 文档第 28-34 行 "Gold 标注方案"

**问题**: 文档说维度二/三共用 30-50 条 gold 查询,但**没说清 gold SQL 是按哪个 Level 写的**:

- 同一句自然语言"查询茅台 2023 年净利润",在 Level 0(英文编码列名)和 Level 2(中文视图)下,**gold SQL 文本完全不同** —— Level 0 的 gold 可能是 `SELECT net_profit FROM ...`,Level 2 是 `SELECT 净利润 FROM v_profit ...`。
- 但**执行结果集应该相同**(只要底层是同一份物理数据)。

**这是关键设计点**: 如果按"SQL 文本精确匹配"评准确率,Level 0/1/2 的 gold SQL 必须各自标注(因为列名不同),工作量大。如果按"结果集比对"评(现有 `eval_exec_match` 就是结果集比对),则**一份 gold 结果集 + 一份 gold SQL(任意 Level 均可)就够**。

**建议**:
1. 明确:**维度三主用"结果集比对"评准确率**,理由是治理对比关心的是"答对没"而非"SQL 写得像不像"。
2. Gold 三元组简化为 `(NL 问题, 目标结果集, 参考SQL)`,其中参考 SQL 只需一份(用 Level 2 的写法,最易读)。
3. **但**要保留一份"Level 0 可执行 SQL"作为对照 —— 用来验证 Level 0 确实"能跑通但答不对",而非"SQL 语法都不对"。这涉及 §B2 第一轮提到的 status 分层。

---

### M8. Token 使用追踪服务端不存在 — 需自行实现或走客户端

**位置**: §3.5 "Token / prompt/completion/reasoning(分列)"

**代码核查**:
- 探索明确报告:**chat 模块无任何 `tokenUsage` / `TokenUsage` 类**。
- LangChain4j 的 OpenAI 集成内部有 token 信息(`OpenAiChatModel.java:54,175,223`),但**未暴露到 API 响应**。
- `ChatParseResp` / `ParseTimeCostResp` 只暴露 `parseTime` / `sqlTime`,无 token 字段。

**问题**: v2 设计的"prompt / completion / reasoning 分列"指标,**服务端拿不到**。要么改 SuperSonic 源码在 LLM 调用点拦截并写入响应(侵入式),要么走客户端(但客户端拿不到 LLM 原始响应,只能拿到最终 SQL)。

**建议** 三选一(按推荐度排序):
1. **服务端最小侵入**: 在 `LLMSqlParser` / `OnePassSCSqlGenStrategy` 的 LLM 调用点,把 `response.tokenUsage()` 写入 `traceId` 关联的日志(keyPipeline.log),benchmark 脚本通过 traceId 拉日志解析。**不改 API 契约**,只加日志。
2. **改 LangChain4j 配置**: 部分 LangChain4j 版本支持 `response.output().tokenUsage()`,在调用处显式取出并存到一个 per-request 的 ThreadLocal/Map,通过新 endpoint 查询。
3. **降级方案**: 维度一(模型对比)用 DashScope 的 token 计费 API 事后查询(按 traceId 时间窗聚合),不追求 per-query 精度。维度二/三弱化 token 指标,只报延迟。

推荐方案 1 —— 改动最小,且 traceId 已是现有可观测性主轴。

---

## 🟡 Minor 级问题

### m5. 维度二"建模耗时"假设过粗

**位置**: §5.4 元数据层 "建模耗时 / 随数据量线性增长"

**代码核查**: `createModel` 是 per-model 的 REST 调用,每次创建一个 model(含若干 dimension/measure)。100 家公司 × 3 表 = 300 个 model 调用,**每个调用是独立 HTTP round-trip + DB 写入**。

**问题**: "随数据量线性增长"是对的,但**常数项(HTTP + DB 单次开销)可能主导**,而非每条 dimension/measure 的边际成本。如果只测端到端总耗时,会得到一个被 HTTP 开销主导的数字。

**建议**: 拆两个指标:
- **per-model 创建耗时**(分布,P50/P95)
- **总建模耗时**(求和)

面试时讲"单次 createModel P95 = 120ms,主要是 DB 写入,与 model 内字段数无关"比"100 家公司建模总耗时 36s"更有信息量。

### m6. EmbeddingMapper 检索的 chunking 参数未纳入治理变量

**位置**: §4.2 未提及

**代码核查**: `MapperConfig.java` 暴露了 `EMBEDDING_MAPPER_TEXT_SIZE=3`、`EMBEDDING_MAPPER_TEXT_STEP=2`(滑窗 chunking)。这些参数**显著影响映射召回**,且是 SuperSonic 真正的"调参点"。

**建议**: 维度三可选增加一个子实验:**固定治理 Level 2,扫 `EMBEDDING_MAPPER_TEXT_SIZE` ∈ {2,3,5}**,观察映射率拐点。这是"我懂 SuperSonic 内部机制"的强信号。

### m7. §7 风险表遗漏 "SuperSonic 字段长度限制"

**位置**: §7

**代码核查**: prompt schema 字符串无显式长度上限,但 LLM context window 是硬约束。100 家公司场景下,prompt 可能超 8K/32K token 上限。

**建议**: 加风险:"schema 膨胀导致 prompt 超 context window,缓解 = Dataset 拆分 / schema 裁剪策略 / 换大窗口模型"。

### m8. 维度二第 3 轮 "50-100 家公司" 与 §5.3 数据源描述不匹配

**位置**: §5.2 vs §5.3

§5.2 只列了 4 类 akShare 接口(三大报表 + 股本),但 §5.3 说"50-100 家公司 × 3 报表"。**每家公司**的资产负债表/利润表/现金流量表是**多期数据**(按报告期堆叠),表结构相同 —— 所以"50 家公司 × 3 表 = 150 张表"的说法可能有误,应该是"50 家公司 × 3 报表类型,合并为 3 张大表(按公司分区) 或 150 张分表"。

**建议**: 明确表设计 —— 是**按公司分表**(每公司 3 张表,测试 schema 膨胀)还是**合表加公司维度**(3 张表,测试单表行数)?这两种设计测的是完全不同的容量场景。结合 §B4 的治理实验,**按公司分表** 更能制造 schema 膨胀,更有测试价值。

---

## 维度二 vs 维度三 的实施优先级再校准

v2 已把维度三排第一,基于本轮代码深挖,进一步建议:

| 维度 | 代码可行性 | 变量可控性 | 叙事价值 | 建议 |
|------|-----------|-----------|---------|------|
| 维度三(治理对比) | ✅ 全部支持(修正 B4-B6 后) | 中(需正交设计) | **高** | **必做**,但按 B4 重设计为消融矩阵 |
| 维度一(模型对比) | ✅ 全部支持(M8 token 需额外工程) | 高 | 中 | 做,作为 baseline |
| 维度二(数据量) | ⚠️ schema 膨胀可能撞 context window | 低(LLM 延迟被 prompt 长度混淆) | 低 | **降级或砍掉 50-100 家轮**,只做 5→20 家验证脚本正确性 |

**核心建议**: 维度二的"50-100 家饱和测试"**性价比最低** —— 它测的是 SuperSonic 作为后端服务的容量,与"Text2SQL + 治理价值"的面试叙事弱相关。把省下的时间投入维度三的消融矩阵,ROI 更高。

---

## 修改清单 (Round 2)

实施前必须解决:
- [ ] **B4** §4.2 治理层级重设计为正交消融矩阵(7 个杠杆列表 + 实验组表)
- [ ] **B5** 删除"BGE-small-zh 手动生成 embedding"档,改用 `Text2SQLType`/`MapModeEnum` 控制是否走 embedding
- [ ] **B6** 显式声明每 Level 的 `use-llm-enhance` 值;映射延迟拆三段计时
- [ ] **M5** 映射指标改用 `/api/semantic/query/chat/map`,删掉"200 OK 比例"
- [ ] **M8** token 追踪选定方案(推荐服务端日志 + traceId 关联)

实施时建议解决:
- [ ] **M6** §5.4 LLM 延迟假设修正 + 记录 prompt token 作代理变量
- [ ] **M7** Gold 标注明确"主用结果集比对",参考 SQL 用 Level 2 写法
- [ ] **m8** §5.3 明确表设计(按公司分表 vs 合表)

可选优化:
- [ ] **m5** 建模耗时拆 per-model + 总计
- [ ] **m6** 维度三加 chunking 参数扫描子实验
- [ ] **m7** 风险表加 context window 风险
- [ ] 砍掉维度二第 3 轮(50-100 家)

---

## 结语

v2 已经从"想法大纲"进化到"可执行设计",这一轮的反馈更多是**实验方法论的精修**而非方向修正。B4(消融矩阵)是本轮最重要的建议 —— 它把"Level 2 比 Level 0 好"这种粗粒度结论,升级为"值解码贡献 +X,列名治理贡献 +Y",这正是面试时区分"跑了个 demo"和"做了严谨实验"的关键。

B5/B6 是被代码证伪的技术假设,修正后维度三才能跑出可解释的结果。M5 是观测手段的错误(用错端点),M8 是观测能力的缺口(token 无服务端追踪),两者都直接影响数据可信度。

建议按 B4 → B5/B6 → M5/M8 的顺序修正,修完后这份方案就具备真正可执行 + 可解释的双重要件了。
