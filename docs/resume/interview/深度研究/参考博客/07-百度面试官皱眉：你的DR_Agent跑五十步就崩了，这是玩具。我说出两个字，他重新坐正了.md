原创 吴师兄 _2026年5月11日 10:01_

大家好，我是吴师兄。

前两天一个训练营学员找我复盘面试，说自己在百度的面试里被一道题卡住了。他做过 Deep Research Agent，这是他最有把握的项目，但面试官的问法让他慌了。

面试官问他："你的 Agent 跑一个研究任务，中间要搜索二十几次，每次都往上下文里塞东西，token 用完了怎么办？"

他说："可以做截断，或者换个 context window 更大的模型。"

面试官皱眉："截断会丢信息，换大模型是花钱，但这不是架构问题的解法。你知道 IterResearch 框架怎么处理这个问题吗？"

他答不上来。

面试官给他点了一句："你看，你的系统跑十步可以，跑五十步就崩了。这说明你的 Agent 没有真正的记忆管理，只是把所有东西堆到上下文里而已。这是玩具和生产系统的区别。"

这句话说得准。我自己用 Claude Code 做项目时也遇到过同样的本质问题——系统的记忆不能无限增长，必须有一套机制决定"什么值得记，什么可以丢"。今天把这个问题从原理到工程细节全部拆开讲。

## 从 ReAct 到 IterResearch：两种上下文策略的根本差异

先说 ReAct 是怎么失败的。

ReAct（Reasoning and Acting）的执行逻辑是这样的：每一步都把 Thought、Action、Observation 追加到上下文末尾，形成一个线性的推理链。第一步搜索的结果、第二步访问网页的内容、第三步的分析……全部堆在那里，等着下一步去参考。

这个设计在短任务里没问题。搜索三次、访问两个网页，上下文不超过 8K token，模型完全能撑住。但 Deep Research 的任务本来就是复杂的：要研究一家企业的固态电池战略，你可能需要搜索这家企业的官网、研报、专利、竞品动态……二十次搜索是起步，每次 Observation 放进去 1000 个 token，20 次就是 2 万 token，加上模型自己的推理输出，很快就把 128K 的上下文填满了。

填满之后发生什么？要么截断，把最早的内容丢掉——但最早搜到的信息可能是关键背景；要么换更大 context window 的模型——成本直接翻倍，而且大模型对超长上下文的注意力本来就会衰减，效果并不线性提升。

IterResearch 的解法是换一个思路：不再让上下文线性增长，而是引入一个"演进报告"（Evolving Report）作为中央记忆。

![ReAct vs IterResearch 上下文管理策略对比](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

ReAct vs IterResearch 上下文管理策略对比

演进报告的核心机制是：Agent 每完成一轮搜索和分析，不是把原始 Observation 堆进上下文，而是更新演进报告——把这一轮发现的关键信息提炼进报告，同时把处理过的原始搜索结果丢弃。下一轮开始时，模型只看到固定大小的演进报告，而不是越来越长的历史记录。

这样，不管任务跑了多少轮，上下文始终保持在可控的大小。五步和五十步，模型面对的 token 数是一样的。

## 演进报告的设计：信息如何在"压缩"中不丢核心

演进报告听起来简单，但真正做过才知道里面有多难。

难在两个地方：

**第一，什么信息值得写进报告，什么可以丢？**

搜索到一篇 5000 字的行业报告，Agent 需要判断：这篇报告里哪些段落是后续决策需要的，哪些是重复的背景介绍可以忽略。这个判断需要模型理解任务目标，而不是无脑摘要。

在我们的 DeepResearch 项目里，演进报告有固定的模板结构：

```
## 研究目标
 [保持不变，任务开始时写入]

 ## 已确认的关键事实
 [每轮更新，格式：事实 | 来源 | 置信度]

 ## 待验证的假设
 [中间状态，事实核实后移至上方或删除]

 ## 信息缺口
 [还没搜到但需要的信息，驱动下一轮搜索方向]

 ## 当前结论草稿
 [基于已有信息的临时结论，会被后续信息修正]
```

每一轮结束，模型按这个结构更新报告，而不是自由发挥。结构化的报告有两个好处：一是强迫模型做显式的信息分类，不把"待验证"的东西当"已确认"用；二是让"信息缺口"模块成为下一轮搜索的驱动引擎，而不是让模型漫无目的地继续搜索。

**第二，报告本身能不能无限增长？**

不能。如果每轮都往报告里加内容，报告本身也会越来越大，回到了原来的问题。

解决方法是报告有大小上限，通常设 2000-3000 token。当报告快到上限时，模型需要做一次"压缩"——把"已确认的关键事实"里相似的条目合并，把"待验证的假设"中已经很久没有进展的条目删掉。

这个压缩动作本身也是模型来做的，不是规则过滤。这就对模型能力有要求：必须训练过处理这种演进报告更新任务。这也是为什么训练数据里要专门构造"报告更新"的样本，而不是只训练搜索和回答。

## Claude Code 的记忆管理：同一个问题，不同的工程解法

说到这里你可能会觉得，这是 Deep Research Agent 专属的问题。但其实 Claude Code 面对的是同一个核心矛盾：持久性知识该怎么存，上下文有限时该怎么选择性地注入。

Claude Code 的解法是把记忆从上下文里剥离出来，存到文件系统。

具体来说，Claude Code 的持久记忆存在 `~/.claude/projects/{project_id}/memory/` 目录下，其中 `project_id` 是工作目录路径的 SHA-256 哈希前缀。每次启动新会话时，系统只把 `MEMORY.md` 的内容注入到 system_prompt 里，其他记忆文件按需读取。

这个设计有一个硬性限制： `MEMORY.md` 最多 200 行，超过就截断，同时在 system_prompt 里显示 `[MEMORY TRUNCATED]` 警告。

200 行是怎么来的？这是工程上的权衡。在内部代码里，这个值叫 `MAX_ENTRYPOINT_LINES` ，定义在 `sections.py:179` 。200 行换算成 token 大约是 3000-4000 个，这个量级不会占用太多上下文窗口，但足够放下几十条关键的项目信息和用户偏好。

```
# Claude Code 内部逻辑（sections.py 简化版）
 MAX_ENTRYPOINT_LINES = 200

 def load_memory_index(memory_dir: Path) -> str:
     memory_file = memory_dir / "MEMORY.md"
     if not memory_file.exists():
         return ""
     lines = memory_file.read_text().splitlines()
     if len(lines) > MAX_ENTRYPOINT_LINES:
         truncated = lines[:MAX_ENTRYPOINT_LINES]
         return "\n".join(truncated) + "\n[MEMORY TRUNCATED - exceeds 200 line limit]"
     return memory_file.read_text()
```

这里有一个值得注意的设计哲学：Claude Code 对记忆的态度是"悲观信任"（pessimistic trust）。在 system_prompt 里，关于记忆的 section 会明确告诉模型： **记忆里的内容是线索，不是事实。使用前必须验证。**

这句话对应的英文原文大概是："Memories are clues, not facts. Always verify before acting on them."

为什么要这样设计？因为记忆是跨会话积累的，上一个会话记下来的"用户喜欢用 pytest"，可能这个会话里用户已经换成了 vitest。如果模型把记忆当事实直接用，而不是当"需要验证的假设"，就会产生错误的行为。

这和演进报告里的"待验证假设"模块是同一个设计思路：持久化的信息不等于可信的信息，系统需要在执行时主动验证。

![两种系统的记忆管理策略对比](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

两种系统的记忆管理策略对比

## ReSum 动态摘要：当演进报告也撑不住时

演进报告解决了大多数情况，但有一类任务会把演进报告本身也撑爆：信息密度极高的研究任务，比如要综合分析五十家企业的财务数据。

这时候需要另一套机制：ReSum（Reasoning with Summarization），也叫动态摘要。

ReSum 的触发逻辑是监控上下文使用率，当超过某个阈值（通常设 80%）时，强制触发一次摘要操作。摘要不是简单截断，而是让模型对当前上下文做结构化压缩，保留关键结论和证据链，丢掉中间过程的 Observation 原文。

```
class ReSumManager:
     def __init__(self, max_tokens: int = 128000, threshold: float = 0.8):
         self.max_tokens = max_tokens
         self.threshold = threshold
         self.trigger_tokens = int(max_tokens * threshold)  # 102400

     def should_trigger(self, current_tokens: int) -> bool:
         return current_tokens >= self.trigger_tokens

     async def compress(self, messages: list, task_goal: str) -> list:
         # 保留 system prompt + 最近 N 条消息
         # 对中间部分做结构化摘要
         summary_prompt = f"""
         任务目标：{task_goal}

         请对以下研究过程做结构化摘要，保留：
         1. 所有已确认的关键事实（保留来源）
         2. 当前结论草稿
         3. 尚未解决的信息缺口

         丢弃：搜索过程的原始 Observation 全文
         """
         # 调用 LLM 做压缩
         summary = await self.llm.compress(messages[2:-5], summary_prompt)
         return [messages[0], messages[1], {"role": "assistant", "content": summary}] + messages[-5:]
```

这套机制在我们训练营的 DeepResearch 项目里有完整实现。实测下来，对于需要 40+ 步搜索的深度任务，开启 ReSum 之后上下文使用量从接近溢出降到平均 65% 左右，同时因为摘要质量高，后续推理的准确率并没有明显下降——关键事实都保留了，只是过程噪声被清掉了。

这套机制和 Claude Code 的 `/compact` 命令是类似的思路。Claude Code 的 compact 也是在会话上下文快满时，让模型把历史对话压缩成一个摘要，然后用摘要替换掉详细历史。但 compact 是单次操作，ReSum 是持续监控、自动触发。

两者的根本区别是：compact 是"当用户感觉慢了才手动触发"，ReSum 是"系统主动监控，在溢出前自动处理"。生产环境里显然应该用后者。

## 信息缺口驱动搜索：避免"漫无目的地搜"

说完记忆管理，再说一个演进报告的隐性作用：它让 Agent 的搜索行为变得有目标性。

ReAct 框架的一个典型问题是"重复搜索"——模型在第 3 步搜过某个关键词，到第 8 步又搜了一遍，因为它记不住自己搜过什么。演进报告的"信息缺口"模块天然解决了这个问题：

1. 每轮搜索完成，把"这次搜索回答了什么问题"记录到"已确认事实"
2. 把"还没找到的内容"记录到"信息缺口"
3. 下一轮的搜索 query，必须从"信息缺口"里选，不允许重复已在"已确认事实"里的方向

这个强制约束在实现时很简单——只是在生成搜索 query 的 prompt 里加一句"不要搜索以下已有信息"，并把已确认事实列出来。但效果很明显：在我们的项目里，开启这个约束后，搜索的重复率从 23% 降到了 6%，每次搜索命中新信息的比例大幅提升。

Claude Code 里有类似逻辑的地方是工具调用的决策过程。Claude Code 在 system_prompt 里有一段规则："Do not re-attempt the exact same tool call. Instead, think about why the user has denied the tool call and adjust your approach."这不完全是重复检测，但也反映了同样的设计直觉：不要无目的地重复，每次行动应该基于上次行动的反馈。

## 面试怎么答"上下文管理"这道题？

面试官问这道题，考察的核心是你有没有真正做过多步长任务的 Agent。

标准回答分三层（建议约 2 分钟）：

**第一层：识别问题（20 秒）** "上下文管理是长任务 Agent 的核心瓶颈。ReAct 框架把所有 Observation 线性堆叠，步数多了就溢出，截断会丢信息，换大模型是治标不治本。"

**第二层：说方案（60 秒）** "我们用的是 IterResearch 框架，核心是引入演进报告作为中央记忆。每轮搜索完成，提炼关键事实更新报告，丢弃原始 Observation。报告有大小上限（2000-3000 token），上限快到时触发压缩。这样不管跑多少步，上下文始终可控。另外报告里单独维护一个'信息缺口'模块，驱动下一轮搜索方向，避免重复搜索。"

**第三层：说数据（40 秒）** "实测效果：对于 40+ 步的深度研究任务，开启演进报告后上下文使用量稳定在 65% 以下，没有溢出；搜索重复率从 23% 降到 6%；配合 ReSum 动态摘要，即使是信息密度极高的任务也没有爆上下文。"

如果面试官追问"演进报告如何更新"，就把报告模板的结构说出来（研究目标、已确认事实、待验证假设、信息缺口、结论草稿），并说"模型是按这个结构更新的，不是自由发挥，结构化的好处是强迫模型做显式的信息分类"。

如果追问"这和 Claude Code 的 Memory 有什么关系"——说两者解决的是同一个本质问题：有限上下文如何管理无限积累的知识，都用到了"有上限的持久存储 + 悲观信任策略"。

![Deep Research Agent 上下文管理全链路](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

Deep Research Agent 上下文管理全链路

## 总结

上下文管理不是"换个大模型"就能解决的问题，它是 Agent 架构里必须在设计阶段就想清楚的核心问题。

演进报告（Evolving Report）的本质贡献是把 Agent 的记忆从"线性堆叠"改成了"结构化提炼"——信息在进入报告之前必须经过筛选和分类，而不是原封不动地堆进去。这个差异直接决定了系统能不能在真实场景里稳定跑起来。

Claude Code 的 Memory 系统用的是另一种形式的同一种思路：把知识从上下文里剥离出来，用 200 行的硬限制强迫写记忆的人做选择，同时用"悲观信任"策略防止历史记忆产生幻觉。

两套系统，同一个设计哲学：记忆不是越多越好，有用的记忆才是好记忆。

今天这道题，只是 Deep Research Agent 工程落地里上下文管理的一个切面。

真正的面试官不会只问这一问。他们会顺着你的回答追下去，追到你答不上来为止，判断的就是你到底做没做过这个系统。

背答案的人和真正做过的人，说话方式完全不一样。前者说"可以用演进报告管理上下文"，后者说"演进报告要设 2000-3000 token 的上限，报告的结构分五个模块，'信息缺口'是驱动下一轮搜索的引擎，这个细节不做过根本想不到要设计它"。

面试官三句话就能听出来你是哪种人。

如果你想成为后者，欢迎了解我们的大模型训练营。近千名学员，最快 26 天拿到 offer，覆盖零基础转型、应届求职、社招转方向。

我是吴师兄，我们下篇文章见。

_本文内容基于吴师兄大模型训练营实战系列课程整理。系列往期文章可在主页查看。_

往期推荐

[面试官说："有 Claude Code 就够了，要什么记忆系统？"我问他 CLAUDE.md 放了什么，他答不上来](https://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490330&idx=1&sn=a3249d68ade12152f708226e85ba88d5&scene=21#wechat_redirect)

[字节面试结束，我反问："你们 DR Agent 怎么判断来源可信度？"，面试官："……你来面我的？"](https://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490322&idx=1&sn=813364a61e172e4f48ef17fcba39af24&scene=21#wechat_redirect)

[滴滴面试官追问："Claude Code 自动帮你记了什么？你翻过 MEMORY.md 文件吗？"我打开一看，里面存的全是废话](https://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490315&idx=1&sn=23d78a7fdd98bb43a20eb2ea9a7a2d98&scene=21#wechat_redirect)

[鹅厂面试官追问："Claude Code 的 Memory 是什么时候注入进 system_prompt 的？"](https://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490302&idx=1&sn=c0fb340413115a5363f47d8a18154a4f&scene=21#wechat_redirect)

大厂真题 · 目录
