# Review: SuperSonic 全面测评方案设计

> **Reviewer**: Claude Code | **日期**: 2026-07-14
> **文档**: `docs/superpowers/specs/2026-07-14-supersonic-benchmark-design.md`
> **结论**: **有条件通过 (Conditional Pass)** — 方案方向正确、结构清晰,但在**方法论严谨性、技术可行性、评测效度**三方面存在需要修正的问题后方可实施。

---

## 总评

这是一份面向"面试可量化展示"目标的三维测评方案,定位务实。框架设计(模型对比 / 数据量 / 治理层级)切中 SuperSonic 语义建模的核心卖点,Level 0→2 的治理对比尤其有讲故事的价值。

但作为"可复现、可对比"的 benchmark 设计,文档存在若干**威胁内部效度(internal validity)**的方法论漏洞,以及若干**被代码现状证伪的技术假设**。下面按严重程度分级列出。

---

## 🔴 Blocker 级问题(必须在实施前解决)

### B1. API 密钥明文写入设计文档 — 安全合规问题

**位置**: §3.2 配置参数,第 45 行

```
apiKey: sk-5956cac478a5429c94d3dadfaa418245  # AES/ECB 加密后写入 DB
```

**问题**:
- 这是一个**真实可用的 DashScope API Key**,以明文形式提交到 git 仓库。注释虽写了"AES/ECB 加密后写入 DB",但 key 本身已泄露。
- 即使后续删除,git 历史仍会保留。
- 现有 `build_models.py:45` 的 `encrypted_key = "Q+oQ..."` 是加密后的形态,说明项目本就在遵循"只提交加密态"的约定,本设计文档破坏了这一约定。

**建议**:
1. **立即作废该 key**(在 DashScope 控制台 revoke + 重新生成)。✅ **已修复**: 规格文档 v2 已替换为占位符，用户需在 DashScope 控制台手动 revoke。
2. 文档中将该字段改为占位符 `${DASHSCOPE_API_KEY}`。✅ 已修复。
3. 在 `.gitignore` 或 pre-commit hook 中加 `git-secrets` / `trufflehog` 扫描,防止再次发生。

---

### B2. 评测效度根本性缺陷:Execution Accuracy 在不存在 gold 结果集的情况下被默认判错

**位置**: `build_pred_result.py:40` 的 `default_sql="select * from tablea "`

**问题**: 这是现有脚本的已有缺陷,但**三维测评方案直接复用 `get_pred_result()` 而未修复**,会系统性地影响三个维度的所有准确率数字:

- 当 SuperSonic 返回 None(解析失败)或抛异常时,`get_pred_sql` 返回 `select * from tablea`。
- `evaluation.py:617 eval_exec_match` 会把这个占位 SQL 拿去 sqlite 执行,因 `tablea` 不存在而抛异常 → `result["equal"]=False`。
- 这本身"恰好"是对的(解析失败=错),但**无法在最终报告里区分**"模型答错"与"服务超时/解析失败"两种情况。

对**模型对比维度**的影响尤为严重:DeepSeek/GLM 的 reasoning 模型更易 timeout,其准确率会被系统性低估,而 Qwen 可能因"答得快但答错"被高估。

**建议**:
1. 在 `build_pred_result.py` 中为每条查询记录 `status` 字段:`ok / parse_fail / timeout / exception`。
2. `benchmark_report.json` 中**分层报告**准确率:只在 `status==ok` 的子集上计算"纯模型准确率",另报告"端到端可用率"。
3. 面试叙事时区分"模型能力上限"与"系统可用性",二者不是一回事。

---

### B3. 维度二/三缺少 gold SQL,无法计算 Execution Accuracy — 文档未提及

**问题**: 现有 DuSQL 评测依赖 `data/gold_example_dusql.txt` + `data/internet.db`(已有 gold 结果集)。但:

- **维度二**(akShare 财务数据)和**维度三**(同数据不同治理层级)都是**新数据集**,文档完全没有说明:
  - gold SQL 从哪来?(人工标注?LLM 生成 + 人工校验?)
  - 没有 gold 就无法跑 `eval_exec_match`,所谓"SQL 准确率 ~60-80%"的预期数字(§5.3)无法落地。

- §5.4 只说"跑相同查询集,对比映射成功率 + SQL 准确率",但"查询集"和"gold"均未定义。

**建议**: 补一节 §5.5 "Gold 标注方案":
- 规模: 维度二/三各 30-50 条人工标注 SQL(不需要 DuSQL 的 100 条规模)。
- 标注流程: 1 人写 + 1 人交叉验证,记录 disagreement。
- 或者降级为"人工评判查询结果正确性"(适合维度三的治理对比,因为重点不是 SQL 文本而是"答对没")。

---

## 🟠 Major 级问题(影响结果可信度)

### M1. DashScope "compatible-mode" 不保证三模型可比 — 对照实验变量未控制

**位置**: §3.1

**问题**: 文档声称三模型"统一走 DashScope compatible-mode API"以保证可比性,但这只控制了**网络层**变量,**模型行为层**差异未控制:

- DeepSeek V4 Flash "总是有 reasoning_content",GLM-5.2 "重度 reasoning" — 这意味着后两者实际消耗的 prompt + reasoning token 远高于 Qwen,而 `temperature=0.0` 并不能消除 reasoning 带来的随机性。
- 三模型可能对 `temperature=0` 的实际实现不同(有些模型在 temp=0 时仍因 batching 引入微小抖动)。

**建议**:
1. **每个查询跑 3 次**,报告准确率的 mean ± std,而非单次结果。面试时"三模型差异在统计上是否显著"比"谁高 2 个点"更可信。
2. 报告 **reasoning token 单独列项**,并在成本对比中区分"输出有效 content token"与"reasoning 开销"。
3. 文档中明确写清:"本对比是**端到端服务能力对比**,包含 reasoning 开销,而非纯模型推理能力对比"。

---

### M2. 模型切换"不重启服务"方案的技术细节未验证,且可能引入状态污染

**位置**: §3.5 "不重启服务,通过切换 Agent 的 `chatModelId` 轮换模型"

**代码核查结果**:
- `AgentController` 只有 `POST`(create)、`PUT`(update)、`DELETE`,**没有专门的 switch endpoint**。
- `build_models.py:343 build_agent` 在创建 Agent 时把 `chatModelId` 写进 `chatAppConfig`。
- NL2SQLParser 通过 `ModelProvider.getChatModel(ModelConfigHelper.getChatModelConfig(chatApp))` 取模型,配置走缓存。

**潜在问题**:
1. **缓存污染**: 切换 `chatModelId` 后,`ModelProvider` / `ModelConfigHelper` 是否立即失效缓存?文档没提。如果走缓存,你以为切了模型其实没切。
2. **并发污染**: 如果三维测评在同一 Agent 上轮换,前一个模型的请求若因 reasoning 慢尚未返回,可能串到下一个模型的统计窗口里。
3. **三模型对应三个 ChatApp key 还是同一个?** 文档没说。如果共用一个 key,切换逻辑就是"改一个字段";如果是三个 key,编排更复杂。

**建议**:
1. 实施前先用 `/api/chat/agent/getAgentList` + PUT 验证:`switch_agent_model(agent_id, new_model_id)` 后,下一次 `/api/chat/query/parse` 确实走了新模型(可通过 traceId + 响应延迟差异快速验证)。
2. 切换后**强制 sleep + 发 1 条 warmup 查询**(不计入统计)冲刷缓存。
3. **更稳妥的替代方案**: 创建 3 个独立 Agent(`agent_qwen` / `agent_deepseek` / `agent_glm`),各自绑死模型,串行跑。 avoids 状态污染,代价只是多 2 个 Agent 记录。

---

### M3. 维度二"数据量测试"的指标定义把"建模"和"查询"混为一谈

**位置**: §4.4

**问题**: 表格中 4 个指标分属两个完全不同的系统层:

| 指标 | 实际测的是 |
|------|-----------|
| 建模耗时 | SuperSonic **元数据层** 性能(创建 Model/Dimension/Metric) |
| 映射成功率 | **Schema Mapper + Embedding** 检索能力 |
| SQL 生成延迟 | **LLM 推理** 性能(主导因素是模型不是数据量) |
| 失败临界点 | **JVM / DB 连接池 / 内存** 层 |

文档把"数据量"作为单一变量,但 100 家公司 × 3 表 = 300 张表的数据量增长,**对这 4 个指标的影响机制完全不同**:
- 建模耗时基本线性增长(合理)。
- SQL 生成延迟主要由 LLM 主导,与数据量**几乎无关**(LLM 看到的是 schema 不是行数据)。
- 映射成功率会因 schema 膨胀而下降(这才是真正有趣的信号)。
- 失败临界点取决于 MetaData 是否走分页/缓存。

**建议**:
1. 把 §4.4 拆成两组指标:
   - **元数据层**: 建模耗时、Schema 加载时间、`getModelList` API 延迟。
   - **查询层**: 映射成功率、映射延迟(分 embedding 检索 vs LLM 生成两段计时)。
2. 明确假设:"数据量增长对 LLM 生成延迟无显著影响,对映射成功率有负向影响"。这样面试时能讲清"我测出了什么因果关系"。

---

### M4. Level 0/1/2 预期数字(§5.3)是凭空估计,会被自己测出的数据打脸

**位置**: §5.3

```
              Level 0    Level 1    Level 2
映射成功率     < 20%      ~50-70%    > 90%
SQL 准确率     ~0%        ~30-50%    ~60-80%
```

**问题**:
- 这些区间没有任何依据(未引用 FinVerBench 或其他来源),纯属"拍脑袋"。
- 如果实测结果落在区间外(完全可能),文档的"预期"就成了负资产 — 面试官会问"为什么你预期 60-80% 实际只测出 40%?"。
- Level 0 "SQL 准确率 ~0%" 过于绝对:即使列名是英文编码,LLM 凭训练知识也可能蒙对简单聚合。

**建议**:
1. 删掉具体数字,改为**定性假设**:
   - "Level 0 → 1 → 2 映射成功率单调递增"。
   - "Level 2 在多表 JOIN 查询上显著优于 Level 0/1"。
2. 或者保留数字但明确标注"待验证的工作假设(prior),以实测为准"。
3. 面试叙事时把"我的 prior 与实测的差距"本身作为亮点:"我发现治理 ROI 在 X 类查询上低于预期,原因是 Y"。

---

## 🟡 Minor 级问题(优化项)

### m1. 100 条 DuSQL 样本量偏小,分难度后 cell 过少

§3.3 用 100 条,分 4 级难度后 easy 可能只有 20-30 条。再分模型 × 难度 = 12 个 cell,每 cell 平均 8 条,**单条查询的准确率波动就是 ±12%**。

**建议**: 在 `benchmark_report.json` 中给每个准确率数字附 `n` 和 95% 置信区间(Wilson interval),面试时"60% ± 11%"比"60%"专业得多。

### m2. §6 项目产出的 `benchmark.sh` 与 §3.5 的新增文件路径不一致

§3.5 写 `evaluation/benchmark.sh`,§6 写 `evaluation/benchmark.sh`(一致),但 §3.6 的输出文件路径未指定目录。建议统一约定 `evaluation/output/<timestamp>/`。

### m3. 风险表(§7)遗漏关键风险

补充:
- **SuperSonic 版本 drift**: 当前 master 已有 modified 文件(NL2SQLParser 等),benchmark 结果受具体 commit 影响。建议记录 git commit hash。
- **DashScope 限流**: 三模型 × 100 条 = 300 次调用,若并发可能触发 QPS 限制。现有 `build_pred_result.py:79` 是 `time.sleep(3)`,需在多模型场景下重新评估。
- **akShare 字段稳定性**: akShare 接口字段可能随上游变动,建议固定一个 snapshot 日期并在脚本中校验字段存在性。

### m4. 缺少"结果可复现性"checklist

面试场景下"可复现"是核心卖点。建议补一节 §8:
- [ ] git commit hash 记录
- [ ] Python venv 锁定(`.venv312` 已存在,补 `requirements.txt` freeze)
- [ ] SuperSonic Docker 镜像 tag
- [ ] DashScope 模型版本(模型可能静默升级,建议每次跑完记录模型返回的版本字段)

---

## 结构性建议

### 关于"三维"框架本身

三个维度的**优先级**建议重新排序,以**ROI(面试叙事价值 / 实施成本)**排序:

| 维度 | 叙事价值 | 实施成本 | ROI |
|------|---------|---------|-----|
| 维度一 模型对比 | 中(业内已卷烂) | 低(改现有脚本) | 中 |
| 维度三 治理对比 | **高(SuperSonic 独有)** | 中(需 gold 标注) | **高** |
| 维度二 数据量 | 低(偏 SRE,偏离 LLM) | **高(akShare 数据工程重)** | 低 |

建议:**先做维度三**(最能体现"你理解 SuperSonic 的语义层价值"),**再做维度一**(作为 baseline),**维度二降级为可选**(时间允许再做 5→20 家的两轮即可,不必到 100 家)。

### 关于"基于 FinVerBench 方法论"的定位

§1 声称"基于 FinVerBench (Panda, 2026) 方法论",但查阅 `references/FinVerBench.md` 后发现:

- FinVerBench 是**财务报表一致性验证(verifcation)** benchmark,任务定义是"检测注入的数值错误"。
- 本方案的三个维度**都不是 verification 任务**:维度一是 Text2SQL,维度二是容量,维度三是治理 ROI。
- 真正借用的只是"三大报表(BS/IS/CFS)的数据结构"和"controlled perturbation"的思想(体现在 Level 0/1/2)。

**建议**:把措辞从"基于 FinVerBench 方法论"改为"参考 FinVerBench 的财务报表数据结构与受控对比思想",避免面试官追问"你和 FinVerBench 的对应关系是什么"时露馅。

---

## 修改清单(Checklist)

实施前必须解决:
- [ ] **B1** 作废泄露的 API key,文档改占位符
- [ ] **B2** `build_pred_result.py` 增加 status 字段,报告分层准确率
- [ ] **B3** 补写维度二/三的 gold 标注方案

实施时建议解决:
- [ ] **M1** 每查询跑 3 次,报告 mean ± std + reasoning token 单列
- [ ] **M2** 验证模型切换缓存失效,或改用 3 个独立 Agent
- [ ] **M3** §4.4 指标拆"元数据层 / 查询层"两组
- [ ] **M4** §5.3 预期数字改为定性假设或标注 prior

可选优化:
- [ ] **m1** 报告 Wilson 置信区间
- [ ] **m3** 补充版本 drift / 限流 / akShare 字段风险
- [ ] **m4** 加可复现性 checklist
- [ ] 调整三维度优先级:三 > 一 > 二
- [ ] 修正"基于 FinVerBench 方法论"措辞

---

## 结语

方案的方向(SuperSonic 三维测评)**值得做**,Level 0→2 的治理对比是真正的亮点。但当前文档更接近"一份想法大纲",距离"可复现 benchmark 设计"还差一层方法论严谨性。建议先解决 B1-B3 三个 blocker,再补 M1-M4 的方法论加固,产出才能在面试中经得起追问。
