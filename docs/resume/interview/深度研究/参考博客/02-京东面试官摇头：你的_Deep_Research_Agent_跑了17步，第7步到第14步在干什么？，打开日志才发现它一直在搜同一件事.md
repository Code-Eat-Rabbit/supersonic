原创 吴师兄 _2026年6月16日 10:01_

大家好，我是吴师兄。

上一篇我们把最小 ReAct（推理与行动，Reasoning and Acting）循环跑通了，一个能循环调用工具、直到判断信息够了才输出答案的 Agent。末尾我提了一个问题：当任务复杂到需要搜索10轮以上，上下文会线性膨胀，模型对早期找到的信息注意力下降，甚至开始混淆不同来源的数据。

今天就在这个基础上，把 ReAct 从"能跑"推到"能用"之间那几道绕不过去的坎填掉。

上周有个学员去京东面大模型应用岗。简历上写了"主导 Deep Research Agent 开发，已上线"。面试官扫了一眼，开口问：

"上线了，那你告诉我，上线之后遇到过什么问题？"

他说："搜索偶尔会超时，我们加了重试机制。"

面试官点了点头，继续问："重试几次？等待多久？如果搜索引擎不是超时，而是返回了一个空结果，你的重试逻辑一样吗？"

他停了一下："差不多，都是重试一下……"

面试官换了个方向："那你的 Agent 有没有出现过死循环？连续十几步搜的是同一件事，或者极其相近的关键词，这种情况你们有监控吗？"

他想了想，说没有专门检测过，但"应该"不会发生。

面试官没有评价这个"应该"，只说了一句话："工具能调通是 Demo。工具调稳才是产品。你现在回答不上来的这几个问题，正好就是这两者之间的距离。"

面试之后这个学员找到我，他说："我以前觉得自己的系统挺好的，这才意识到，我根本没有在意它出过什么问题。"

今天把这段距离走完：让 ReAct 能在真实生产环境里稳定运行。

上一篇已经有了基础的 try/except，这篇要做的是三件事，① **分级处理工具失败** ，② **检测并打破重复搜索循环** ，③ **主动管理 token 预算** 。跑完这三件事，你手里会有一个可以接生产流量的 ReAct 执行器。

## 一、工具失败不是"抛了个异常"这么简单

说工具失败处理，很多人想到的就是：加 try/except，失败了重试，没问题。

这解决了最表面的一层，漏掉了更危险的情况。

工具失败有两种形态。一种是显式的：抛了异常，你能发现、能处理。另一种是无声的：工具调用成功返回了，返回的却是垃圾。后者麻烦得多，因为你不知道出了问题，模型还在基于错误的信息往下推理。

我们在内测阶段遇到过一个真实案例。一个用户问某上市公司的2023年财报数据，Agent 开始执行，前6步顺利找到了行业背景。第7步，搜索返回了一个内容付费网站，整页都是登录提示，"请订阅后查看完整财报"。没有任何异常被抛出，这个登录页被完整地送进了 Observation。

接下来发生的事情很奇特：模型"看见"了一个说"请登录"的页面，开始推理自己应该怎么"绕过"这个限制，换了各种关键词继续搜。步骤7到14，8步里有6步都是"某公司财报 PDF 下载"、"某公司年度报告 免费"之类的变体。每次搜索结果都差不多，模型陷入了循环。

整个任务跑了18步才超时停下，最后的报告是胡说八道。我们排查了很久，才在日志里发现步骤7那次搜索返回的东西。

工具失败要分三类来处理，每一类的处理逻辑完全不同。

```
import asyncio
 import time

 class ToolResult:
     def __init__(self, content: str, status: str, error_type: str = None):
         self.content = content
         self.status = status        # "ok" / "retry" / "skip" / "degrade"
         self.error_type = error_type

 async def execute_tool_safe(tool_name: str, tool_fn, **kwargs) -> ToolResult:
     """
     分级工具执行：区分超时/空结果/垃圾内容三种失败，
     对每种情况给出不同的处理建议，而不是统一重试
     """
     # ── 第一类：超时/网络异常 → 指数退避重试，最多3次 ──────────────
     # 为什么要指数退避（1s, 3s, 9s）而不是固定间隔？
     # 超时通常是服务器压力大导致的，固定间隔重试会在同一时间段内继续打压，
     # 指数退避给服务器时间恢复，重试成功率高很多
     for attempt in range(3):
         try:
             result = await asyncio.wait_for(
                 tool_fn(**kwargs),
                 timeout=10.0
             )
             break
         except asyncio.TimeoutError:
             if attempt == 2:
                 return ToolResult(
                     content="[搜索超时，建议换一个更简短的关键词重试]",
                     status="retry",
                     error_type="timeout"
                 )
             await asyncio.sleep(3 ** attempt)  # 1s, 3s, 9s
         except Exception as e:
             # 非超时的硬错误：不重试，直接上报
             return ToolResult(
                 content=f"[工具调用出错：{type(e).__name__}，请调整参数后重试]",
                 status="skip",
                 error_type="hard_error"
             )

     # ── 第二类：空结果 → 不重试，换关键词 ─────────────────────────
     # 为什么空结果不重试？
     # 重试同一个关键词只会得到同样的空结果，纯粹浪费步数。
     # 正确做法是告知模型"没搜到"，让它自己决定换个角度
     if not result or len(result.strip()) < 50:
         return ToolResult(
             content=f"[当前关键词未找到有效结果，请尝试换一种表述方式或拆分为更小的子问题]",
             status="skip",
             error_type="empty_result"
         )

     # ── 第三类：内容质量检查 → 过滤垃圾，不把垃圾传给模型 ─────────
     # 为什么要主动过滤，而不是把结果直接传给模型让它自己判断？
     # 因为"登录页面"、"404页面"在语义上和正常内容很相似，
     # 模型不一定能识别出来，会把垃圾当信息使，导致后续推理全部跑偏
     content_flags = _check_content_quality(result)
     if content_flags["is_garbage"]:
         return ToolResult(
             content=f"[页面内容无法提取（{content_flags['reason']}），请尝试其他来源]",
             status="skip",
             error_type=f"garbage_{content_flags['reason']}"
         )

     return ToolResult(content=result, status="ok")

 def _check_content_quality(content: str) -> dict:
     """检测常见的垃圾内容模式"""
     content_lower = content.lower()

     # 登录墙检测
     login_signals = ["please log in", "sign in to continue", "请登录", "订阅后查看", "会员专享"]
     if any(s in content_lower for s in login_signals):
         return {"is_garbage": True, "reason": "login_wall"}

     # 空页面/404检测
     if len(content.strip()) < 100:
         return {"is_garbage": True, "reason": "too_short"}

     # 广告页检测（内容里超过30%是URL）
     url_count = content.count("http")
     word_count = len(content.split())
     if word_count > 0 and url_count / word_count > 0.15:
         return {"is_garbage": True, "reason": "ad_page"}

     return {"is_garbage": False, "reason": None}
```

有了分级处理，模型收到的反馈就变得有意义了，不再是一个原始的堆栈报错，也不再是一堆登录提示，而是一句明确的"建议"：换关键词、换来源、或者换一种拆问方式。模型能理解这类提示，通常能自己调整过来。

加了这个之后，我们测试集上因为工具返回垃圾内容、导致模型推理方向跑偏（比如把"请登录"页面当成正文、转头去研究怎么绕过登录）的比例，从11%降到了3%以内。

光加 try/except 是不够的。你还要主动过滤返回内容的质量，把"没搜到"和"搜到了垃圾"分开，给模型不同的处理建议。

## 二、重复搜索：比死循环更难发现的问题

处理了工具失败，再说更难发现的问题：重复搜索。

它不报错，也不停，步数一直在涨，但没有一步在推进任务。模型一直在"努力工作"，换着关键词搜同一个东西，离答案却没有更近。

这个问题隐蔽，因为从外面看不出来，日志里有很多搜索记录，Agent 在"运行"，没有报错，就是不给出答案。

字符串完全匹配没用，因为模型每次会换一两个词，但意思完全一样。我们需要用 embedding 相似度来检测。

```
import numpy as np

 class LoopDetector:
     def __init__(self, window: int = 5, threshold: float = 0.88):
         # window：检测最近几次搜索是否有重复
         # threshold：相似度超过这个值，判定为重复
         # 0.88 是我们测试下来的经验值：太低会误报（"固态电池"和"锂电池"本来就相似），
         # 太高又漏报（"苹果2023财报 PDF"和"Apple annual report 2023"相似度约0.86）
         self.window = window
         self.threshold = threshold
         self.history: list[dict] = []  # {"query": str, "embedding": np.array, "result_quality": str}

     def check(self, new_query: str, new_embedding: np.ndarray) -> dict:
         """
         检查新的搜索词是否和最近的搜索重复
         返回：{"is_loop": bool, "hint": str}
         """
         if len(self.history) < 2:
             self._record(new_query, new_embedding, "unknown")
             return {"is_loop": False, "hint": ""}

         recent = self.history[-self.window:]
         similarities = [
             float(np.dot(new_embedding, h["embedding"]) /
                   (np.linalg.norm(new_embedding) * np.linalg.norm(h["embedding"]) + 1e-9))
             for h in recent
         ]
         max_sim = max(similarities)
         most_similar_idx = similarities.index(max_sim)

         if max_sim > self.threshold:
             # 找到了高度相似的历史搜索，分析当时的结果质量
             past_quality = recent[most_similar_idx]["result_quality"]
             hint = self._generate_hint(past_quality, recent[most_similar_idx]["query"])
             return {"is_loop": True, "hint": hint}

         self._record(new_query, new_embedding, "unknown")
         return {"is_loop": False, "hint": ""}

     def mark_result_quality(self, quality: str):
         """记录最近一次搜索的结果质量，供下次循环检测使用"""
         if self.history:
             self.history[-1]["result_quality"] = quality

     def _generate_hint(self, past_quality: str, past_query: str) -> str:
         """根据上次失败原因，给出针对性的提示"""
         # 为什么不直接说"你重复了"，要分情况说"因为什么原因"？
         # 模型接收到"你重复了"时，倾向于继续搜附近的词（微调关键词）；
         # 如果告知"上次这个方向搜不到"，模型更容易真正换角度
         if past_quality == "empty_result":
             return f"检测到重复搜索：'{past_query}'方向之前已经搜索过，未找到有效结果。请从完全不同的角度切入，例如换成对立面、上位概念或具体案例来源。"
         elif past_quality == "garbage":
             return f"检测到重复搜索：'{past_query}'方向返回的是无效内容（登录墙/广告页）。建议直接访问可信来源（如官网、权威媒体）的具体URL，而非继续关键词搜索。"
         else:
             return f"检测到重复搜索：已有相似检索，结果大概率相同。请重新梳理当前的信息缺口，从子问题出发设计搜索词，而不是重复大范围搜索。"

     def _record(self, query, embedding, quality):
         self.history.append({"query": query, "embedding": embedding, "result_quality": quality})
         if len(self.history) > 20:  # 只保留最近20条，不无限增长
             self.history.pop(0)
```

把 LoopDetector 接入 ReAct 循环，在每次生成工具调用之前先过一遍：

```
async def react_loop_prod(user_query, llm, tools, embedder, max_steps=15):
     messages = [
         {"role": "system", "content": SYSTEM_PROMPT},
         {"role": "user", "content": user_query}
     ]
     loop_detector = LoopDetector()
     token_budget = TokenBudget(max_tokens=28000)  # 下一节介绍

     for step in range(max_steps):
         response = await llm.chat_async(messages=messages, tools=list(tools.values()))

         if not response.tool_calls:
             return response.content  # 模型认为信息够了，输出答案

         tool_call = response.tool_calls[0]
         tool_name = tool_call.function.name
         tool_args = json.loads(tool_call.function.arguments)

         # 只对搜索类工具做重复检测（Visit/Python工具不检测，语义不适用）
         if tool_name == "search":
             query_text = tool_args.get("query", "")
             query_emb = await embedder.embed(query_text)
             loop_check = loop_detector.check(query_text, query_emb)

             if loop_check["is_loop"]:
                 # 不执行工具，把提示注入进去，让模型自己调整策略
                 messages.append(response.to_message())
                 messages.append({
                     "role": "tool",
                     "tool_call_id": tool_call.id,
                     "content": loop_check["hint"]
                 })
                 continue  # 跳过工具执行，直接进下一步让模型重新决策

         # 执行工具（带分级失败处理）
         tool_result = await execute_tool_safe(tool_name, tools[tool_name], **tool_args)

         # 记录结果质量，供下次循环检测使用
         if tool_name == "search":
             loop_detector.mark_result_quality(tool_result.error_type or "ok")

         messages.append(response.to_message())
         messages.append({
             "role": "tool",
             "tool_call_id": tool_call.id,
             "content": tool_result.content
         })

     return _force_conclude(messages)  # 到达步数上限，强制输出已有内容
```

![重复搜索检测：死循环 vs 自动跳出](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

重复搜索检测：死循环 vs 自动跳出

加了重复检测之后，我们测试集里平均每次研究任务的有效步骤比例从73%提升到了91%，之前将近1/4的步骤是在原地打转，现在基本上每步都在推进任务。

系统上线后，先把每次任务的搜索词日志打出来，肉眼看一下有没有重复的模式。通常你会发现比预想的多得多。

## 三、token 预算：要在"溢出前"处理，不是"溢出后"

第一篇讲了 ReAct 的上下文会线性膨胀，10步后可能到三四万 token，模型对早期内容的注意力会下降。今天说的不是怎么根本性地解决这个问题（那是下一篇 IterResearch 的内容），而是在现有 ReAct 框架里，怎么用 token 预算管理来推迟这个问题、降低它的影响。

处理 token 的时机要前移：不是等上下文撑满了才动手，而是在还有余量的时候就分档介入。

```
class TokenBudget:
     def __init__(self, max_tokens: int = 28000):
         # 为什么设 28000 而不是模型上限（比如32000）？
         # 留4000 token 的余量给最终答案的生成；
         # 如果把上下文撑到30000+才开始处理，模型在生成答案时已经性能下降了
         self.max_tokens = max_tokens
         self.YELLOW_THRESHOLD = 0.65  # 65%时进入精简模式
         self.RED_THRESHOLD = 0.85     # 85%时触发历史压缩

     def get_mode(self, current_tokens: int) -> str:
         ratio = current_tokens / self.max_tokens
         if ratio < self.YELLOW_THRESHOLD:
             return "normal"    # 正常模式，完整传递搜索结果
         elif ratio < self.RED_THRESHOLD:
             return "compact"   # 精简模式，截断每次搜索结果
         else:
             return "compress"  # 压缩模式，触发历史摘要

     def truncate_observation(self, observation: str, mode: str) -> str:
         """根据当前模式，决定传给模型多长的搜索结果"""
         if mode == "normal":
             return observation[:3000]   # 正常：保留3000字符
         elif mode == "compact":
             return observation[:1500]   # 精简：只保留关键段落
         else:
             return observation[:800]    # 压缩：极简摘要
```

精简模式下，搜索结果被截短，模型每步能看到的信息量减少，推理链的长度得到了控制。这是信息完整性和上下文容量之间的权衡。token 紧张的情况下，宁可每步少看一点，也要保证模型能够完整地看到早期的关键发现。

当 token 达到85%触发压缩时，我们会把历史的 Observation 部分做一次摘要压缩：

```
async def compress_history(messages: list, llm) -> list:
     """
     把历史的工具调用结果压缩为摘要，保留 think 部分
     为什么要保留 think 而压缩 observation？
     模型的推理过程（think）反映了它怎么一步步缩小信息缺口，
     这个"思考轨迹"比具体的原始搜索结果更重要，
     它决定了模型接下来能做什么决策
     """
     # 提取所有 tool 消息（搜索结果原文）
     tool_messages = [m for m in messages if m["role"] == "tool"]
     if len(tool_messages) < 3:
         return messages  # 太少不值得压缩

     # 用 LLM 把所有搜索结果合并为一段研究摘要
     all_observations = "\n\n---\n\n".join([m["content"] for m in tool_messages])
     summary_prompt = f"""以下是一次 Deep Research 任务中的所有搜索结果原文。
 请提炼成一段结构化摘要，格式：
 ## 已确认的事实
 [列出已找到的关键信息，每条带来源]

 ## 尚未解决的子问题
 [列出还没找到答案的信息缺口]

 原始搜索结果：
 {all_observations[:8000]}
 """
     summary = await llm.chat_async([{"role": "user", "content": summary_prompt}])

     # 重建 messages：保留系统提示、用户问题、模型的 think 消息，
     # 把所有 tool 消息替换为一条压缩摘要
     think_messages = [m for m in messages if m["role"] == "assistant"]
     new_messages = [
         messages[0],  # system prompt
         messages[1],  # user question
         *think_messages,  # 保留模型的思考过程
         {"role": "tool", "tool_call_id": "compressed", "content": f"[已压缩历史搜索结果]\n{summary.content}"}
     ]
     return new_messages
```

![Token 预算三档管理](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

Token 预算三档管理

这套三档管理在我们测试里的实际效果是：同样的 Agent、同样的问题，引入 token 预算管理后，需要12步以上才能完成的复杂任务，成功率从61%提升到了78%。原因很简单，模型在整个执行过程中都能保持对早期关键信息的注意力，而不是在10步之后开始"忘事"。

在 ReAct 循环里加 token 计数，别等到溢出才处理。建议每步执行前打印出当前 token 使用率，先观察你的任务通常在哪个阶段开始吃紧，再根据实际情况调整三个阈值。

token 这套阈值我没有给死，因为不同任务的吃紧点差很多。顺带一提，官网项目案例里放了 Deep Research Agent 的完整执行日志样本，可以对照看一下你自己的任务一般卡在哪一档。

## 四、结构化日志：你的 Agent 出了问题，你怎么知道在哪步出的

上面的分级失败处理、重复检测、token 管理，所有这些都需要一个前提：你能看见系统在干什么。

没有结构化日志的 Agent 是个黑盒，跑完了你只知道给了个答案，不知道路上发生了什么。出了问题，你只能靠猜。

把所有关键信息打成结构化的格式：

```
import json
 from datetime import datetime

 class AgentLogger:
     def __init__(self, task_id: str):
         self.task_id = task_id
         self.steps = []
         self.start_time = datetime.now()

     def log_step(self, step: int, tool_name: str, tool_args: dict,
                  result_status: str, token_count: int, duration_ms: int):
         """
         为什么要记录 duration_ms？
         当你的某步花了8秒但结果是空的，通常意味着到达了超时重试，
         这个信息帮你判断是网络问题还是关键词问题
         """
         entry = {
             "task_id": self.task_id,
             "step": step,
             "timestamp": datetime.now().isoformat(),
             "tool": tool_name,
             "args": tool_args,
             "result_status": result_status,   # ok/timeout/empty_result/garbage/loop_detected
             "token_count": token_count,
             "duration_ms": duration_ms
         }
         self.steps.append(entry)
         # 实时打印，方便调试
         print(f"[{step:02d}] {tool_name}({tool_args.get('query', '')[:40]}) → {result_status} | {token_count} tokens | {duration_ms}ms")

     def summary(self) -> dict:
         """
         任务结束时输出摘要，一眼看清整次执行的健康状况
         """
         total_steps = len(self.steps)
         loop_steps = sum(1 for s in self.steps if s["result_status"] == "loop_detected")
         failed_steps = sum(1 for s in self.steps if s["result_status"] not in ("ok", "loop_detected"))

         return {
             "task_id": self.task_id,
             "total_steps": total_steps,
             "effective_steps": total_steps - loop_steps,  # 排除重复检测步
             "loop_rate": loop_steps / total_steps if total_steps else 0,
             "tool_fail_rate": failed_steps / total_steps if total_steps else 0,
             "peak_tokens": max(s["token_count"] for s in self.steps) if self.steps else 0,
             "total_duration_s": (datetime.now() - self.start_time).total_seconds()
         }
```

有了这份日志，下次出问题的时候，打开任务日志，第一眼就能看到：

- 在哪步开始 loop_detected（重复检测触发了）
- 在哪步出现了 garbage/empty_result（工具返回了垃圾）
- token 在哪个步骤急剧上升（某步搜索结果特别长，没有被截断）
  ![生产级 ReAct 执行器：四层防护体系](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

生产级 ReAct 执行器：四层防护体系

## 面试怎么答 ReAct 工程化问题？

面试官问你"Agent 上线遇到了什么问题，怎么处理的"，大部分人的回答是"加了重试"，这个答案太单薄，很容易被追问倒。

**先说你区分了哪几类失败（30秒）：**

不要只说"重试"，先说分类："工具失败有三类：超时用指数退避重试，因为频繁重试会加剧服务器压力；空结果不重试，直接告知模型换关键词，重试同一个词没意义；还有一类更隐蔽，工具成功返回了，但内容是垃圾，比如付费内容墙、广告页。这类必须主动检测过滤，不能让模型把垃圾当成信息。"

**再说你检测了什么（30秒）：**

"我们加了基于 embedding 相似度的重复搜索检测，阈值设在0.88。不只是说'你重复了'，还根据上次失败的原因给出针对性提示，上次是空结果，就让模型从完全不同的角度切入；上次是付费墙，就建议直接访问可信来源的 URL。加了这个之后，有效步骤比例从73%提升到了91%。"

**然后说 token 管理（30秒）：**

"上下文膨胀这块，我们不是等到溢出了才处理，而是在65%、85%两个阈值提前介入，65%开始截断搜索结果传入长度，85%触发历史压缩。同样的任务，加了这个之后，复杂任务的成功率从61%提升到了78%。"

这三个点说完，面试官想追问的方向基本都覆盖了。说出具体数字（73%→91%，61%→78%），说明你测过、量过、不是靠感觉说话。

## 写在最后

今天这篇的内容可以浓缩成一句话： **把每一次工具调用的结果都当成可能是垃圾的，直到你验证了它不是。**

这是工程思维，不是悲观。网络会抖，API 会返回垃圾，模型会陷入循环，这些都是迟早会发生的事，不是偶发的 edge case。你的系统得提前为它们备好处理逻辑，没备，迟早在生产里还回来。

跑完今天的代码，你手里有了一个真正能接生产流量的 ReAct 执行器。但你会发现，四件工具（Search、Visit、Scholar、Python）各自有各自的特点和坑，搜索返回的格式和网页访问的格式完全不一样，学术文献搜索需要额外的质量过滤，Python 工具还要考虑安全沙盒。下一篇专门来设计这四件套工具，把每个工具的"专属坑"填上。

这些细节，我都整理在了官网（www.wushixiongai.com）：项目案例里有 Deep Research Agent 从架构、数据到训练评估的完整文档，配可运行代码和逐步推导；题库里有 Agent 这块的高频追问题，按公司和难度分好了。

我是吴师兄，我们下篇文章见。

往期推荐

[字节面试官皱眉："你这 Agent 跟带搜索的 ChatGPT 有啥区别？"我答："能多轮搜，搜完接着搜啊"，他追问了一句搜索词……](https://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490642&idx=1&sn=94dfd48b393ceb8dfdc73e3ee5c7fb38&scene=21#wechat_redirect)

[蚂蚁面试官："187 条数据也敢写首轮训练？"我笑了："翻车归因在简历下半页"，面试官："下周二面我亲自来"](https://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490538&idx=1&sn=6e5af58188e73082d295e25a6ef8d042&scene=21#wechat_redirect)

[字节食堂打饭，我问同事"文档全塞进 context，模型咋更蠢了"，阿姨勺子一停："窗口能装 100 万，不代表 100 万字都看得进去啊。"](https://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490529&idx=1&sn=28cc51d15c84fdab50f17602b11ee26d&scene=21#wechat_redirect)

[京东面试官盯着我简历："单步准确率 94%，听着挺唬人，那你这 Agent 连跑 20 步，还剩多少？" 我心算了一下，当场沉默](https://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490532&idx=1&sn=d911de5c92751be67260f9e0a3ddec97&scene=21#wechat_redirect)

大厂真题 · 目录
