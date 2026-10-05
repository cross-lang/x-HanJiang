# 汉江开放平台门户（HanJiang Open Portal）

汉江开放平台门户是 [汉江（HanJiang）全栈快速开发平台](https://github.com/cross-lang/x-HanJiang) 的开发者门户前端，基于 Vue 3 + TypeScript + Vite + Element Plus 构建，面向外部开发者提供应用接入、能力文档与认证指引的一站式开放平台入口，配套 FastAPI 后端使用。

[English](README.en.md) | 中文

## ✨ 功能特性

- **开发者账号**：注册 / 登录（有状态会话：JWT + Redis 登录态，登出 / 改密 / 刷新令牌后旧令牌立即失效）、资料维护、个人 / 企业认证申请
- **应用管理**：创建应用（AppId 生成 + AppKey 仅此一次返回）、编辑 / 删除（软删）、scope 申请与调整、AppKey 轮换、审批状态与意见跟踪（未通过的应用无法调用开放接口）
- **开放能力文档**：内置 18 个开放接口的能力目录（健康管理 / 应用信息 / 用户管理 / 角色管理 / 文件管理），逐接口展示请求头、Query / Body 参数、响应字段与示例、cURL 调用示例（HanJiang-1 HMAC 签名模式）
- **认证与授权文档**：HanJiang-1 签名说明（签名算法 / 防重放时间窗）、通用请求参数、网关鉴权错误码
- **站内信**：右上角铃铛未读数角标（15s 轮询）、消息列表、单条已读 / 全部已读
- **个人中心**：开发者资料、认证状态、修改密码
- **代码高亮**：接口文档代码块基于 highlight.js 渲染

## 🛠️ 技术栈

| 分类            | 技术                                        |
| --------------- | ------------------------------------------- |
| **框架**        | Vue 3.5（Composition API）                  |
| **语言**        | TypeScript 5.7                              |
| **构建工具**    | Vite 6                                      |
| **UI 组件库**   | Element Plus 2.9 + @element-plus/icons-vue  |
| **状态管理**    | Pinia（开发者会话状态）                     |
| **路由**        | Vue Router 4（含登录守卫）                  |
| **HTTP 客户端** | Axios 1.7（统一封装）                       |
| **代码高亮**    | highlight.js 11                             |

## 🚀 快速开始

### ⚙️ 环境要求

| 工具    | 版本要求 |
| ------- | -------- |
| Node.js | >= 18    |
| npm     | >= 9     |

### 📦 安装依赖

```bash
npm install
```

### 💻 开发启动

```bash
npm run dev
```

访问 http://localhost:5174。Vite 会将 `/api/`、`/docs`、`/redoc`、`/openapi.json` 请求代理到后端 `http://127.0.0.1:8000`，开发时无需处理跨域。

> 注意：门户开发端口为 **5174**（与管理系统前端 5173 区分）；Vite 仅代理 `/api/` 前缀，避免吞掉以 `/api` 开头的前端路由（如 `/api-docs`）。

### 🏭 生产构建

```bash
npm run build
```

构建过程包含 `vue-tsc` 类型检查 + Vite 打包，产物输出到 `dist/` 目录，可部署至 Nginx 等静态服务器（需将 `/api` 反向代理到后端）。

### 🖥️ 本地预览

```bash
npm run preview
```

## 📁 项目结构

```
open_portal/
├── src/
│   ├── api/                # API 请求封装
│   │   ├── request.ts      # Axios 实例（拦截器、统一错误处理，baseURL /api/open-portal/v1）
│   │   ├── auth.ts         # 注册 / 登录 / 刷新 / 登出 / 改密
│   │   ├── developer.ts    # 开发者资料与认证
│   │   ├── apps.ts         # 应用 CRUD / scope 申请 / 密钥轮换
│   │   ├── scopes.ts       # scope 目录
│   │   └── messages.ts     # 站内信（未读数 / 列表 / 已读）
│   ├── components/         # 通用组件
│   │   ├── GroupCheckboxPanel.vue # scope 分组勾选面板
│   │   ├── NotificationBell.vue   # 顶栏通知铃铛（未读数角标）
│   │   └── SecretResultDialog.vue # AppKey 一次性展示弹窗
│   ├── composables/
│   │   └── useScopeCatalog.ts     # scope 目录数据
│   ├── data/
│   │   └── capability.ts   # 开放能力接口目录（18 个开放接口，与 /api/open/v1 一一对应）
│   ├── router/
│   │   └── index.ts        # 路由配置 + 登录守卫
│   ├── stores/
│   │   └── developer.ts    # 开发者会话状态（Pinia）
│   ├── types/              # TypeScript 类型定义
│   ├── views/              # 页面组件
│   │   ├── home/           # 首页（开放能力模块总览）
│   │   ├── apps/           # 应用管理（CRUD / scope 申请 / 审批状态）
│   │   ├── capability/     # 开放能力接口详情（三级菜单：模块 → 接口）
│   │   ├── auth/           # 认证与授权文档（签名说明 / 通用参数 / 错误码）
│   │   ├── login/ register/ # 登录与注册
│   │   └── profile/        # 个人中心
│   ├── App.vue             # 根组件
│   └── main.ts             # 入口
├── index.html
├── vite.config.ts          # Vite 配置（别名 @、端口 5174、后端代理）
├── package.json
├── tsconfig.json           # TypeScript 配置
└── tsconfig.node.json
```

## 🧭 页面与路由

| 路由                             | 页面             | 说明                                                          |
| -------------------------------- | ---------------- | ------------------------------------------------------------- |
| `/login`                         | 登录页           | 开发者登录                                                    |
| `/register`                      | 注册页           | 注册开发者账号                                                |
| `/home`                          | 首页             | 开放能力模块总览 + 我的应用概览                               |
| `/apps`                          | 应用管理         | 应用 CRUD + scope 申请 + AppKey 轮换 + 审批状态               |
| `/capability/:module/:apiId`     | 开放能力         | 接口级文档（请求头 / 参数 / 响应 / cURL 示例）                |
| `/auth/signature`                | 签名说明         | HanJiang-1 签名算法与防重放说明                               |
| `/auth/params`                   | 通用参数         | 公共请求头与响应结构                                          |
| `/auth/errors`                   | 网关错误码       | 开放接口鉴权错误码说明                                        |
| `/profile`                       | 个人中心         | 资料维护 / 认证申请 / 修改密码                                |

## 🔗 接口调用约定

门户前端涉及两类接口，前缀与鉴权方式严格隔离：

| 类型       | 前缀                   | 鉴权方式                                             |
| ---------- | ---------------------- | ---------------------------------------------------- |
| 门户接口   | `/api/open-portal/v1`  | 开发者会话 JWT（`Authorization: Bearer <access_token>`，存于 localStorage） |
| 开放接口   | `/api/open/v1`         | `X-App-Id` / `X-App-Key` + HanJiang-1 HMAC 签名      |

- 统一响应包裹：`{ code, message, data, timestamp, request_id }`
- 分页结构：`data: { items, total, page, page_size, total_pages }`
- 应用创建后进入管理端审批流（`approval_status = pending`），审批通过后方可调用开放接口
- 应用与 scope 申请、审批结果通过开发者站内信（`developer_messages` 表）通知

> 后端接口依赖全量清单见 [API_DEPENDENCIES.md](./API_DEPENDENCIES.md)。

## 🤝 联调说明

- 开发前需先启动后端服务（参考 [server/README.md](../../server/README.md)），默认端口 `8000`
- 门户使用独立的开发者账号体系，与管理系统用户体系隔离（开发者表 + 开发者会话登录态）
- 生产构建后，`dist/` 为纯静态产物，需在 Web 服务器（如 Nginx）中将 `/api` 等前缀反向代理到后端服务
