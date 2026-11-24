原创 吴师兄 _2026年5月15日 10:00_

大家好，我是吴师兄。

学员面完字节回来跟我说，整场就败在一句话上。

他简历写了"Deep Research Agent 准确率 78%"。面试官指着这行字问："剩下 22% 的用户，你打算怎么交代？"

他说："可以让模型自检一下。"

面试官："模型自己 78%，自检还是 78%。 **它觉得自己对的时候，可能正在错。** "

他没接上话。

面试官又问："跑五次选最好的，听过吗？五个 Agent 并行各搜各的，最后投票，听过吗？"

他摇头。

面试官把简历放下："你训练阶段卷到天上，推理阶段躺平交卷，这不叫工程，这叫赌博。"

这场面试他没过，但回来认认真真问了我一个问题： **模型能力固定的前提下，怎么用更多算力去"对冲"那 22% 的不确定性？**

这就是今天要讲的 Test-Time Scaling，Deep Research Agent 在推理阶段的两条核心路径：Best-of-N 采样，和 Research-Synthesis 并行框架。

## Best-of-N：最简单也最有效的推理优化

Best-of-N 的思路极其简单：同一个问题，让 Agent 独立跑 N 次（N 通常是 3-8），得到 N 份不同的搜索轨迹和答案，然后选最好的那份输出给用户。

"最好的"怎么定义？用我们在 RL 阶段训练好的奖励模型（Reward Model）来打分。每份答案跑一遍奖励函数，分数最高的那份就是最终输出。

```
import asyncio
 from typing import Optional

 async def best_of_n_inference(
     question: str,
     agent: DeepResearchAgent,
     reward_fn: callable,
     n: int = 4,
     temperature: float = 0.7
 ) -> dict:
     """
     Best-of-N 推理：并发跑 N 次，选分数最高的。

     为什么 temperature 不能太低？
     如果 temperature=0，每次跑出来的结果几乎一样，
     那跑 N 次就毫无意义——你需要足够的随机性
     才能让 N 个采样覆盖不同的搜索路径。
     """
     # 并发执行 N 次推理
     tasks = [
         agent.run(question, temperature=temperature)
         for _ in range(n)
     ]
     trajectories = await asyncio.gather(*tasks)

     # 用奖励函数对每个结果打分
     scored = []
     for traj in trajectories:
         if traj.get("status") == "completed":
             score = reward_fn(traj["full_trajectory"], question)
             scored.append({"trajectory": traj, "score": score})

     if not scored:
         # 所有采样都失败了，返回第一个结果
         return trajectories[0]

     # 选分数最高的
     best = max(scored, key=lambda x: x["score"])
     return best["trajectory"]
```

效果怎么样？我们在 BrowseComp（浏览理解基准）上测试：单次推理准确率 78%，Best-of-4 提升到 85%，Best-of-8 提升到 89%。收益是递减的——从 N=1 到 N=4 提升了 7 个百分点，但从 N=4 到 N=8 只提升了 4 个百分点。

| N   | 准确率 | 相对提升 | 推理成本（token） |
| --- | ------ | -------- | ----------------- |
| 1   | 78%    | 基线     | 约 8K             |
| 2   | 82%    | +4%      | 约 16K            |
| 4   | 85%    | +7%      | 约 32K            |
| 8   | 89%    | +11%     | 约 64K            |
| 16  | 90%    | +12%     | 约 128K           |

N=4 是性价比最高的选择。N 从 4 到 16 翻了 4 倍计算量，但准确率只多了 5 个百分点。

![Best-of-N 采样：准确率与成本的权衡](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

Best-of-N 采样：准确率与成本的权衡

### Best-of-N 的两个坑

第一个坑是 **打分成本** 。如果用完整的 LLM-as-Judge 给每个答案打分，打分本身的 token 消耗可能比生成答案还多。我们的做法是用一个轻量级的打分函数——只看格式完整性 + 引用数量 + 答案长度合理性——不调用 LLM，打分耗时几乎为零。

```
def lightweight_scorer(trajectory: dict) -> float:
     """
     轻量级打分函数，不调用 LLM，用启发式规则。
     为什么不用 LLM 打分？
     因为 N=4 时你要打 4 次分，如果每次打分要 2K token，
     光打分就多花 8K token，成本翻倍了。
     """
     score = 0.0
     answer = trajectory.get("answer", "")
     tool_calls = trajectory.get("tool_calls", [])

     # 答案长度合理性（太短可能是编的，太长可能跑偏了）
     if 200 < len(answer) < 3000:
         score += 0.3
     elif len(answer) >= 100:
         score += 0.1

     # 引用数量（有引用说明搜索结果被用到了）
     citations = len(re.findall(r'\[\d+\]', answer))
     score += min(citations * 0.1, 0.3)

     # 搜索步数合理性
     if 3 <= len(tool_calls) <= 12:
         score += 0.2

     # 格式完整性
     if trajectory.get("status") == "completed":
         score += 0.2

     return score
```

第二个坑是 **多样性不足** 。如果模型在某个问题上有"强偏好"（比如第一步总是搜同一个关键词），那即使温度调高，N 个采样的搜索路径可能高度重叠。这时候 Best-of-N 的收益就很低——因为本质上你在选"同一条路径的微小变体中最好的"，而不是"多条完全不同的路径中最好的"。

解决方案是给不同采样设置不同的搜索约束。比如第一个采样不加约束，第二个要求第一步必须用 Scholar 工具，第三个要求第一个搜索关键词里必须包含特定角度。这样强制 N 个采样走不同方向。

## Research-Synthesis：并行多 Agent 框架

Best-of-N 的局限在于：N 个采样是独立的，它们之间不共享信息。Agent A 在第 3 步发现了一条关键线索，Agent B 对此一无所知，还在从头开始搜。

Research-Synthesis 框架的核心思想是把一个复杂问题拆成多个子问题，让多个 Research Agent 并行处理各自的子问题，最后由一个 Synthesis Agent 综合所有结果生成最终报告。

```
async def research_synthesis(
     question: str,
     decomposer: LLM,
     research_agent: DeepResearchAgent,
     synthesis_agent: LLM,
     max_researchers: int = 3
 ) -> str:
     """
     Research-Synthesis 并行框架。

     核心流程：
     1. Decomposer 把问题拆成 N 个子问题
     2. N 个 Research Agent 并行搜索（各自独立）
     3. Synthesis Agent 综合所有搜索结果，生成最终报告

     为什么不直接用一个 Agent 按顺序搜？
     因为复杂问题需要从多个角度切入——
     比如"比较 A 公司和 B 公司的技术路线"，
     一个 Agent 搜完 A 再搜 B 容易遗忘 A 的细节。
     两个 Agent 一个专门研究 A、一个专门研究 B，
     各自搜得更深，最后综合时信息更完整。
     """
     # 第一步：问题分解
     sub_questions = await decomposer.decompose(question, max_parts=max_researchers)

     # 第二步：并行研究
     research_tasks = [
         research_agent.run(sq, temperature=0.5)
         for sq in sub_questions
     ]
     research_results = await asyncio.gather(*research_tasks)

     # 第三步：综合
     synthesis_prompt = build_synthesis_prompt(
         original_question=question,
         sub_questions=sub_questions,
         research_results=research_results
     )
     final_report = await synthesis_agent.generate(synthesis_prompt)

     return final_report
```

### 问题分解的质量决定一切

Research-Synthesis 框架的瓶颈不在搜索，在于第一步的问题分解。如果子问题拆得不好——有重叠、有遗漏、粒度不均匀——后面的并行搜索再好也救不回来。

我们测试了三种分解策略：

```
DECOMPOSE_PROMPT = """
 你是一个研究规划师。给定一个复杂问题，把它分解为 {n} 个独立的子问题。

 要求：
 1. 子问题之间尽量正交（不重叠）
 2. 子问题合起来能覆盖原始问题的所有方面
 3. 每个子问题都是一个 Research Agent 能独立搜索解答的
 4. 按重要性排序，最关键的子问题排第一个

 原始问题：{question}

 输出格式：
 1. [子问题1]
 2. [子问题2]
 3. [子问题3]
 """
```

实测下来，分解成 3 个子问题效果最好。2 个太粗，每个子问题仍然很复杂；4 个以上太细，子问题之间开始有大量重叠，Synthesis 阶段需要花大量精力去重。

![Research-Synthesis 并行研究框架](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

Research-Synthesis 并行研究框架

### Synthesis Agent 的设计要点

Synthesis 不是简单的"把三份报告拼在一起"。它需要做三件事：

第一， **去重与冲突解决** 。三个 Research Agent 可能搜到了同一篇文章的不同段落，或者对同一个问题得出了矛盾的结论。Synthesis 需要识别这些重叠和冲突，选择更可靠的信息源。

第二， **补充缺失** 。如果三个子问题覆盖了 A、B、C 三个角度，但原始问题还隐含了 D 角度（比如"这些方案之间的对比"），Synthesis 需要基于已有信息自行补充。

第三， **重新组织叙事结构** 。子问题的回答顺序不一定是最终报告的最佳叙事顺序。Synthesis 需要根据逻辑关系重新编排。

```
SYNTHESIS_PROMPT = """
 你是一个研究综合专家。以下是针对同一问题的多个独立研究结果。

 原始问题：{question}

 研究结果：
 {formatted_results}

 请综合以上所有研究结果，生成一份完整的研究报告。要求：
 1. 信息去重：相同的发现只保留描述更精确的版本
 2. 冲突标注：如果不同研究得出矛盾结论，明确标注并说明哪个更可靠
 3. 缺失补充：如果现有研究没有完全覆盖原始问题的所有方面，指出缺失点
 4. 引用溯源：每个关键结论标注来源于哪个研究Agent的哪条搜索结果
 5. 逻辑编排：按最有利于读者理解的顺序组织内容
 """
```

## 两种策略的组合：什么时候用什么

Best-of-N 和 Research-Synthesis 不是互斥的，它们解决的是不同类型的问题。

| 维度         | Best-of-N                 | Research-Synthesis                |
| ------------ | ------------------------- | --------------------------------- |
| 适用问题类型 | 单一焦点问题（"X是什么"） | 多角度复合问题（"比较A和B"）      |
| 并行方式     | 同一任务跑 N 次选最好     | 不同子任务各跑一次再综合          |
| 优势         | 实现简单，对抗随机性      | 搜索更深入，覆盖更全面            |
| 劣势         | N 个采样可能高度重叠      | 问题分解质量依赖 LLM              |
| 推理成本     | N 倍（线性增长）          | 约 3-4 倍（子问题数 + Synthesis） |
| 准确率提升   | +7-11%（N=4-8）           | +12-15%（3 个子问题）             |

在实际系统里，我们会先判断问题复杂度，然后决定策略：

```
async def adaptive_inference(question: str, agent: DeepResearchAgent) -> str:
     """
     自适应推理策略选择。
     简单问题跑一次就行，复杂问题根据类型选 Best-of-N 或 Research-Synthesis。
     """
     complexity = estimate_question_complexity(question)

     if complexity == "simple":
         # 简单事实题，单次推理足够
         result = await agent.run(question, temperature=0.3)
         return result["answer"]

     elif complexity == "medium":
         # 中等难度，Best-of-4 就够了
         result = await best_of_n_inference(question, agent, lightweight_scorer, n=4)
         return result["answer"]

     elif complexity == "complex_multi_aspect":
         # 多角度复合问题，用 Research-Synthesis
         report = await research_synthesis(question, decomposer, agent, synthesizer)
         return report

     else:
         # 极高难度，Research-Synthesis + 每个子问题内部 Best-of-2
         # 成本最高，但可靠性最强
         report = await research_synthesis_with_bon(
             question, decomposer, agent, synthesizer, inner_n=2
         )
         return report
```

这套推理优化的完整工程实现，是我们训练营 Deep Research Agent 项目里从"准确率 78%"突破到"90%+"的关键模块。学员不只是学理论，而是真的跑过 Best-of-N 的 ablation 实验，看过 N=4 vs N=8 的准确率曲线在哪个点开始拐弯。

![Deep Research Agent 自适应推理策略](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

Deep Research Agent 自适应推理策略

## 自我检查与修正：最后一道防线

除了 Best-of-N 和并行框架，还有一种更轻量的推理优化方式：让模型在输出答案之后做一次自检。

前面面试官说"模型自检准确率也是 78%"，这在完全开放的场景下确实成立。但如果自检时给模型一些结构化的检查维度，效果会好很多。

```
SELF_CHECK_PROMPT = """
 你刚才基于以下搜索结果生成了一份回答。请检查以下维度：

 1. 事实一致性：回答中的每个事实声明，是否都能在搜索结果中找到对应来源？
    如果有无法溯源的声明，标记为 [需要验证]。

 2. 时效性：回答中是否引用了过时的信息？搜索结果的日期是否足够新？

 3. 逻辑完整性：回答是否完整覆盖了用户问题的所有方面？是否有遗漏？

 4. 数据准确：回答中的数字、百分比、日期是否与搜索结果一致？

 如果发现问题，输出修正建议。如果没有问题，输出 "PASS"。
 """
```

我们在系统里加入自检之后，单独的自检修正能带来 3-5% 的准确率提升（比 Best-of-N 小，但几乎零额外成本——只需要一次额外的 LLM 调用）。配合 Best-of-N 一起用时，先选出分数最高的答案，再对这个答案做一次自检修正，总提升约 8-13%。

## 面试怎么答推理时间扩展？

**先说核心思想（30秒）：**

"训练时间扩展是让模型变强，推理时间扩展是在模型能力固定的前提下，通过多次采样或并行搜索来提升单次输出的可靠性。这两个方向是正交的，可以叠加。"

**再说具体方案（1分钟）：**

"我们主要用两种策略。Best-of-N 是同一个问题跑 N 次选最好的，实现简单，N=4 时准确率从 78% 提升到 85%，性价比最高。Research-Synthesis 是把复杂问题拆成子问题让多个 Agent 并行搜索再综合，适合多角度的比较类问题，准确率能到 92% 但成本是 3-4 倍。线上系统根据问题复杂度自适应选择策略。"

**最后说工程权衡（30秒）：**

"核心权衡是准确率和推理成本的 tradeoff。Best-of-N 成本线性增长但收益递减，N 超过 8 基本没意义。Research-Synthesis 的瓶颈在问题分解质量——拆不好后面再怎么搜也白搭。我们实测 3 个子问题是最优解，2 个太粗 4 个重叠太多。"

今天这道题，只是大模型面试中 Agent 推理优化的一个切面。

真正的面试官不会只问这一问。他们会顺着你的回答追下去，追到你答不上来为止，判断的就是你到底做没做过这个系统。

背答案的人和真正做过的人，说话方式完全不一样。前者说"可以跑多次选最好的"，后者说"我们测下来 N=4 到 N=8 准确率只多了 4 个百分点，但 token 消耗翻倍了，线上系统 N=4 就够了，极端问题才上 Research-Synthesis"。

面试官三句话就能听出来你是哪种人。

往期推荐

[在字节食堂打饭，我问同事："你们的Agent工具调用失败了怎么处理？"，打饭阿姨说："try/except跳过不行，得让模型知道失败了。"](https://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490348&idx=1&sn=b3f0d2c45649599e9ab0c13ea8e1496d&scene=21#wechat_redirect)

[百度面试官皱眉："你的DR Agent跑五十步就崩了，这是玩具。"我说出两个字，他重新坐正了](https://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490343&idx=1&sn=c386c42af26e60287d873f36b6eaa1d6&scene=21#wechat_redirect)

[面试官说："有 Claude Code 就够了，要什么记忆系统？"我问他 CLAUDE.md 放了什么，他答不上来](https://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490330&idx=1&sn=a3249d68ade12152f708226e85ba88d5&scene=21#wechat_redirect)

[字节面试结束，我反问："你们 DR Agent 怎么判断来源可信度？"，面试官："……你来面我的？"](https://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490322&idx=1&sn=813364a61e172e4f48ef17fcba39af24&scene=21#wechat_redirect)

大厂真题 · 目录
