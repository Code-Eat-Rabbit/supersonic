# 任务 5 执行报告

- **状态：** 已完成
- **实现：** 修正 `docs/resume/interview/深度研究/05-工程化能力.md` 中 `tool_calls_exceeded` 与简历并发口径，对齐 `03` 诚实模板与 `miro-flow-solution` 标本代码。
- **未改范围：** `my_resume.md`、02/03/04 及其他业务代码。

---

## 1. `tool_calls_exceeded` 核对

**标本路径：** `config/agent_llm_qwen37plus.yaml` → Main/Sub 均为 `GPTOpenAIClient`。

**orchestrator（`orchestrator.py` L1116–1122 / L701–707）：**
- 计算 `tool_calls_exceeded = len(tool_calls[0]) > max_tool_calls`
- 超限时 `logger.warning(...)`，执行循环仅切片 `[:max_tool_calls]`
- 调用 `update_message_history(..., tool_calls_exceeded)`

**GPTOpenAIClient（`gpt_openai_client.py` L252–266）：**
- 签名接受 `tool_calls_exceeded: bool = False`
- 实现**完全忽略**该参数，只追加已执行 tool result 到 history

**对照：** `gpt5_openai_client.py` 等 provider 会在 `tool_calls_exceeded=True` 时写入说明文本，但 qwen 复习标本未使用该路径。

**文档修正：**
- §1.3 诚实边界新增「单轮截断」行
- §3.3.2 重写：截断 + warning + 客户端忽略参数 + 代码摘录
- §3.3.3 对照表「触发结果」列更正
- §3.8 面试说法、§3.9 易踩坑同步

---

## 2. 简历并发口径对齐

**对齐来源：** `03-Main-Sub-Agent编排.md` §9.3 分层诚实模板。

**文档修正（§3.7）：**
- 标题扩展为「并发 / 子智能体并发」
- 增加四层对照表：架构能力 / 当前标本 / 业务落地 / 已落地并行
- 可背话术点明：**不可把标本说成已 `gather`**
- §3.8 面试说法改为分层答法

---

## 自检

| 检查项 | 结果 |
|--------|------|
| 不说模型一定能看见超限提示 | ✅ |
| qwen 标本 `GPTOpenAIClient` 忽略 `tool_calls_exceeded` | ✅ |
| 简历并发分层答 + 不可说成已 gather | ✅ |
| 未改 `my_resume.md` | ✅ |
| 仅改 `05-工程化能力.md` + 本报告 | ✅ |

---

**Commit：** `d552a936f`（`docs: fix tool_calls_exceeded and resume concurrency honesty`）
