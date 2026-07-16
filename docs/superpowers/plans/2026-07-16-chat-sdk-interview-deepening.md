# chat-sdk 面试文档深化 — 实现计划

> **执行方式：** 本次任务由当前会话交互式完成（教学 + 文档编写），不使用子代理。步骤使用复选框（`- [ ]`）语法跟踪进度。

**目标：** 通过代码驱动学习深化对 chat-sdk 组件库的理解，并将现有面试文档从 6 问扩展到 14 问（精写 5 + 简写 3）。

**架构：** 三阶段漏斗——15 分钟概念速讲 → 6 层代码走读（每层映射面试问题）→ 面试文档编写。交付物：更新后的 `docs/superpowers/resume/04-chat-sdk.md`。

**技术栈：** React 18 / TypeScript 4.9 / Rollup 3 / Less + CSS Modules / pnpm workspace / Ant Design 5

---

### 任务 1：Phase 1 概念速讲 — Monorepo + pnpm workspace

**产出：** 无文件产出。交互式讲解，以 SuperSonic 实际代码为案例。

**讲解要点：**
- Multirepo vs Monorepo 对比（修改→打包→发布→安装 改 修改→热更新）
- pnpm workspace 工作原理：`pnpm-workspace.yaml` → symlink → 本地源码引用
- SuperSonic 实际配置：`webapp/pnpm-workspace.yaml` 逐行解读

**代码锚点：** `webapp/pnpm-workspace.yaml`（3 行关键配置）

- [ ] 讲解 Monorepo 概念（5 min）
- [ ] 用户确认理解，进入下一概念

---

### 任务 2：Phase 1 概念速讲 — Rollup vs Webpack

**产出：** 无文件产出。

**讲解要点：**
- 对比表：Rollup（库）vs Webpack（应用）
- chat-sdk 为什么双工具并用：Rollup 出产物 + Webpack Dev Server 做调试
- Rollup 插件链概念预览（为 L1 代码走读打底）

**代码锚点：** `package.json` scripts 字段（`build-es` vs `start:dev`）

- [ ] 讲解 Rollup vs Webpack（5 min）
- [ ] 用户确认理解，进入下一概念

---

### 任务 3：Phase 1 概念速讲 — peerDependencies vs dependencies

**产出：** 无文件产出。

**讲解要点：**
- 语义区别：deps（自用，打包包含）vs peerDeps（宿主已有，不重复）
- 关键风险：React 重复打包 → hooks 闭包上下文不同 → "Invalid hook call"
- chat-sdk 实际做法：`exclude-dependencies-from-bundle` 插件
- antd 为什么放在 dependencies 而非 peerDeps

**代码锚点：** `package.json` 第 8-33 行（deps + peerDeps）+ `rollup.esm.config.mjs` 第 15 行

- [ ] 讲解 peerDeps 设计（5 min）
- [ ] 用户确认理解

---

### 任务 4：Phase 2 L1 — 项目全貌走读

**产出：** 无文件产出。理解 chat-sdk 的工程化骨架。

**文件清单：**
- `package.json`：四入口（main/module/unpkg/types）、scripts、deps/peerDeps/devDeps
- `tsconfig.json` + `tsconfig.build.json`：noEmit（开发）vs declaration:true（构建）
- `rollup/rollup.config.mjs` + `rollup.esm.config.mjs`：基础配置 + ESM 扩展
- 目录树：`Chat/ Copilot/ components/ service/ utils/ styles/ demo/`

**讲解要点：**
- `package.json` 的 `main` vs `module` vs `unpkg` vs `types` 四种入口的使用场景
- Rollup 插件链：typescript2 → nodeResolve → commonjs → styles → terser → excludeDeps，顺序为什么不能换
- `rollup-plugin-styles` 的 `autoModules`：自动识别 `.module.less` 为 CSS Modules

**面试映射：** Q "SDK 的工程化配置是怎么设计的？"

- [ ] 走读 package.json（四入口 + 脚本）
- [ ] 走读 tsconfig（开发 vs 构建差异）
- [ ] 走读 Rollup 配置（插件链顺序）
- [ ] 走读目录结构（模块划分逻辑）
- [ ] 总结：L1 → 面试问题映射

---

### 任务 5：Phase 2 L2 — 入口层走读

**产出：** 无文件产出。

**文件清单：**
- `src/index.tsx`（44 行）：barrel export
- `src/common/type.ts`（269 行）：类型定义

**讲解要点：**
- Barrel Export 模式：一个文件聚合所有导出
- 导出分层：组件（开箱即用 UI）+ API（逻辑复用）+ 类型（编译期检查）
- Chat vs ChatItem 分导出 = 渐进式集成（第三方可用 ChatItem 自定义消息列表）
- TypeScript `export type` vs `export` 的区别（编译后前者被擦除）

**面试映射：** Q "SDK 的 API 设计原则是什么？"

- [ ] 走读 src/index.tsx 逐行解读
- [ ] 走读 common/type.ts 核心类型（MsgDataType / SendMsgParamsType / ChatContextType）
- [ ] 总结：L2 → 面试问题映射

---

### 任务 6：Phase 2 L3 — Chat 核心组件走读

**产出：** 无文件产出。

**文件清单：**
- `src/Chat/index.tsx`（526 行）：核心组件
- `src/Chat/type.ts`：Chat 专用类型

**讲解要点（聚焦两段核心代码）：**
1. 状态声明（第 60-79 行）：14 个 useState + 2 个 useRef，理解"做什么用"
2. forwardRef + useImperativeHandle：暴露哪些方法给父组件（Copilot 会用到）
3. 消息发送流程：`onSendMsg` → API 调用 → messageList 更新 → 滚动到底部
4. Agent 切换：`onCurrentAgentChange` → 重置 messageList + conversation
5. `useThrottleFn` 防抖滚动加载历史消息

**面试映射：** Q "Chat 组件的状态管理怎么设计的？"

- [ ] 走读 Chat 组件 Props 定义（第 32-43 行）
- [ ] 走读状态声明（第 60-79 行），解释每个 state 的职责
- [ ] 走读 forwardRef + useImperativeHandle（定位相关代码）
- [ ] 走读消息发送链路（定位 onSendMsg 核心逻辑）
- [ ] 总结：L3 → 面试问题映射

---

### 任务 7：Phase 2 L4 — Copilot 包装组件走读

**产出：** 无文件产出。

**文件清单：**
- `src/Copilot/index.tsx`（149 行）

**讲解要点：**
- 组合模式：Copilot 不继承 Chat，而是将其作为子组件渲染
- `useImperativeHandle` 暴露 `sendCopilotMsg(params)` 给外部（按钮点击触发）
- `sendCopilotMsg` 内部逻辑：Agent 不同→切换+重置 / Agent 相同→直接发送
- ref 链：外部 ref → Copilot → Chat ref（两层 ref 透传）
- Props 透传：token / agentIds / isDeveloper → Chat 组件

**面试映射：** Q "Chat 和 Copilot 的组件通信设计有什么不同？"

- [ ] 走读 Copilot Props（第 19-28 行）
- [ ] 走读 useImperativeHandle（第 49-51 行）
- [ ] 走读 sendCopilotMsg 实现（第 65-68 行）
- [ ] 走读 Chat 子组件渲染（定位 JSX）
- [ ] 总结：L4 → 面试问题映射

---

### 任务 8：Phase 2 L5 — 渲染组件走读

**产出：** 无文件产出。

**文件清单：**
- `src/components/ChatItem/index.tsx` + 子组件（ParseTip / SqlItem / ExecuteItem / Typing / Loading）
- `src/components/ChatMsg/index.tsx` + 子组件（Table / Bar / Pie / MetricCard / MetricTrend / MarkDown / Text）

**讲解要点：**
- ChatItem 解析链路：ParseTip（解析提示）→ SqlItem（展示 SQL）→ ExecuteItem（执行）→ 最终渲染
- ChatMsg 策略模式：根据 msgType 分发 → Table / Bar / Pie / MetricCard / MetricTrend / MarkDown / Text
- 关键子组件：FilterSection（筛选条件展示）、DateOptions（时间范围选择）、DrillDownDimensions（下钻维度）

**面试映射：** Q "SDK 如何支持多种消息类型的渲染？"

- [ ] 走读 ChatItem 核心结构（index.tsx 的组件组合方式）
- [ ] 走读 ChatMsg 的策略分发逻辑
- [ ] 选读 2-3 个关键子组件（Table / MetricTrend / MarkDown）
- [ ] 总结：L5 → 面试问题映射

---

### 任务 9：Phase 2 L6 — 服务层 + 工具层走读

**产出：** 无文件产出。

**文件清单：**
- `src/service/index.ts`（161 行）：API 函数
- `src/service/axiosInstance.ts`：axios 实例封装
- `src/utils/utils.ts`：工具函数
- `src/setupProxy.js`：开发代理

**讲解要点：**
- axios 实例：baseURL / request 拦截器（token 注入）/ response 拦截器（统一错误处理）
- 移动端 vs PC 端：`isMobile ? '/openapi' : '/api'`
- 关键 API：`searchRecommend` / `chatQuery` / `chatParse` / `getHistoryMsg`
- 工具函数：`setToken`（存储到 storage）/ `uuid`（消息 ID 生成）/ `jsonParse`（安全解析）

**面试映射：** Q "SDK 的 API 层怎么设计的？"

- [ ] 走读 axiosInstance 封装
- [ ] 走读 service/index.ts 关键 API
- [ ] 走读 utils 核心函数
- [ ] 总结：L6 → 面试问题映射

---

### 任务 10：Phase 3 — 编写精写 Q7：peerDependencies 设计哲学

**产出：** 更新 `docs/superpowers/resume/04-chat-sdk.md`

**文件：** 修改 `docs/superpowers/resume/04-chat-sdk.md`

**内容结构：**
- 问题：为什么要区分 peerDependencies 和 dependencies？chat-sdk 中分别是哪些？
- 回答：语义区别 + React 重复打包风险 + antd 为什么在 deps + exclude-deps 插件原理
- 追问链：
  - 如果 React 被打包两份会出什么 bug？（hooks 闭包上下文不同 → "Invalid hook call"）
  - antd 为什么放 dependencies 而不是 peerDependencies？（SDK 使用者不一定用 antd）
  - `rollup-plugin-exclude-dependencies-from-bundle` 做了什么？（打包时排除 peerDeps 中的包）

**代码锚点：** `package.json:8-33` + `rollup.esm.config.mjs:15`

- [ ] 编写 Q7 完整内容（问题 + 回答 + 追问链）
- [ ] 在现有文档中插入（Q6 之后）

---

### 任务 11：Phase 3 — 编写精写 Q8：forwardRef + useImperativeHandle 实践

**产出：** 更新 `docs/superpowers/resume/04-chat-sdk.md`

**内容结构：**
- 问题：Copilot 组件中 forwardRef + useImperativeHandle 是怎么用的？
- 回答：组合模式 + ref 通信设计 + sendCopilotMsg 内部逻辑
- 追问链：
  - 为什么不用 props 回调而用 ref？（Copilot 是封装层，回调传递链太长）
  - sendCopilotMsg 内部 Agent 切换逻辑？（不同则切换+重置，相同则直接发送）
  - ref 通信的注意事项？（null check、TypeScript 类型安全、避免过度暴露）
- 代码片段：Copilot/index.tsx 第 30-51 行精简版

**代码锚点：** `Copilot/index.tsx:30-51` + `Chat/index.tsx` useImperativeHandle 部分

- [ ] 编写 Q8 完整内容
- [ ] 插入文档

---

### 任务 12：Phase 3 — 编写精写 Q9-Q11

**产出：** 更新 `docs/superpowers/resume/04-chat-sdk.md`

**Q9：CSS Modules 样式隔离方案**
- 代码锚点：`*.module.less` + `variables.less` + `PREFIX_CLS`
- 追问：为什么 CSS Modules 而非 styled-components？宿主如何覆盖变量？

**Q10：Rollup 插件链设计**
- 代码锚点：`rollup/rollup.config.mjs` + `rollup.esm.config.mjs`
- 追问：插件顺序为什么不能换？autoModules 做了什么？ESM vs UMD 使用场景？

**Q11：Chat 组件消息流与状态管理**
- 代码锚点：`Chat/index.tsx` 状态声明 + 消息发送逻辑
- 追问：Agent 切换状态重置？移动端 vs PC 端？useThrottleFn 怎么用？

- [ ] 编写 Q9 完整内容
- [ ] 编写 Q10 完整内容
- [ ] 编写 Q11 完整内容
- [ ] 按顺序插入文档

---

### 任务 13：Phase 3 — 编写简写 Q12-Q14 + 附录

**产出：** 更新 `docs/superpowers/resume/04-chat-sdk.md`

**Q12：SDK 开发调试流程**
- Webpack Dev Server + setupProxy + demo 页面
- 3-5 行要点

**Q13：TypeScript 类型系统设计**
- common/type.ts 组织思路 + export type 机制
- 3-5 行要点

**Q14：API 错误处理与边界情况**
- axios 拦截器统一处理 + token 过期处理
- 3-5 行要点

**附录：关键代码片段索引**
- 表格格式：面试问题 → 关键文件 → 核心行号
- 方便面试前快速回顾

- [ ] 编写 Q12-Q14 简写内容
- [ ] 编写附录（代码片段索引表）
- [ ] 全文通读，确保格式一致、无矛盾

---

### 任务 14：最终检查 + Commit

**产出：** 最终版 `docs/superpowers/resume/04-chat-sdk.md` + git commit

**检查项：**
- 新旧 Q&A 编号连续无跳跃
- 代码行号与当前代码库一致
- 追问链覆盖了代码锚点中的所有关键知识点
- 中文表达自然，符合面试回答的口语化风格

- [ ] 全文检查（编号/行号/一致性/中文表达）
- [ ] `git add docs/superpowers/resume/04-chat-sdk.md`
- [ ] `git commit -m "docs: deepen 04-chat-sdk interview doc with 8 new Q&As"`

---

## 自检

### 规格覆盖度

| 规格需求 | 对应任务 |
|----------|---------|
| Phase 1: 3 个概念讲解 | 任务 1-3 |
| Phase 2: L1 项目全貌 | 任务 4 |
| Phase 2: L2 入口层 | 任务 5 |
| Phase 2: L3 Chat 核心 | 任务 6 |
| Phase 2: L4 Copilot | 任务 7 |
| Phase 2: L5 渲染组件 | 任务 8 |
| Phase 2: L6 服务层 | 任务 9 |
| Phase 3: 精写 Q7-Q11 | 任务 10-12 |
| Phase 3: 简写 Q12-Q14 | 任务 13 |
| 附录 | 任务 13 |
| 交付物 commit | 任务 14 |

✅ 全覆盖，无遗漏。

### 占位符扫描

检查所有任务中的代码块和内容描述：
- 任务 10-13 中 Q&A 内容描述了结构（问题/回答/追问链），未留 TODO
- 无"待定""后续补充"等占位符
- 每个接口/类型名都来自实际代码库

✅ 无占位符。

### 类型一致性

- 任务 10 中引用的 `package.json:8-33` 与任务 4 中走读的 `package.json` 一致
- 任务 11 中引用的 `Copilot/index.tsx:30-51` 与任务 7 中走读的文件一致
- 所有代码锚点的行号在走读阶段已验证

✅ 一致，无矛盾。
