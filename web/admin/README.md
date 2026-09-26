# 汉江管理后台（HanJiang Admin）

基于 Vue 3 + TypeScript + Vite + Element Plus 的管理后台前端。

## 技术栈

- **框架**：Vue 3（Composition API）
- **语言**：TypeScript
- **构建**：Vite 6
- **UI 组件库**：Element Plus
- **状态管理**：Pinia
- **路由**：Vue Router 4
- **HTTP 客户端**：Axios
- **图表**：ECharts + vue-echarts

## 快速开始

### 环境要求

- Node.js >= 18
- npm >= 9

### 安装依赖

```bash
npm install
```

### 开发启动

```bash
npm run dev
```

访问 http://localhost:5173，Vite 会自动代理 `/api`、`/docs`、`/redoc`、`/openapi.json` 请求到后端 `http://127.0.0.1:8000`。

### 生产构建

```bash
npm run build
```

构建产物在 `dist/` 目录，可部署到 Nginx 或其他静态文件服务器。

## 目录结构

```
admin/
├── src/
│   ├── api/          # API 请求封装
│   ├── assets/       # 静态资源（logo 等）
│   ├── router/       # 路由配置
│   ├── stores/       # Pinia 状态管理
│   ├── views/        # 页面组件
│   ├── App.vue       # 根组件
│   └── main.ts       # 入口文件
├── index.html
├── vite.config.ts    # Vite 配置（含代理）
└── package.json
```

## 页面

| 路由 | 页面 | 说明 |
|---|---|---|
| `/login` | 登录页 | 用户名密码登录 |
| `/` | 布局页 | 侧边栏 + 顶栏 |
| `/dashboard` | 首页 | 欢迎信息 + 快捷入口 |
| `/panel` | 仪表盘 | 统计卡片 + ECharts 图表 + 最近记录 |
| `/users` | 用户管理 | 用户列表 + 多角色选择 + 编辑/禁用/重置密码 |
| `/roles` | 角色管理 | 角色列表 + 权限分组勾选 + 编辑/删除/启停 |
| `/permissions` | 权限管理 | 权限列表（自动从路由扫描注册） |
| `/audit` | 审计日志 | 业务操作日志列表 |
| `/audit/login` | 登录日志 | 登录日志列表 |
| `/apps` | 开放应用管理 | 开放平台应用 CRUD + scope 权限勾选 |
| `/profile` | 个人中心 | 个人信息修改 + 修改密码 |
| `/api-docs` | Swagger 文档 | 内嵌 Swagger UI |

## 后端代理

`vite.config.ts` 中配置了以下代理：

| 前缀 | 目标 |
|---|---|
| `/api` | http://127.0.0.1:8000 |
| `/docs` | http://127.0.0.1:8000 |
| `/redoc` | http://127.0.0.1:8000 |
| `/openapi.json` | http://127.0.0.1:8000 |
