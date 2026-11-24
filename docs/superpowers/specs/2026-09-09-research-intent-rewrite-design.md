# 研究路由：本地 0.5B 分类 + default 外部改写

> 版本: v1.0 | 日期: 2026-09-09 | 状态: 待审查  
> 范围：Python 接单分类、worker 拼 prompt、SQLite 字段。不改 Java↔Python HTTP 契约。  
> 面试口径：[`02-集成设计-面试文档.md`](../../resume/interview/深度研究/02-集成设计-面试文档.md) §5.3 Q1/Q2；实现规格：[`02-集成设计.md`](../../resume/interview/深度研究/02-集成设计.md) §7.4–§7.6。

## 1. 背景

原先 IntentClassifier 一次远程 LLM 同时输出 `research_type` + `data_domain`，金融再按域拼 `domains/*.md`；`default` 只硬编码 prepend 约束。问题：

- 问数结果几乎都是表，领域标签容易猜错，错了还钉进 prompt。
- 分类挡在 200 前面，不该每次打远程大模型。
- 0.5B 适合三分类，不适合改句子。

## 2. 目标

1. 同步路径用本地 **Qwen2.5-0.5B-Instruct** 做三分类（约 50ms、<1GB 显存）。
2. 去掉 `data_domain` 列和 `domains/*.md` 路由。
3. `financial_analyst` / `academic`：原文 + 对应范式 md，不改写。
4. `default`：worker 用 **pipeline 同一套 chat API** 改写问句（短超时 20s），再拼 `default.md`。
5. 分类 / 改写失败不挡入队、不挡 pipeline；**只有 pipeline 超时或抛错才把同一行 UPDATE 成 `FAILED`**。

## 3. 数据流

```
POST /v1/research/jobs
  → FastAPI 进程内 0.5B 分类（整段 query，Java 已截断，Python 不再切）
  → INSERT PENDING（只存 research_type）→ 200

worker claim
  → default：chat API 改写（20s）失败则原文
  → academic / financial_analyst：不调改写
  → compose_task(type.md) → pipeline 14min
  → 成功：截断写 JSON，SQLite COMPLETED + report_uri
  → 超时/抛错：SQLite FAILED + error_msg，不写报告文件
```

## 4. 分类器

加载位置：**仅 FastAPI 进程**。worker 不加载 0.5B。

输入：请求体 `query` 原样（问题 + 表 + 解读）。截断权威在 Java（表 2000 / 解读 1000 / 整段 4000）。

模型 JSON：

```json
{"label": "financial_analysis" | "academy_research" | "default"}
```

落库映射：

| 模型 label | SQLite `research_type` |
| --- | --- |
| `financial_analysis` | `financial_analyst` |
| `academy_research` | `academic` |
| `default` | `default` |

System prompt（含「不确定则 default」，避免报表题全打成金融）：

```
你是一个文本分类器。你的任务是根据用户输入的自然语言内容，将其划分为以下三类之一：
- financial_analysis：与金融分析、市场数据、财务报表、投资分析等相关
- academy_research：与学术研究、论文、理论推导、实验设计、文献综述等相关
- default：不属于以上两类的其他内容

只有用户明确要走金融分析或学术研究范式时才输出前两类；看表算数、归因、解释问数结果但没有指定范式时，输出 default。不确定时必须输出 default。

你必须且只能输出一个合法的 JSON 对象，格式如下：
{"label": "financial_analysis" | "academy_research" | "default"}

不要输出任何额外文字、解释或标记。
```

失败（未加载 / 超时 / 非法 JSON / 未知 label）→ `default`，照常 INSERT 200。若模型包了 markdown 代码围栏，解析层剥掉再读。

## 5. 为什么删除 `data_domain`

分类器只决定研究方法论（三套范式），不猜杜邦 / 碳 / 五力。领域框架交给 14 分钟大模型。

`domains/*.md` 的「加文件零代码」会多一列、启动扫描、金融强制选域；0.5B 在报表上本就会偏金融，再猜领域更容易把错误片段钉进 prompt。也和「不确定走 default 再改写」打架。

SQLite 不再有 `data_domain`。GET 响应、报告 JSON 也不再带该字段。金融就一份 `financial_analyst.md`。加新研究风格 = 加 type md + 分类 label，不加领域列。

## 6. Worker 拼 prompt

| `research_type` | 行为 |
| --- | --- |
| `financial_analyst` / `academic` | 原文 `query` + 对应 md |
| `default` | 同一套 pipeline chat 客户端改写整段 `query` → 再拼 `default.md` |
| 改写超时 / 5xx / 空串 | 原文 + `default.md`，**不** UPDATE FAILED |

改写结果只进 `full_task`。报告 JSON 可留 `rewritten_query`（与原文不同才写），不回写 SQLite。

`REWRITE_TIMEOUT_S = 20`，禁止套用 14 分钟 pipeline 硬超时。

## 7. 失败面

| 故障 | SQLite | 报告文件 |
| --- | --- | --- |
| 分类失败 | `PENDING`（type=`default`） | 无 |
| 改写失败 | 仍 `RUNNING`，继续 pipeline | 无（尚未落盘） |
| pipeline 14min / 抛错 | **同一行 UPDATE `FAILED` + `error_msg`** | 不写 |
| 成功 | `COMPLETED` + `report_uri` | 写 JSON |

不要为失败再 INSERT 一行。

## 8. 测试

- label 三映射；非法 JSON → `default`
- schema / INSERT / GET 无 `data_domain`
- 金融 / 学术：改写 API 调用次数为 0
- `default`：会调 chat API；超时后仍进 pipeline
- 0.5B 不可用时 POST 仍 200 PENDING
- pipeline 超时：行状态 `FAILED`，无 report 文件

## 9. 非目标

- 不把 0.5B 做成独立 sidecar（worker 已不需要它）
- 不另配第二家改写模型
- 不改 Java POST body
- 不在本规格里实现 0.5B 量化细节（transformers / MLX 由实现选，约束是进程内、<1GB、~50ms）
