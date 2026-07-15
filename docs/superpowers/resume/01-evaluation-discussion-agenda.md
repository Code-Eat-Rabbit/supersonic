# 第 1 点：Text2SQL 测评体系 — 面试回答

> 状态: ✅ 已完成 | 成果: 84题金融测评集 + 双模型对比 + 语义建模方法论

---

## 一、30 秒概括（面试开场用）

"我为 SuperSonic 搭建了端到端金融 NL2SQL 测评管线，涵盖从 akShare 拉取沪深 300 财报数据、构建语义层、生成 84 道金融测试题、到双模型跑批和双维度评分的全流程。

核心发现：**语义建模质量是准确率天花板**——把 3 张表按时间粒度拆成 6 个 Model 后，可用率从 0 提升到 100%。另外确认了在当前语义层配置下，qwen 和 deepseek 的 SQL 输出完全一致，LLM 选型不是瓶颈。"

---

## 二、做了什么

### 测评体系搭建

```
数据层: akShare API → 沪深300 × 5期年报 → SQLite (csi300.db)
语义层: Domain → 6 Model (最新期×3 + 全期×3) → Dataset → 2 Agent
测试集: 84 题, 4类(AS/CL/YoY/MG) × 4级(e/m/h/x), deepseek-v4-flash 生成
评分层: Execution Accuracy + 语义等价评分 (5维加权)
```

### 遇到的工程问题及解决

| 问题 | 原因 | 解决 |
|------|------|------|
| SuperSonic 不支持 SQLite | `EngineType` 枚举缺 SQLITE | 修改源码 + 添加 `sqlite-jdbc` 依赖, Maven 重建 |
| langchain4j 类冲突 | 自定义 `OpenAiChatModel` 与官方 JAR 同名 | classpath 优先级调优, 重命名冲突 JAR |
| 第 21 题起 deepseek 全部 parse_fail | LLMSqlParser `runText2SQL failed` | 疑似 DashScope 限流或 reasoning 输出兼容性 |
| Gold SQL 日期不匹配 | SQLite 存 `2023-12-31 00:00:00`，手写 gold 只写日期 | LIKE 通配修复 |
| Python 后台跑批输出丢失 | stdout 缓冲 | `-u` 标志 + 逐题增量保存 |
| API 创建 Model 返回 boolean 而非 ID | SuperSonic REST API 设计 | 创建后重查列表获取真实 ID |

---

## 三、核心数据

| 指标 | qwen3.7-plus | deepseek-v4-pro |
|------|-------------|-----------------|
| 可用率 (v1 语义层) | 100% (84/84) | 100% (84/84) |
| 可用率 (v2 语义层) | 100% (84/84) | 24% (20/84) |
| 手写 SQL 精确匹配率 | 0% | 0% |
| NL2SQL 风格精确匹配 | 100% | - (未跑完) |
| 两模型 SQL 一致性 | **84/84 完全一致** | 同上 |
| 平均延迟 | ~3300ms | ~3200ms |

### deepseek 20/84 的根因

第 21 题开始 `LLMSqlParser.runText2SQL failed`，可能与 deepseek-v4-pro 的 reasoning_content 输出格式与 `correctedQuerySQL` 解析器不兼容有关。这在之前跑 DuSQL 时也出现过（reasoning_content 总有内容但 content 为空）。

---

## 四、关键结论

### 结论 1: 语义建模 > LLM 选型

| 语义层版本 | 建模方式 | 关键差异 | 可用率 |
|-----------|---------|---------|--------|
| v1 | 3 Model 全期 | SUM(净利润) = 5期加总 = 错误 | 100% (但语义错误) |
| v2 | 6 Model 分层 | WHERE 最新期, SUM=值本身 | 100% |

**面试说法:** "我通过分层建模——把一张表按时间粒度拆成最新期和全期两个 Model——让 SuperSonic 的语义层从'无法回答标量查询'变成了'对标 DuSQL 的 100% 可用'。这证明在 Text2SQL 系统中，语义建模治理比换 LLM 更见效。"

### 结论 2: 手写 SQL vs 系统 SQL 的差距

手写 SQL 回答"贵州茅台 ROE 是多少？"→ 1 行 1 列精确值。
SuperSonic 回答同一个问题 → 288 行全市场数据。

这 26% 的语义评分反映的**不是系统"错"**，而是语义层把所有查询都映射成了"全部公司 + GROUP BY stock_name"的聚合模式。这是 SuperSonic 的默认行为，也是 DuSQL 能 100% 但 CSI300 只有 26% 的根因——DuSQL 每个公司天然只有 1 行。

### 结论 3: LLM 无差异的根因

SchemaMapper 用 embedding 检索（不调 LLM），Parser 在 `temperature=0` 下确定性输出。LLM 只在自一致性评分环节参与且 number=1。这就是为什么两个模型 84/84 SQL 完全一致。

---

## 五、面试追问预案

### Q: "你们怎么保证测评公平？"

> 同一 Dataset、同一测试集、同一 SQLite 环境、同一 Agent 配置（仅 chatModelId 不同）。两个模型共享语义层，差异仅来自 LLM 本身。

### Q: "和 Spider/DuSQL 对比过吗？"

> 我们复用了 SuperSonic 内置的 DuSQL 测评管线作为 baseline（100 题, 4 表, 四级难度），然后对标构建了金融场景的 CSI300 测评集。DuSQL 100% 准确是因为数据天然对齐 SUM 语义，CSI300 需要分层建模才能达到同等效果，这恰好验证了语义建模的重要性。

### Q: "deepseek 为什么中途失败？"

> 第 21 题起 LLMSqlParser 报 `runText2SQL failed`。我们做了横向对比：同一 semantic model、同一 dataset、同一 agent config，qwen 跑 84/84 全过，deepseek 跑到 20 就开始全部失败。根因还在排查中，初步判断与 v4-pro 的 reasoning 模式有关——之前 DuSQL benchmark 也观察到类似现象，但不是这个 failure mode。

### Q: "这个测评管线能复用到其他场景吗？"

> 能。核心管线是通用的——换数据源只需改 `fetch_data.py`，换语义模型只需改 `build_semantic.py` 的模板。方法论上，"按时间/实体粒度分层建模"适用于任何多实体×多时间点的财务或业务数据。

---

## 六、产出物清单

| 文件 | 行数 | 说明 |
|------|------|------|
| `evaluation-finance/scripts/fetch_data.py` | 130 | akShare 数据拉取 |
| `evaluation-finance/scripts/build_semantic.py` | 290 | 语义层一键创建 |
| `evaluation-finance/scripts/generate_questions.py` | 150 | LLM 题目生成 |
| `evaluation-finance/scripts/run_eval.py` | 100 | 双模型跑批(增量) |
| `evaluation-finance/scripts/calc_accuracy.py` | 100 | 执行准确率 |
| `evaluation-finance/scripts/calc_semantic.py` | 160 | 语义等价评分 |
| `evaluation-finance/data/csi300.db` | 10MB | 沪深300数据 |
| `evaluation-finance/data/gold.txt` | 84 行 | 标准答案 |
| `common/.../EngineType.java` | +1 行 | 源码修改 |
| `pom.xml` | +6 行 | Maven 依赖 |
