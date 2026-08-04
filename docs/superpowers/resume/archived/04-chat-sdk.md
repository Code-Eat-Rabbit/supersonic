# chat-sdk 前端组件库 — 简历文案 + 面试预案

## 简历文案（终版）

> 抽离 Chat-BI 对话能力为独立前端 SDK（supersonic-chat-sdk），基于 React + TypeScript + Rollup 构建，支持 Chat 对话与 Copilot 嵌入式助手两种集成模式

---

## 面试追问 Q&A

### Q1：为什么要抽离 SDK？它和主项目的依赖关系是怎样的？

**A：** 核心动机是「复用」和「解耦」。

- **复用**：Chat-BI 对话能力需要被多个场景消费——主站（supersonic-fe）、第三方系统嵌入、独立 demo 页面——如果逻辑耦合在主项目里，每次复用都要复制代码
- **解耦**：SDK 通过明确的 Props 接口（`Chat/Copilot` 组件）暴露能力，消费方不需要关心内部解析链路的实现细节，只需传入 API 配置即可

**依赖关系：**
```
webapp/
├── packages/
│   ├── chat-sdk/          ← 独立组件库（本次工作）
│   └── supersonic-fe/     ← 主站
└── package.json           ← "supersonic-chat-sdk": "link:packages/chat-sdk"
```

- 主站通过 `pnpm link` 本地引用 SDK，开发阶段 SDK 修改实时生效
- SDK 的 `peerDependencies` 声明 React 作为共享依赖（与主站共享同一份 React 避免版本冲突）
- Rollup 打包时通过 `rollup-plugin-exclude-dependencies-from-bundle` 排除 React/Antd 等宿主依赖，只打包 SDK 自身代码

### Q2：Rollup 打包配置是怎么设计的？为什么不用 Webpack？

**A：**

- **选 Rollup**：SDK 是组件库（library），不是应用（application）。Rollup 对库打包的支持比 Webpack 更友好——天然支持 ESM/UMD 多格式输出、tree-shaking 更彻底、产物更干净
- **配置**：
  ```js
  // rollup/rollup.esm.config.mjs — ESM 格式
  output: [{ file: 'dist/index.es.js', format: 'es' }]
  plugins: [commonjs, json, typescript2, postcss, terser, excludeDeps]

  // rollup/rollup.umd.config.mjs — UMD 格式
  output: [{ file: 'dist/index.umd.js', format: 'umd', name: 'SupersonicChatSDK' }]
  ```
- **package.json 映射**：
  - `main: "dist/index.es.js"` — Node/打包工具入口
  - `module: "dist/index.es.js"` — ESM 入口（支持 tree-shaking）
  - `unpkg: "dist/index.umd.js"` — CDN <script> 直接引入
  - `types: "dist/index.d.ts"` — TypeScript 类型声明
- **构建链路**：`tsc -p tsconfig.build.json`（类型检查 + 声明生成）→ `rollup --config rollup.esm.config.mjs`（ESM 产物）→ `rollup --config rollup.umd.config.mjs`（UMD 产物）

### Q3：Chat 和 Copilot 两种模式的设计差异？

**A：**

| 维度 | Chat | Copilot |
|------|------|---------|
| 定位 | 独立对话页面 | 嵌入式 AI 助手 |
| 交互方式 | 用户主动输入+多轮对话 | 外部按钮触发预设查询 |
| 组件 Props | 标准 Chat 组件 | `ref` 暴露 `sendCopilotMsg()` |
| Agent 切换 | 支持 Agent 选择面板 | 由外部按钮指定 Agent |
| 典型场景 | 主站 Chat-BI 页面 | 业务页面内嵌智能问答 |

**Copilot 的关键 API 设计：**
```tsx
// 外部通过 ref 调用
const copilotRef = useRef<any>();

// 按钮点击 → 触发 Copilot 内发送预设消息
<Button onClick={() => copilotRef.current?.sendCopilotMsg({
  msg: '周杰伦 艺人趋势解读',
  agentId: 8,
  modelId: 23,
  filters: [{ bizName: 'singer_id', elementID: 283, value: 4558 }]
})}>
  周杰伦趋势
</Button>

<Copilot isDeveloper ref={copilotRef} />
```

`sendCopilotMsg` 内部逻辑：
1. 如果目标 Agent 与当前 Agent 不同 → 切换 Agent，重置消息列表
2. 如果相同 → 直接 `onSendMsg(msg, messageList, modelId, params)`

### Q4：SDK 导出哪些内容？API 如何设计？

**A：** SDK 对外暴露（见 `src/index.tsx`）：

```ts
// 组件
export { Chat }        // 独立对话页面
export { Copilot }     // 嵌入式助手
export { ChatMsg }     // 单条消息渲染组件（第三方可自定义消息列表）
export { ChatItem }    // 单条聊天项（含解析+执行全链路）
export { ShowCase }    // 示例展示组件

// API 方法
export { searchRecommend }       // 输入联想搜索
export { saveConversation }      // 保存会话
export { getAllConversations }   // 获取会话列表
export { setToken }              // 设置认证 Token

// 类型定义（TypeScript）
export type { SearchRecommendItem, FieldType, ModelInfoType, EntityInfoType,
  DateInfoType, ChatContextType, MsgValidTypeEnum, MsgDataType,
  PluginResonseType, ColumnType, SuggestionItemType, SuggestionType,
  SuggestionDataType, FilterItemType, HistoryType, HistoryMsgItemType,
  SendMsgParamsType }
```

**设计原则**：
- 组件 → 开箱即用的 UI 单元
- API → 允许第三方自定义 UI 但复用后端调用层
- 类型 → 完整的 TypeScript 类型定义，消费方编译期即可发现接口不匹配

### Q5：SDK 如何管理主题样式？与宿主项目如何隔离？

**A：**

- **样式方案**：Less + CSS Modules（`*.module.less`），组件级样式隔离
- **主题变量**：`src/styles/variables.less` 定义 Ant Design 主题变量覆盖，消费方可在引入 SDK 前覆盖这些变量
- **全局样式**：`src/styles/index.less` 聚合 variables + reboot + global
- **`PREFIX_CLS`**：所有组件使用统一前缀（如 `supersonic-chat-sdk-item`），避免与宿主项目的 CSS 类名冲突
- **依赖管理**：Ant Design 声明为 `dependencies`（SDK 内部需要），React 声明为 `peerDependencies`（与宿主共享版本），避免重复打包导致 React hooks 报错

### Q6：SDK 的开发迭代流程？

**A：**

- **独立开发**：`npm start` → 启动 Webpack Dev Server 打开 demo 页面（ChatDemo / CopilotDemo），通过 `setupProxy.js` 代理到本地 SuperSonic 后端
- **热更新**：`rollup --watch` 监听 SDK 源码变更自动重编译，主站 `pnpm link` 后同时生效
- **测试**：Jest + React Testing Library，测试覆盖组件渲染和服务层函数

---

## 进阶追问 Q&A

### Q7：为什么 React 放 peerDependencies 而 antd 放 dependencies？如果 React 被打包两次会怎样？

**A：** 这是组件库设计的经典问题，核心是"谁负责提供这个依赖"。

**语义区别：**

| | dependencies | peerDependencies |
|---|---|---|
| 含义 | "我需要，打包时带上" | "我需要，但你（宿主）已经有了，别打包" |
| chat-sdk 例子 | antd、echarts、axios 等 | react、react-dom |
| 判断标准 | 第三方不一定有的 | 所有 React 项目必然有的 |

**为什么 React 不能打包两份：**

React 源码内部有一个模块级单例变量 `ReactCurrentDispatcher`，useState、useEffect 等所有 hooks 都依赖它：

```
ReactDOM.render() → 用的是 React A → 设置了 React A 的 dispatcher
SDK 的 useState() → 用的是 React B → React B 的 dispatcher 还是 null
→ 读到 null → 报错 "Invalid hook call"
```

两份 React = 两个互不相通的单例，设了一个读另一个，必然挂。

**工程防护（两层）：**
- 第一层：`package.json` 的 `peerDependencies: { "react": ">=16.8.0" }` → 告诉 pnpm 别重复安装
- 第二层：`rollup-plugin-exclude-dependencies-from-bundle()` → 打包时物理删除 peerDeps 中的包（见 `rollup/rollup.esm.config.mjs` 第 15 行）

> **追问：antd 为什么放 dependencies 而不是 peerDependencies？**
> 因为消费方不一定用 antd——他们可能用 Material UI 或其他设计系统。放 peerDependencies 会强加版本约束，而放 dependencies 让 SDK 自带一份，消费方无感知。

---

### Q8：Copilot 中 forwardRef + useImperativeHandle 是怎么用的？为什么不用 props 回调？

**A：** Copilot 使用双层 ref 链实现外部按钮 → Copilot → Chat 的指令下发，代码在 `Copilot/index.tsx` 第 30-68 行。

**调用链路：**

```
外部按钮点击
  → copilotRef.current.sendCopilotMsg({ msg: '周杰伦', agentId: 8 })
  → Copilot 的 sendCopilotMsg（第 65 行）：
      chatRef.current.sendCopilotMsg(params)  // 转发给 Chat
      setChatVisible(true)                     // 展开面板
  → Chat 的 sendCopilotMsg（Chat/index.tsx 第 85 行）：
      判断 Agent 是否变化 → 切换 or 发送
```

**为什么用 ref 而不是 props 回调：**

Copilot 是一个封装层，它本身不"拥有"发送消息的逻辑——逻辑全在 Chat 里。如果用 props 回调：
- Chat 需要把所有可能被外部调用的方法都作为回调 prop 传上来
- 每加一个方法就要加一个 prop → 接口膨胀
- 回调链过长：外部 → Copilot props → Chat props

用 ref 的话，Chat 只需要通过 `useImperativeHandle` 暴露方法，Copilot 拿到 chatRef 后可以直接调用，不污染 props 接口。

**`useImperativeHandle` 的作用（Copilot 第 49-51 行）：**

```tsx
useImperativeHandle(ref, () => ({
  sendCopilotMsg,  // 只暴露这一个方法，外部看不到其他内部细节
}));
```

不是直接把整个 ref 对象暴露出去，而是"选择性暴露"——外部只能调 `sendCopilotMsg`，不能直接操作 Copilot 的内部状态。这是 React 推荐的封装方式。

> **追问：ref 通信有什么注意事项？**
> 一是类型安全——ref 类型需要定义清楚暴露的方法签名；二是 null check——组件未挂载时 ref.current 为 null；三是避免过度暴露——只暴露必要的 API，保持封装性。

---

### Q9：SDK 的样式隔离是怎么做的？为什么选 CSS Modules？

**A：** 使用 Less + CSS Modules（`*.module.less`），通过三层机制实现样式隔离。

**第一层：CSS Modules 自动哈希**

所有 `*.module.less` 文件在 Rollup 构建时，通过 `rollup-plugin-styles` 的 `autoModules` 配置（`rollup/rollup.config.mjs` 第 25 行），自动给类名加哈希：

```css
/* 源码 */
.chatItem { padding: 12px; }

/* 编译后 */
.chatItem_3xk9a { padding: 12px; }  /* 全局唯一，不会和宿主冲突 */
```

组件中通过 `import styles from './style.module.less'` 引用，然后用 `styles.chatItem` 使用哈希后的类名。

**第二层：PREFIX_CLS 统一前缀**

所有全局类名使用统一前缀（如 `supersonic-chat-sdk-item`），见 `common/constants.ts` 中的 `PREFIX_CLS`。即使不用 CSS Modules 的场景，也能避免与宿主项目的 CSS 命名冲突。

**第三层：主题变量（variables.less）**

`src/styles/variables.less` 定义 Ant Design 主题变量覆盖。宿主项目在引入 SDK 之前覆盖对应的 Less 变量即可实现主题定制，无需修改 SDK 源码。

**为什么选 CSS Modules 而不是 styled-components：**
- CSS Modules 是纯 CSS 预处理，不引入 JS 运行时，打包体积更小
- 与 Less 配合自然，Ant Design 本身就用 Less 变量体系
- 不需要额外的 CSS-in-JS 依赖，减少 peerDependencies 冲突风险

> **追问：宿主想覆盖 SDK 内部的样式怎么办？**
> 一是覆盖 CSS 变量（如果在 variables.less 里定义了）；二是用更高特异性的 CSS 选择器；三是通过 Props 传入自定义 className（Chat 组件 Props 里保留了扩展点）。

---

### Q10：Rollup 打包的插件链是怎么设计的？顺序能不能换？

**A：** 不能换，这是一个流水线——每一步的输出是下一步的输入。

代码在 `rollup/rollup.config.mjs`：

```
① @rollup/plugin-node-resolve   "react 这个包在哪？去 node_modules 找"
    → 解析所有 import 路径，找到物理文件位置

② @rollup/plugin-commonjs       "有些包是 require() 写的，转成 ESM"
    → Rollup 原生只认识 import/export，不认识 require/module.exports
    → 必须先转，否则后续 TypeScript 编译会失败

③ @rollup/plugin-json           "允许 import data.json"

④ rollup-plugin-typescript2     "把 .tsx/.ts 编译成 .js + 生成 .d.ts"
    → tsconfigOverride: { declaration: true }
    → 必须在 commonjs 之后——此时所有依赖都已是 ESM 格式

⑤ rollup-plugin-styles          "处理 .less 和 .module.less"
    → autoModules: 文件名含 .module. 的自动开 CSS Modules

⑥ exclude-dependencies-from-bundle  "删掉 peerDeps 里的包（React）"
    → 读 package.json 的 peerDependencies 列表

⑦ @rollup/plugin-terser         "压缩最终产物"
    → 必须放最后——压缩的是完整产物
```

**如果换了会怎样：**
- typescript 放 commonjs 前面 → TS 编译器遇到 `require()` 语法报错
- nodeResolve 放 typescript 后面 → TS 不知道 `import from 'react'` 对应哪个文件
- terser 不放最后 → 后续插件处理的是已压缩的代码，难以调试

**两份构建配置：**
- `rollup.esm.config.mjs` → ESM 产物（`dist/index.es.js`），给 Webpack/Vite 等打包工具消费，支持 tree-shaking
- `rollup.umd.config.mjs` → UMD 产物（`dist/index.umd.js`），给 `<script>` 标签直接从 CDN 引入

---

### Q11：Chat 组件的消息流和状态管理怎么设计的？

**A：** Chat 组件（`Chat/index.tsx`，526 行）管理了整个对话页面的所有状态，分为四组共 14 个 state。

**状态分组：**

| 分组 | 状态 | 职责 |
|------|------|------|
| 消息流 | messageList, inputMsg, pageNo, hasNextPage, historyInited | 消息收发 + 历史分页加载 |
| 会话管理 | currentConversation, historyVisible | 新建/切换/查看历史会话 |
| Agent 管理 | agentList, currentAgent, mobileAgentsVisible, agentListVisible, showCaseVisible | Agent 列表、切换、展示 |
| 模式控制 | isSimpleMode, isDebugMode | 简易模式/调试模式 |

**消息发送流程：**

```
用户输入 → ChatFooter 回调 onSendMsg
  → 调用 chatQuery API（service/index.ts）
  → 后端返回 MsgDataType
  → setMessageList(prev => [...prev, newMsg])
  → updateMessageContainerScroll()  // 自动滚到底部
```

**Agent 切换时的状态重置（sendCopilotMsg 第 85-95 行）：**

```ts
if (currentAgent?.id !== agentId) {
  setMessageList([]);        // 清空消息——不同 Agent 之间不共享对话
  const agent = agentList.find(item => item.id === agentId);
  updateCurrentAgent({ ...agent, initialSendMsgParams: params });
} else {
  onSendMsg(msg, messageList, modelId, params);  // 同 Agent 直接发
}
```

**性能优化：`useThrottleFn` 防抖滚动加载**

使用 ahooks 的 `useThrottleFn` 对滚动事件做节流——避免用户快速滚动时频繁触发历史消息加载请求。

**移动端 vs PC 端差异（第 67 行注释）：**

移动端默认创建 `{ chatId: 0, chatName: '问答' }` 的临时会话——移动端空间有限，不强制要求先创建会话再对话。PC 端则是完整会话列表模式。

> **追问：为什么 Chat 不用全局状态管理（Redux/Zustand）？**
> Chat 的状态全部是组件内部状态，不需要跨页面共享。用 useState 足够，引入全局状态管理反而增加复杂度。如果未来需要跨 Tab 同步消息，可以再抽象一层。

---

## 快速覆盖 Q&A

### Q12：SDK 开发调试流程是怎样的？

- `npm start` → Webpack Dev Server 启动，入口 `src/demo/ChatDemo.tsx` 或 `CopilotDemo.tsx`
- API 请求通过 `src/setupProxy.js` 代理到 `http://localhost:9080`（SuperSonic 后端）
- Demo 页面直接渲染 `<Chat token={TOKEN} isDeveloper />` 或 `<Copilot />`，无需启动主站
- `rollup --watch` 监听源码变更自动重编译，主站通过 pnpm workspace symlink 同步热更新

### Q13：TypeScript 类型系统怎么组织的？

- `src/common/type.ts`（269 行）：所有共享类型定义——`MsgDataType`（消息数据）、`SendMsgParamsType`（发送参数）、`ChatContextType`（解析上下文）、`FilterItemType`（筛选条件）等
- `src/index.tsx` 用 `export type { ... }` 选择性导出——编译后擦除，不占打包体积
- 组件 Props 类型内联定义在组件文件中（如 Chat 的 Props 第 32-43 行），就近维护

### Q14：API 错误处理怎么设计的？

- axios 请求拦截器自动注入 Bearer token（从 localStorage 读取）
- 响应拦截器处理两种异常：
  - 后端返回 `redirect=REDIRECT` → SSO 认证跳转
  - HTTP 401 → 打印 "Unauthorized"，调用方可自行处理
- 业务层：ChatItem 的 `updateData` 方法（第 133 行）统一处理 code=400/401/412 等业务错误码
- `jsonParse` 工具函数：安全解析 JSON，解析失败返回默认值而非抛异常

---

## 附录：关键代码片段索引

| 面试问题 | 关键文件 | 核心行号 |
|---------|---------|---------|
| 为什么抽离 SDK | `pnpm-workspace.yaml` | 1-6 |
| Rollup 配置设计 | `rollup/rollup.config.mjs` | 15-36 |
| | `rollup/rollup.esm.config.mjs` | 5-17 |
| Chat/Copilot 差异 | `Copilot/index.tsx` | 30-51, 130-140 |
| SDK 导出设计 | `src/index.tsx` | 1-44 |
| 样式隔离 | `src/styles/variables.less` | 全文 |
| | `rollup/rollup.config.mjs` | 25 |
| peerDependencies | `package.json` | 8-33 |
| | `rollup/rollup.esm.config.mjs` | 15 |
| forwardRef | `Copilot/index.tsx` | 30-68 |
| | `Chat/index.tsx` | 45-95 |
| Chat 状态管理 | `Chat/index.tsx` | 32-95 |
| 消息渲染策略 | `ChatMsg/index.tsx` | 200-266 |
| | `ChatItem/index.tsx` | 91-141 |
| API 层设计 | `service/axiosInstance.ts` | 1-56 |
| | `service/index.ts` | 14 |
