# 汉江开放平台前端（web/open）后端接口依赖清单

> 版本：2026-10-03
> 工程：`web/open`（vite + vue3 + TS + element-plus，dev 端口 5174）
> 说明：清单按「已实现 / 待实现」双轨标注。**已实现**指后端 `server/src/api/open/v1` 中已存在且可调用的接口；**待实现**指前端已按约定路径接入、后端尚未落地的接口（统一在 api 层注释为「前端已接入、后端待实现」）。

## 通用约定

| 项 | 值 |
| --- | --- |
| 请求前缀 | `/api/open/v1`（vite dev 代理到 `http://127.0.0.1:8000`） |
| 登录鉴权 | `Authorization: Bearer <access_token>`（前端存于 localStorage `open_access_token`） |
| 网关凭证 | `X-App-Id` + `X-App-Key`（调用开放接口时携带） |
| 权限控制 | 接口按 scope 授权（`user:read` / `user:write`），未获批 scope 返回 403 |
| 统一响应包裹 | `{ code, message, data, timestamp, request_id }`（见 `server/src/api/response.py`） |
| 分页结构 | `data: { items, total, page, page_size, total_pages }` |

---

## 一、已实现接口（open 域网关，可直接调用）

> 来源：`server/src/api/open/v1/{health,app,user}.py`，鉴权方式均为 X-App-Id / X-App-Key。

### 健康管理（无需 scope）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/open/v1/health` | 开放平台健康检查，返回 `{status, service, app}` |
| GET | `/api/open/v1/version` | 开放平台版本，返回 `{app_version, api_version}` |

### 应用信息（无需 scope）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/open/v1/me` | 当前调用方应用信息（id / app_id / name / auth_mode / scopes / status / description） |

### 用户管理（scope: user:read / user:write）

| 方法 | 路径 | scope | 说明 |
| --- | --- | --- | --- |
| POST | `/api/open/v1/users` | `user:write` | 创建用户（201；body: username/email/password/name/phone/gender/birthday/role_ids/status?） |
| GET | `/api/open/v1/users` | `user:read` | 分页列表（query: page/page_size/keyword/status） |
| GET | `/api/open/v1/users/{user_id}` | `user:read` | 用户详情 |
| PATCH | `/api/open/v1/users/{user_id}` | `user:write` | 更新用户（仅更新提供字段） |
| DELETE | `/api/open/v1/users/{user_id}` | `user:write` | 删除用户，返回 `{deleted: true}` |

> scope 元数据唯一来源：`server/src/constants/scopes.py` 的 `OpenApiScopeCode`（启动时对账到 openapi_scopes 表）。

---

## 二、待实现接口（前端已按约定路径接入）

> 统一前缀 `/api/open/v1`。前端 `web/open/src/api/*` 已全部就绪，后端落地后即自动生效。

### 2.1 开发者账号（auth，页面：登录 / 注册）

| 方法 | 路径 | 页面 | 说明 |
| --- | --- | --- | --- |
| POST | `/api/open/v1/auth/register` | 注册页 | 注册开发者账号，body: username/email/password/confirm_password/certification_type |
| POST | `/api/open/v1/auth/login` | 登录页 | 登录（账号=用户名或邮箱），返回 `{access_token, token_type}` |
| POST | `/api/open/v1/auth/logout` | 顶部菜单 | 退出登录 |
| POST | `/api/open/v1/auth/change-password` | 个人中心-安全设置 | 修改密码，body: old_password/new_password |

### 2.2 开发者资料与认证（developer，页面：个人中心）

| 方法 | 路径 | 页面 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/open/v1/developer/profile` | 布局/个人中心 | 当前开发者资料（username/name/email/phone/certification_type/certification_status/company_name） |
| PUT | `/api/open/v1/developer/profile` | 个人中心-基本信息 | 更新姓名/手机号 |
| POST | `/api/open/v1/developer/certification` | 个人中心-开发者认证 | 提交认证申请（personal/enterprise） |

### 2.3 应用管理（apps，页面：应用管理）

| 方法 | 路径 | 页面 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/open/v1/apps` | 应用列表 | 我的应用分页列表（query: page/page_size/keyword） |
| POST | `/api/open/v1/apps` | 新建应用弹窗 | 创建应用（201；**app_key 明文仅此一次返回**） |
| GET | `/api/open/v1/apps/{id}` | 编辑回显 | 应用详情 |
| PUT | `/api/open/v1/apps/{id}` | 编辑应用弹窗 | 更新应用（name/description/auth_mode） |
| DELETE | `/api/open/v1/apps/{id}` | 应用列表 | 删除应用 |
| PUT | `/api/open/v1/apps/{id}/scopes` | scope 申请弹窗 | 提交 scope 申请/调整（body: scopes + reason，进入审批流） |
| POST | `/api/open/v1/apps/{id}/rotate-key` | 应用列表 | 重置 App Key（新 key 仅此一次返回） |

### 2.4 scope 目录（scopes，页面：应用管理 / 首页）

| 方法 | 路径 | 页面 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/open/v1/scopes` | 应用表单、权限展示 | scope 目录（id/scope_code/scope_name/module/module_label/operation/description） |

### 2.5 接口文档（docs，页面：开放接口）

| 方法 | 路径 | 页面 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/open/v1/docs/catalog` | 开放接口 | 接口目录（当前页面为内置静态目录，接口就绪后切换为动态数据源） |

### 2.6 站内信（messages，页面：站内信【预留】）

| 方法 | 路径 | 页面 | 说明 |
| --- | --- | --- | --- |
| GET | `/api/open/v1/messages` | 站内信列表 | 分页列表（category: system/audit/notify） |
| PUT | `/api/open/v1/messages/{id}/read` | 站内信（预留） | 标记已读 |

---

## 三、前端页面 ↔ 接口映射

| 页面 | 已实现接口 | 待实现接口 |
| --- | --- | --- |
| 登录 `/login` | — | auth/login |
| 注册 `/register` | — | auth/register |
| 首页 `/home` | — | developer/profile、apps、scopes |
| 应用管理 `/apps` | — | apps CRUD、apps/{id}/scopes、apps/{id}/rotate-key、scopes |
| 开放接口 `/docs` | health、version、me、users×5（静态目录） | docs/catalog（切换为动态） |
| 站内信 `/messages` | — | messages、messages/{id}/read |
| 个人中心 `/profile` | — | developer/profile、developer/certification、auth/change-password |

---

## 四、管理端可复用接口（审批流依赖，双路径兼容）

> 管理端已实现，`/api/v1` 与 `/api/admin/v1` 双路径均可访问（同 handler）。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/admin/apps/scopes` | scope 目录（open 前端 listScopes 当前即走此接口） |
| POST | `/api/v1/admin/apps` | 管理员创建应用（返回 app_key 一次） |
| GET | `/api/v1/admin/apps` | 应用分页列表 |
| GET/PUT/DELETE | `/api/v1/admin/apps/{id}` | 应用详情 / 更新 / 删除 |
| PUT | `/api/v1/admin/apps/{id}/scopes` | 覆盖式调整应用 scope（审批落地） |
| PUT | `/api/v1/admin/apps/{id}/status` | 启用/禁用 |
| POST | `/api/v1/admin/apps/{id}/rotate-key` | 重置密钥 |

> 备注：开放平台的注册/应用/审批为独立域（developers 体系），与管理系统 users 分表；开放平台侧 `apps/{id}/scopes` 提交申请后，审批动作最终落在管理端 `admin/apps` 系列接口上（衔接点待后端开发时确认）。
