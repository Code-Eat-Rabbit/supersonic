# chat-sdk 面试文档深化 — 设计规格

## 元信息

- 日期：2026-07-16
- 目标：在现有 `resume/04-chat-sdk.md` 基础上深化面试文档，同时补足 monorepo 组件库基础知识
- 策略：代码驱动学习（方案 B），60% 面试文档深化 + 40% 基础理解
- 节奏：紧凑模式，1-2 天
- 起点：用户对 monorepo / 前端工程化基本不了解

## 背景

SuperSonic 项目 webapp 目录是一个 pnpm monorepo，chat-sdk 是其中独立的前端组件库子包。用户此前未接触过 monorepo 组件库开发，现有面试文档（6 组 Q&A）需要深化以覆盖更多面试方向。

参考资料：
- `docs/superpowers/references/React 组件库面试可能问题.md` — 20+ 问题的面试题库
- `docs/superpowers/references/Monorepo 体系下构建业务组件库.md`
- `docs/superpowers/references/前端组件库分层体系设计与实践.md`
- `docs/superpowers/references/前端组件库使用中的常见问题与实践 —— 以 Ant Design 系列为例.md`

chat-sdk 技术栈：React 18 + TypeScript 4.9 + Rollup 3 + Less + CSS Modules + Ant Design 5

## 整体架构：三阶段漏斗

```
Phase 1 (15 min): 课前概念
  3 个必须提前懂的核心概念：
    1. Monorepo + pnpm workspace + symlink
    2. Rollup 打包 vs Webpack 打包
    3. peerDependencies vs dependencies

Phase 2 (~2h): 代码走读（六层）
  L1 项目全貌 → L2 入口层 → L3 Chat 核心组件
  → L4 Copilot 包装 → L5 ChatItem/ChatMsg 渲染 → L6 服务层
  每层走读完映射到可支撑的面试问题

Phase 3 (~1h): 面试文档深化
  保留现有 6 问 + 精写 5 问 + 简写 3 问
```

## Phase 1：课前概念（3 个核心知识块）

### 概念 1：Monorepo + pnpm workspace + Symlink

SuperSonic 的实际结构：
```
webapp/
├── pnpm-workspace.yaml  ← packages: ['packages/*']
├── packages/
│   ├── chat-sdk/        ← 组件库（独立的 npm 包）
│   └── supersonic-fe/   ← 主站
```

- pnpm workspace 通过 `packages/*` 声明哪些目录是"兄弟包"
- `overrides: { supersonic-chat-sdk: link:packages/chat-sdk }` 强制使用本地源码
- 主站 `import { Chat } from 'supersonic-chat-sdk'` 实际通过 symlink 指向本地源码
- 效果：修改 chat-sdk 源码 → 主站热更新（秒级），无需 npm publish

### 概念 2：Rollup 打包 vs Webpack 打包

| | Rollup | Webpack |
|---|---|---|
| 定位 | 库（library）打包 | 应用（app）打包 |
| Tree-shaking | 天然支持，更彻底 | 支持但不如 Rollup |
| 代码分割 | 弱 | 强 |
| chat-sdk 中 | 打包 ESM/UMD 产物 | 开发调试（Dev Server） |

chat-sdk 双工具并用：Rollup 出产物，Webpack Dev Server 做本地 demo 调试。

### 概念 3：peerDependencies vs dependencies

- `dependencies`：SDK 自己需要，打包时会包含（如 antd、echarts）
- `peerDependencies`：假设宿主已有，不重复打包（如 react、react-dom）
- 关键风险：React 被打包两份会导致 hooks 闭包上下文不同，报 "Invalid hook call"
- 解决：`rollup-plugin-exclude-dependencies-from-bundle` 排除 peer 依赖

## Phase 2：代码走读（六层）

每层格式：**文件 → 知识点 → 面试映射**

### L1 项目全貌

文件：`package.json` / `tsconfig.json` / `rollup/rollup.config.mjs` / 目录树

知识点：
- `package.json` 四入口：`main`(ESM) / `module`(ESM) / `unpkg`(UMD) / `types`(.d.ts)
- `tsconfig.json`：`declaration: true` 生成 .d.ts 类型声明文件
- Rollup 插件链：`typescript2 → nodeResolve → commonjs → styles → terser → excludeDeps`
- 目录组织：`Chat/ Copilot/ components/ service/ utils/ styles/`

面试映射：Q "SDK 的工程化配置是怎么设计的？"

### L2 入口层

文件：`src/index.tsx` / `src/common/type.ts`

知识点：
- Barrel Export 模式：一个文件聚合所有导出
- 导出粒度：组件（UI 开箱即用）+ API（逻辑复用）+ 类型（TypeScript 编译期检查）
- 为什么 Chat 和 ChatItem 分导出：支持渐进式集成（第三方可用 ChatItem 自定义消息列表）

面试映射：Q "SDK 的 API 设计原则是什么？"

### L3 Chat 核心组件

文件：`src/Chat/index.tsx`（526 行）

知识点：
- `forwardRef` + `useImperativeHandle`：暴露内部方法给父组件
- 状态管理：`messageList` / `currentAgent` / `currentConversation` 三轴联动
- Agent 切换时 messageList 重置逻辑
- `useThrottleFn` 对滚动加载历史消息的性能优化

面试映射：Q "Chat 组件的状态管理怎么设计的？"

### L4 Copilot 包装组件

文件：`src/Copilot/index.tsx`（149 行）

知识点：
- 组合模式：Copilot 内部复用 Chat，而非继承
- `useImperativeHandle` 暴露 `sendCopilotMsg()` 给外部调用
- Chat 通过 ref 通信（Copilot → Chat），Copilot 通过 ref 通信（外部 → Copilot）
- `sendCopilotMsg` 内部：Agent 不同则切换+重置，相同则直接发送

面试映射：Q "Chat 和 Copilot 的组件通信设计有什么不同？"

### L5 渲染组件 ChatItem + ChatMsg

文件：`src/components/ChatItem/*` / `src/components/ChatMsg/*`

知识点：
- 消息解析链路：ParseTip → SqlItem → ExecuteItem → 图表渲染
- ChatMsg 多模式渲染：Table / Bar / Pie / MetricCard / MetricTrend / MarkDown / Text
- 策略模式：根据 `msgType` 分发不同渲染组件

面试映射：Q "SDK 如何支持多种消息类型的渲染？"

### L6 服务层 + 工具层

文件：`src/service/index.ts` / `src/service/axiosInstance.ts` / `src/utils/`

知识点：
- axios 实例封装：baseURL / 拦截器 / token 注入
- 移动端 vs PC 端 API 路径区分：`/openapi` vs `/api`
- 工具函数：`setToken` / `uuid` / `jsonParse` / `isMobile`

面试映射：Q "SDK 的 API 层怎么设计的？"

## Phase 3：面试文档深化

### 保留现有 6 问

Q1-Q6 质量尚可，保留并在代码走读中补充细节证据。

### 精写 5 问（每问含追问链）

**Q7：peerDependencies vs dependencies 的设计哲学**

- 代码锚点：`package.json` 第 8-33 行
- 追问链：React 重复打包的 hook 报错机制 → antd 为什么放 dependencies → exclude-dependencies-from-bundle 原理
- 难度：★★★

**Q8：forwardRef + useImperativeHandle 在 Copilot 中的应用**

- 代码锚点：`Copilot/index.tsx` 第 30-51 行
- 追问链：为什么不用 props 回调 → Agent 切换逻辑 → ref 通信的 null check 和类型安全
- 难度：★★★★（React 进阶，区分度高）

**Q9：CSS Modules 样式隔离方案**

- 代码锚点：全项目 `*.module.less` / `variables.less`
- 追问链：为什么选 CSS Modules 而非 styled-components → PREFIX_CLS 作用 → 宿主如何覆盖变量
- 难度：★★

**Q10：Rollup 插件链设计**

- 代码锚点：`rollup/rollup.config.mjs` + `rollup.esm.config.mjs`
- 追问链：插件顺序为什么不能换 → autoModules 原理 → ESM vs UMD 产物使用场景
- 难度：★★★

**Q11：Chat 组件消息流与状态管理**

- 代码锚点：`Chat/index.tsx` 第 60-80 行 + 消息发送逻辑
- 追问链：Agent 切换时状态重置 → 移动端 vs PC 端差异 → useThrottleFn 优化
- 难度：★★★

### 简写 3 问（覆盖型）

- Q12：SDK 开发调试流程（Webpack Dev Server + setupProxy）
- Q13：TypeScript 类型系统设计（common/type.ts 组织思路）
- Q14：API 错误处理与边界情况

### 最终文档结构

```
resume/04-chat-sdk.md
├── 简历文案（保留）
├── 基础追问 Q1-Q6（保留，微调补充代码证据）
├── 进阶追问 Q7-Q11（新增精写，每问含追问链）
├── 快速覆盖 Q12-Q14（新增简写）
└── 附录：关键代码片段索引（新增）
```

## 边界与约束

- 本次只深化面试文档，不修改 chat-sdk 源码
- 不新增 Skill，纯知识性产出
- 交付物只有一份：更新后的 `resume/04-chat-sdk.md`
- 学习过程中的对话记录保留在会话中，不单独存档

## 风险

- 紧凑模式下代码走读可能不够深 → 接受"面试够用"的深度，在 Q&A 追问链中补充
- chat-sdk 526 行 Chat 组件无法逐行精读 → 聚焦状态管理 + 消息流两个核心逻辑
