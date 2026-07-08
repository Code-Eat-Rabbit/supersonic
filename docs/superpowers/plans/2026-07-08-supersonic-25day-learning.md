# SuperSonic 25 天前端学习 — 实现计划

> **面向 AI 代理的工作者：** 使用 superpowers:subagent-driven-development 或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 25 天内从零基础到能讲透 SuperSonic 前端架构和 4 大简历主题，产出完整面经手册。

**架构：** 三层漏斗式 — Layer 1 全局观（Day 1-4）→ Layer 2 功能模块深入（Day 5-15）→ Layer 3 简历亮点面试准备（Day 16-25）。每层路径：读资料 → 读代码/调试/demo → 写面经。

**技术栈：** React 18, UmiJS 4 Max, Ant Design 5, ECharts 5, pnpm workspaces, Rollup, Less, TypeScript

**前置条件：**
- 仓库：`~/workspace/supersonic`（已 clone）
- 资料夹：`/Users/yourton_ma/Documents/frontend_tutorials/前端方向文章合集/`
- 简历亮点速查：`docs/项目简历亮点.md`

---

## 任务 0：初始化目录结构

**文件：**
- 创建：`docs/面经/01-全局观/`（空目录）
- 创建：`docs/面经/02-功能模块/`（空目录）
- 创建：`docs/面经/03-简历亮点/`（空目录）

- [ ] **步骤 1：创建目录**

```bash
mkdir -p ~/workspace/supersonic/docs/面经/01-全局观
mkdir -p ~/workspace/supersonic/docs/面经/02-功能模块
mkdir -p ~/workspace/supersonic/docs/面经/03-简历亮点
```

- [ ] **步骤 2：验证**

```bash
ls -la ~/workspace/supersonic/docs/面经/
```

预期：三个子目录均存在。

- [ ] **步骤 3：Commit**

```bash
cd ~/workspace/supersonic
git add docs/面经/
git commit -m "chore: 初始化面经目录结构"
```

---

## Layer 1：全局观（Day 1-4）

### 任务 1：Day 1 — 项目跑通 + 面经产出

**目标：** 前后端全链路跑通，产出第一篇面经。

**文件（阅读）：**
- `assembly/bin/supersonic-build.sh`
- `assembly/bin/supersonic-daemon.sh`
- `webapp/packages/supersonic-fe/config/config.ts:1-50`（环境变量配置）
- 阅读资料：`前端项目调试完全指南：从VSCode到Chrome DevTools.md`

- [ ] **步骤 1：阅读调试指南**

打开 `前端方向文章合集/前端项目调试完全指南：从VSCode到Chrome DevTools.md`，了解 Chrome DevTools 的 Sources/Network/Application 面板基本用法。

- [ ] **步骤 2：构建并启动后端**

```bash
cd ~/workspace/supersonic
./assembly/bin/supersonic-build.sh standalone
./assembly/bin/supersonic-daemon.sh start
```

验证：`curl http://localhost:9080` 返回非空响应。

- [ ] **步骤 3：安装前端依赖并启动**

```bash
cd ~/workspace/supersonic/webapp
pnpm install
cd packages/supersonic-fe
pnpm dev
```

验证：浏览器打开 `http://localhost:9000`，能看到登录页或 Chat 页。

- [ ] **步骤 4：走一遍 Chat 问答流程**

在浏览器中：输入自然语言问题 → 观察解析结果 → 查看图表渲染 → 尝试下钻/调整。

- [ ] **步骤 5：用 Chrome DevTools Network 面板观察请求**

打开 DevTools → Network 标签，再次提问，记录：
- `/api/chat/parse` 请求和响应结构
- `/api/chat/execute` 请求和响应结构
- 其他 API 调用

- [ ] **步骤 6：产出面经 `docs/面经/01-全局观/01-项目跑通.md`**

包含 5 个 Q&A：

1. **你是怎么把项目跑起来的？** 答：先 Maven build + daemon 脚本启动 Java 后端（端口 9080），再 pnpm install + pnpm dev 启动 React 前端（端口 9000）。需要配置 MySQL 和 LLM API key。

2. **前后端是怎么通信的？** 答：前端 UmiJS 配置了 proxy，`/api/chat/` 和 `/api/semantic/` 请求被代理到 `localhost:9080`。开发环境用 proxy，生产环境用 Nginx 反代。

3. **项目用了哪些环境变量？怎么管理的？** 答：`config/config.ts` 中通过 `process.env` 注入，区分 `REACT_APP_ENV=dev/prod`，`APP_TARGET=opensource/inner`。`API_BASE_URL` 等挂载在 `process.env` 下。

4. **起项目时遇到过什么问题？怎么解决的？** 答：（记录实际遇到的问题和解决过程）

5. **Chrome DevTools 你主要用哪些面板？分别看什么？** 答：Sources（断点调试）、Network（API 请求/响应）、Application（localStorage/Cookie）、Console（错误日志）。

- [ ] **步骤 7：Commit**

```bash
cd ~/workspace/supersonic
git add docs/面经/01-全局观/01-项目跑通.md
git commit -m "docs: Day1 面经 — 项目跑通"
```

---

### 任务 2：Day 2 — 前端项目结构全景分析 + 面经产出

**目标：** 画出包职责图、路由页面映射表、组件树层级图、状态流转图，产出第二篇面经。

**文件（阅读）：**
- `webapp/pnpm-workspace.yaml`
- `webapp/packages/chat-sdk/package.json`（name/main/module 字段）
- `webapp/packages/supersonic-fe/package.json`（dependencies 中 chat-sdk 引用）
- `webapp/packages/supersonic-fe/config/routes.ts`（全部路由定义）
- `webapp/packages/chat-sdk/src/index.tsx`（SDK 对外入口）
- `webapp/packages/chat-sdk/src/components/Chat.tsx`（Chat 主组件）
- `webapp/packages/chat-sdk/src/components/ChatItem/index.tsx`（消息项组件）

- [ ] **步骤 1：画出包职责地图**

阅读 `pnpm-workspace.yaml` + 两个 `package.json`，画出：

```
webapp/
├── packages/
│   ├── chat-sdk/        → SDK 包（Rollup 构建，独立发布）
│   │   职责：Chat 组件、图表渲染、轮询 hooks、类型定义
│   │   消费方式：supersonic-fe 通过 workspace:* 引用
│   └── supersonic-fe/   → 宿主应用（UmiJS 4 构建）
│       职责：路由、页面、权限、请求代理、系统设置
│       消费 chat-sdk：config.ts alias + package.json workspace:*
```

- [ ] **步骤 2：画出路由与页面映射表**

阅读 `config/routes.ts`，整理出：

| 路径 | 页面组件 | 说明 |
|------|---------|------|
| `/chat` | ChatPage | Chat BI 对话（核心） |
| `/chat/mobile` | ChatPage | 移动版对话 |
| `/agent` | Agent | Agent 配置 |
| `/plugin` | ChatPlugin | 插件管理 |
| `/model/domain/:domainId` | DomainManager | 语义模型-领域管理 |
| `/model/domain/manager/:domainId/:modelId` | ModelManager | 语义模型-模型管理 |
| `/model/dataset/:domainId/:datasetId` | Dataset Detail | 数据集详情 |
| `/model/metric/...` | Metric Edit | 指标编辑 |
| `/model/dimension/...` | Dimension Detail | 维度详情 |
| `/metric` | Metric Market | 指标市场 |
| `/tag` | Insights | 标签/洞察 |
| `/login` | Login | 登录页 |
| `/database` | DatabaseTable | 数据库配置 |
| `/llm` | LlmTable | LLM 配置 |
| `/system` | System | 系统设置（需 SYSTEM_ADMIN） |

- [ ] **步骤 3：画出组件树层级图**

阅读 `chat-sdk/src/index.tsx` → `Chat.tsx` → `ChatItem/index.tsx`，画出：

```
ChatProvider（注入 baseUrl/token/agentId）
  └── Chat（对话容器）
        └── 消息列表
              └── ChatItem（单条消息）
                    ├── 用户消息（文本）
                    └── 助手消息
                          ├── ExpandParseTip（澄清选择，候选>1时显示）
                          ├── ParseTip（交互式查询调整）
                          ├── ChatMsg（图表/数据渲染）
                          │     ├── MetricCard（指标卡）
                          │     ├── MetricTrend（折线图）
                          │     ├── MetricBar（柱状图）
                          │     ├── MetricPie（饼图）
                          │     ├── Table（表格）
                          │     └── Text（文本/Markdown）
                          ├── DrillDownDimensions（维度下钻）
                          └── Tools（评分反馈）
```

- [ ] **步骤 4：画出状态流转图**

追踪一次对话的完整状态变迁：

```
用户输入问题
  → chatParse(question, agentId) → parseResult[]（多候选）
  → 候选数>1？ExpandParseTip 展示候选选择
  → 用户选候选（或候选=1自动选）→ 更新 currentParseInfo
  → chatExecute(parseId) → msgData（columns+rows+queryId）
  → usePolling 轮询 getExecuteSummary(queryId)
  → queryMode !== null？停止轮询
  → ChatMsg 渲染：getMsgContentType(data) → 选图表类型 → ECharts render
  → 用户下钻？→ 追加维度 → chatExecute 重新查询
  → 用户调整？→ ParseTip 修改条件 → chatExecute（不重新 parse）
  → 用户评分？→ updateQAFeedback(queryId, score) → 记忆管理
```

- [ ] **步骤 5：产出面经 `docs/面经/01-全局观/02-项目结构全景.md`**

包含 5 个 Q&A：

1. **这个项目的 Monorepo 是怎么组织的？为什么拆成 chat-sdk 和 supersonic-fe 两个包？** 答：pnpm workspaces，`workspace:*` 协议硬链接。chat-sdk 是可独立发布的 SDK 包（Rollup 构建），supersonic-fe 是宿主应用（UmiJS 构建）。拆分的目的是 SDK 可嵌入任何 React 应用（Copilot 模式），实现解耦。

2. **从用户在输入框提问到图表渲染出来，数据在前端经过了哪些组件和状态？** 答：（用步骤 4 的状态流转图回答）

3. **前端有哪些页面？分别对应什么功能？** 答：（用步骤 2 的映射表回答）

4. **chat-sdk 是怎么做到既能独立运行又能嵌入宿主应用的？** 答：通过 ChatProvider 注入 baseUrl/token/renderCustomNode 等配置，内部用 React Context 消费。Chat 组件是纯 UI，不依赖具体后端。Demo 模式下 ChatDemo.tsx 可独立启动。

5. **项目里 React 状态是怎么管理的？为什么没上 Redux？** 答：chat-sdk 用 React Context + useState/useReducer，supersonic-fe 用 UmiJS 的 `useModel()`（轻量全局状态）。项目状态不复杂，不需要 Redux 的样板代码。Context + useReducer 足够覆盖 Chat 对话场景。

- [ ] **步骤 6：Commit**

```bash
cd ~/workspace/supersonic
git add docs/面经/01-全局观/02-项目结构全景.md
git commit -m "docs: Day2 面经 — 项目结构全景分析"
```

---

### 任务 3：Day 3 — 前端工程化速览 + 方案对比 + 面经产出

**目标：** 理解 pnpm/Rollup/UmiJS 的基本原理和同源方案对比，产出第三篇面经。

**文件（阅读）：**
- `webapp/pnpm-workspace.yaml`
- `webapp/packages/chat-sdk/rollup/`（Rollup 配置目录）
- `webapp/packages/supersonic-fe/config/config.ts`（UmiJS 配置全量）
- `webapp/packages/supersonic-fe/config/proxy.ts`
- `webapp/packages/supersonic-fe/config/routes.ts`（复读，关注 access 字段）
- 阅读资料（按顺序）：
  1. `为什么要有前端构建工具，它解决了什么问题？.md`
  2. `简单理解 Webpack.md`
  3. `三分钟快速理解 Tree Shaking 原理.md`
  4. `前端工程化在大厂面试中的常见考察点与答题思路.md`
  5. `前端如何缩小打包体积：实用指南与最佳实践.md`
  6. `基于 Vite 的前端构建优化实践：路由级懒加载与 manualChunks 精细拆包.md`
  7. `Monorepo 高频问题与标准答法体系.md`
  8. `Monorepo 体系下构建业务组件库.md`

- [ ] **步骤 1：阅读工程化资料（上午）**

按顺序读完上述 8 篇资料，边读边标注关键概念和对比点。

- [ ] **步骤 2：分析 SuperSonic 的工程化方案（下午前半段）**

打开 chat-sdk 的 Rollup 配置目录，回答：输出什么格式？（ESM + UMD）为什么用 Rollup 不用 Webpack？（SDK 不需要 dev server，Rollup 更轻量，tree-shaking 更好）

打开 config.ts，回答：UmiJS 提供了哪些开箱即用的能力？（路由、代理、权限 access、国际化、antd 按需加载、MFSU 加速、initialState）

- [ ] **步骤 3：写方案对比笔记**

整理表格，每种技术都要回答"为什么选 A 不选 B"：

| 对比维度 | SuperSonic 选型 | 替代方案 | 为什么选这个 |
|---------|----------------|---------|------------|
| 包管理 | pnpm workspaces | npm/yarn workspaces, Turborepo, Lerna | 硬链接节省磁盘，严格依赖隔离避免幽灵依赖，`workspace:*` 协议简单 |
| SDK 构建 | Rollup | Webpack, Vite, esbuild | SDK 不需要 dev server，Rollup 输出更干净，tree-shaking 效果好 |
| 应用框架 | UmiJS 4 Max | CRA, Next.js, Vite | 约定式路由减少配置，内置权限/国际化/代理/antd，中后台场景开箱即用 |
| 请求库 | umi-request / axios | fetch, react-query | umi-request 与 UmiJS 深度集成，axios 在 chat-sdk 中用于独立包场景 |

- [ ] **步骤 4：产出面经 `docs/面经/01-全局观/03-工程化构建部署.md`**

包含 5 个 Q&A：

1. **pnpm workspaces 和 npm workspaces 有什么区别？为什么用 pnpm？** 答：pnpm 使用硬链接 + 内容寻址存储，多个项目共享同一份依赖，节省磁盘。`workspace:*` 协议直接链接本地包。关键优势是严格依赖隔离——没有幽灵依赖问题（npm/yarn 的扁平 node_modules 可能让包访问未声明的依赖）。

2. **为什么 chat-sdk 用 Rollup 打包而不用 Webpack？** 答：Rollup 更适合库打包——输出更干净、tree-shaking 更好、支持 ESM/UMD 双格式。Webpack 适合应用打包（需要 dev server/HMR/代码分割）。chat-sdk 作为 SDK 不需要 dev server，Rollup 是更轻量的选择。

3. **UmiJS 和 CRA/Next.js 有什么区别？** 答：CRA 太基础，需要手动配路由/权限/代理。Next.js 偏 SSR/全栈。UmiJS 约定式路由、内置权限 access 插件、antd 按需加载、MFSU 加速，适合中后台场景。SuperSonic 选 UmiJS 是因为它和 Ant Design Pro 生态深度绑定。

4. **项目是怎么做代理的？为什么开发环境需要代理？** 答：`config/proxy.ts` 配置了 `/api/chat/` → `localhost:9080` 的代理规则。开发时前端在 9000 端口，后端在 9080，直接请求会跨域。代理把同域请求转发到后端，绕过浏览器的同源策略。

5. **什么是 Tree Shaking？Rollup 怎么做 Tree Shaking？** 答：Tree Shaking 是 dead code elimination——只打包被 import 且实际使用的代码。Rollup 基于 ES Module 的静态分析，构建时标记未使用的 export 并移除。关键条件是使用 ES Module（`import/export`），不能用 CommonJS（`require`）。

- [ ] **步骤 5：Commit**

```bash
cd ~/workspace/supersonic
git add docs/面经/01-全局观/03-工程化构建部署.md
git commit -m "docs: Day3 面经 — 工程化速览与方案对比"
```

---

### 任务 4：Day 4 — 自定义 Hooks 基础 + 状态流转深入 + 面经产出

**目标：** 掌握自定义 Hook 写法，手写 mini usePolling，彻底理解状态流转，产出第四篇面经。

**文件（阅读）：**
- `webapp/packages/chat-sdk/src/hooks/`（全部 hooks）
- `webapp/packages/chat-sdk/src/components/ChatItem/index.tsx`（polling 调用位置）
- `webapp/packages/chat-sdk/src/components/Chat.tsx`（ChatProvider 用法）
- `webapp/packages/chat-sdk/src/service/index.ts`（API 调用）
- 阅读资料：
  1. `React Hooks 源码深入解析 - 面试必备指南.md`
  2. `React 面试系列之 自定义 Hook 专题.md`
  3. `大厂前端面试：高频手撕自定义 Hooks 全解析.md`
  4. `React 状态管理工具选型：Redux vs Zustand vs Context 的工程化决策指南.md`
  5. `一文讲透前端路由的原理与工程实现.md`

- [ ] **步骤 1：阅读 Hooks 资料（上午前半段）**

按顺序读完 5 篇资料，重点关注自定义 Hook 的规则和常见模式。

- [ ] **步骤 2：学习自定义 Hook 基础规则**

总结三条核心规则：
1. **命名**：必须以 `use` 开头（React 用这个前缀识别 Hook，做 lint 检查）
2. **调用位置**：只能在函数组件顶层或其他 Hook 内部调用，不能在条件/循环中
3. **本质**：自定义 Hook 就是一个内部调用了 React Hook（useState/useEffect 等）的普通 JS 函数，它封装的是**状态逻辑**而非 UI

- [ ] **步骤 3：手写 mini usePolling**

创建文件 `/tmp/mini-usePolling.js`（不在仓库内，仅供练习）：

```javascript
// mini usePolling — 理解轮询 Hook 的核心原理
function usePolling(fetchFn, interval = 500, maxAttempts = 60) {
  const [data, setData] = useState(null);
  const [attempts, setAttempts] = useState(0);
  const abortRef = useRef(new AbortController());

  useEffect(() => {
    let timer;
    const poll = async () => {
      try {
        const result = await fetchFn(abortRef.current.signal);
        setData(result);
        if (result.isComplete || attempts >= maxAttempts) return; // 停止条件
        setAttempts(prev => prev + 1);
        timer = setTimeout(poll, interval); // setTimeout 非 setInterval
      } catch (err) {
        if (err.name !== 'AbortError') throw err;
      }
    };
    poll();
    return () => {
      clearTimeout(timer);
      abortRef.current.abort(); // 组件卸载时中断
    };
  }, []);

  return { data, attempts };
}
```

关键点注释：
- 用 `setTimeout` 而非 `setInterval`——每次回调完成才调度下一次，不会堆积请求
- `AbortController` 中断控制——组件卸载时 `abort()` 避免 setState 到已卸载组件
- `maxAttempts` 兜底——后端异常时不会无限轮询
- 闭包陷阱：functional setState（`setAttempts(prev => prev + 1)`）避免闭包中的 stale state

- [ ] **步骤 4：精读 usePolling 源码 + ChatItem 轮询调用**

打开 `chat-sdk/src/hooks/`，找到 usePolling 的实际实现，对比 mini 版看差异：
- 实际版本可能有多轮查询（summary + 最终结果）
- 轮询状态暴露（loading/error/done）给 UI 层
- queryMode 作为停止条件（后端返回非 null 表示总结完成）

打开 `ChatItem/index.tsx:190-203`，看轮询是怎么在组件中调用的。

- [ ] **步骤 5：追踪完整状态流转（结合 Day 2 步骤 4 深入）**

在 Chrome DevTools Sources 面板中，给以下位置打断点，重新提问走一遍：
1. `chatParse` 调用处 — 看参数和返回值
2. `chatExecute` 调用处 — 看 parseId 怎么传
3. `usePolling` 内部 `setTimeout` 回调 — 看每次轮询的数据变化
4. `ChatMsg` 渲染处 — 看 `msgData` 怎么变成图表

- [ ] **步骤 6：产出面经 `docs/面经/01-全局观/04-组件树与状态流转.md`**

包含 5 个 Q&A：

1. **什么是自定义 Hook？怎么写一个自定义 Hook？** 答：自定义 Hook 是以 `use` 开头、内部调用 React Hook 的 JS 函数，封装可复用的状态逻辑。三步：① 确定要封装的状态逻辑（如轮询、表单、请求）② 用 useState/useEffect 等实现 ③ 返回状态和操作方法。示例：usePolling 封装了轮询调度 + 中断控制 + 兜底逻辑。

2. **usePolling 为什么用 setTimeout 而不是 setInterval？** 答：setInterval 不管上一次回调是否完成，固定间隔触发，网络慢时会堆积请求。setTimeout 在每次回调完成后再调度下一次，保证串行。配合 AbortController 可以在组件卸载时终止。

3. **项目里一个完整对话的状态是怎么流转的？** 答：（用 Day 2 步骤 4 的状态流转图回答，这次加上具体的 state 变量名：parseResult[] → currentParseInfo → msgData → queryMode → contentType）

4. **ChatProvider 是怎么工作的？Context 在项目里起了什么作用？** 答：ChatProvider 是一个 Context Provider 组件，注入 baseUrl/token/agentId 等配置。子组件通过 useContext 消费这些配置，避免 props drilling。Chat SDK 的所有组件都在 ChatProvider 子树内。

5. **UmiJS 的 useModel 和 React Context 有什么区别？** 答：useModel 是 UmiJS 的全局状态方案（基于 hooks + Context），适合跨页面共享数据（如用户信息、权限列表）。React Context 更轻量，适合组件树内共享（如 ChatProvider）。项目里 supersonic-fe 用 useModel 做全局状态，chat-sdk 用 Context 做 SDK 内部状态。

- [ ] **步骤 7：Commit**

```bash
cd ~/workspace/supersonic
git add docs/面经/01-全局观/04-组件树与状态流转.md
git commit -m "docs: Day4 面经 — 自定义Hooks与状态流转"
```

---

## Layer 2：功能模块深入（Day 5-15）

### 任务 5：Day 5-7 — Chat BI 核心对话流（3 天）

**目标：** Debug 断点追踪一次完整对话，理解流式渲染、图表判断、澄清选择、维度下钻的完整链路。产出 Chat BI 面经。

**文件（阅读）：**
- `webapp/packages/chat-sdk/src/components/ChatItem/ExpandParseTip.tsx`（268 行）
- `webapp/packages/chat-sdk/src/components/ChatItem/ParseTip.tsx`
- `webapp/packages/chat-sdk/src/components/ChatMsg/index.tsx`（getMsgContentType 函数）
- `webapp/packages/chat-sdk/src/components/DrillDownDimensions/index.tsx`
- `webapp/packages/chat-sdk/src/components/Tools/index.tsx`
- `webapp/packages/chat-sdk/src/components/Tools/FeedbackModal.tsx`
- `webapp/packages/chat-sdk/src/hooks/usePolling.ts`
- `webapp/packages/chat-sdk/src/hooks/index.ts`
- `webapp/packages/chat-sdk/src/service/index.ts`
- `webapp/packages/chat-sdk/src/types/`（类型定义）
- 阅读资料（按需选读，不要求全部）：
  - 流式渲染：`Agent 场景下的流式输出方案选型：SSE vs WebSocket 的工程权衡.md`、`前端如何处理流式输出：从协议到工程实践的全流程解析.md`、`基于 SSE 的实时 AI 对话技术方案.md`、`构建 AI 对话的流式渲染模块：逐字输出与长文本平滑体验.md`
  - 闭包：`JS 闭包深度解析 —— 从作用域到内存回收.md`、`一文解决 React 闭包问题：大厂面试全面准备.md`
  - 稳定性：`前端渲染稳定性问题实战：虚拟列表抖动 & 流式 Markdown 图片闪烁.md`
  - 图表：`ECharts 图表自适应与稳定性优化实践.md`、`前端面试中对于 ECharts 到底怎么考？.md`
  - 设计：`React组件设计原则：构建可维护、可复用的前端结构.md`、`前端开发中的边界与鲁棒性：从请求态到组件交互的全面思考.md`

- [ ] **步骤 1：阅读核心资料（Day 5 上午）**

必读：流式输出方案选型（SSE vs WebSocket vs 轮询）+ React 闭包问题 + ECharts 面试考点。其余按需选读。

- [ ] **步骤 2：Debug 追踪完整对话流（Day 5 下午 + Day 6 上午）**

在 Chrome DevTools Sources 面板中设置断点，走一遍完整对话：

断点位置：
1. `service/index.ts` → `chatParse()` — 看请求参数（question, agentId）和 ParseResult 响应
2. `ChatItem/index.tsx` → 候选选择逻辑 — 看 ExpandParseTip 什么时候显示
3. `ExpandParseTip.tsx` → `onSelectParse()` — 看怎么更新 currentParseInfo
4. `ChatMsg/index.tsx` → `getMsgContentType()` — 看数据特征怎么映射到图表类型
5. `usePolling.ts` → `setTimeout` 回调 — 看轮询数据累积和 queryMode 变化
6. `DrillDownDimensions/index.tsx` → 下钻触发 — 看维度怎么追加

记录每一步的入参、出参和状态变化。

- [ ] **步骤 3：精读关键源码（Day 6 下午）**

逐一回答以下问题，每个问题都要"找到代码证据"：

| 问题 | 代码位置 | 你的理解 |
|------|---------|---------|
| 流式渲染怎么实现？为什么用轮询不用 SSE？ | usePolling.ts + ChatItem:190-203 | |
| getMsgContentType 的 7 种类型判断优先级？ | ChatMsg/index.tsx:74-162 | |
| 候选数 = 1 和 >1 的行为有何不同？ | ExpandParseTip.tsx | |
| Parse/Execute 为什么解耦？用户微调触发哪个？ | ParseTip.tsx | |
| 下钻后图表会变吗？为什么？ | DrillDownDimensions/index.tsx | |
| 评分联动怎么触发记忆管理？ | Tools/index.tsx + FeedbackModal.tsx | |

- [ ] **步骤 4：产出面经 `docs/面经/02-功能模块/01-ChatBI核心对话流.md`（Day 7）**

包含 6 个 Q&A（每个对应上表一个问题 + 30 秒概括）：

1. **流式渲染是怎么实现的？为什么用 setTimeout 轮询而不是 SSE？**
2. **智能图表类型判断是怎么做的？7 种类型的优先级？**
3. **澄清选择机制——候选数 = 1 时和 >1 时的行为差异？**
4. **Parse 和 Execute 为什么要解耦？用户微调触发什么？**
5. **维度下钻是怎么实现的？下钻后图表会变吗？**
6. **Agent 记忆管理——前端做了哪些事？评分联动怎么触发？**

每个 Q&A 需包含追问链（至少 2 个追问）。

- [ ] **步骤 5：Commit**

```bash
cd ~/workspace/supersonic
git add docs/面经/02-功能模块/01-ChatBI核心对话流.md
git commit -m "docs: Day5-7 面经 — Chat BI核心对话流"
```

---

### 任务 6：Day 8-9 — 语义模型配置（2 天）

**目标：** 理解语义模型配置页面的 CRUD 流程，手写 mini 指标创建表单 demo，产出第二篇功能模块面经。

**文件（阅读）：**
- `webapp/packages/supersonic-fe/src/pages/SemanticModel/index.tsx`（入口）
- `webapp/packages/supersonic-fe/src/pages/SemanticModel/DomainManager/`（领域管理）
- `webapp/packages/supersonic-fe/src/pages/SemanticModel/ModelManager.tsx`（模型管理）
- `webapp/packages/supersonic-fe/src/pages/SemanticModel/components/ModelCreateFormModal.tsx`（创建表单）
- `webapp/packages/supersonic-fe/src/pages/SemanticModel/components/MetricInfoCreateForm.tsx`（指标创建）
- `webapp/packages/supersonic-fe/src/pages/SemanticModel/components/MetricFieldFormTable.tsx`
- `webapp/packages/supersonic-fe/src/pages/SemanticModel/models/`（数据模型层）
- 阅读资料：
  1. `React 动态表单实现与技术设计.md`
  2. `基于 Vue3 Composition API 的通用列表与表单逻辑抽象实践.md`（取表单抽象思路）
  3. `前端组件库使用中的常见问题与实践 —— 以 Ant Design 系列为例.md`

- [ ] **步骤 1：阅读资料（Day 8 上午）**

读完上述 3 篇，重点提取"动态表单"和"Ant Design 配置式表单"的实现思路。

- [ ] **步骤 2：精读语义模型路由和页面结构（Day 8 下午）**

打开 `config/routes.ts`，画出语义模型的路由树：

```
/model/
  ├── /model/domain/:domainId          → DomainManager（领域管理）
  │     └── /model/domain/manager/:domainId/:modelId
  │           → ModelManager（模型管理 — 指标/维度/数据集 Tab）
  ├── /model/dataset/:domainId/:datasetId
  │     → Dataset Detail
  ├── /model/metric/:domainId/:modelId/:metricId
  │     → Metric Edit
  └── /model/dimension/:domainId/:modelId/:dimensionId
        → Dimension Detail
```

打开 `SemanticModel/index.tsx`，看整体布局结构（左侧领域树 + 右侧内容区）。

- [ ] **步骤 3：手写 mini 指标创建表单 demo（Day 9 上午）**

创建 `/tmp/mini-metric-form.html`，用 React + Ant Design 写一个简化的指标创建表单：

```jsx
// mini 指标创建表单 — 理解配置式表单的核心
function MetricCreateForm() {
  const [form] = Form.useForm();
  // 表单字段：指标名称、指标类型、所属模型、计算公式、数据类型
  // 关键：ProForm + schema 驱动渲染，而非手写每个 Form.Item
  return (
    <ProForm form={form} onFinish={handleSubmit}>
      <ProFormText name="name" label="指标名称" rules={[{required: true}]} />
      <ProFormSelect name="type" label="指标类型" options={typeOptions} />
      <ProFormSelect name="modelId" label="所属模型" options={modelOptions} />
      <ProFormTextArea name="expr" label="计算公式" />
      <ProFormSelect name="dataType" label="数据类型" options={dataTypeOptions} />
    </ProForm>
  );
}
```

目的不是写出完整表单，而是理解配置式表单的核心思想：字段用 schema 定义，渲染由 ProForm 统一处理，而非逐个手写 Form.Item。

- [ ] **步骤 4：产出面经 `docs/面经/02-功能模块/02-语义模型配置.md`（Day 9 下午）**

包含 4 个 Q&A：

1. **语义模型管理涉及哪些概念？它们的关系是什么？** 答：Domain（领域）→ Model（模型，绑定数据库表）→ Metric（指标，如"销售额"）/ Dimension（维度，如"地区"）/ Dataset（数据集，指标+维度组合）。层级关系：一个 Domain 下多个 Model，一个 Model 下多个 Metric/Dimension。

2. **前端的表单是怎么做的？为什么用配置式而不是手写每个字段？** 答：ProForm + schema 驱动渲染。字段定义（name/type/rules）集中管理，ProForm 自动渲染 Form.Item。好处：新增字段只需加 schema 条目，不用改 JSX；统一校验逻辑；减少重复代码。

3. **语义模型配置页的权限控制是怎么体现的？** 答：路由层面通过 Umi access 插件控制菜单可见性，组件内通过 PermissionSection 控制操作按钮（创建/编辑/删除）的可见性。列级权限通过字段的 authorized 标记控制表格列显示。

4. **模型的维度和指标配置最终是怎么传给后端的？** 答：前端通过 `SemanticModel/service.ts` 调用 REST API（`/api/semantic/model/save`），payload 包含 modelId、metrics[]、dimensions[] 等。后端负责持久化和语义解析。

- [ ] **步骤 5：Commit**

```bash
cd ~/workspace/supersonic
git add docs/面经/02-功能模块/02-语义模型配置.md
git commit -m "docs: Day8-9 面经 — 语义模型配置"
```

---

### 任务 7：Day 10-11 — 登录鉴权全链路（2 天）

**目标：** Debug 追踪登录 → token 注入 → 路由守卫 → 按钮权限的完整链路，产出第三篇功能模块面经。

**文件（阅读）：**
- `webapp/packages/supersonic-fe/src/pages/Login/`（登录页面）
- `webapp/packages/supersonic-fe/src/services/login.ts`（登录 API）
- `webapp/packages/supersonic-fe/src/services/request.ts`（请求拦截器）
- `webapp/packages/supersonic-fe/config/config.ts`（access 插件配置，第 146 行）
- `webapp/packages/supersonic-fe/config/routes.ts`（access 字段，第 212 行）
- `webapp/packages/supersonic-fe/src/components/RightContent/AvatarDropdown.tsx`（用户菜单）
- `webapp/packages/chat-sdk/src/components/ChatMsg/ApplyAuth/index.tsx`（申请权限）
- `webapp/packages/chat-sdk/src/components/ChatMsg/NoPermissionChart/index.tsx`（无权限占位）
- 阅读资料：
  1. `Axios 拦截器与统一登录封装设计 —— 面试准备总结.md`
  2. `前端登录功能实现方案.md`
  3. `前端登录方案技术详解.md`
  4. `前端项目权限管理分类总结.md`
  5. `React 项目中的登录体系设计与实现.md`
  6. `前端安全与跨域请求综合指南.md`

- [ ] **步骤 1：阅读资料（Day 10 上午）**

读完 6 篇，重点摘录：token 存储方式对比（localStorage vs Cookie）、请求拦截器设计模式、权限模型（RBAC）。

- [ ] **步骤 2：Debug 追踪登录全链路（Day 10 下午）**

断点位置：
1. `Login/index.tsx` → 登录表单提交
2. `services/login.ts` → login API 调用，看返回的 token 怎么存储
3. `services/request.ts` → 请求拦截器，看 token 怎么注入到每个请求头
4. 路由守卫 → `config/config.ts` access 插件 + `routes.ts` access 字段
5. `AvatarDropdown.tsx` → 用户信息展示和退出登录

走通两条路径：
- 正常登录 → 获得 token → 页面可访问 → 按钮可点击
- 未登录 → 访问 `/system`（需 SYSTEM_ADMIN）→ 重定向或 403

- [ ] **步骤 3：精读权限控制代码（Day 11 上午）**

精读 ApplyAuth 和 NoPermissionChart 组件，回答：
- 字段的 `authorized` 标记从哪里来？（execute API 返回）
- 未授权字段渲染什么？（锁图标 + 申请权限按钮）
- 路由级权限怎么配？（routes.ts 中 `access: ROUTE_AUTH_CODES.SYSTEM_ADMIN`）
- 前端权限是安全保障还是 UX 优化？（UX 优化，真正安全在后端）

- [ ] **步骤 4：产出面经 `docs/面经/02-功能模块/03-登录鉴权全链路.md`（Day 11 下午）**

包含 5 个 Q&A：

1. **项目的登录流程是怎样的？token 怎么存储和传递？** 答：（从 Login 页 → API → token 存储 → 请求拦截器注入 → 路由守卫验证）

2. **请求拦截器做了什么？为什么需要统一封装？** 答：注入 token 到请求头、统一错误处理（401 跳登录/403 提示无权）、loading 状态管理。好处：不用在每个 API 调用处重复写 token 注入逻辑，改一处全局生效。

3. **项目做了哪几级权限控制？分别是前端还是后端负责？** 答：三级——① 路由级（Umi access 插件，控制页面可见性）② 按钮级（Authorized 组件，控制操作按钮）③ 数据级（字段 authorized 标记 + 后端 SQL 注入）。前端权限是 UX 优化，真正兜底在后端。

4. **字段的 authorized 标记从哪里来？未授权字段怎么处理？** 答：execute API 返回数据时，每个字段带 authorized 布尔值，由后端根据用户角色计算。前端检查到 authorized=false 时渲染 ApplyAuth 组件（锁图标 + "申请权限"按钮），替代真实数据。

5. **token 存在哪？localStorage 还是 Cookie？安全性如何考虑？** 答：（分析实际代码中的存储方式 + 对比两种方式的优劣：localStorage 易用但有 XSS 风险、httpOnly Cookie 防 XSS 但有 CSRF 风险、最佳实践是 access token 在内存 + refresh token 在 httpOnly Cookie）

- [ ] **步骤 5：Commit**

```bash
cd ~/workspace/supersonic
git add docs/面经/02-功能模块/03-登录鉴权全链路.md
git commit -m "docs: Day10-11 面经 — 登录鉴权全链路"
```

---

### 任务 8：Day 12-13 — chat-sdk 独立包深入（2 天）

**目标：** 理解 SDK 打包、发布、消费的完整链路，手写 mini npm 包模拟 SDK 模式，产出第四篇功能模块面经。

**文件（阅读）：**
- `webapp/packages/chat-sdk/rollup/`（全部 rollup 配置）
- `webapp/packages/chat-sdk/src/index.tsx`（SDK 对外入口，看 export 了哪些）
- `webapp/packages/chat-sdk/src/demo/ChatDemo.tsx`（独立 Demo）
- `webapp/packages/chat-sdk/src/demo/CopilotDemo.tsx`（Copilot 嵌入 Demo）
- `webapp/packages/chat-sdk/tsconfig.build.json`（构建 TS 配置）
- `webapp/packages/supersonic-fe/config/config.ts:163-165`（alias 配置）
- 阅读资料：
  1. `Monorepo 体系下构建业务组件库.md`
  2. `Monorepo 高频问题与标准答法体系.md`
  3. `前端组件库分层体系设计与实践.md`
  4. `React 组件库面试可能问题.md`

- [ ] **步骤 1：阅读资料（Day 12 上午）**

读完 4 篇，重点提取：Monorepo 下组件库的版本管理、组件库分层设计、面试常问问题。

- [ ] **步骤 2：精读 Rollup 配置 + SDK 入口（Day 12 下午）**

打开 `rollup/` 目录，回答：
- 输出了哪些格式？（ESM → `dist/index.es.js`，UMD → `dist/index.umd.js`）
- 为什么输出两种格式？（ESM 用于现代打包工具 tree-shaking，UMD 用于 CDN 直接引入）
- 外部依赖怎么处理？（peerDependencies — react/react-dom 不打包进 SDK，由消费方提供）
- TypeScript 声明文件怎么生成？（`tsconfig.build.json` → `tsc` 生成 `.d.ts`，package.json 的 `types` 字段指向声明入口）

打开 `src/index.tsx`，列出对外暴露的所有导出：
```typescript
export { Chat, Copilot, ChatProvider, ... }  // 组件
export { useChat, usePolling, ... }           // hooks
export type { MsgDataType, ContentType, ... }  // 类型
```

- [ ] **步骤 3：手写 mini npm 包体验 SDK 发布消费（Day 13 上午）**

创建 `/tmp/mini-sdk/` 目录：

```
/tmp/mini-sdk/
├── package.json    # name: "mini-sdk", main: "dist/index.js"
├── rollup.config.js
├── src/
│   └── index.js    # export function greet(name) { return `Hello ${name}` }
└── consumer/
    └── app.js      # import { greet } from 'mini-sdk'; console.log(greet('World'))
```

Steps：
1. 写 `src/index.js`（一个简单的 greet 函数）
2. 写 `package.json`（配置 main/module）
3. 写 `rollup.config.js`（ESM 输出）
4. 运行 `npx rollup -c` 生成 dist
5. 在 consumer 中用 `npm link` 或直接 `import` 测试

目的不是做出完整的 SDK，而是体验"写库 → 打包 → 消费"的完整流程。

- [ ] **步骤 4：产出面经 `docs/面经/02-功能模块/04-chat-sdk独立包.md`（Day 13 下午）**

包含 5 个 Q&A：

1. **chat-sdk 是怎么从 Monorepo 中抽离出来的？为什么这样做？** 答：pnpm workspaces + Rollup 构建 ESM/UMD。目标是将 Chat 核心能力解耦为独立包，支持宿主应用通过 `import` 集成，而不需要引入整个 supersonic-fe。

2. **SDK 导出了哪些内容？怎么保证可嵌入性？** 答：组件（Chat/Copilot）、hooks（useChat/usePolling）、类型（MsgDataType 等）。通过 ChatProvider 注入配置（baseUrl/token），内部用 Context 消费，不依赖具体宿主框架。

3. **Rollup 的 ESM 和 UMD 输出有什么区别？为什么都要？** 答：ESM 支持 tree-shaking，现代打包工具能移除未用代码。UMD 兼容 `<script>` 直接引入，用于 CDN 或旧项目。两种格式覆盖不同消费场景。

4. **SDK 的类型定义是怎么导出的？消费者怎么获得类型提示？** 答：`tsconfig.build.json` → `tsc` 生成 `dist/index.d.ts`，`package.json` 的 `types` 字段指向它。消费者 `import type { MsgDataType } from 'supersonic-chat-sdk'` 即可获得完整类型提示。

5. **Monorepo 下 SDK 的版本怎么管理？改了 SDK 宿主怎么同步？** 答：开发阶段用 `workspace:*` 协议，宿主实时引用最新 SDK 代码（config.ts 中 alias 到源码目录）。发布阶段用 changeset 管理版本号，宿主通过 `workspace:*` 自动锁定。

- [ ] **步骤 5：Commit**

```bash
cd ~/workspace/supersonic
git add docs/面经/02-功能模块/04-chat-sdk独立包.md
git commit -m "docs: Day12-13 面经 — chat-sdk独立包深入"
```

---

### 任务 9：Day 14-15 — 系统设置 + Agent/插件 + 数据库/LLM 配置（2 天）

**目标：** 速读剩余页面，提炼面试要点，产出一篇覆盖面经。

**文件（阅读）：**
- `webapp/packages/supersonic-fe/src/pages/System/`（系统设置）
- `webapp/packages/supersonic-fe/src/pages/Agent/`（Agent 管理）
- `webapp/packages/supersonic-fe/src/pages/ChatPlugin/`（插件管理）
- `webapp/packages/supersonic-fe/src/pages/SemanticModel/components/Database/DatabaseTable.tsx`（数据库配置）
- `webapp/packages/supersonic-fe/src/pages/SemanticModel/components/LLM/LlmTable.tsx`（LLM 配置）
- 阅读资料：
  1. `AI 对话项目中组件封装在前端面试的探讨.md`
  2. `面试中如何讲 Axios 的二次封装.md`

- [ ] **步骤 1：速读各页面代码（Day 14）**

对每个页面，快速抓取：
- 页面职责（一句话）
- 核心组件列表
- 与后端 API 的交互点
- 值得在面试中提的点

用表格记录：

| 页面 | 职责 | 面试可提点 |
|------|------|-----------|
| /system | 系统参数配置 | 参数持久化、权限管控（SYSTEM_ADMIN） |
| /agent | Agent 策略配置 | LLM 绑定、解析策略选择 |
| /plugin | 插件管理 | 插件注册/启停机制 |
| /database | 数据库连接配置 | 多数据源支持（MySQL/PG/ClickHouse等） |
| /llm | LLM 模型配置 | 多模型支持、API key 管理 |

- [ ] **步骤 2：产出面经 `docs/面经/02-功能模块/05-系统设置与Agent.md`（Day 15）**

包含 4 个 Q&A：

1. **系统设置页面做了哪些功能？权限怎么控制的？** 答：（参数配置 + SYSTEM_ADMIN 权限路由守卫）
2. **Agent 是怎么回事？它在 Chat BI 中起什么作用？** 答：Agent 是解析策略的配置入口，绑定 LLM 模型和解析规则，不同 Agent 可有不同的解析行为。用户提问时指定 agentId，后端按该 Agent 的策略执行 NL2SQL。
3. **项目支持哪些数据库？数据库配置页面做什么？** 答：MySQL/PostgreSQL/ClickHouse/StarRocks/Presto/H2/DuckDB。配置页面管理数据库连接信息（host/port/db/user/password），建好后供语义模型绑定。
4. **LLM 配置页面做什么？支持哪些模型？** 答：配置 LLM 的 API endpoint、API key、模型名称、温度等参数。支持 OpenAI/DeepSeek/DashScope 等兼容接口的模型。

- [ ] **步骤 3：Commit**

```bash
cd ~/workspace/supersonic
git add docs/面经/02-功能模块/05-系统设置与Agent.md
git commit -m "docs: Day14-15 面经 — 系统设置与Agent"
```

---

## Layer 3：简历亮点面试准备（Day 16-25）

### 任务 10：Day 16 — 简历定稿日

**目标：** 基于 Layer 1+2 的全部积累，重新审视简历，确定最终的 4 大主题和子点。

**文件（阅读/修改）：**
- `docs/面经/01-全局观/`（4 篇，回顾）
- `docs/面经/02-功能模块/`（5 篇，回顾）
- `docs/项目简历亮点.md`（待重写）

- [ ] **步骤 1：调研（2h）**

通读 Layer 1+2 的全部 9 篇面经，用荧光笔标注（或在旁边写注释）：
- "面试官听了会追问"的模块
- "这个点比预想的更有深度"
- "这个点没什么可追问的"

整理出一个"候选亮点清单"，每个候选标注：代码位置、深度评级（高/中/低）、可追问点数。

- [ ] **步骤 2：决策（2h）**

四个预设主题逐条确认/调整：

| 主题 | 决策 | 理由 |
|------|------|------|
| Chat BI 核心体验 | 确认保留，子点：流式输出+图表判断+澄清选择+维度下钻 | Layer 2 中代码量最大、追问点最多 |
| 语义模型配置 | 确认保留，子点：配置式表单+模型层级关系 | CRUD 型页面但抽象层次值得讲 |
| 权限控制体系 | 确认保留，子点：登录鉴权+三级权限控制 | 安全意识和全栈视角加分 |
| chat-sdk 独立包 | 确认保留，子点：Monorepo+Rollup+可嵌入设计 | 工程化能力的集中体现 |

如有新增（如性能优化、虚拟滚动等），纳入对应主题或新增主题。

- [ ] **步骤 3：写简历（2h）**

按"问题 → 手段 → 结果"格式，重写 `docs/项目简历亮点.md`。每条遵循经验贴原则：
- 不是"完成了 XXX 功能"
- 而是"通过 XXX 解决了 YYY 问题，达到了 ZZZ 效果"
- 可量化尽量量化（组件复用率、开发效率、DOM 节点减少量等）

- [ ] **步骤 4：重排 Layer 3 计划（2h）**

根据最终的主题数和子点数，分配 Day 17-22 的时间：
- Chat BI 核心体验（子点多，可能多半天）
- 语义模型配置
- 权限控制体系
- chat-sdk 独立包

在 `docs/面经/03-简历亮点/README.md` 中记录重排后的日程。

- [ ] **步骤 5：Commit**

```bash
cd ~/workspace/supersonic
git add docs/项目简历亮点.md docs/面经/03-简历亮点/README.md
git commit -m "docs: Day16 简历定稿 — 4大主题确认与Layer3计划重排"
```

---

### 任务 11：Day 17-22 — 四大主题面经撰写

**目标：** 按 Day 16 重排后的计划，逐一撰写简历亮点的深度面经。

**文件（产出）：**
- `docs/面经/03-简历亮点/01-ChatBI核心体验.md`
- `docs/面经/03-简历亮点/02-语义模型配置.md`
- `docs/面经/03-简历亮点/03-权限控制体系.md`
- `docs/面经/03-简历亮点/04-chat-sdk独立包.md`

每篇面经格式：
```markdown
# 主题名

## 简历条目原文
> [Day 16 定稿后的简历描述]

## 30秒一句话概括
> [定义 → 原理 → 示例]

## 子点 1：[子点名]

### 代码位置
[精确到文件和行号]

### 面试说辞（3分钟版）
[背景 → 技术路径 → 结果，可背诵的结构化回答]

### 追问链
- 追问1：xxx → 答：xxx
- 追问2：xxx → 答：xxx
- 追问3：xxx → 答：xxx

### 技术选型对比
| 方案 | 优点 | 缺点 | 为什么选当前 |
|------|------|------|------------|
| 当前 | xxx | xxx | — |
| 替代A | xxx | xxx | xxx |
| 替代B | xxx | xxx | xxx |

## 子点 2：...
```

- [ ] **步骤 1：撰写 Chat BI 核心体验面经（预计 2-2.5 天）**

子点：流式输出、智能图表判断、澄清选择与交互式查询调整、维度下钻。
每个子点含：代码位置 + 3 分钟说辞 + 3 个追问 + 技术选型对比表。

- [ ] **步骤 2：撰写语义模型配置面经（预计 1-1.5 天）**

子点：Domain/Model/Metric/Dimension 层级关系、配置式表单设计、模型绑定数据库流程。

- [ ] **步骤 3：撰写权限控制体系面经（预计 1-1.5 天）**

子点：登录鉴权流程（token 存储/注入/刷新）、路由权限守卫（access 插件）、行列级权限控制（authorized 标记）。

- [ ] **步骤 4：撰写 chat-sdk 独立包面经（预计 1-1.5 天）**

子点：Monorepo 架构、Rollup 打包策略、SDK 可嵌入设计（ChatProvider 模式）、Copilot 嵌入模式。

- [ ] **步骤 5：每完成一篇即 Commit**

```bash
cd ~/workspace/supersonic
git add docs/面经/03-简历亮点/01-ChatBI核心体验.md
git commit -m "docs: Day17-22 面经 — Chat BI核心体验（简历亮点）"
# ... 依此类推
```

---

### 任务 12：Day 23 — 跨模块串联 + 后端数据流

**目标：** 产出全链路串联面经，能从"用户输入问题"一路讲到"数据库返回结果"。

**文件（阅读）：**
- 后端 Chat 模块概览：`chat/` 目录结构（不深入源码，了解模块划分即可）
- 阅读资料：`前端项目中前后端的协作问题.md`、`前端面试官问你前后端协作其实在看什么.md`

- [ ] **步骤 1：阅读后端数据流资料**

快速了解 SuperSonic 后端 Chat BI 的处理链：
```
用户提问 → Knowledge Base（schema提取）→ Schema Mapper（识别指标/维度/实体）
  → Semantic Parser（生成S2SQL，规则+LLM双引擎）
  → Semantic Corrector（校验修正）→ Semantic Translator（S2SQL→物理SQL）
  → 数据库执行 → 结果返回
```

- [ ] **步骤 2：写全链路串联回答**

用"一段话讲清楚项目" + "全链路追问"的结构：

1. **一段话介绍 SuperSonic 项目** → 30 秒版本
2. **从前端输入框到数据库返回结果的完整链路** → 跨前后端的全链路描述
3. **前后端怎么协作？接口协议怎么定的？** → REST API + JSON 协议
4. **前端怎么处理后端返回的异常？** → 超时重试 + 错误提示 + 兜底方案

- [ ] **步骤 3：产出 `docs/面经/03-简历亮点/05-全链路串联.md`**

- [ ] **步骤 4：Commit**

```bash
cd ~/workspace/supersonic
git add docs/面经/03-简历亮点/05-全链路串联.md
git commit -m "docs: Day23 面经 — 全链路串联"
```

---

### 任务 13：Day 24 — 模拟面试

**目标：** 逐主题走一遍"你讲 → 我追问 → 你答 → 我点评"的流程。

**不需要代码或文件，纯口语练习。** 对照 4 大主题面经，每个主题按以下流程：

1. 你先用 30 秒概括这个主题做了什么
2. 我挑一个子点追问（"为什么用 A 不用 B？""如果不用这个库你怎么做？"）
3. 你回答
4. 我点评：回答结构是否清晰 / 有无模糊表述 / 是否覆盖了"为什么"
5. 换下一个追问

全部主题走完后，练习"项目整体四段式介绍"：背景 → 角色 → 结果 → 反思。

记录薄弱点，供 Day 25 回补。

---

### 任务 14：Day 25 — 全复盘 + 面经手册终稿

**目标：** 回顾所有面经，修补薄弱点，定稿面经手册。

- [ ] **步骤 1：逐篇复盘**

按顺序重读全部 14 篇面经（4 篇全局观 + 5 篇功能模块 + 4 篇简历亮点 + 1 篇全链路），标出：
- 回答不够自信的 Q&A
- 追问链不完整的 Q&A
- 技术选型对比缺失的 Q&A

- [ ] **步骤 2：修补薄弱点**

针对标记出的薄弱 Q&A，回读源码或资料，补充完善。

- [ ] **步骤 3：添加 README 索引**

在 `docs/面经/README.md` 中创建目录索引：

```markdown
# SuperSonic 前端面经手册

## 01-全局观
- [项目跑通](01-全局观/01-项目跑通.md)
- [项目结构全景](01-全局观/02-项目结构全景.md)
- ...

## 02-功能模块
...

## 03-简历亮点
...
```

- [ ] **步骤 4：最终 Commit**

```bash
cd ~/workspace/supersonic
git add docs/面经/
git commit -m "docs: Day25 面经手册终稿 — 全14篇完成"
```

---

## 自检清单

1. **规格覆盖度**：逐条对照设计规格的三层日程和四大主题，均有对应任务。✓
2. **占位符扫描**：无"TODO""待定""后续实现"。✓
3. **类型一致性**：面经目录结构与设计规格一致，文件名命名一致。✓
