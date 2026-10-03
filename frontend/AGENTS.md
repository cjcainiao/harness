# 前端开发规则

## 常用命令
- 开发：`npm run dev`（Vite，默认 5173）
- 构建：`npm run build`，类型检查：`npm run type-check`（vue-tsc）
- 格式化：`npm run format`（prettier：无分号、单引号、行宽 100）

## 目录结构
- 页面按模块放 `src/views/<模块>/`，模块内自包含：
  - `LayoutView.vue` 布局壳，`pages/` 放模块子页面，`components/` 放模块级组件
  - `components/` 内按页面区块分子文件夹（如 `sidebar/`、`message/`、`input/`）
  - 布局壳只保留分区骨架和 `router-view`，成块的内容一律封装成 `components/` 组件
  - 跨模块通用的组件才进顶层 `src/components/`
- 通用工具放 `src/utils/`，命名 `xxxUtil.ts`（如 `sseUtil.ts`）
- 接口请求按页面模块放 `src/api/<模块>.ts`（如 `api/chat.ts`）
- 全局初始化样式放 `src/assets/css/init.css`（main.ts 引入），组件内不写全局样式
- 全局状态用 Pinia，放 `src/stores/`
- 引用统一用 `@` 别名（指向 `src/`）

## 与后端对接
- 前端请求路径统一带 `/api` 前缀
- 开发模式走 Vite 代理（`vite.config.ts` 的 `server.proxy`）：`/api` 原样转发到 `http://127.0.0.1:8000`，不剥前缀（后端路由本身就挂在 `/api` 下）
- `requestUtil`/`sseUtil` 的 baseURL 默认空串，即同源相对路径 `/api`：开发由 Vite 代理转发，部署由站点反代透传 `/api`（反代同样不能剥前缀，SSE 要关响应缓冲）
- 只有跨源直连才配 `VITE_API_BASE_URL=http://<后端地址>`，此时依赖后端 `system.allow_origins` 白名单
- 环境变量不区分环境文件：真实配置在 `.env`，格式示例在 `.env.example`；Vite 不读 example，改它不生效
- 普通请求走 `utils/requestUtil`，响应结构对应后端 `Result`：`{ code, message, data }`，业务码 200 才算成功
- 流式对话走 `utils/sseUtil`，不经过 axios 封装
- 接口路径以后端 `app/gateway/` 实际路由为准

## 长列表翻页
- 一次固定条数，游标取本页最早那条服务端返回的原始值（时间串或序号），不用本地时间戳反推
- 触发不能只挂 `@scroll`：内容不足一屏没有滚动条时也要补页，按 `scrollHeight - scrollTop - clientHeight` 判底，列表长度变化和窗口 resize 都重新判断
- 自动补页要有停止条件：不再触底、已到底、或一页没拿到新数据
- 顶部 prepend 更早内容后手动补 `scrollTop` 增量，滚动容器加 `overflow-anchor: none`
- 还原历史后停在最新一条，否则既看不到结尾也滑不出更早分页
- 翻页状态提示复用同一句式：加载中… / 没有更早的…

## 浮层与提示
- `ElMessage` 一律传对象并带 `plain: true`，不用 `ElMessage.warning('文案')` 简写：只有对象形式能带选项
- `plain` 是白底加投影，不带才是主题色浅底加彩边，两者别搞反
- 点开就会拉起系统对话框、焦点留在按钮上的触发器，`ElTooltip` 不声明 `focus` 触发，只留默认的悬停：否则对话框一关气泡自己弹出来
- 弹层里的滚动内容：用户自己往上翻了就不再打扰，别每帧把他拉回去

## 流式展开区滚动
- 思考正文和工具参数区在流式追加时跟到最新一行，这一段结束后回到顶部
- 判"是否贴在底部"必须在默认 pre-flush 的 watcher 里读 `scrollHeight`/`scrollTop`/`clientHeight`，`flush: 'post'` 读到的是新内容上屏后的高度，永远判不出贴底；写 `scrollTop` 放到 `nextTick` 里
- `v-for` 内的滚动元素用函数 ref 按条目 id 登记，`ref="xxx"` 在 `v-for` 里只是字符串 ref，拿不到每条的元素
- 只在会增量增长的字段上挂 watcher，一次性写入的 output 不用跟

## 附件上传闸门
- 入口只有 `ChatInput.vue` 的 `addFiles`，三条闸门按序：类型白名单 → 当前模型 `supports_vision` 拦图片 → 按 `fileKey`（`name:size:lastModified`）去重
- 不合格的只出提示、不进附件条；视觉拦截的文案不带文件名
- 白名单写死在 `utils/fileUploadUtil.ts`，接后端配置时替换这一处
- 附件条 `v-for` 的 `:key` 就是 `fileKey`，要放开重复必须同时换成每项自增 uid，否则 Vue 撞 key、移除会删错条
- 隐藏的 `<input type="file">` 每次选完要 `input.value = ''`，否则同一个文件再选不触发 `change`

## 触屏适配
- `:hover` 样式一律包在 `@media (hover: hover)` 里，否则手机点完会残留悬停态
- 命中区只在 `@media (any-pointer: coarse)` 里放大（图标按钮 40×40、行内触发器 `min-height: 36px`），鼠标侧尺寸不动
- 小控件加 `touch-action: manipulation` 去掉 300ms 双击缩放延迟，加 `-webkit-tap-highlight-color: transparent` 去掉点击灰块
- 悬停气泡在触屏上按 `window.matchMedia('(hover: hover)')` 关掉：`ElTooltip` 传 `:disabled="!canHover"`
- 触屏分支用 `event.pointerType !== 'mouse'` 判断，不用 `ontouchstart` 探测

## 浏览器 API 兜底
- 唯一标识只走 `utils/uuidUtil` 的 `createUuid()`，不许直接 `crypto.randomUUID()`：HTTP 部署下它是 undefined，写在 setup 里就是整页白屏
- 复制只走 `utils/clipboardUtil` 的 `copyToClipboard()`，不许直接 `navigator.clipboard`：同样是非安全上下文没有，且它失败要退回 `execCommand`
- 复制没成功就不翻成"已复制"状态，图标本身就是反馈，不加提示条
- 用到 `crypto.subtle`、Service Worker、`SharedArrayBuffer` 这类安全上下文专属 API 前先确认部署协议

## 组件写法
- 每个 SFC 在 `<template>` 上方紧贴一行注释写明这个组件是干什么的，如 `<!--审批组件-->`，中间不空行
- 注释只写用途名词短语，不写实现方式、不写作者和日期
- 一律 `<script setup lang="ts">` 三段式 SFC，`<style scoped>`
- 页面组件命名 `XxxView.vue`（PascalCase），普通组件 PascalCase

## 路由规范
- 每个页面模块一个路由文件：`src/router/modules/<模块>.ts`，导出 `XxxRoutes: RouteRecordRaw[]`
- 顶层路径指向模块 `LayoutView.vue`，子页面挂在 `children` 里，index 子路由 `path: ''`
- `src/router/routes.ts` 只做汇总：`import` 各模块后展开合并
- `src/router/index.ts` 用 `routes` 调 `createRouter`，不放具体路由

## 代码风格
- 注释用中文短语标签，一行以内，如 `// 注册ElementPlus`
- 导出的工具类/接口可写 `/** */` 块注释说明用途
- 类型来自 `interface`/`type`，接口返回数据必须定义类型，不滥用 `any`
