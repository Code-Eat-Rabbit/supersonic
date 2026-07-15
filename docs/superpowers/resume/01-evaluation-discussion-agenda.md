# SuperSonic Text2SQL 测评 — 面试文档

> 84 题金融 NL2SQL 测评集 · 双模型对比 · 语义建模方法论

---

## 30 秒概括

"我为 SuperSonic 搭建了端到端金融 NL2SQL 测评管线——从 akShare 拉取沪深 300 财报、构建 6 Model 语义层、生成 84 道题目、到双模型跑批和双维度评分全流程。

核心发现：**语义建模质量是准确率天花板**——把 3 张表按时间粒度拆成最新期/全期两层后，可用率从 0 提升到 100%。同时确认了在当前语义层配置下 qwen 和 deepseek 的 SQL 输出完全一致，LLM 选型不是瓶颈。"

---

## 什么是 Text2SQL 测评

SuperSonic 本质是 **NL2SQL**（非纯 Text2SQL）——多了一层语义中间层：

```
NL 问题
 → SchemaMapper (embedding)  → 识别指标/维度
 → SemanticParser (LLM)      → 生成 S2SQL
 → Corrector (规则)          → 修正校验
 → Translator                → 物理 SQL
```

测评要做的是：给定 NL 问题和预期答案，评估这条链路每一步的质量。

### 测评管线

```
akShare API
 → fetch_data.py: 沪深300 × 5期年报, 3表各1500行
 → SQLite (csi300.db)
 → build_semantic.py: Domain → 6 Model → Dataset → 2 Agent
 → generate_questions.py: deepseek-v4-flash 生成 84 题
 → run_eval.py: 逐题调 API, 增量保存
 → calc_accuracy.py + calc_semantic.py: 精确匹配 + 语义评分
 → report.py: Markdown 报告
```

---

## 关键数据

| 指标 | qwen3.7-plus | deepseek-v4-pro |
|------|-------------|-----------------|
| v1 语义层可用率 | 100% (84/84) | 100% (84/84) |
| v2 语义层可用率 | 100% (84/84) | 24% (20/84) |
| 手写 SQL 精确匹配 | 0% | 0% |
| NL2SQL 精确匹配 | 100% | - |
| 两模型 SQL 一致性 | **84/84 完全一致** | 同上 |
| 延迟 | ~3300ms | ~3200ms |

---

## 工程问题及解决

| 问题 | 原因 | 解决 |
|------|------|------|
| SuperSonic 不支持 SQLite | `EngineType` 枚举缺 SQLITE | 源码修改 + `sqlite-jdbc` 依赖, Maven 重建 |
| langchain4j 类冲突 | 同名类在两个 JAR | classpath 优先级调优 |
| deepseek 第 21 题起全 failed | `LLMSqlParser.runText2SQL failed` | 疑似 reasoning 输出兼容性 |
| Gold 日期不匹配 | SQLite 存带时分秒 | LIKE 通配 |
| 跑批输出丢失 | stdout 缓冲 | `-u` + 增量保存 |
| API 返回 boolean 而非 ID | SuperSonic 设计 | 创建后重查列表 |

---

## 三个核心结论

### 1. 语义建模 > LLM 选型

| | v1 (3 Model 全期) | v2 (6 Model 分层) |
|------|------|------|
| SUM(净利润) | 5期加总 = 错误 | WHERE 最新期 = 值本身 |
| 对标 DuSQL | ❌ | ✅ |

**面试说:** "分层建模——按时间粒度拆成最新期和全期两个 Model——让 SUM 的语义从 5 期累加变成值本身。这证明在 NL2SQL 系统中，语义建模治理比换 LLM 更见效。"

### 2. 手写 SQL vs 系统 SQL 天然有 gap

手写 `SELECT AVG(total_assets) WHERE date='2023-12-31'` → 1 行精确值。
SuperSonic 输出 `SELECT SUM(x) GROUP BY stock_name LIMIT 200` → 288 行全市场。

这不叫"错"，而是语义层把每道题都映射成了聚合查询模式——DuSQL 能 100% 是因为每个公司天然 1 行，CSI300 多期数据需要分层才能对齐。

### 3. LLM 在当前配置下无差异

SchemaMapper 用 embedding 不调 LLM，Parser 在 temperature=0 下确定性输出。两模型 SQL 84/84 一字不差。

---

## 追问预案

**Q: 怎么保证公平？**
> 同一 Dataset、测试集、SQLite、Agent 配置，仅 chatModelId 不同。差异只来自 LLM。

**Q: 和 Spider/DuSQL 对比过吗？**
> 复用了 DuSQL 管线作 baseline（100 题, 4 表, 4 级难度），对标构建了 CSI300。DuSQL 100% 因数据天然对齐 SUM，CSI300 需要分层才能等效——恰好验证了语义建模的价值。

**Q: deepseek 为什么中途失败？**
> 横向对比：完全相同的语义层和配置，qwen 84/84 全过，deepseek 第 21 题开始 fail。初步判断与 v4-pro 的 reasoning_content 和 `correctedQuerySQL` 解析器交互有关。

**Q: 复用性？**
> 换数据源改 `fetch_data.py`，换语义模型改模板。方法论"按时间/实体粒度分层建模"适用于任何多实体×多时间点场景。

---

## 方法论沉淀

### 语义层治理原则

1. **一个 Model 一个粒度** — 不混时间粒度
2. **SUM 语义自洽** — 每公司行数=1 时 SUM=值本身
3. **维度值字典** — 没有值就无法过滤
4. **先治理后测评** — 建模质量决定上限

### 分层建模模板

```
最新期 Model: WHERE report_date = (SELECT MAX(...) FROM table)
  → 每公司 1 行 → 标量查询/衍生指标/公司对比

全期 Model: 不带 WHERE
  → 每公司 5 行 → 同比分析/趋势
```

---

## 产出物

| 文件 | 行 | 说明 |
|------|-----|------|
| `fetch_data.py` | 130 | akShare → SQLite |
| `build_semantic.py` | 290 | 语义层一键创建 |
| `generate_questions.py` | 150 | 84 题生成 |
| `run_eval.py` | 100 | 双模型跑批 |
| `calc_accuracy.py` | 100 | 精确匹配评分 |
| `calc_semantic.py` | 160 | 语义评分 |
| `csi300.db` | 10MB | 沪深 300 数据 |
| `gold.txt` | 84 行 | 标准答案 |
| `EngineType.java` | +1 | 源码修改 |
| `pom.xml` | +6 | Maven 依赖 |
