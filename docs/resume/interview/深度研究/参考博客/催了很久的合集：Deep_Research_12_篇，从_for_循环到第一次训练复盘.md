原创 吴师兄 _2026年7月3日 10:00_

大家好，我是吴师兄。

上个月那篇讲首轮训练复盘的文章下面，有条留言我一直记着："希望能看到前面几篇的合集"。

后台私信里问得更直接：系列到底有几篇，先看哪篇，哪几篇讲训练，问得有道理。

这个系列从 4 月初写到现在，断断续续发了 12 篇，因为写起来确实费劲，中间还穿插了别的选题，有几篇后来因为前文有 bug，又重写优化过重新发了一遍，老读者跟着追还能拼出脉络，新关注的朋友点开历史文章，看到的是一堆"面试官问"，根本不知道从哪下手。

所以今天这篇不讲新东西，就干一件事：把 12 篇按学习顺序重新串一遍。注意是学习顺序，不是发布顺序。发布顺序是我边做边写的顺序，学习顺序是你上手应该走的顺序，这两个不一样。

每篇我用三四句话讲清楚：它解决什么问题，看完你能带走什么，什么情况下可以跳过。你可以把这篇收藏了当目录用，读到哪勾到哪。

![Deep Research Agent 从 0 到 1 · 12 篇学习地图](https://mmbiz.qpic.cn/sz_mmbiz_png/uvQZiaXrG4t5QyR8dxKjZhhj7XibMZibWydP7yknLGDsDMFRZPhNWX3RF0x6MPwrficKdibcc7Od7v30GJmu9siblRf1o5kvtYXYl7ek6kPBOFJzY/640?from=appmsg&watermark=1&tp=webp&wxfrom=5&wx_lazy=1#imgIndex=0)

Deep Research Agent 从 0 到 1 · 12 篇学习地图

## 阶段一：先让它跑起来（第 1 到 4 篇）

这个阶段解决一个问题：从零写出一个能跑、而且敢接真实流量的 Deep Research Agent 执行器。不碰训练，只碰工程。

**第 1 篇： [你这 Agent 跟带搜索的 ChatGPT 有啥区别？](http://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490642&idx=1&sn=94dfd48b393ceb8dfdc73e3ee5c7fb38&chksm=c27c8df0f50b04e6e96923cf3230841a165f4cf340946f37ed239a80ca08231d5f7666d5cdc0&scene=21#wechat_redirect)**

系列开篇。从 RAG、带搜索的对话产品和 Deep Research 的本质差异讲起，然后写出一个最小可用的 ReAct 循环：一个 while，模型决定搜什么，工具返回结果，模型决定下一步。看完你会发现 Deep Research 的骨架真的就是个循环，但也会明白为什么"for 循环就叫 Deep Research"会被面试官追问到哑口无言：骨架谁都写得出来，差距全在后面十一篇讲的细节里。

**第 2 篇： [跑了 17 步，第 7 步到第 14 步在干什么？](http://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490651&idx=1&sn=4c1a25f15fe736a57a048c26dac093e1&chksm=c27c8df9f50b04ef639d08ad3216f4cf3e0800c7d3650177cebf03f542a90e14a5e2e7c451d7&scene=21#wechat_redirect)**

把最小循环升级成生产级执行器。核心是四件事：分级的工具失败处理、用 embedding 做重复搜索检测（不做这个，你的 Agent 会在第 7 步到第 14 步反复搜同一件事，标题就是这么来的）、token 三档预算管理、结构化日志。这篇的日志设计后面每一篇都在用，跳过它，后面看别人翻日志定位问题时会跟不上。

**第 3 篇： [抓回一个网页，到底给模型喂了什么？](http://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490657&idx=1&sn=094ffc716d978c6f8b55c86507952d06&chksm=c27c8dc3f50b04d55640579389ba3bed70c8c42b701ca4c9990490055bfa0e75f41a769cfab1&scene=21#wechat_redirect)**

工具篇。Search、Visit、Scholar、Python 四件套的完整实现，重点不在调通，而在每个工具后面那层质量过滤：Visit 抓回来的网页，导航栏、评论区、推荐位占了一大半，直接喂给模型就是拿 token 换垃圾。这篇讲怎么只留正文。做过爬虫的人可以快速翻，没做过的建议细读，工具喂进去什么，决定了整个系统的上限。

**第 4 篇： [工具调用失败率 12%，你当线上是实验室 Demo？](http://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490133&idx=1&sn=dd973475824444c23a18a68c8284409a&chksm=c27c8bf7f50b02e14f10284eb9cf3008d15e598a0b25bc9477fdba462854e89830d7b5e2dd33&scene=21#wechat_redirect)**

兜底篇。搜索 API 超时、网页 403、代码执行报错，每一类失败该重试、该降级还是该放弃，策略是不一样的。加个 try/except 失败就跳过，这是我见过最常见也最伤的写法：错误不处理会顺着链路往下传，最后在报告里变成一句看起来很有道理的胡话。

## 阶段二：跑得久，还不崩（第 5 到 7 篇）

执行器能跑十步之后，真正的麻烦才开始：上下文装不下、搜回来的东西质量参差、整个系统怎么攒成能上线的架构。这三篇解决"从能跑到能用"。

**第 5 篇： [跑了 20 步，模型记不住第 3 步找到的结论了](http://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490293&idx=1&sn=eb3a1f5648c0d3656a222fb6e4db6549&chksm=c27c8b57f50b024179ae76e87c13894204a96ee1f929c4111ba5aa8cc06e841953b0dc4e79fd&scene=21#wechat_redirect)**

上下文篇，也是全系列我最建议精读的一篇。ReAct 的线性历史跑到 15 步以上必然塌，把窗口开大不解决问题只推迟问题，还把成本抬上去了。解法是用一份持续演进的研究报告替换线性历史，每一步只带着"到目前为止的结论"往前走。这个思路不止 Deep Research 能用，任何长链路 Agent 都用得上。

**第 6 篇： [搜了 150 条结果，8 篇是同一篇转载](http://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490322&idx=1&sn=813364a61e172e4f48ef17fcba39af24&chksm=c27c8ab0f50b03a65d353cd7ebb495d900f108f75b6e4005477e28e10afd22562a302daabb21&scene=21#wechat_redirect)**

来源质量篇。上下文管理做得再好，喂进去的本身是垃圾也白搭。这篇讲搜索结果的去重和可信度分层：怎么识别出 8 篇"独立来源"其实是同一篇稿子的转载，怎么给域名和内容做可信度打分。写研究类 Agent 的人早晚要撞这个问题，早看早省事。

**第 7 篇： [跑五十步就崩，这是玩具](http://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490343&idx=1&sn=c386c42af26e60287d873f36b6eaa1d6&chksm=c27c8a85f50b03938a6c62cdb67d1b3719d894b6f8fddb7731e7acd3b1e9d8871155c3b639b6&scene=21#wechat_redirect)**

架构篇，阶段二的收束。把前面六篇的零件拼成完整系统：执行器、工具层、上下文管理、失败兜底各放在哪一层，模块之间怎么传状态。如果你只想搭系统不打算碰训练，读到这篇可以先停，后面五篇是另一个世界的事。

## 阶段三：训练侧，让模型本身变强（第 8 到 12 篇）

前七篇都在"用现成模型"。这五篇回答另一个问题：怎么训练一个自己的 Deep Research 模型。这是目前公开中文内容里写得最少的部分，也是这个系列后半段的重心。

**第 8 篇： [训练数据从哪来？"网上爬的"换不来 offer](http://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490707&idx=1&sn=f6da3b6a24c2ed25e2797fe84eb2dc56&chksm=c27c8d31f50b0427b8e3584fa96cc318d077a66c6b8dda686eec272328e7a09324edc770dfbc&scene=21#wechat_redirect)**

数据构造篇。现成的问答数据集训不出多步深挖行为，因为单跳、两跳问题和 Deep Research 需要的复杂度之间有断层。这篇讲四种造题方法：知识图谱随机游走、种子问题迭代升级、形式化推理链、实体替换，以及配比怎么定。训练侧一切工作的地基。

**第 9 篇： [Teacher 搜错了，你也学？](http://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490373&idx=1&sn=bafa55d93d247ae12be7085b4038a661&chksm=c27c8ae7f50b03f17bb3b4722cc1786c3da18b7753b6348196d7db716b1bf7c45c1dd664b5cb&scene=21#wechat_redirect)**

轨迹过滤篇。有了问题还要有"解题过程"，也就是 Teacher 模型采出来的搜索轨迹。但轨迹不是采了就能用：答案对但过程绕远路的、过程对但格式崩掉的、蒙对的，都要按不同规则处理。这篇讲三阶段过滤漏斗，最后大概只留三成多。只想看结论的人容易低估这篇，实际训练里数据过滤吃掉的时间比训练本身多。

**第 10 篇： [准确率 71% 到 94%，这个数怎么来的？](http://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490352&idx=1&sn=c939b0dfe04ec996333465dc36104aa1&chksm=c27c8a92f50b0384cd4b719cbd9415ca994769867793abdd52cf44b157c66f4519d06d9cdfec&scene=21#wechat_redirect)**

SFT 冷启动篇。从数据到第一版模型：Loss 该 mask 掉什么（observation 不算 loss，这一步做错整个训练白跑）、训练参数怎么定、以及最重要的，评估链路怎么搭。工具调用准确率这种数字，能把"怎么测出来的"讲圆，比数字本身值钱。

**第 11 篇： [跑一次就交卷？那 22% 错的用户活该吗](http://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490376&idx=1&sn=5fd397cbd39e393672167683d0a4d4a3&chksm=c27c8aeaf50b03fc634d3660a76a10cc2926d2fc24065a1b87362407eaf8366176f336e6f842&scene=21#wechat_redirect)**

推理扩展篇。模型训完了，单次推理仍有随机性，同一个问题这次对下次错。Best-of-N、并行采样加裁判这些推理时扩展手段怎么选、代价是几倍的推理成本、什么场景划得来。预算敏感的场景建议把这篇里的成本账自己重新算一遍。

**第 12 篇： [格式分从 4 飙到满分，你就说训练成功了？](http://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490538&idx=1&sn=6e5af58188e73082d295e25a6ef8d042&chksm=c27c8a48f50b035e12f6a783d6ed936cc4f7cdc10f203afd647d0b98c82bd11055958c3b0971&scene=21#wechat_redirect)**

首轮训练复盘篇，系列目前的最后一篇。187 条数据跑第一轮训练，格式分拉满，看着很成功，拆开看工具选择的正确率惨不忍睹。这篇把翻车归因完整走了一遍：哪些指标是虚胖，哪些才说明模型真的学到了。失败复盘比成功案例信息量大，这篇是全系列评论区争论最多的一篇。

## 三种读法

12 篇全读大概要几个晚上，不是每个人都需要。按你的目标挑：

| 你的情况                        | 建议读法                                            |
| ------------------------------- | --------------------------------------------------- |
| 想快速搞懂 Deep Research 是什么 | 第 1、5、8 篇，三篇看完框架就有了                   |
| 要自己搭一个系统上线            | 第 1 到 7 篇按顺序读，训练侧可以先放                |
| 简历上写了这个项目，要应付追问  | 第 2、4、9、10、12 篇，面试官爱问的全在细节和翻车里 |
| 关心训练侧，想自己训模型        | 第 8 到 12 篇按顺序，第 5 篇补上下文背景            |

不管哪种读法，第 12 篇的翻车复盘都值得读。知道别人在哪摔过跤，比多看一篇成功经验有用。

## 系列接下来写什么

这个系列规划了 15 篇，还差三块：一是停止条件，Deep Research 真正值钱的不是会搜，而是知道什么时候停，这篇已经在草稿箱了；二是奖励函数设计的完整展开；三是整个系列的成本账，从推理到训练一次跑下来到底花多少钱。

写完这三篇，这个系列就差不多可以收口了。

然后说点其它的，这个系列写了三个月，中间有几篇发出去阅读平平，我一度怀疑过要不要继续。让我改主意的是评论区：留言问的问题越来越具体，从"Deep Research 是什么"变成"轨迹过滤的第二阶段为什么卡格式"。

大家都在跟着往深处走，这比阅读量诚实，特别是昨天的几个评论，我觉得有必要继续把实战内容完善下去。

![图片](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

如果你只带走一个判断：Deep Research 的门槛不在那个循环，在循环外面的所有东西。工具喂什么、上下文留什么、失败怎么兜、数据怎么造、翻车怎么归因，每一层都是活。那个循环三十行就能写完，剩下的每一层，才是这 12 篇真正在讲的东西。

我是吴师兄，下篇见。

大厂真题 · 目录
