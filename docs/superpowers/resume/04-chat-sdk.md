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
