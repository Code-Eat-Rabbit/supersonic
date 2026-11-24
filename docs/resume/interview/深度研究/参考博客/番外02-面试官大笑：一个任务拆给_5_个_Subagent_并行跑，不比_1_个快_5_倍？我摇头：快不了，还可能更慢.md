原创 吴师兄 _2026年7月28日 10:19_

大家好，我是吴师兄。

前两个月，我在重构 AlgoMooc 网站过程中，发现一个问题：在 Claude Code 里把一个任务拆给 5 个 Subagent 并行跑，结果可能比 1 个 agent 从头干到尾还慢？

大多数人的第一反应是反过来的：活是并行干的，5 个 agent 不说快 5 倍，快个两三倍总有吧。这个直觉的问题在于，它把"能同时运行"当成了"能同时干完"。前者是调度器给的，后者要任务结构自己配合。

我自己的结论可以先写成一个公式：并行的收益，等于任务里真正能独立拆分的那部分；而并行的税有四项，重复认路乘以人头数、依赖链把并行退化成串行、共享文件的冲突处理、主 agent 单点的汇总和验收。

收益盖不过四项税的时候，5 个就是比 1 个慢。

它考的不是 Claude Code 的用法，是你有没有把分布式系统的常识迁移到 agent 上的能力。把"加机器"当成"加速度"的错误，后端工程师在消息队列和微服务上犯过一轮，现在轮到 agent 了。

上下文隔离、结果只回传摘要这些基础机制，我之前写 Subagent 的文章已经讲过，这篇不再重复。今天只算账：依赖、调度、协调、验收，一项一项过。

![五倍直觉与并行税公式](https://mmbiz.qpic.cn/sz_mmbiz_png/uvQZiaXrG4t7UmK9GBD6ta8iaQ8GfCvrdCBc2VA2WzACP8HNiavyljmgib9K14yxa60iaMqh1KYHY97q6s99jt649TSQuZatQ7QewutM8OyqXvqo/640?from=appmsg&watermark=1&tp=webp&wxfrom=5&wx_lazy=1#imgIndex=0)

五倍直觉与并行税公式

## 任务结构先于agent数量：依赖链怎么锁死总时长

官方文档对"什么时候并行"说得很克制：并行研究在各条研究路径互不依赖时效果最好。反过来，任务之间有依赖怎么办？官方给的姿势是串行链，一个 subagent 干完，结果回到主 agent，主 agent 再把相关上下文转交给下一个。

注意这个结构的含义。5 个任务里只要藏着一条 A 到 B 到 C 的依赖链，你的总时长就被这条链锁死了，这就是调度里的关键路径。B 必须等 A 的产出，C 必须等 B，真正并行的只有旁边那两个散活。而且每一跳还要多付一笔中转费：结果先回主 agent，主 agent 消化之后重新派单，这段时间链上所有人都在等。

这套逻辑其实一点都不新。并行计算里它叫阿姆达尔定律：不管加多少处理器，加速比永远被任务里串行部分的占比压死。Agent 并行只是这条老定律换了张新皮，而且条件更苛刻，因为 agent 之间的协调成本比 CPU 核心之间高出几个量级，每一次"等结果、转上下文"都是完整的一轮模型调用。

所以拿到任务先别数人头，先画依赖图。哪些产出是别人的输入，哪些文件是多人要碰的，哪些结论要等别人的中间结果。依赖图画出来，能并行的部分往往比想象中小。Anthropic 的工程博客里有一句很扫兴但很诚实的话：大多数编码任务里，真正可并行的子任务比研究类任务少，而且模型目前也不擅长实时协调和委派其他 agent。

![依赖链把并行退化成串行](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

依赖链把并行退化成串行

## 第一项税：五个白纸agent，各自重新认路

Subagent 拿不到你主对话里已经建立的认知。官方文档把这一点直接列为"什么时候该用主会话"的理由：延迟敏感的场景别用 subagent，因为它们从零开始，需要时间收集上下文。

从零开始意味着什么？你的主对话已经知道项目结构、知道改动目标、知道哪些文件相关。5 个 subagent 各自要重新读 CLAUDE.md、重新摸目录结构、重新 grep 同一批文件。同样的认路工作被做了 5 遍，这些 token 和时间在单 agent 方案里只花一次。

Anthropic 博客里对应的失败模式描述是：任务描述不够详细时，agent 会重复劳动、留下空当、找不到必要的信息。他们给 lead agent 的派单要求是四要素齐全：目标、输出格式、工具和信息源的指引、明确的任务边界。四要素本身就有成本：你得在派单 prompt 里把主对话的认知重新压缩一遍。写得越省事，下游重复认路越严重。

![重复认路税与派单四要素](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

重复认路税与派单四要素

## 第二项税：调度不是魔法，上限和阻塞都写在文档里

很多人对"并行"的想象是无限车道，实际的调度机制长这样，都是官方文档里的白纸黑字。

| 调度事实     | 官方口径                               |
| ------------ | -------------------------------------- |
| 默认并发方式 | v2.1.198 起 subagent 默认后台并发运行  |
| 阻塞条件     | 需要某个结果才能继续时，前台阻塞等待   |
| 并发上限     | 默认 20 个，超限直接报错拒绝，不是排队 |
| 单会话总量   | 默认最多 200 个 subagent               |
| 嵌套         | 默认关闭，subagent 不能再开 subagent   |
| 相互通信     | 不支持，子代理之间不交换信息           |

其中最容易想当然的是第三条：超过并发上限不是排队等空位，是报错，而且官方明确提示不要立即重试，要等运行中的数量降下来。把"开 50 个总有 20 个在跑"当成策略的人，会在报错重试里浪费更多轮次。Anthropic 自己复盘早期系统时列过一个失败案例：给简单查询开了 50 个 subagent。这不是假想敌，是他们真踩过的坑。

第一条也值得多说一句。后台并发听起来很美，但后台跑完的结果是以完成通知的形式，在之后的轮次里陆续到达主对话的。也就是说主 agent 不是实时看着五个人干活，它是在收快递，收齐了才能开始汇总。至于让 agent 之间直接商量着干活，那不是 subagent 的能力，子代理之间不通信，需要协作通信是另一套叫 agent teams 的机制，成本结构完全不同。

![调度机制的六条事实](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

调度机制的六条事实

## 第三项税：共享文件的所有权，比你想的难分

5 个 agent 只读不写，冲突税约等于零，这也是为什么检索、审计、调研类任务是并行的最佳场景。一旦要写文件，问题就变成：谁拥有哪些文件？

我去年在 AlgoMooc 的题解动画上踩过一次完整的坑。五道题的动画课件页，看起来是五个完全独立的任务，一题一个 subagent，理论上互不相干。实际跑起来才发现它们共享同一个播放器组件：其中一个 agent 觉得组件接口缺一个暂停回调，顺手把共享组件改了；另外四个基于旧接口写的调用，等我合并时全对不上。表面上五个独立任务，底下压着一个没人认领的共享依赖。那个下午我花在对齐接口、返工调用上的时间，比动画生成本身还多。

复盘下来，写并行任务的第一件事是把文件所有权切干净：每个 agent 一块独占地盘，共享的部分要么冻结不许动，要么单独立一个任务先改好，其他人等它。所有权分不干净的任务，就不配并行。

同一个任务现在让我重排，会是这样：第一步单独派一个任务，把播放器组件的接口补齐、定稿、冻结，这一步串行，谁也不等谁；第二步五道题的课件并行开工，派单里写死一条边界，只许写各自题目目录，共享组件只读；第三步验收尽量交给机器，课件页能不能构建、资源路径在不在，脚本一跑就知道，主线只人工看动画效果这种机器判不了的部分。同样五个 agent，把依赖前置、所有权切开、验收自动化之后，才轮得到并行发挥作用。

worktree 能帮上一部分忙。Claude Code 支持给 subagent 配 isolation: worktree，让它在一个临时的 git worktree 里干活，写操作物理隔离，互相踩不到，任务结束时没有改动的 worktree 还会自动清理。git 这一层也有内置保护：同一个分支默认不允许被第二个 worktree 检出，从机制上堵死了两个人同时站在一根分支上互相覆盖的可能。

但要认清它的边界：git 官方文档里 worktree 只负责多工作树的写隔离，从头到尾没有任何自动合并机制，分出去的五份改动怎么合回来、语义冲突怎么处理，还是主线的活。物理冲突好办，git 会报给你看；语义冲突才要命，两个 agent 各自改了不同文件，单看都对，合在一起行为就变了，这种冲突任何工具都不会替你发现。还有一个很容易中招的细节：Claude Code 的临时 worktree 默认从仓库的 default branch 分出来，不是你会话当前的 HEAD。你会话里还没合入的改动，worktree 里的子代理根本看不见，它是基于一个旧世界在干活。

![worktree 解决什么，不解决什么](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

worktree 解决什么，不解决什么

## 第四项税：最后所有路都汇到一个瓶颈上

假设前三项税都交完了，5 份产出顺利回来，最后一关才是大头：谁来汇总、谁来验收、谁来合并跑测试？

答案只有一个：主 agent，加上屏幕前的你。官方文档专门有一条警告，多个 subagent 各自回传详细结果，会把主上下文重新吃满。你用隔离省下的上下文，在汇总这一步连本带利还回去。Anthropic 描述自家系统时也承认，lead agent 是同步执行 subagent 的，等一整批完成才走下一步；他们也考虑过异步化，但代价是要处理结果协调、状态一致性和错误传播这三座山。

验收更是纯串行。5 份交付物要一份一份读、一份一份对齐约定、合并后统一跑测试。我那次动画课件的翻车，一半时间就耗在这里：第三份产出的接口问题，是我合并完前两份之后才暴露的，返工又牵连着后面两份。并行生产，串行验收，验收才是流水线的瓶颈。

还有一层容易被忽略的风险放大效应。Anthropic 博客里写过，agent 的一步出错，可能让它走上完全不同的执行轨迹，结果不可预测。单 agent 的跑偏你在对话里当场就能看见、当场纠；5 个后台 agent 的跑偏，你要等它们全部交卷才知道，错误在各自的轨迹里已经复利了一路。人越多，发现问题的时点越晚，返工半径越大。

![汇总与验收：并行生产，串行收口](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

汇总与验收：并行生产，串行收口

## 成本账：官方自己给的数字

值不值得开多 agent，Anthropic 在工程博客里给过量级参考，引用时我把条件说全：在他们的统计里，agent 类交互的 token 消耗大约是普通对话的 4 倍，多智能体系统大约是 15 倍。他们的结论是，多智能体架构要用在任务价值高到付得起这笔溢价的地方。

同一篇博客还给了规模参考：简单的事实查证，1 个 agent 加 3 到 10 次工具调用就够；直接的对比类任务，2 到 4 个 subagent，各 10 到 15 次调用；只有复杂的研究类任务才值得上 10 个以上。注意这是研究系统的经验，编码任务的可并行度还要再打折扣。

需要说明的是，他们的多智能体系统在内部研究评测上确实比单 agent 好了 90.2%，但那是质量分，不是速度，而且是研究检索场景。拿这个数字论证"多开就是快"，属于拿着别人的账本记自己的账。

![官方成本账与规模参考](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

官方成本账与规模参考

## 面试怎么答这道题？

60 到 90 秒版本，四步。

先破直觉，十五秒：5 个 agent 快 5 倍的前提是任务完全独立可拆，这个前提在编码任务里很少成立。并行收益等于可独立拆分的部分，剩下的全是协调成本。

再列税单，三十秒：四项。一，subagent 从零启动，项目认知要重建 5 遍；二，任务间有依赖链的话，关键路径把并行退化成串行，每跳还有主 agent 中转；三，写共享文件要处理所有权和冲突，worktree 只管写隔离不管合并；四，汇总验收是主 agent 单点串行，回传的详细结果还会重新吃满主上下文。

给数字背书，二十秒：Anthropic 官方博客的量级是 agent 约 4 倍 token、多智能体约 15 倍，他们明确说这架构只配价值足够高的任务，还说编码任务里真正可并行的子任务比研究类少。

收口，十五秒：我的做法是先画依赖图再决定人头数，文件所有权切不干净的任务不并行，只读的调研类任务才放心大胆开并行。

![60 秒回答框架](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

60 秒回答框架

## 面试官大概率会追问的三个问题

追问一：文件所有权具体怎么划？要点：按目录或模块给每个 agent 划独占写区，共享代码冻结或者前置成单独任务；拿不准的 agent 一律给只读工具白名单，把写权限收在主线；合并动作永远只发生在主线一个地方，谁分出去的谁负责收。

追问二：worktree 是不是把冲突问题解决了？要点：只解决了一半。它给的是物理写隔离，代价是两个新问题：临时 worktree 默认从 default branch 分出来，看不到会话里未合入的改动，起点就是旧的；合并和语义冲突处理没有任何自动化，还是人和主线的活。隔离越彻底，合并时的信息差越大。

追问三：那什么时候 5 个真的比 1 个好？要点：三个特征同时满足的时候。任务能被切成互不依赖的块；过程产物大但结论短，隔离能省下真金白银的上下文；产出的验收标准客观，机器能判对错，不用主线逐份人肉审。典型场景是大仓库的多角度检索和审计。反过来，多阶段共享大量上下文的活，官方文档明说该留在主会话。

## 写在最后

第一，并行收益不由 agent 数量决定，由任务的依赖结构决定，先画依赖图再数人头。第二，四项并行税各有出处：重复认路、依赖串行化、文件冲突、单点验收，每一项官方文档或工程博客都白纸黑字写着。第三，worktree 是写隔离工具不是合并工具，默认从 default branch 出发这个细节，坑过的人才记得住。

也说一个我旗帜鲜明的看法：把"多开 subagent"当成性能优化手段，方向就偏了。它首先是上下文管理手段，省的是主对话的注意力，不是墙上时钟的时间。真图快，先把任务拆干净，拆不干净的任务，一个 agent 老老实实串行做完，往往就是最快的方案。

判断准则还是那句话：这个任务里，能独立拆分的部分值多少，四项税加起来要收多少。税比收益高，人多就是添乱。

我是吴师兄，下篇见。

往期推荐

[面试官皱眉："Skill、MCP、Hook 都能给 Agent 加能力，混着用不就行了？"我摇头："选错不是跑不起来，是跑起来了却在关键时刻失效"](https://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490967&idx=1&sn=6abb0b2ed96c9966336e05b1bf52193f&scene=21#wechat_redirect)

[面试官皱眉："RAG 答错了，你就改 Prompt、换模型、调大 Top-K？"我摇头："连证据在哪层丢的都不知道，改参数就是碰运气"](https://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490955&idx=1&sn=896b6978ab3bb9e4d2f9b509d174c505&scene=21#wechat_redirect)

[面试官皱眉："资料里没答案，RAG 怎么才能不硬答？"我说"设个相似度阈值"面试官直摇头："这只答到了最外层"](https://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490952&idx=1&sn=2eb7fde3ec2da14495717e7cbc2bfd7d&scene=21#wechat_redirect)

大厂真题 · 目录
