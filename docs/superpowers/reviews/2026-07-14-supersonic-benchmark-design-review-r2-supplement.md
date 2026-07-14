# Review Round 2 补充: 纠偏与重新定位(权威版)

> **日期**: 2026-07-14
> **触发**: 用户澄清了维度二/三的真实意图,与 R2 假设的方向不同
> **关系**: 本文件**修正** `2026-07-14-supersonic-benchmark-design-review-r2.md` 中跑偏的部分(B4 整段作废),保留仍成立的事实修正(B5/B6/M5/M8)。**本文件是当前权威方向。**

---

## 0. SuperSonic 语义模型层级(代码核查 — 后续所有讨论的基础共识)

这一节澄清后续 benchmark 设计用到的全部术语,所有关系均经代码核查。

### 实体层级图

```
Domain 主题域  (DomainDO.java:11,有 parentId,可嵌套)
│
├── Model 模型  (ModelDO.java:11,有 domainId,【无 dataSetId】)
│   │   创建 Model 时在 ModelDetail 里【内联定义】:
│   │     ├── identifiers   (主键/外键,如 company_id)
│   │     ├── dimensions    (维度)
│   │     ├── measures      (度量 = 原始物理数值字段 + 聚合规则)
│   │     └── fields        (物理列)
│   │   ModelServiceImpl.createModel:90-99 会把这些【拆成独立实体】:
│   │     ├── Dimension 表  (DimensionDO,有 modelId) ← 维度归属 Model
│   │     └── Metric 表     (MetricDO,   有 modelId) ← 指标归属 Model
│   │
│   └── "指标管理"为什么在 Model 下? 因为 Metric.modelId 指向 Model
│
└── Dataset 数据集  (DataSetDO.java:11,有 domainId,【无 modelId】)
    │   Dataset 不创建新维度/指标,而是【按 Model 分组引用】已存在的:
    │     DataSetDetail.dataSetModelConfigs = [
    │       { id: model_id,  includesAll: false,
    │         metrics: [...],     ← 引用 Metric.id
    │         dimensions: [...] },← 引用 Dimension.id
    │       ...
    │     ]
    │
    └── Dataset 是"逻辑视图",从多个 Model 挑维度/指标组合;Model 间 JOIN 由系统处理

Agent (Agent.java:99-115,dataSetIds: Set<Long>)
└── 只绑定 Dataset,用户提问时 LLM 只看到所绑 Dataset 的 schema
```

### 四个关键关系(易混淆点)

| 关系 | 结论 | 代码依据 |
|------|------|---------|
| Model 与 Dataset 的相对位置 | **平级兄弟**,都挂在 Domain 下 | 都有 `domainId`,互不引用 |
| 维度/指标的归属 | **归属 Model**(有 `modelId`),Dataset 只引用 | DimensionDO/MetricDO 只有 modelId |
| 一个 Model 能否被多 Dataset 引用 | **能**(Model 无 `dataSetId`) | 这是 Dataset 作为"逻辑视图"的核心 |
| Dataset 是创建还是引用维度/指标 | **引用**(按 Model 分组的 ID 清单) | `DataSetModelConfig` |

### 指标的两类区别(benchmark 治理变量的关键)

ModelDetail.measures 是**原始物理字段 + 聚合**(如 `SUM(annual_turnover)`),创建 Model 时系统一对一转成**基础 Metric**。但之后可在"指标管理"单独定义**衍生 Metric**,用 `expr` 表达式,例如:
- 基础指标: `净利润 = SUM(net_profit)` ← 对应物理字段
- 衍生指标: `净利率 = 净利润 / 营业收入` ← 表达式,不对应物理字段

衍生指标是语义层的真正价值,也是**干净的单变量治理测试**(见后文子实验 D')。

### DuSQL 示例对照

| 物理层 (`tables_dusql.json`) | SuperSonic 语义层 |
|------------------------------|------------------|
| `db_id: internet` | 1 个 Domain(DuSQL_互联网企业) |
| 4 张表 company/brand/... | 4 个 Model,每个内联定义维度+度量 |
| 跨表 JOIN 查询 | 1 个 Dataset 聚合 4 个 Model,系统用 Model 关系自动 JOIN |

---

## 1. 用户澄清的两个疑问

### 疑问 1: 维度一 — evaluation 脚本是否会创建语义模型?

**答案: 会创建,而且是幂等的。**

核查 `evaluation/build_models.py`:
- `build()` (line 400) 依次执行: `build_domain()` → `build_model_1..4()` → `build_dataSet()` → `build_model_rela1..4()` → `build_agent()` → `build_chat()`
- 创建的主题域/模型/Dataset/Agent 对应 DuSQL 的 4 张表
- 每个函数都有幂等检查(`if not exist: build=True`),**第二次运行不重复创建**

**对维度一的含义**:
- **语义模型(Domain/Model/Dataset)只需创建一次**,三个对比模型共享同一套 DuSQL 语义建模。
- v2 §3.3 "3 个独立 Agent" 的精确含义(结合第 0 节): **同一个 Dataset,创建 3 个 Agent,各自 `dataSetIds` 都指向它,只有 `chatModelId` 不同**。不是 3 套独立的语义模型。
- 脚本改动很轻:在现有 `build_agent()` 之后 clone 出 2 个 Agent(共 3 个),改 `chatModelId`,`dataSetIds` 保持指向同一 Dataset。

→ 维度一评估维持不变(只有 M8 token 追踪问题)。

### 疑问 2: 维度二/三的真实意图 — Agent 规模最佳实践

**用户的真实问题**:
> 在本项目中可以通过创建多个 agent,每个 agent 关联不同的数据表,来实现分而治之的效果。但是我很好奇的是,最佳实践是怎样的,也就是说一个 agent 关联多少个数据表比较合适,最多关联多少个指标。

**这完全不是 R2 B4 假设的"治理层级 Level 0/1/2 消融矩阵"。** 用户问的是**落地工程的规模最佳实践**。R2 B4 整段作废。

### 术语精确化(基于第 0 节)

用户口语中的"表/指标"在 SuperSonic 里有精确含义:
- **"Agent 关联多少个表"** = `Agent.dataSetIds` 含几个 Dataset(每个 Dataset 背后是若干 Model,每个 Model 通常对应一张物理表或一个 SQL 查询块)。
- **"Dataset 含多少表"** = 一个 Dataset 的 `dataSetModelConfigs` 有几条(每条对应一个 Model)。
- **"Dataset 含多少指标"** = 所有 `dataSetModelConfigs[].metrics` 列表的并集大小。

后续子实验都用精确术语,不用"表/指标"口语。

---

## 2. SuperSonic 架构核查 — Agent 规模机制

深挖代码后,SuperSonic 的"分而治之"有**两层自动筛选机制**:

### 机制 1: Dataset 路由(winner-takes-all)

**代码**: `HeuristicDataSetResolver.java:27-37`

```java
public Long resolve(ChatQueryContext chatQueryContext, Set<Long> agentDataSetIds) {
    Set<Long> matchedDataSets = mapInfo.getMatchedDataSetInfos();
    matchedDataSets.retainAll(agentDataSetIds);  // 限定到 agent 的 datasets
    if (matchedDataSets.size() == 1) return ...; // 唯一命中直接选
    return selectDataSetByMatchSimilarity(mapInfo); // 多个命中,按相似度选最高
}
```

- Agent 即使关联了 N 个 Dataset,映射阶段只选**相似度最高的一个** 进入 LLM。
- 选择优先级: ① dataset 总相似度 → ② metric 相似度 → ③ 总和 → ④ metric 使用次数。
- **含义**: "一个 Agent 关联多个 Dataset" **不是真正的瓶颈** — 因为只有赢家的 schema 进 LLM。

### 机制 2: Schema 字段过滤(PARSER_FIELDS_COUNT_THRESHOLD)

**代码**: `LLMRequestService.java:34-47` + `ParserConfig.java:56-58`

```java
int fieldCntThreshold = Integer.valueOf(parserConfig.getParameterValue(
    PARSER_FIELDS_COUNT_THRESHOLD)); // 默认 0

if (queryCtx.getMapInfo().getMatchedElements(dataSetId).size() <= fieldCntThreshold) {
    // 命中元素少 → 用全量 schema
    llmSchema.setMetrics(queryCtx.getSemanticSchema().getMetrics());
    llmSchema.setDimensions(queryCtx.getSemanticSchema().getDimensions());
} else {
    // 命中元素多 → 只用映射命中的元素
    llmSchema.setMetrics(getMappedMetrics(queryCtx, dataSetId));
}
```

- **默认 threshold=0** = **永远用全量 schema**(因为命中元素数 > 0 永远成立,走 else 分支... **需实测复核逻辑**,但默认行为是全量喂)。
- 设为 >0 后,映射命中元素 ≤ 阈值时只喂命中的元素 → prompt 显著缩短。
- 这是 SuperSonic **真正的"分而治之"调参点**。

### 无硬限制(核查结果)

| 维度 | 是否有 MAX | 证据 |
|------|-----------|------|
| Agent.dataSetIds 数量 | ❌ 无 | `Agent.java:99-115` `Set<Long>` 无校验 |
| 一个 Dataset 含 Model 数 | ❌ 无 | `DataSetDetail.java:11` `List<DataSetModelConfig>` 无限制 |
| Dataset 聚合的指标数 | ❌ 无 | `DataSetSchemaBuilder.java:174-189` 全量聚合,无分页 |

**结论**: 没有硬限制,实际瓶颈是 **prompt token 上限** 和 **映射阶段的检索质量**。

---

## 3. 重新定位的维度二/三设计建议

建议把维度二/三**重新定义为"Agent / Dataset 规模最佳实践"**,原来的"治理层级"用**衍生指标**这个干净变量重新设计(见子实验 D')。

### 新维度: Agent / Dataset 规模最佳实践

**核心叙事(面试价值)**: "我系统测了 SuperSonic 在不同 Agent/Dataset 规模下的表现拐点,给出了'何时该拆分 Agent / 何时该合并 Dataset / threshold 调到多少'的工程建议。"

**四个正交子实验**:

#### 子实验 A — Dataset 内 Model 数量
- **变量**: 一个 Dataset 的 `dataSetModelConfigs` 含 1 / 5 / 10 / 20 个 Model
- **固定**: 同一个 Agent,单一 Dataset,全量 schema(threshold=0),同一份 gold 查询集
- **观察**: 准确率拐点、prompt token 增长、LLM 延迟、context window 是否撞顶
- **预期发现**: 准确率随 schema 膨胀下降,找到"单 Dataset 最多多少 Model"的实用上限

#### 子实验 B — `PARSER_FIELDS_COUNT_THRESHOLD` 调参 ★(最有价值)
- **变量**: threshold ∈ {0(全量), 5, 10, 20}
- **固定**: 大 Dataset(20 个 Model),同一份 gold 查询集
- **观察**: threshold 对准确率(过滤是否漏掉必要字段)、延迟、token 的影响
- **预期发现**: threshold 存在甜点区 — 太小=漏字段=准确率降,太大=prompt 长=延迟升。找到这个甜点=**真正懂 SuperSonic 内部机制**。
- **叙事价值极高**: 这是 SuperSonic 文档里没明确讲清的调参点,实测数据很有说服力。
- **⚠️ 前置验证**: 实施前先实测确认 threshold=0 的真实分支行为(是否真的全量喂),避免实验设计建立在错误假设上。

#### 子实验 C — Agent 跨 Dataset 的分而治之策略
- **变量**:
  - 方案 1: 1 个大 Agent 关联 10 个 Dataset(靠 winner-takes-all 路由)
  - 方案 2: 10 个小 Agent 各关联 1 个 Dataset(用户手工分治)
  - 方案 3: 3 个中 Agent 各关联 3-4 个 Dataset(按业务域分组)
- **固定**: 同一份总数据,同一份 gold 查询集(每个查询标注它属于哪个 Dataset)
- **观察**: 路由准确率(winner 是否选对)、端到端准确率、运维复杂度
- **预期发现**: winner-takes-all 在 Dataset 语义重叠时会选错 → 这种情况必须手工分治。给出"何时自动路由够用 / 何时必须手工拆分"的判据。

#### 子实验 D' — 衍生指标的价值(替代原 Level 0/1/2)★(最干净的治理实验)
利用第 0 节"基础指标 vs 衍生指标"的区别,做一个**真正的单变量**治理实验:
- **变量**: Dataset 是否包含衍生指标
  - 对照组: Dataset 只引用基础指标(来自 measure,如 `净利润=SUM(net_profit)`)
  - 实验组: 同一 Dataset 额外引用衍生指标(如 `净利率=净利润/营业收入`)
- **固定**: 同一物理 Model,同一份 gold 查询集
- **测试集**: 含"比率/衍生"语义的查询(如"各公司净利率排名"),这些查询在对照组里 LLM 需要自己拼表达式,实验组里直接用衍生指标。
- **观察**: 含比率语义查询的准确率差异
- **为什么比原 L0/L1/L2 好**: 只改一个变量(衍生指标的有无),不混入列名/值映射/embedding 等其他变量。归因干净。
- **叙事价值**: 直接量化"语义层衍生建模值多少钱",这是 SuperSonic 区别于纯 Text2SQL 的核心卖点。

### Gold 标注方案(更新)

- **Gold 四元组**: `(NL 问题, 目标 Dataset ID, 目标结果集, 参考 SQL)`
- `目标 Dataset ID` —— 子实验 C 必需(评判路由是否选对)。
- 参考 SQL 用完整治理写法(最易读),准确率评判**主用结果集比对**(R2 M7 仍成立)。

---

## 4. 指标体系(更新)

| 指标层 | 指标 | 适用子实验 |
|--------|------|-----------|
| 路由层 | Dataset 选择正确率(winner == gold Dataset) | A / C |
| 路由层 | 映射命中的元素数量分布 | A / B |
| Prompt 层 | prompt_tokens(每次 LLM 调用) | A / B |
| 准确率层 | Execution Accuracy(结果集比对) | 全部 |
| 延迟层 | 映射延迟 / LLM 延迟 / 端到端延迟 | 全部 |
| 容量层 | context window 命中率 / 截断率 | A |

R2 的 M5(用 `/api/semantic/query/chat/map` 测纯映射)在子实验 C 仍然适用 —— 路由层指标必须用这个端点。

---

## 5. R2 各条 checklist 的处置

| R2 条目 | 处置 | 原因 |
|---------|------|------|
| **B4** 消融矩阵 | ❌ **作废** | 用户意图不是治理消融,是规模最佳实践 |
| **B5** BGE-small-zh 不可行 | ✅ **保留** | 事实修正,代码核查成立(embedding 是 in_process ONNX,无注入 API) |
| **B6** use-llm-enhance 默认 true | ✅ **保留** | 事实修正,s2-config.yaml:45 默认 true |
| **M5** 用 `/chat/map` 而非 `query/search` | ✅ **保留** | 子实验 C 评判路由仍需要纯映射端点 |
| **M6** LLM 延迟与 schema 膨胀相关 | ✅ **保留并强化** | 子实验 A 的核心假设就是它 |
| **M7** Gold 主用结果集比对 | ✅ **保留** | 仍然成立,补"目标 Dataset ID"字段 |
| **M8** token 服务端无追踪 | ✅ **保留** | 仍然成立,子实验 A/B 都需要 prompt_tokens |

---

## 6. 修改清单(R2 补充)

spec 文档需要的修改:

- [ ] §4 维度三标题从"数据治理方案对比"改为 **"Agent / Dataset 规模最佳实践"**
- [ ] §4.2 删除 Level 0/1/2 三级定义,改为四个正交子实验 A/B/C/D' 的设计
- [ ] §4.2 用第 0 节的精确术语(Dataset 内 Model 数、聚合指标数)替换口语化的"表/指标"
- [ ] §5 维度二(数据量)与新维度三合并 —— "数据量"本质上就是"Dataset 内 Model 数"(子实验 A)
- [ ] Gold 元组增加 `目标 Dataset ID` 字段(从三元组升四元组)
- [ ] §4/§5 指标表加入: Dataset 选择正确率、prompt_tokens、context window 命中率
- [ ] §3.3 维度一补一句: "3 个 Agent 共享同一个 DuSQL Dataset(`dataSetIds` 相同),仅 `chatModelId` 不同"
- [ ] B5 删除"BGE-small-zh 手动生成"假设
- [ ] B6 显式声明各实验组的 `use-llm-enhance` 值
- [ ] 子实验 B 实施前先实测确认 `PARSER_FIELDS_COUNT_THRESHOLD=0` 的真实分支行为

实施优先级:

1. **子实验 B(threshold 调参)** — 最高 ROI,叙事价值最强,代码改动最小(只改一个参数)
2. **子实验 D'(衍生指标)** — 最干净的单变量治理实验,直接量化语义层价值
3. **子实验 A(Dataset 内 Model 数)** — 验证容量拐点
4. **维度一(模型对比)** — baseline
5. **子实验 C(分而治之策略)** — 时间允许再做

---

## 7. 结语

这次澄清把整个 benchmark 的焦点从"治理对比"(偏学术)拉到了"**工程最佳实践 + 衍生建模价值**"(偏落地)。后者对面试更有价值 —— 面试官关心的是"你能不能告诉我怎么用",而不是"你做了一个消融实验"。

子实验 B(`PARSER_FIELDS_COUNT_THRESHOLD` 调参)和子实验 D'(衍生指标价值)是两个最大的亮点:
- B 直接回答"大 schema 时字段过滤开多大"这个文档没讲清的工程问题。
- D' 直接量化"语义层衍生建模值多少钱"这个 SuperSonic 的核心卖点。

两者都用**干净的单变量设计**,结论经得起追问。测出这两个甜点,是真正懂这个系统的信号。
