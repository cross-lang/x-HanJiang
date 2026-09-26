# 汉江（HanJiang）管理后台（HanJiang Admin）

基于 Vue 3 + TypeScript + Vite + Element Plus 的管理后台前端。

## 技术栈

- **框架**：Vue 3（Composition API）
- **语言**：TypeScript
- **构建**：Vite 6
- **UI 组件库**：Element Plus
- **状态管理**：Pinia
- **路由**：Vue Router 4
- **HTTP 客户端**：Axios

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

访问 http://localhost:5173，Vite 会自动代理 `/api` 请求到后端 `http://127.0.0.1:8000`。

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
| `/dashboard` | 首页 | 系统概览 |
| `/users` | 用户管理 | 用户列表 + 新建用户 |
