### 为什么选择 Monorepo 架构来管理组件库？相比多仓库方式有哪些优劣？
在组件库场景下，通常需要同时维护：

+ 组件源码（packages/components）
+ 构建产物与发布配置
+ 文档站点（docs / storybook）
+ 工具包（hooks / utils）

**Monorepo** 指将多个相互关联的包统一维护在一个代码仓库中，通过 workspace 管理依赖关系。

#### Monorepo 的优势
1. **依赖统一，避免版本地狱**
    - 所有包共享同一份 node_modules
    - React、TypeScript 等基础依赖版本强一致，避免多仓库常见的 peerDependency 冲突问题
2. **跨包协作成本低**
    - 组件、文档、工具包可以直接源码级引用
    - 本地调试无需 npm link / yalc 等手段
3. **更适合组件库演进**
    - 新组件、新工具包可直接在 workspace 内新增
    - 适合长期维护和规模增长
4. **工程规范可统一落地**
    - ESLint / Prettier / Husky 在根目录统一配置
    - 提交规范、代码风格、CI 策略一致

#### 多仓库（Multi-repo）的问题
+ 依赖升级需要跨仓库同步，成本高
+ 组件与文档解耦后，联调体验差
+ 对于组件库这种“高内聚项目”，维护成本明显偏高

#### 在组件库中的具体实现
+ 使用 pnpm workspace： 
    - packages/cream-design：组件库主包
    - packages/docs / storybook：文档与示例
+ 通过 workspace 实现：
    - 依赖统一提升（hoist）
    - 内部包以源码方式引用，避免构建前依赖问题

#### 潜在问题与权衡
+ **仓库体积膨胀**：通过拆分 package scope 控制影响面
+ **CI 构建成本上升**：后续可引入 changeset + 增量发布
+ **对新成员理解成本略高**：通过明确目录约定降低认知负担

总结：**组件库属于强关联工程，Monorepo 在可维护性与工程效率上明显更优。**

### 你是如何实现组件的按需引入和全量引入的？用了哪些工具或技术？
组件库需要同时满足：

+ **全量引入**：快速使用，开发体验优先
+ **按需引入**：减小 bundle 体积，提升性能

#### 技术方案与对比
#### 可选方案
1. babel-plugin-import（传统方案）
2. 基于 ESM 的 Tree Shaking（现代方案）
3. 构建期多入口产物

Cream-Design 采用的是 **ESM + 多入口构建方案**，更符合 Vite 生态。

### 具体实现方式
#### 1）导出结构设计
```jsx
// packages/cream-design/index.ts
export { Button } from './components/Button'
export { Upload } from './components/Upload'
```

同时为每个组件提供独立入口：

```jsx
// packages/cream-design/components/Button/index.ts
export { default as Button } from './Button'
```

#### 2）构建配置
+ 使用 **Vite + Rollup**
+ 输出：
    - es：ESM，支持 Tree Shaking
    - lib：全量入口

#### 3）使用方式
```jsx
// 按需
import { Button } from 'cream-design'

// 全量
import CreamDesign from 'cream-design'
```

#### 4）潜在问题与注意点
+ Tree Shaking 前提是：
    - ESM 规范
    - 无副作用（或明确标注）
+ CSS 需避免全量注入：
    - 组件级样式拆分
+ 需在 package.json 中正确声明： 
    - module 
    - sideEffects

### 组件库是如何分类和组织的？你怎么保证结构清晰且便于扩展？props 你会从什么角度设计，比如说这个组件下有一个请求（副作用）你会怎么实现？
#### 组件分类原则
以 **“使用语义 + 复杂度”** 为核心，而非实现细节：

+ **通用组件**
    - Button / Icon / Typography
+ **数据录入类**
    - Input / Upload / AutoComplete
+ **反馈类**
    - Message / Modal / Tooltip
+ **布局类**
    - Grid / Space

### 目录组织示例
```plain
components/
 ├─ button/
 ├─ upload/
 ├─ auto-complete/
 └─ hooks/
```

每个组件内部统一约定：

+ index.ts：对外出口
+ types.ts：Props 类型 
+ style.ts：样式 
+ **tests**

#### 3. Props 设计思路（重点）
#### 1）职责单一
Props 只描述**组件能力，不承载业务逻辑**

#### 2）副作用（如请求）的处理方式
以 Upload 为例：

+ **组件不直接发请求**
+ 通过 props 向外暴露控制权

```jsx
onUpload(file) => Promise
beforeUpload(file) => boolean
```

优点：

+ 避免组件与接口强耦合
+ 易测试、易复用
+ 更符合企业级组件设计

#### 4. 扩展性保障
+ 组合优于继承
+ slot / render props 支持复杂定制
+ Props 保持扁平，避免深层嵌套对象

### 你在实现比如 Upload 或 AutoComplete 这类组件时，遇到过哪些难点？是怎么解决的？
授人以渔，你去 github 找出 antd 的源码，打开这个组件，喂给 ai（curosr，gpt，trae 等都可以）

我这边就简单提一下

#### Upload 的核心难点
1. **异步状态复杂**
    - pending / success / error
2. **多文件并发上传**
3. **进度控制**
4. **失败重试与中断**

**他**问你难点的话，肯定不是想考你会不会用axios的进度回调、会不会用拖拽 API

你要提现组件库级别的抽象设计、通用性、可扩展性思维，而非一次性业务代码能力，复杂场景、边界 case 的全链路兜底处理能力，对 React 组件设计规范（受控 / 非受控、状态管理、逻辑解耦）的理解深度，像 upload 的话

你可以举个把例子，像多场景兼容的上传进度实时更新与状态管理，组件库需要兼容单文件 / 多文件并发 / 大文件分片等全场景，既要保证进度计算的精准性、多文件状态的隔离性，还要符合 React 受控 / 非受控组件设计规范，同时解决高频更新的性能问题与极端场景的兜底，这是基础 API 调用无法覆盖的核心难点。

这个时候不同上传场景的进度计算逻辑不统一：普通单文件可直接用loaded/total，但分片上传需要聚合所有分片的进度，还要处理分片重传的进度回补。多文件并发上传时，多个文件的进度更新存在竞态问题，容易出现状态错乱。组件库必须同时支持受控与非受控模式，既要能内部管理状态，也要能完全把控制权交给父组件，避免状态不同步。还存在大量边界场景：空文件、响应头无Content-Length、上传中断 / 取消 / 失败时的进度重置，以及高频进度更新导致的不必要重渲染。你再针对这几个讲具体怎么做，普通单文件：基于 XHR/axios 的onUploadProgress事件，用loaded / total * 100计算，同时做防超界处理（固定 0-100% 区间）与整数取整，避免出现小数进度

分片上传场景：维护分片进度映射表，总进度 = 所有分片已上传大小之和 / 文件总大小 * 100，分片重传时自动更新对应分片进度，保证总进度精准

异常兜底：空文件、无Content-Length的场景，直接切换为加载中状态，避免出现NaN/Infinity等异常值导致组件崩溃。用useReducer替代useState管理多文件队列的进度状态，保证并发场景下多个文件的进度更新是原子化的，彻底解决竞态导致的状态错乱。对进度更新做 16ms 节流（对应浏览器刷新率），避免高频回调导致的组件不必要重渲染。监听上传中断、取消、失败事件，自动重置对应文件的进度状态，避免残留错误进度，组件卸载时自动清空进度队列，防止内存泄漏，这样子去叙述

#### 解决方案
+ 使用状态机思想管理文件状态
+ 单个文件独立维护状态
+ 上传逻辑抽象为可替换函数

#### AutoComplete 的核心难点
1. 输入与下拉状态同步
2. 防抖 + 请求竞态
3. 键盘可访问性

#### 解决方案
+ 使用 useDebounce
+ 请求添加序列号 / AbortController 防止脏数据
+ 明确 focus / blur 行为边界

### 如何在 Storybook 中实现组件的交互演示和属性说明？有没有做二次封装或自定义插件？
这种库你弄明白为什么用比背 api 有用多了，api 稍微记几个让面试官感觉你是真自己做过就行

#### 基础能力使用
+ args / argTypes 描述 props
+ Controls 实现属性实时调节
+ Docs 自动生成 API 表

#### 二次增强点
1. **自定义 Preview 插件**
    - 实时展示源码
    - highlight.js 高亮
2. **交互 Story**
    - 模拟真实业务状态
    - 多状态 Story 拆分
3. **统一文档规范**
    - 组件介绍
    - 使用场景
    - 注意事项

#### 潜在问题
+ Storybook 与真实项目存在差异
+ 控制文档复杂度，避免过度工程化

### Preview 插件的设计原理是什么？它是怎么做到实时预览和代码高亮的？
### highlight.js 是怎么集成到文档展示中的？你有没有对高亮主题或样式做过定制？
### ESLint、Prettier、Husky、lint-staged 是如何集成在 CI 流程中的？这些工具分别解决了哪些问题？
### Jest 单元测试中是如何设计用例的？主要测试哪些场景？有没有遇到过模拟异步交互的问题？
### 组件的 props 类型定义是如何做的？有没有用到泛型或联合类型？
### 如何保证组件在多种场景下的可复用性和扩展性？有没有做 slots、render props 或 context 的封装？
### 组件的样式是怎么写的？用了哪种 CSS 方案（如 CSS Modules、Tailwind、cssinjs）？为什么选它？
### 你如何在 Storybook 中同步组件的更新（热更新）？有没有解决过 story 内容不同步或渲染异常的问题？
### 组件库是否做了版本管理和发布？是怎么发布到 npm 的？如何处理依赖更新问题？
### 你有没有设计“主题化”或“国际化”功能？如果需要支持换肤或多语言，该怎么扩展组件架构？
### 项目开发过程中，有没有团队协作？你是如何制定组件规范和开发流程的？
### 你怎么看目前市面上的开源组件库（如 Ant Design、MUI），你们组件库的定位和目标是什么？
### 使用 pnpm workspace 时，是否遇到过依赖冲突或包引用异常？是怎么处理的？
### 你是否做过组件性能优化，比如渲染优化、虚拟滚动、懒加载等？
### 你会如何衡量一个组件是否“设计得好”？有哪些判断标准或经验？
