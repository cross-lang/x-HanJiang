# 汉江管理后台（HanJiang Admin）

汉江管理后台是 [汉江（HanJiang）全栈快速开发平台](https://github.com/cross-lang/x-HanJiang) 的前端项目，基于 Vue 3 + TypeScript + Vite + Element Plus 构建，配套 FastAPI 后端使用，提供企业级管理系统开箱即用的管理界面。

## 功能特性

- **登录与安全**：用户名 / 密码登录，JWT 令牌自动携带，401 自动跳转登录页
- **仪表盘**：统计卡片 + ECharts 图表 + 最近记录 + 我的最近活动
- **用户管理**：用户列表（分页 / 关键字 / 状态过滤）、多角色分配、编辑 / 禁用 / 重置密码、CSV 导入导出
- **角色管理**：角色 CRUD、权限分组勾选、绑定 / 解绑权限
- **权限管理**：权限列表（后端自动扫描注册）与权限元数据
- **审计与日志**：业务审计日志、登录日志（含详情与导出）
- **文件管理**：上传、列表、下载、删除
- **通知中心**：通知记录列表 / 统计、站内信未读数与已读、通知偏好与接收人管理
- **系统通知配置**：渠道配置查看 / 更新（热生效）、渠道测试、系统监控状态
- **开放平台**：应用 CRUD、scope 授权、AppKey 轮换、scope 列表
- **个人中心**：资料维护、修改密码（邮箱验证码二次认证）、修改手机号 / 邮箱
- **全局搜索**：跨用户 / 角色 / 权限 / 应用 / 文件关键字搜索（顶栏搜索框）
- **API 文档**：内嵌 Swagger UI，浏览器内直接调试接口

## 技术栈

| 分类 | 技术 |
|---|---|
| **框架** | Vue 3.5（Composition API） |
| **语言** | TypeScript 5.7 |
| **构建工具** | Vite 6 |
| **UI 组件库** | Element Plus 2.9 + @element-plus/icons-vue |
| **状态管理** | Pinia |
| **路由** | Vue Router 4（含登录守卫） |
| **HTTP 客户端** | Axios 1.7（统一封装） |
| **图表** | ECharts 6 + vue-echarts |

## 快速开始

### 环境要求

| 工具 | 版本要求 |
|---|---|
| Node.js | >= 18 |
| npm | >= 9 |

### 安装依赖

```bash
npm install
```

### 开发启动

```bash
npm run dev
```

访问 http://localhost:5173。Vite 会自动将 `/api`、`/docs`、`/redoc`、`/openapi.json` 请求代理到后端 `http://127.0.0.1:8000`，开发时无需处理跨域。

### 生产构建

```bash
npm run build
```

构建过程包含 `vue-tsc` 类型检查 + Vite 打包，产物输出到 `dist/` 目录，可部署至 Nginx 等静态服务器（需将 `/api` 反向代理到后端）。

### 本地预览

```bash
npm run preview
```

## 项目结构

```
admin/
├── src/
│   ├── api/                # API 请求封装
│   │   ├── request.ts      # Axios 实例（拦截器、统一错误处理）
│   │   └── auth.ts         # 认证相关接口（登录 / 当前用户 / 菜单 / 登出）
│   ├── assets/             # 静态资源
│   ├── components/         # 通用组件
│   │   ├── GlobalSearch.vue     # 顶栏全局搜索
│   │   └── NotificationBell.vue # 顶栏通知铃铛（站内信未读数）
│   ├── router/
│   │   └── index.ts        # 路由配置 + 登录守卫
│   ├── stores/
│   │   └── user.ts         # 用户状态（Pinia）
│   ├── utils/
│   │   └── format.ts       # 格式化工具（日期等）
│   ├── views/              # 页面组件
│   ├── App.vue             # 根组件
│   └── main.ts             # 入口（Element Plus 中文语言包、全局图标注册）
├── index.html
├── vite.config.ts          # Vite 配置（别名 @、端口 5173、后端代理）
├── package.json
├── tsconfig.json           # TypeScript 配置
└── tsconfig.node.json
```

## 页面与路由

| 路由 | 页面 | 说明 |
|---|---|---|
| `/login` | 登录页 | 用户名密码登录 |
| `/` | 布局页 | 侧边栏 + 顶栏（含全局搜索、通知铃铛） |
| `/dashboard` | 首页 | 欢迎信息 + 快捷入口 |
| `/panel` | 仪表盘 | 统计卡片 + ECharts 图表 + 最近记录 |
| `/users` | 用户管理 | 用户列表 + 多角色 + 编辑 / 禁用 / 重置密码 + 导入导出 |
| `/roles` | 角色管理 | 角色列表 + 权限分组勾选 + 编辑 / 删除 / 启停 |
| `/permissions` | 权限管理 | 权限列表（后端自动扫描注册）+ 权限元数据 |
| `/apis/swagger` | Swagger 文档 | 内嵌 Swagger UI，在线调试接口 |
| `/audit` | 审计日志 | 业务操作日志列表（含导出） |
| `/audit/login` | 登录日志 | 登录日志列表（含导出） |
| `/apps` | 开放应用管理 | 开放平台应用 CRUD + scope 授权 + AppKey 轮换 |
| `/app-scopes` | 应用 scope | 开放平台 scope 列表 |
| `/system-notification` | 系统通知配置 | 渠道配置 / 渠道测试 / 监控状态 |
| `/profile` | 个人中心 | 个人信息 + 改密（邮箱验证码）+ 通知偏好 / 接收人 |
| `/files` | 文件管理 | 上传 / 列表 / 下载 / 删除 |

## 请求封装约定

- `src/api/request.ts` 创建 Axios 实例，`baseURL` 为 `/api/v1`
- **请求拦截器**：自动从 `localStorage` 读取 `access_token` 并注入 `Authorization: Bearer <token>`
- **响应拦截器**：直接返回 `response.data`；401 时清除令牌并跳转登录页；其他错误统一弹出 `ElMessage` 提示
- 业务页面统一通过 `request` 调用接口，路径与后端 `/api/v1` 前缀下的路由对应（如 `/users`、`/profile/me`）

## 后端代理

`vite.config.ts` 中配置了以下代理（开发环境）：

| 前缀 | 目标 |
|---|---|
| `/api` | http://127.0.0.1:8000 |
| `/docs` | http://127.0.0.1:8000 |
| `/redoc` | http://127.0.0.1:8000 |
| `/openapi.json` | http://127.0.0.1:8000 |

## 联调说明

- 开发前需先启动后端服务（参考 [server/README.md](../../server/README.md)），默认端口 `8000`
- 默认超级管理员账号：`superadmin` / `admin@123456`，生产环境请务必修改
- 生产构建后，`dist/` 为纯静态产物，需在 Web 服务器（如 Nginx）中将 `/api` 等前缀反向代理到后端服务
