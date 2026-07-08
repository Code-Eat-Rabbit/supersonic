# SuperSonic 25 天前端学习计划 — 设计规格

> 版本: v1.0 | 日期: 2026-07-08 | 状态: 已确认

## 一、背景与目标

### 1.1 学习对象

SuperSonic（腾讯音乐开源）— Chat BI + Headless BI 平台。
仓库路径：`~/workspace/supersonic`

### 1.2 目标定位

**面试准备型**：能讲清楚前端架构和简历 7 条关键模块的实现原理，逐条吃透代码 + 能应对追问，后端了解数据流即可。

### 1.3 约束条件

| 维度 | 约束 |
|------|------|
| 时间 | 25 天，每天 6-8h（约 150-200h） |
| 前端工程化基础 | 几乎为零（只会写 React 组件，不懂构建工具/Monorepo） |
| TypeScript | 不需要单独学（Java 泛型/接口思维可迁移） |
| 项目跑通 | 前后端全链路（Maven + Java + MySQL + pnpm） |
| 已有经验 | 之前跑通过项目，Day 1 跑通无难度 |

### 1.4 参考资料

- `docs/项目简历亮点.md`（简历 7 条面试准备速查）
- `/Users/yourton_ma/Documents/frontend_tutorials/前端方向文章合集/`（经验贴合集）
- 记忆中的 React 学习进度：Academind 课程第 10 章（useEffect/useReducer/Context API 进行中）

## 二、设计原则

### 2.1 三层漏斗过滤

```
Layer 1: 全局观（覆盖面 100%，广而浅）
    ↓
Layer 2: 功能模块深入（覆盖面 ~60%，按模块深挖）
    ↓
Layer 3: 简历亮点面试准备（覆盖面 7 条，精炼话术 + 模拟面试）
```

### 2.2 面经驱动 + 代码精读并行

每个模块的学习流程分两步，缺一不可：

**第一步：代码精读或动手调试**
- 通读核心源文件，标注关键逻辑和数据流
- Layer 2 优先用 debug 断点追踪（如 Chat BI 对话流、登录鉴权链路）
- 部分模块辅以手写 mini demo（如 chat-sdk 独立包、语义模型表单）

**第二步：产出面试问答文档**
- 基于精读理解，提炼面试官会问什么、怎么回答
- 两层并行，不割裂——看不懂代码就写不出有深度的面经

面经格式：30 秒一句话概括（定义→原理→示例）+ 3-5 个问题 × 结构化回答（背景→技术路径→结果）+ 追问链。

### 2.3 工程化融入实战

不单独排理论课。pnpm、Rollup、UmiJS 等工程化知识在 Layer 1 速览建立概念，在 Layer 2/3 读代码时深入细节。

### 2.4 React 进阶随项目学

custom hooks、useCallback/useMemo、Context Provider 等高级模式不单独排课，在阅读 chat-sdk 代码时遇到即学。

## 三、详细日程

### Layer 1：全局观（Day 1-4）

| 天 | 主题 | 核心内容 | 配套阅读资料 |
|---|------|---------|------------|
| Day 1 | 项目跑通 | Maven build + Java 启动后端 + MySQL + LLM key + pnpm dev 前端 | 前端项目调试完全指南：从VSCode到Chrome DevTools |
| Day 2 | 前端项目结构全景分析 | ① 包职责地图（supersonic-fe vs chat-sdk）② 路由与页面映射（/chat, /model, /agent, /login, /system 等）③ 组件树层级（ChatProvider → Chat → ChatItem → ChatMsg）④ 状态流转图（一次对话的完整状态机） | —（以代码为主） |
| Day 3 | 前端工程化速览 + 方案对比 | ① pnpm workspace vs npm/yarn workspaces vs Turborepo/Lerna ② Rollup vs Webpack vs Vite vs esbuild ③ UmiJS vs CRA vs Next.js ④ 同源方案对比（为什么选当前这套）⑤ SuperSonic config.ts 精读（代理/路由/权限/环境变量/antd/MFSU） | 为什么要有前端构建工具、简单理解Webpack、Tree Shaking原理、前端工程化面试考点、缩小打包体积指南、Vite构建优化/路由懒加载/manualChunks、Monorepo高频问题与标准答法、Monorepo构建业务组件库 |
| Day 4 | 自定义 Hooks 基础 + 组件树/状态流转 | ① 自定义 Hook 基础：规则（use 前缀/顶层调用/纯函数）、常见模式（封装状态逻辑、复用副作用）、手写一个 mini usePolling ② 组件树层级深入：ChatProvider → Chat → ChatItem → ChatMsg ③ 状态流转图：一次对话的完整状态机（parseResult→msgData→queryMode→currentParseInfo）④ chat-sdk 如何被宿主消费 | React Hooks 源码深入解析、自定义 Hook 专题、高频手撕自定义 Hooks、React 状态管理工具选型（Redux vs Zustand vs Context）、前端路由原理与工程实现 |

**Layer 1 产出**：`docs/面经/01-全局观/` 4 篇，每篇 5 个 Q&A。

### Layer 2：功能模块深入（Day 5-15）

每个模块的学习路径：**精读资料 → 读代码/调试/demo → 写面经**

| 天 | 功能模块 | 核心代码路径 | 学习方式 | 配套阅读资料 |
|---|---------|-------------|---------|------------|
| Day 5-7 | Chat BI 核心对话流（3天） | ChatPage → ChatProvider → Chat → ChatItem → ChatMsg → ECharts；usePolling/hooks/services/types | Debug 断点追踪一次完整对话 | 流式渲染：SSE vs WebSocket 方案选型、流式输出全流程解析、SSE 实时 AI 对话方案、流式渲染模块逐字输出、闭包深度解析/React 闭包问题；渲染稳定性：虚拟列表抖动 & 流式 Markdown 闪烁；图表：ECharts 自适应优化、ECharts 面试考点；组件设计原则、边界与鲁棒性、前端常用设计模式 |
| Day 8-9 | 语义模型配置（2天） | /model/* 路由族：Domain → Model → Metric → Dimension → Dataset CRUD | 手写 mini 指标创建表单 demo | React 动态表单实现与技术设计、通用列表与表单逻辑抽象、Ant Design 组件库使用实践 |
| Day 10-11 | 登录鉴权全链路（2天） | /login → request 拦截器(token) → Umi access 插件 → 路由守卫 → 按钮级权限 | Debug 追踪登录→鉴权→渲染 | Axios 拦截器与统一登录封装、前端登录功能实现方案/登录方案技术详解、前端项目权限管理分类总结、React 项目中的登录体系设计、前端安全与跨域请求综合指南 |
| Day 12-13 | chat-sdk 独立包深入（2天） | Rollup config、SDK index.tsx 入口、Copilot 嵌入模式、Demo 独立运行 | 手写 mini npm 包模拟 SDK 发布消费 | Monorepo 体系下构建业务组件库、Monorepo 高频问题与标准答法、前端组件库分层体系设计、React 组件库面试问题 |
| Day 14-15 | 系统设置 + Agent/插件 + 数据库/LLM 配置（2天） | /system, /agent, /plugin, /database, /llm | 速读 + 面经提炼 | AI 对话项目中组件封装探讨、Axios 二次封装面试讲法 |

**Layer 2 产出**：`docs/面经/02-功能模块/` 5 篇。

> Layer 2 已覆盖简历条 ②③④⑤⑥⑦ 的代码区域（流式渲染、图表判断、澄清选择、维度下钻、权限控制、记忆管理）。

### Layer 3：简历亮点面试准备（Day 16-25）

> ⚠️ **Layer 3 入口检查点**：Day 16 开始前，基于 Layer 1+2 的积累重新审视简历。
> 经过 15 天的深入阅读和调试，你可能发现：
> - 某些模块比你预想的更有深度 → 升级为新的简历亮点
> - 某些模块没那么出彩 → 降级或合并
> - 原来以为不重要的模块实际很精彩 → 新增
> 
> **Day 16 上午预留 2h 做简历修订**，重新定稿后再按新版本进入 Layer 3 的面试准备。以下日程以当前 7 条为默认，实际执行时以修订后的版本为准。

| 天 | 内容 | 配套阅读资料 |
|---|------|------------|
| Day 16-17 | Day 16 上午：简历修订（2h）→ 下午+Day 17：简历条 ①② 面试文档精炼（Monorepo+SDK 架构 + 流式对话渲染） | 如何用一个基础项目通过大厂面试、如何在前端面试中把一个项目讲得出彩、前端面试项目准备方法总结、AI 对话项目应突出解决问题的能力 |
| Day 18-19 | 简历条 ③④ 面试文档精炼（智能图表判断 + 澄清选择与查询调整） | 大厂前端面试高频答疑：项目问题回答思路、前端面试表达方法论、前端项目怎么写出亮点 |
| Day 20-21 | 简历条 ⑤⑥⑦ 面试文档精炼（维度下钻 + 行列权限 + Agent 记忆管理） | —（以 Layer 2 面经为基础精炼） |
| Day 22 | 跨模块串联：全链路回答 + 后端数据流（Parse → S2SQL → Execute → SQL） | 前端项目中前后端的协作问题、前端面试官问你前后端协作其实在看什么 |
| Day 23-24 | 模拟面试：7 条逐条「讲→追问→答→点评」+ 项目整体四段式介绍 | 前端面试表达方法论、前端面试中的软技能问题 |
| Day 25 | 全复盘 + 薄弱点回补 + 面经手册终稿 | — |

**Layer 3 产出**：`docs/面经/03-简历亮点/` 7 篇深度面经 + 1 篇跨模块全链路回答。

## 四、最终交付物

```
docs/面经/
├── 01-全局观/
│   ├── 01-项目跑通.md
│   ├── 02-项目结构全景.md
│   ├── 03-工程化构建部署.md
│   └── 04-组件树与状态流转.md
├── 02-功能模块/
│   ├── 01-ChatBI核心对话流.md
│   ├── 02-语义模型配置.md
│   ├── 03-登录鉴权全链路.md
│   ├── 04-chat-sdk独立包.md
│   └── 05-系统设置与Agent.md
└── 03-简历亮点/
    ├── 01-Monorepo与SDK架构.md
    ├── 02-流式对话渲染.md
    ├── 03-智能图表判断.md
    ├── 04-澄清选择与查询调整.md
    ├── 05-维度下钻.md
    ├── 06-行列权限控制.md
    ├── 07-Agent记忆管理.md
    └── 08-全链路串联回答.md
```

每篇面经标准格式：

```markdown
# 模块名

## 30秒一句话概括
> [定义 → 原理 → 示例 格式]

## 面试问题清单

### Q1: xxx
**回答**：[结构化：背景 → 技术路径 → 结果]
**追问1**：xxx → **答**：xxx
**追问2**：xxx → **答**：xxx
```

## 五、面经生成原则（来自经验贴）

1. **代码精读是面经的前提** — 看不懂代码就写不出有深度的回答；每个模块先读代码 / debug / 写 demo，再提炼面经
2. **面试官不看"做了什么功能"，看"解决了什么问题"** — 每个问题从痛点出发
3. **四层追问**：做了什么 → 为什么这么做(技术选型对比) → 不用库怎么手写 → 底层原理
4. **回答结构**：定义→原理→示例，30 秒讲清一个技术点
5. **"为什么"比"是什么"重要十倍** — 每个模块强制包含技术选型对比
6. **AI 对话项目的核心**：流式输出(解决等待焦虑) + 兜底方案(解决失败恐慌)
