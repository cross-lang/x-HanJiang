<div align="center">

<img src="me/logo-icon-little.png" alt="HanJiang" width="250"/>

# 汉江（HanJiang）— 全栈快速开发平台

基于 **FastAPI + Vue 3** 的**开箱即用**的全栈开发平台，五分钟搭建企业级中后台，省时又省事。

**一套代码库，覆盖「管理系统 / 开放 API / 开放平台门户」三类场景。**

[English](README.en.md) | 中文

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python\&logoColor=white)
![FastAPI 0.115+](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi\&logoColor=white)
![Vue 3](https://img.shields.io/badge/Vue%203-4FC08D?logo=vuedotjs\&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript\&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?logo=mysql\&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis\&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker\&logoColor=white)

![GitHub Stars](https://img.shields.io/github/stars/cross-lang/x-HanJiang?style=flat\&logo=github\&logoColor=white\&label=Stars)
![GitHub Forks](https://img.shields.io/github/forks/cross-lang/x-HanJiang?style=flat\&logo=github\&logoColor=white\&label=Forks)
![License](https://img.shields.io/github/license/cross-lang/x-HanJiang?style=flat\&label=License)
![Commits](https://img.shields.io/github/commit-activity/m/cross-lang/x-HanJiang?style=flat\&logo=github\&logoColor=white\&label=Commits)

</div>

## 💡 项目介绍

汉江（HanJiang）是一个开箱即用的企业级全栈快速开发平台：后端基于 FastAPI 深度封装（三层架构 + 依赖注入），前端提供两套 Vue 3 管理界面，单机 Docker Compose 一键部署（nginx 统一入口）。三端一体覆盖企业内部管理、对外 API 开放、开发者门户三类场景。

| 你需要的                   | HanJiang | 裸 FastAPI 自研 | 通用前后端模板 |
| ---------------------- | -------- | ------------ | ------- |
| 开箱即用的后台系统              | ✅        | ⚠️ 需自研       | ❌ 只有 UI |
| FastAPI 异步高性能后端        | ✅        | ✅ 但需自建       | ❌ 无后端   |
| RBAC 菜单/按钮权限 + 启动自动注册  | ✅        | ⚠️ 需自研       | ❌       |
| AI 助手（SSE 流式对话 / 工具编排） | ✅        | ❌            | ❌       |
| 开放平台签名鉴权（HMAC / 防重放）   | ✅        | ❌            | ❌       |
| 多渠道通知（站内信/邮件/钉钉/飞书）    | ✅        | ❌            | ❌       |
| 审计日志 + 登录日志            | ✅        | ❌            | ❌       |
| Docker 一键部署            | ✅        | ⚠️           | ⚠️      |

### ✨ 核心能力

- **管理系统（web/admin + `/api/admin/v1`）**：JWT 认证 + RBAC 权限模型，`@permission` 装饰器声明式注册，启动时自动扫描同步到数据库；内置用户 / 角色 / 权限、审计与登录日志、文件、公告、系统通知广播、全局搜索、仪表盘、AI 助手等企业级中后台能力
- **开放 API（`/api/open/v1`）**：面向外部应用的网关接口，HanJiang-1 HMAC 签名鉴权（明文/签名双模式）、AppId/AppKey 生命周期管理、scope 授权与密钥轮换、应用审批流、防重放
- **开放平台门户（web/open_portal + `/api/open-portal/v1`）**：面向开发者的独立门户，支持开发者注册 / 登录（有状态会话）、应用申请与审批跟踪、scope 申请、开放能力文档（18 个接口的请求 / 响应 / 签名示例）、站内信与个人中心
- **AI 助手**：SSE 流式对话（token / navigate / done 事件）、会话管理、四层记忆体系（系统提示词 / 长期记忆 / 滚动摘要 / 最近原文）、内置页面跳转与只读查询工具，`openai_compat` 协议可对接 DeepSeek / 火山方舟 / 通义 / vLLM 等
- **通知系统**：事件驱动多渠道分发（站内信/邮件/钉钉/飞书），模板变量插值、用户级偏好、失败自动重试
- **可观测性**：业务审计日志、登录日志、操作日志趋势、系统告警
- **工程化**：分层架构（API → Service → Repository）、统一异常处理、Swagger 文档、Alembic 迁移、GitHub Actions CI

## 🍪 在线体验

| 端 | 地址 | 账号 |
|----|------|------|
| 🌐 开放平台 | `http://121.40.147.234/open-portal/` | `yeyushilai` / `admin@123456` |
| 💻 管理系统 | `http://121.40.147.234/admin/` | `superadmin` / `admin@123456` |

## 📸 界面预览

### 管理系统

![登录页](./me/admin_login.png)
![首页](./me/admin_dashboard.png)
![系统管理](./me/admin_system.png)
![AI助手](./me/admin_assistant.png)
![开放应用](./me/admin_openapp.png)

### 开放平台

![登录页](./me/open_portal_login.png)
![首页](./me/open_portal_dashboard.png)
![应用管理](./me/open_portal_app.png)
![开放能力](./me/open_portal_openapi.png)
![认证和授权](./me/open_portal_auth.png)
![个人中心](./me/open_portal_profile.png)

## 🚀 快速开始

### 🖥️ 后端

```bash
cd server
uv run x-HanJiang --reload
```

配置说明见 [server/README.md](server/README.md)。

### 🌐 管理系统前端（web/admin）

```bash
cd web/admin
npm install
npm run dev
```

访问 <http://localhost:5173>，详见 [web/admin/README.md](web/admin/README.md)。

### 🌐 开放平台前端（web/open\_portal）

```bash
cd web/open_portal
npm install
npm run dev
```

访问 <http://localhost:5174>，详见 [web/open\_portal/README.md](web/open_portal/README.md)。

## 📁 项目结构

```
x-HanJiang/
├── server/                     # 后端（FastAPI，三套 API 体系）
│   ├── src/
│   │   ├── api/                # API 路由层
│   │   │   ├── admin/          #   管理系统接口（/api/admin/v1，JWT + RBAC）
│   │   │   ├── open/           #   开放 API 接口（/api/open/v1，AppId/AppKey + HMAC 签名 + scope）
│   │   │   └── open_portal/    #   开放平台接口（/api/open-portal/v1，开发者会话 JWT）
│   │   ├── assistant/          # AI 助手（agent 循环 / 记忆 memories/ / 工具 tools/ / 协议防御）
│   │   ├── core/               # 核心支撑（配置 / 中间件 / 异常 / 安全 / 种子数据）
│   │   ├── infras/             # 基础设施（数据库 / 缓存 / 存储 / 通知渠道 / LLM）
│   │   ├── models/             # SQLAlchemy ORM 实体
│   │   ├── notification/       # 通知子系统（分发器 / 模板 / 重试）
│   │   ├── repositories/       # 数据访问层
│   │   ├── schemas/            # Pydantic 请求 / 响应 DTO
│   │   ├── services/           # 业务逻辑层
│   │   ├── templates/          # 提示词模板（AI 助手）
│   │   └── main.py             # 应用入口
│   ├── alembic/                # 数据库迁移（0001~0033）
│   ├── tests/                  # 单元测试（目录结构与 src/ 镜像）
│   └── pyproject.toml          # 依赖声明（uv 管理锁文件）
├── web/
│   ├── Dockerfile              # 前端多阶段构建（npm build → Nginx 托管）
│   ├── nginx.conf              # 生产环境统一入口路由（/ 管理端、/portal/ 门户、/api/ 反代）
│   ├── admin/                  # 管理系统前端（Vue3 + TS + Element Plus，开发端口 5173）
│   └── open_portal/            # 开放平台门户前端（Vue3 + TS + Element Plus，开发端口 5174）
├── docs/                       # 部署文档（阿里云 ECS / 轻量服务器中英双语指南）
├── me/                         # 品牌素材与界面截图
├── docker-compose.yml          # 单机编排：nginx（80 统一入口）+ app + mysql + redis
└── LICENSE                     # MIT 协议
```

## 🏗️ 系统架构

### 🏗️ 系统分层架构

```mermaid
flowchart TB
  U[浏览器 / 外部应用] -->|HTTP :80| NG[nginx 统一入口<br/>/ 管理系统 · /portal/ 开放平台 · /api/ 反向代理]

  subgraph Backend[FastAPI 后端（app 容器）]
    NG -->|"/api/admin/v1"| A1["管理系统 API<br/>JWT + RBAC 权限"]
    NG -->|"/api/open/v1"| A2["开放 API 网关<br/>AppId/AppKey + HMAC 签名 + scope"]
    NG -->|"/api/open-portal/v1"| A3["门户 API<br/>开发者会话 JWT"]
    A1 --> SVC[业务服务层<br/>用户 · 角色 · 审计 · 通知 · 公告 · 文件 · AI]
    A2 --> SVC
    A3 --> SVC
    SVC --> REPO[数据访问层<br/>Repository 模式]
  end

  REPO --> DB[(MySQL)]
  SVC --> RD[(Redis<br/>登录态 · 限流 · 重试队列)]
  SVC --> ST[对象存储<br/>本地 / S3 兼容]
  SVC --> LLM[大模型 API<br/>openai_compat 协议]
```

### 🔄 一次请求的旅程（Docker 单机部署）

```mermaid
flowchart LR
  C[浏览器] -->|"http://IP:80"| N[nginx 容器<br/>静态托管 + 反代]
  N -->|"静态请求"| DISK[["/ 管理系统 SPA<br/>/portal/ 门户 SPA"]]
  N -->|"/api/ 注入 X-Real-IP"| A[app 容器<br/>gunicorn + uvicorn workers]
  A --> M[(mysql 容器)]
  A --> R[(redis 容器)]
  A -->|"SSE 流式"| LLM[外部大模型 API]
```

### 🧩 关键技术组件说明

| 组件 | 位置 | 职责 |
|------|------|------|
| 管理系统前端 | `web/admin` | 企业级中后台界面（用户/角色/权限/审计/通知/公告/AI 助手等 17 个路由页） |
| 开放平台门户前端 | `web/open_portal` | 开发者自助门户（注册登录 / 应用管理 / 开放能力文档 / 站内信） |
| 后端服务 | `server` | 三套 API 体系 + 业务编排，详见 [server/README.md](server/README.md) |
| 统一入口 | `web/nginx.conf` | 生产环境静态托管 + `/api/` 反代 + SSE 透传 + X-Real-IP 注入 |
| 容器编排 | `docker-compose.yml` | nginx / app / mysql / redis 四服务单机编排，健康检查 + 数据卷持久化 |

## 🛠️ 技术栈

| 分类 | 技术                                                         |
| -- | ---------------------------------------------------------- |
| 后端 | Python 3.11+ / FastAPI / SQLAlchemy 2.0 / Alembic          |
| 前端 | Vue 3 + TypeScript / Vite / Element Plus / Pinia / ECharts |
| 存储 | MySQL / Redis                                              |
| 认证 | JWT（用户态/开发者态）+ HMAC 签名（开放接口）                               |
| AI | OpenAI SDK（openai\_compat 协议）                              |
| 工程 | uv / Ruff / mypy / pytest / ESLint / Prettier / Loguru     |
| 部署 | Docker / docker-compose / Nginx                            |

## 🔌 API 文档说明

后端启动后访问（Docker 部署时将 `localhost:8000` 替换为部署地址即可，nginx 已代理 `/docs`）：

- **Swagger UI**：<http://localhost:8000/docs>
- **ReDoc**：<http://localhost:8000/redoc>
- **OpenAPI JSON**：<http://localhost:8000/openapi.json>

三套 API 体系与核心接口清单（100+ 接口）详见 [server/README.md](server/README.md#-api-文档说明)。

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

## 📚 参考资料

| 技术 | 官方文档 |
|------|----------|
| FastAPI | https://fastapi.tiangolo.com/ |
| Vue 3 | https://vuejs.org/ |
| Element Plus | https://element-plus.org/ |
| SQLAlchemy | https://docs.sqlalchemy.org/ |
| uv | https://docs.astral.sh/uv/ |
| Vite | https://vite.dev/ |
| Docker | https://docs.docker.com/ |

## 📮 联系方式

- **作者**：John Young（夜雨诗来）
- **邮箱**：<john.young@foxmail.com>
- **Gitee**：<https://gitee.com/yeyushilai>
- **GitHub**：<https://github.com/yeyushilai>
- **项目地址**：<https://github.com/cross-lang/x-HanJiang>
