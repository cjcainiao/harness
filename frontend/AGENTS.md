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
- 开发模式走 Vite 代理（`vite.config.ts` 的 `server.proxy`）：去掉 `/api` 前缀后转发到 `http://127.0.0.1:8000`
- `requestUtil`/`sseUtil` 的 baseURL 由 `VITE_API_BASE_URL` 控制：留空走同源相对路径（配合代理），配置为后端地址则直连（依赖 CORS）
- 环境变量不区分环境文件：真实配置在 `.env`，格式示例在 `.env.example`
- 普通请求走 `utils/requestUtil`，响应结构对应后端 `Result`：`{ code, message, data }`，业务码 200 才算成功
- 流式对话走 `utils/sseUtil`，不经过 axios 封装
- 接口路径以后端 `app/gateway/` 实际路由为准

## 组件写法
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
