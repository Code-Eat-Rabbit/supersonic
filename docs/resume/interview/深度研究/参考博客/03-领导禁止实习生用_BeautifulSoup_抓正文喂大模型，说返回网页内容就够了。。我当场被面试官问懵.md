原创 吴师兄 _2026年6月17日 10:51_

大家好，我是吴师兄。

"返回网页内容"，上周一个学员就栽在这六个字上。

他去搜索类业务的大模型应用岗，简历上写了一行"独立实现 Deep Research Agent，支持四种工具调用"。面试官扫到这行，问了一个我听完都觉得有点刁的问题：

"你的 Visit 工具，抓一个网页回来之后，到底给模型喂的是什么？"

他答："返回网页的正文内容。"

面试官没急着评价，接着问："一篇新闻正文三千字，但导航栏、相关推荐、评论区、页脚版权加一块还有五千字，你这五千字也一起喂进去了？"

他停了两秒："……应该是过滤过的，我用 BeautifulSoup 抓了正文。"

面试官又换了个方向："那你的 Scholar 工具，搜回来的论文，你怎么确认它真的跟问题相关？就按 Semantic Scholar 返回的顺序直接拿前几篇？"

他没接上话。他确实没做相关性过滤，搜到前几篇论文，摘要直接塞进上下文，就完事了。

面试官最后说了一句，正好点在要害上："工具设计不是会调 API 就算完了。你喂给模型的是什么，比模型本身更关键。垃圾进，垃圾出。"

他后来找到我，说那次面试让他意识到一件事，自己做的其实是"能跑的 Demo"，不是"设计过的工具"。

这是 Deep Research Agent 从0到1实战系列的第三篇。前两篇我们把最小 ReAct（推理与行动，Reasoning and Acting）循环跑通了，又给它加上分级失败处理、重复搜索检测和 token 预算管理，手里已经有一个能接生产流量的执行器。

第二篇结尾我留了一句话：四件工具 Search、Visit、Scholar、Python 各自有各自的坑，下篇专门来填。

今天就是填坑这篇，我们就把这四件工具真正设计一遍，不是能调通就行，而是每一个都带上自己的质量控制逻辑，最后用一个统一接口接回第二篇的执行器。

## 一、工具的核心职责不是取回信息，是过滤噪声

第二篇我们的执行器处理过"工具调用失败"，超时、空结果、内容垃圾。但"内容垃圾"这一类里，其实藏着一个更深的问题：什么叫垃圾？

[京东面试官摇头："你的 Deep Research Agent 跑了17步，第7步到第14步在干什么？"，打开日志才发现它一直在搜同一件事](https://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490651&idx=1&sn=4c1a25f15fe736a57a048c26dac093e1&scene=21#wechat_redirect)

工具的活儿，很多人理解成"把货架上的东西拿回来"。Search 返回一页十条链接，Visit 抓回五千字网页，Scholar 找回五篇论文摘要，全塞进上下文。模型面对的就不是信息了，是噪声。

我自己在第一版系统里栽过一次。有个用户问一个技术选型的问题，Agent 的 Visit 工具访问了一篇技术博客。那篇博客正文大概两千字，是真有价值的内容。但整个页面里还塞着：侧边栏的推荐文章标题加摘要（约八百字）、读者评论区（一千多字）、"作者其他文章"列表（五百字）、页脚的版权和导航（五百字）。这五千多字一起进了模型的上下文。

下一步就出事了。模型开始推理"作者的其他文章是不是有更多信息"，还顺着一条读者评论里的观点分析了半天。整个推理跑偏了将近四步，白烧了一大把 token，最后那份报告质量很差。我排查了挺久，最后定位到根子上就是 Visit 返回的内容里掺了太多跟主题无关的东西。

所以这篇我想先把一个观点立起来： **工具最重要的职责不是"取回信息"，而是"过滤噪声"。**

一个能从五千字网页里提炼出两三百字相关内容的 Visit 工具，和一个直接把五千字全文丢回来的工具，对 Agent 是两种完全不同的输入。在我们一组四十道需要多页深读的测试题上，直接返回全文那版的任务完成率是 55%，加了相关性过滤之后到 76% 左右。同一个模型、同一批题，差距就在工具这一层。

从一开始就把"相关性过滤"当成工具的核心需求，别留到后期再优化。这件事补起来不难，但你越晚做，前面攒下的跑偏 case 越多。

![工具的职责：取回信息 vs 过滤噪声](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

工具的职责：取回信息 vs 过滤噪声

_工具的职责：取回信息 vs 过滤噪声_

## 二、Search 工具：别只做 API 结果的二传手

Search 看起来是四件套里最简单的：给个关键词，调搜索引擎 API，返回一个结果列表。但"结果列表"本身就有质量问题。

搜索引擎的返回里，内容农场、SEO 垃圾站、付费推广混在一起，排名根本不代表质量。前二十条里可能有一半正文就一句话，剩下全是广告导流。这种东西原样传给模型，纯属拿 token 喂垃圾。

Search 工具不能只做二传手，至少要加两层过滤：域名黑名单，加 snippet 质量打分。

```
import re
 from dataclasses import dataclass

 # 已知低质量域名黑名单
 # 为什么要维护这个黑名单？很多 SEO 垃圾站排名不低，
 # 但内容是拼凑的、过时的，或者点进去就是付费墙，让模型看这些是白烧 token
 LOW_QUALITY_DOMAINS = {
     "zhidao.baidu.com",      # 百度知道：答案参差，很多已过时
     "wenwen.sogou.com",      # 搜狗问问：同上
     "wenda.so.com",          # 360 问答：同上
     "tieba.baidu.com",       # 贴吧：非结构化，信噪比低
     "mp.weixin.qq.com",      # 公众号：抓不到原文，只有一段摘要
 }

 @dataclass
 class SearchResult:
     url: str
     title: str
     snippet: str
     domain: str
     quality_score: float   # 0-1，工具自己估的质量分

 async def search(query: str, num_results: int = 5) -> list[SearchResult]:
     """
     为什么 num_results 默认 5 而不是 10？
     我们测下来，前 5 条基本覆盖了九成的有效信息。
     条数越多反而让模型分心，"哪条最重要"这个判断本身也吃 token
     """
     raw_results = await _call_search_api(query, num_results=10)  # 多取一点，过滤后留 5 条

     filtered = []
     for r in raw_results:
         domain = _extract_domain(r["url"])
         if domain in LOW_QUALITY_DOMAINS:
             continue

         # snippet 太短，通常意味着内容被截断或本就是营销页
         snippet_quality = _score_snippet(r.get("snippet", ""))
         if snippet_quality < 0.3:
             continue

         filtered.append(SearchResult(
             url=r["url"], title=r["title"], snippet=r["snippet"],
             domain=domain, quality_score=snippet_quality
         ))
         if len(filtered) >= num_results:
             break

     return sorted(filtered, key=lambda x: x.quality_score, reverse=True)

 def _score_snippet(snippet: str) -> float:
     """snippet 是第一道过滤：连摘要都是垃圾，点进去大概率也是垃圾"""
     if len(snippet) < 50:
         return 0.1
     spam = ["点击查看", "立即购买", "优惠活动", "限时折扣", "免费下载"]
     if any(p in snippet for p in spam):
         return 0.2
     score = 0.5
     if re.search(r'\d+', snippet):           # 有数字，通常有具体信息
         score += 0.1
     tech = ["方案", "实现", "研究", "分析", "数据", "结果", "测试"]
     score += min(0.3, sum(1 for s in tech if s in snippet) * 0.05)
     return min(1.0, score)
```

还有一个容易忽略的点：返回格式。别把原始 JSON 直接丢给模型。模型读自然语言比读 JSON 顺，而且 JSON 里那一堆 `title` 、 `url` 、 `snippet` 字段名，十条结果叠起来也占掉不少 token。整理成一段干净的结构化文本再喂：

```
def format_search_results(results: list[SearchResult]) -> str:
     lines = [f"搜索返回 {len(results)} 条结果：\n"]
     for i, r in enumerate(results, 1):
         lines.append(f"[{i}] {r.title}")
         lines.append(f"    来源：{r.domain}")
         lines.append(f"    摘要：{r.snippet[:200]}")
         lines.append("")
     return "\n".join(lines)
```

加了域名黑名单之后，我们测试集里"模型访问到垃圾来源"的比例从 18% 压到了 5% 以内。代价也得说清楚：这个黑名单是要持续养的，新的垃圾站天天冒出来，你得隔段时间翻一遍日志补几个进去，指望一次列全不现实。

还有一点容易想当然： **域名黑名单不是哪儿都该上。** 如果你的 Agent 是垂直场景，比如只搜学术库、只搜某几个官方站点，那压根没有垃圾来源混进来，黑名单就是个永远不触发的空摆设，维护它纯属给自己加负担。它真正值钱是在"开放互联网搜索"这种来源杂、质量不可控的场景。

## 三、Visit 工具：网页访问的核心是提炼，不是复制

Visit 是四件套里最容易写出问题的一个，恰恰因为它看着最简单：访问 URL，返回文本，完了。但"返回文本"这四个字里全是细节。

它不该是"把网页内容给我"，而该是"把网页里跟我这次查询相关的内容给我"。整页复印回来，和摘出相关的几段，对模型是两种东西。区别就在工具有没有先搞清楚"这次访问到底是要解决什么问题"。

所以我把 `query` 设成 Visit 的 **必填** 参数。没有 query，工具根本不知道该留哪段，只能返回全文，等于没过滤。

```
from bs4 import BeautifulSoup
 import httpx

 async def visit(url: str, query: str, max_chars: int = 2000) -> str:
     """query 必填：工具得知道'为什么访问这个页面'，才知道该提取哪部分"""
     try:
         async with httpx.AsyncClient(timeout=10.0) as client:
             resp = await client.get(url, follow_redirects=True)
             resp.raise_for_status()
     except httpx.TimeoutException:
         return "[访问超时]"
     except Exception as e:
         return f"[访问失败：{e}]"

     main_text = _extract_main_content(resp.text)          # 第一步：去模板，扒正文
     if len(main_text) > max_chars:
         main_text = _filter_by_relevance(main_text, query, max_chars)  # 第二步：相关性过滤
     return main_text if main_text else "[页面内容无法提取]"

 def _extract_main_content(html: str) -> str:
     """为什么不直接 get_text()？那会把导航、广告、评论全卷进来"""
     soup = BeautifulSoup(html, "html.parser")
     for tag in soup.find_all(["nav", "footer", "header", "aside", "script", "style"]):
         tag.decompose()
     # 优先找语义化正文容器
     for sel in ["article", "main", '[role="main"]', ".post-content", ".article-body", "#content"]:
         el = soup.select_one(sel)
         if el and len(el.get_text(strip=True)) > 200:
             return el.get_text(separator="\n", strip=True)
     # 降级：取够长的 <p>
     paras = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 50]
     return "\n".join(paras)

 def _filter_by_relevance(text: str, query: str, max_chars: int) -> str:
     """
     为什么不直接截前 max_chars 个字符？
     很多网页前几段是背景铺垫，真正的关键信息在中间或后面。
     截头部会把最相关的内容丢掉。这里按段落拆，挑相关度最高的几段
     """
     paras = [p.strip() for p in text.split("\n") if len(p.strip()) > 30]
     if not paras:
         return text[:max_chars]

     query_words = set(query.lower().split())
     scored = []
     for idx, para in enumerate(paras):
         overlap = len(query_words & set(para.lower().split()))
         position_bonus = 0.3 if idx < 3 else 0     # 靠前的段落略加权
         scored.append((idx, para, overlap + position_bonus))

     scored.sort(key=lambda x: x[2], reverse=True)
     selected, total = [], 0
     for idx, para, _ in scored:
         if total + len(para) > max_chars:
             break
         selected.append(idx)
         total += len(para)

     # 选完按原文顺序重排，保证读起来连贯
     return "\n\n".join(paras[i] for i in sorted(selected))
```

![Visit 工具的两阶段内容处理](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

Visit 工具的两阶段内容处理

_Visit 工具的两阶段内容处理_

Visit 还得跟第二篇的垃圾内容检测对齐。第二篇里我们写过一个 `_check_content_quality()` ，专门认付费墙和登录提示。Visit 里直接复用，让它返回状态而不是闷头 raise，执行器才好根据状态决定下一步：

```
async def visit_with_quality_check(url: str, query: str) -> tuple[str, str]:
     """返回 (内容, 状态)。状态：ok / paywall / empty / error"""
     content = await visit(url, query)
     if "请登录" in content or "订阅后查看" in content or len(content) < 100:
         status = "paywall" if ("登录" in content or "订阅" in content) else "empty"
         return "", status      # paywall 让模型换免费来源，empty 让它弃掉这个 URL
     return content, "ok"
```

**段落级相关性过滤，我一开始就没用 embedding。** 这点跟不少教程是反着来的。网上很多写法是把网页按段切开，每段算一次 embedding 跟 query 求余弦相似度，挑最高的几段。听起来更"准"，但 Visit 是高频调用的工具，一次深度研究可能访问十几个页面，每个页面再切成几十段，全量算 embedding，延迟和调用成本一下就上去了。我先用关键词重叠这种轻量方案扛着，它覆盖了大部分情况，省下的延迟在 Agent 这种连环调用的场景里很实在。

当然它有失效的地方，得讲清楚： **关键词重叠在 query 和正文语言不一致时基本歇菜。** 用户用中文问，页面是英文正文，词对不上，过滤就退化成乱选。碰到这种跨语言场景，要么先把 query 翻译成目标语言再做重叠，要么这时候才值得上 embedding。把贵的方案留给真正需要它的场景，而不是一上来全场景套。

工具里这种"必填还是可选""轻量还是上模型"的取舍，恰恰是面试官最爱往深里追的地方。我在官网题库整理了 Agent 工具设计这块的高频追问题，按公司和难度分好了，想提前练手的可以去翻翻。

## 四、Scholar 工具：学术文献的门槛比网页更高

Scholar 工具调学术搜索 API（比如 Semantic Scholar 或 arXiv），返回相关论文。它的特殊在于：学术内容的质量门槛跟普通网页不一样，相关性过滤的逻辑也不一样。

你要的不是"关键词匹配上的论文"，是"真跟问题相关、来源可靠、时间也合理"的论文。直接按检索引擎排序拿前几篇，很容易抓回一堆引用数巨高、其实是相邻领域的论文。

我们接 Semantic Scholar 的时候就踩过这坑。有个用户问某个模型架构的优化方法，Scholar 返回了五篇引用数很高的论文，结果其中三篇是这个架构的基础综述，跟"优化方法"关联度很低。模型把这三篇综述的摘要挨个看了一遍，一大把 token 全花在背景知识上，反而没集中在用户真正要的那点东西。

这里有个反直觉的点， **别拿引用数当相关性排序。** 引用数高的常常是奠基性工作，但对一个具体问题未必最有用。用户问"Transformer 的位置编码有哪些改进方法"，Attention is All You Need 引用数最高，可它本身根本不讲"改进方法"。

```
from dataclasses import dataclass
 from datetime import datetime
 from typing import Optional

 @dataclass
 class ScholarResult:
     title: str
     abstract: str
     year: int
     citation_count: int
     venue: str                      # 发在哪个会议/期刊
     open_access_url: Optional[str]  # 有没有免费全文
     relevance_score: float

 async def scholar_search(query: str, max_results: int = 3) -> list[ScholarResult]:
     """
     为什么默认只要 3 篇？学术摘要一般 250-400 字，3 篇就是七百到一千二。
     这个量对模型刚好：背景够看，又不会被一堆引用和实验细节淹掉
     """
     raw = await _call_semantic_scholar(query, limit=10)
     results = []
     for paper in raw:
         abstract = paper.get("abstract", "")
         if not abstract or len(abstract) < 50:      # 没摘要的直接跳过
             continue
         results.append(ScholarResult(
             title=paper.get("title", ""),
             abstract=abstract[:500],
             year=paper.get("year", 0),
             citation_count=paper.get("citationCount", 0),
             venue=paper.get("venue", "未知"),
             open_access_url=(paper.get("openAccessPdf") or {}).get("url"),
             relevance_score=_compute_relevance(query, paper),
         ))
     results.sort(key=lambda x: x.relevance_score, reverse=True)   # 按相关性，不按引用数
     return results[:max_results]

 def _compute_relevance(query: str, paper: dict) -> float:
     score = 0.0
     qwords = set(query.lower().split())
     title = paper.get("title", "").lower()
     abstract = paper.get("abstract", "").lower()
     # 标题命中：高权重
     score += len(qwords & set(title.split())) / max(len(qwords), 1) * 0.5
     # 摘要命中：中权重
     score += len(qwords & set(abstract.split())) / max(len(qwords), 1) * 0.3
     # 时间：快速发展的领域，近几年的更值钱
     year = paper.get("year", 0)
     cur = datetime.now().year
     if year >= cur - 2:
         score += 0.15
     elif year >= cur - 5:
         score += 0.05
     if (paper.get("openAccessPdf") or {}).get("url"):   # 有全文可访问，加一点
         score += 0.05
     return min(1.0, score)
```

格式化的时候有个细节：要把年份和发表会议带上。学术摘要里的数据通常比博客可靠，但也更滞后，最新的工程实践未必进了论文。所以工具不替模型下"这篇可不可信"的结论，只把年份、venue、被引数摆出来，让模型自己掂量来源有多新、有多权威。

```
def format_scholar_results(results: list[ScholarResult]) -> str:
     if not results:
         return "未找到相关学术文献。"
     lines = [f"找到 {len(results)} 篇相关文献：\n"]
     for i, r in enumerate(results, 1):
         lines.append(f"[{i}] {r.title}（{r.year}年 · {r.venue} · 被引 {r.citation_count}）")
         lines.append(f"    摘要：{r.abstract}")
         if r.open_access_url:
             lines.append(f"    全文：{r.open_access_url}")
         lines.append("")
     return "\n".join(lines)
```

按相关性重排比按引用数排，多花的就是每篇算一遍打分的那点计算，可以忽略。真正的代价在召回那一步：你得多取一些（我取了 10 篇）再筛到 3 篇，API 调用的量上去了一点。换来的是模型不再被综述带跑，这笔账在学术类问题上很划算。

## 五、Python 工具：安全沙盒是必须项，不是可选项

Python 工具是四件套里最特殊的。前面三个都是读取外部信息，Python 是让模型"执行代码"。这里有个本质区别：你不能让 LLM 生成的代码直接在生产环境裸跑。

LLM 写出来的代码，有可能调 `os.system()` 执行系统命令，用 `open()` 读写本地文件，import `subprocess` 起任意进程，甚至不小心写了个死循环把 CPU 跑满。这些在 Deep Research 任务里不常见，但一旦发生就是真事，等于把一台没人盯着的机器，交给了一段不可控的代码。

我的做法是两关：执行前静态检查（白名单优先于黑名单），加子进程隔离里跑。

```
import subprocess, tempfile, os, sys

 # 白名单：允许的标准库
 # 为什么用白名单不用黑名单？黑名单容易漏（禁了 subprocess 忘了禁 os.popen），
 # 白名单是明确的：只有这些算安全
 ALLOWED_IMPORTS = {
     "math", "statistics", "json", "re", "datetime",
     "collections", "itertools", "functools",
     "numpy", "pandas", "scipy",
 }

 DANGEROUS_PATTERNS = [
     "import os", "import sys", "import subprocess", "__import__",
     "eval(", "exec(", "open(", "file(",
     "socket", "urllib", "requests", "httpx",   # 网络
     "shutil", "glob",                          # 文件
 ]

 def validate_code(code: str) -> tuple[bool, str]:
     """先做文本静态检查，把明显危险的请求提前拒掉，缩小沙盒的攻击面"""
     for p in DANGEROUS_PATTERNS:
         if p in code:
             return False, f"代码包含不允许的操作：{p}"
     return True, ""

 async def python_execute(code: str, timeout: int = 10) -> str:
     """
     timeout 为什么 10 秒？Deep Research 里的 Python 多半是数值计算或数据处理，
     正常 3 秒内出结果。10 秒上限能覆盖复杂计算，又能挡住死循环吃满时间片
     """
     ok, reason = validate_code(code)
     if not ok:
         return f"[代码验证失败：{reason}]"

     with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
         # 在代码最前面注入限制：import 只放行白名单，禁掉危险内置函数
         prefix = f"""
 _orig_import = __builtins__.__import__
 def _safe_import(name, *a, **k):
     if name.split('.')[0] not in {ALLOWED_IMPORTS}:
         raise ImportError("不允许导入 " + name)
     return _orig_import(name, *a, **k)
 __builtins__.__import__ = _safe_import
 __builtins__.__dict__['open'] = None
 __builtins__.__dict__['eval'] = None
 __builtins__.__dict__['exec'] = None
 """
         f.write(prefix + "\n" + code)
         tmp = f.name

     try:
         r = subprocess.run([sys.executable, tmp], capture_output=True, text=True, timeout=timeout)
         if r.returncode != 0:
             # 只回最后 5 行错误，完整堆栈对模型没用
             return "[执行出错]\n" + "\n".join(r.stderr.strip().split("\n")[-5:])
         out = r.stdout.strip()
         if len(out) > 2000:
             out = out[:2000] + f"\n[输出已截断，共 {len(out)} 字符]"
         return out or "[代码执行完成，无输出]"
     except subprocess.TimeoutExpired:
         return f"[执行超时：超过 {timeout} 秒]"
     finally:
         os.unlink(tmp)
```

错误信息怎么回，这是个容易被忽略的细节。完整的 Python 堆栈通常二十来行，大半是框架内部的调用链，跟模型写的那几行逻辑没关系。你把整段堆栈喂回去，模型容易被中间那些层带偏，烧一堆 token 去分析其实无关的中间调用。只回最后五行（真正报错的地方），模型改代码的成功率反而更高。

子进程加白名单这套，代价是每次执行都有子进程启动的开销，大概几十毫秒，比直接 in-process 跑慢。但这点延迟换的是安全，值。它能覆盖九成以上的需求。剩下那些更高安全要求的场景，比如要跑不可信的复杂代码，才需要上容器或者 gVisor、Firecracker 这类隔离，但它们冷启动有额外延迟，在 Agent 高频调用下开销不小，别无脑套。

timeout 也别追求"永不超时"，就设短，10 到 15 秒。超时本身是个信号：一段正常的数值计算要是跑过 10 秒，多半是代码逻辑出了问题（数据量估错了，或者循环条件写错了），让模型重想一遍，比让它干等强。

## 六、ToolRegistry：把四件套统一接回执行器

四个工具内部逻辑各不相同，但对外的接口得统一。执行器通过一个 `ToolRegistry` 调用，不需要知道每个工具内部怎么实现的。

```
from typing import Callable
 from dataclasses import dataclass

 @dataclass
 class ToolDefinition:
     name: str
     description: str    # 给模型看的，说明这工具能干嘛
     parameters: dict    # JSON Schema，模型照着填参数
     fn: Callable        # 真正的执行函数

 class ToolRegistry:
     """
     为什么要 Registry，不在执行器里 if/elif 判断工具名？
     Registry 让工具能动态注册。技术研究和市场分析挂的工具集不一样，
     换工具集只动注册表，主循环代码一行不用改
     """
     def __init__(self):
         self._tools: dict[str, ToolDefinition] = {}

     def register(self, t: ToolDefinition):
         self._tools[t.name] = t

     async def call(self, name: str, args: dict) -> str:
         if name not in self._tools:
             return f"[工具不存在：{name}]"
         try:
             return str(await self._tools[name].fn(**args))
         except Exception as e:
             return f"[工具执行异常：{e}]"

     def get_schema(self) -> list[dict]:
         return [{"name": t.name, "description": t.description, "parameters": t.parameters}
                 for t in self._tools.values()]

 def build_research_tools() -> ToolRegistry:
     reg = ToolRegistry()
     reg.register(ToolDefinition(
         name="search",
         description="用关键词搜索互联网，返回相关网页列表（标题、来源、摘要）。适合快速摸清一个话题的概况，或找到值得深入读的来源。",
         parameters={"type": "object", "properties": {
             "query": {"type": "string", "description": "搜索关键词，越具体越好"}}, "required": ["query"]},
         fn=search))
     reg.register(ToolDefinition(
         name="visit",
         description="访问一个网页，提取与当前研究目标相关的内容。用在你已经找到一个值得深读的来源之后。",
         parameters={"type": "object", "properties": {
             "url": {"type": "string", "description": "完整 URL"},
             "query": {"type": "string", "description": "当前研究的核心问题，用于相关性过滤"}},
             "required": ["url", "query"]},
         fn=visit_with_quality_check))
     reg.register(ToolDefinition(
         name="scholar",
         description="搜索学术论文库，返回相关论文的标题、摘要和发表信息。适合需要可靠学术来源的技术问题。",
         parameters={"type": "object", "properties": {
             "query": {"type": "string", "description": "研究主题关键词，建议用英文以获得更好的召回"}},
             "required": ["query"]},
         fn=scholar_search))
     reg.register(ToolDefinition(
         name="python",
         description="执行 Python 代码，用于数值计算、数据处理或统计分析。禁止网络访问和文件读写。",
         parameters={"type": "object", "properties": {
             "code": {"type": "string", "description": "要执行的代码，最后一行用 print() 输出结果"}},
             "required": ["code"]},
         fn=python_execute))
     return reg
```

![Deep Research 四件套工具集成架构](data:image/svg+xml,%3C%3Fxml version='1.0' encoding='UTF-8'%3F%3E%3Csvg width='1px' height='1px' viewBox='0 0 1 1' version='1.1' xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'%3E%3Ctitle%3E%3C/title%3E%3Cg stroke='none' stroke-width='1' fill='none' fill-rule='evenodd' fill-opacity='0'%3E%3Cg transform='translate(-249.000000, -126.000000)' fill='%23FFFFFF'%3E%3Crect x='249' y='126' width='1' height='1'%3E%3C/rect%3E%3C/g%3E%3C/g%3E%3C/svg%3E)

Deep Research 四件套工具集成架构

_Deep Research 四件套工具集成架构_

把第二篇的执行器和这篇的四件套接上，一个能在生产里跑的 Deep Research Agent 骨架就成形了。工具注册统一交给 ToolRegistry，别在主循环里写死调用逻辑。这样以后换工具集，只动注册表，主循环稳着不动。

## 七、面试怎么答工具设计这道题？

面试官问"你的 Agent 用了哪些工具，怎么设计的"，最差的答法是把工具名报一遍：Search、Visit、Scholar、Python，完。下一句必然是"那怎么设计的"，然后就卡住了。

**先把核心问题点出来（30 秒）：**

"工具设计的核心不是会调 API，是控制返回给模型的内容质量。我们第一版 Visit 直接返回网页全文，五千字里有三千多是导航、评论、广告，模型在这堆噪声里推理，跑偏得厉害。后来给每个工具加了专属的质量过滤层，多页深读类任务的完成率从 55% 提到了 76% 左右。"

**再逐个说关键设计（1 分钟）：**

"Search 加了域名黑名单和 snippet 打分，默认返回 5 条不是 10 条。Visit 把 query 设成必填，做段落级相关性过滤，挑最相关的段落而不是直接截前 N 个字符。Scholar 按相关性排序而不是引用数排序，并且把年份和发表会议标出来，让模型自己判断来源可不可靠。Python 跑在子进程里，有模块白名单和 10 秒超时，错误只回最后 5 行。"

**如果追问"Python 为什么不用容器而是子进程"（30 秒）：**

"Deep Research 里的 Python 任务多半是简单数值计算，不需要完整容器隔离。子进程加白名单能覆盖九成以上的安全需求，而容器冷启动有额外延迟，在 Agent 高频调用下不划算。真要更高安全等级，可以上 gVisor 或 Firecracker，但得认这个延迟代价。"

把这些取舍说出来，为什么返回 5 条不是 10 条、为什么 query 给 Visit 设成必填、为什么错误只回 5 行，面试官能感觉到你是真做过、真想过，不是只撸了一个调 API 的壳。

## 写在最后

这三篇连起来，你手里已经有一个能跑的 Deep Research Agent 完整基础层了：最小 ReAct 循环（第一篇）、生产级执行器（第二篇）、带质量控制的工具集（这一篇）。

但你接着会撞上一个根子上的问题：碰到需要十五步以上的复杂研究任务，上下文还是会随步数线性涨。即便有 token 预算管理在减速，终究有个上限。搜了十几次之后，历史里堆了一大堆信息，模型对早期那几个关键事实的注意力会掉下来，推理质量开始飘。

这个问题，优化工具是解不掉的，得在框架层动一刀：用一份不断演进的研究报告，替掉线性堆积的历史记录。这就是 IterResearch 的核心思路，下一篇来讲。

今天这道题，只是 Deep Research Agent 工具层的一个切面。真正备面的时候，光看懂一篇不够，你得把整条工具链自己跑一遍，还得见过同一个点被面试官从不同角度追问的样子。Agent 工具设计这块的关联面试题，我按公司和难度分好放在了官网题库。

我是吴师兄，我们下篇文章见。

往期推荐

[京东面试官摇头："你的 Deep Research Agent 跑了17步，第7步到第14步在干什么？"，打开日志才发现它一直在搜同一件事](https://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490651&idx=1&sn=4c1a25f15fe736a57a048c26dac093e1&scene=21#wechat_redirect)

[字节面试官皱眉："你这 Agent 跟带搜索的 ChatGPT 有啥区别？"我答："能多轮搜，搜完接着搜啊"，他追问了一句搜索词……](https://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490642&idx=1&sn=94dfd48b393ceb8dfdc73e3ee5c7fb38&scene=21#wechat_redirect)

[蚂蚁面试官："187 条数据也敢写首轮训练？"我笑了："翻车归因在简历下半页"，面试官："下周二面我亲自来"](https://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490538&idx=1&sn=6e5af58188e73082d295e25a6ef8d042&scene=21#wechat_redirect)

[字节食堂打饭，我问同事"文档全塞进 context，模型咋更蠢了"，阿姨勺子一停："窗口能装 100 万，不代表 100 万字都看得进去啊。"](https://mp.weixin.qq.com/s?__biz=MzkzMDIwMzg1Mw==&mid=2247490529&idx=1&sn=28cc51d15c84fdab50f17602b11ee26d&scene=21#wechat_redirect)

大厂真题 · 目录
