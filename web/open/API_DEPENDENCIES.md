# 汉江开放平台前端（web/open）后端接口依赖清单

> 版本：2026-10-03
> 工程：`web/open`（vite + vue3 + TS + element-plus，dev 端口 5174）
> 说明：开放平台分两类接口，前缀与鉴权方式严格隔离：
> - **门户接口** `/api/open-portal/v1`：供 web/open 前端页面调用，鉴权 = 开发者会话（JWT + Redis 登录态，有状态，登出/改密可撤销，参考管理系统登录会话模块实现）
> - **开放接口** `/api/open/v1`：供外部应用调用汉江平台能力，鉴权 = `X-App-Id`/`X-App-Key` + HanJiang-1 签名

## 通用约定

| 项 | 值 |
| --- | --- |
| 门户请求前缀 | `/api/open-portal/v1`（vite dev 代理到 `http://127.0.0.1:8000`） |
| 门户登录鉴权 | `Authorization: Bearer <access_token>`（前端存于 localStorage `open_access_token`；配套存 `open_refresh_token` 用于续期） |
| 门户会话模型 | 有状态会话：登录签发 access/refresh 令牌对并写入服务端登录态（Redis `login_dev:{developer_id}` = jti）；登出、改密、刷新令牌后旧 access 令牌立即失效 |
| 网关凭证 | `X-App-Id` + `X-App-Key`（HanJiang-1 签名，仅开放接口使用，与门户鉴权完全无关） |
| 统一响应包裹 | `{ code, message, data, timestamp, request_id }`（见 `server/src/api/response.py`） |
| 分页结构 | `data: { items, total, page, page_size, total_pages }` |

---

## 一、门户接口（/api/open-portal/v1，已实现）

> 来源：`server/src/api/open_portal/v1/{auth,developer,apps,scopes}.py`，鉴权 = 开发者会话 Bearer JWT（有状态）。

### 1.1 开发者账号（auth，页面：登录 / 注册 / 个人中心-安全设置）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/open-portal/v1/auth/register` | 注册开发者账号（username/email/password/confirm_password/certification_type?，201） |
| POST | `/api/open-portal/v1/auth/login` | 登录（account=用户名或邮箱 + password），返回 `{access_token, refresh_token, token_type, expires_in}` |
| POST | `/api/open-portal/v1/auth/refresh` | 刷新令牌（body: refresh_token），换新令牌对，旧 access 令牌随之失效 |
| POST | `/api/open-portal/v1/auth/logout` | 退出登录（需登录态；撤销服务端会话，全部已签发令牌立即失效） |
| POST | `/api/open-portal/v1/auth/change-password` | 修改密码（old_password/new_password；成功后服务端登录态被撤销，需重新登录） |

### 1.2 开发者资料与认证（developer，页面：个人中心）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/open-portal/v1/developer/profile` | 当前开发者资料（username/name/email/phone/certification_type/certification_status/company_name） |
| PUT | `/api/open-portal/v1/developer/profile` | 更新姓名/手机号 |
| POST | `/api/open-portal/v1/developer/certification` | 提交认证申请（personal/enterprise，预留，进入待审） |

### 1.3 应用管理（apps，页面：应用管理）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/open-portal/v1/apps` | 我的应用分页列表（owner 隔离，仅本人名下；query: page/page_size/keyword） |
| POST | `/api/open-portal/v1/apps` | 创建应用（201；**app_key 明文仅此一次返回**；创建后 approval_status=pending，须管理端审批通过后方可调用开放接口） |
| GET | `/api/open-portal/v1/apps/{app_id}` | 应用详情（含审批状态/意见） |
| PUT | `/api/open-portal/v1/apps/{app_id}` | 更新应用（name/description/auth_mode） |
| DELETE | `/api/open-portal/v1/apps/{app_id}` | 删除应用（软删） |
| PUT | `/api/open-portal/v1/apps/{app_id}/scopes` | 提交 scope 申请/调整（body: scopes + reason，进入审批流，approval_status 复位 pending） |
| POST | `/api/open-portal/v1/apps/{app_id}/rotate-key` | 重置 App Key（新 key 仅此一次返回） |

### 1.4 scope 目录（scopes，页面：应用管理 / 首页）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/open-portal/v1/scopes` | scope 目录（id/scope_code/scope_name/module/module_label/operation/description） |

### 1.5 站内信（messages，页面：右上角铃铛）

> 开发者站内信独立表 `developer_messages`（与管理端用户站内信 notification_records 分表隔离）。
> 数据表：`server/src/models/entities/developer_message_entity.py` + 迁移 `0016_create_developer_messages`；
> 类型约定：category = system 系统消息 / audit 审批结果 / notify 业务通知，read 布尔。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/open-portal/v1/messages/unread-count` | 未读消息数（右上角铃铛角标，前端 15s 轮询） |
| GET | `/api/open-portal/v1/messages` | 我的站内信分页列表（query: page/page_size；时间倒序） |
| POST | `/api/open-portal/v1/messages/{msg_id}/read` | 标记单条已读 |
| POST | `/api/open-portal/v1/messages/read-all` | 全部已读 |

> 发送方预留：审批结果、系统通知等场景经 `DeveloperMessageService.send()` 写入（站内信表已就绪，发送方后续接入）。

---

## 二、开放接口（/api/open/v1，网关，已实现）

> 来源：`server/src/api/open/v1/{health,app,user,role,file}.py`，鉴权 = X-App-Id / X-App-Key（HanJiang-1 签名）。
> **前置门槛**：应用 `approval_status` 非 approved 一律 403（审批通过前不可调用）。

### 健康管理（无需 scope）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/open/v1/health` | 健康检查，返回 `{status, service, app}` |
| GET | `/api/open/v1/version` | 版本，返回 `{app_version, api_version}` |

### 应用信息（无需 scope）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/open/v1/me` | 当前调用方应用信息（id / app_id / name / auth_mode / scopes / status / description） |

### 用户管理（scope: user:read / user:write）

| 方法 | 路径 | scope | 说明 |
| --- | --- | --- | --- |
| POST | `/api/open/v1/users` | `user:write` | 创建用户（201） |
| GET | `/api/open/v1/users` | `user:read` | 分页列表（query: page/page_size/keyword/status） |
| GET | `/api/open/v1/users/{user_id}` | `user:read` | 用户详情 |
| PATCH | `/api/open/v1/users/{user_id}` | `user:write` | 更新用户 |
| DELETE | `/api/open/v1/users/{user_id}` | `user:write` | 删除用户，返回 `{deleted: true}` |

### 角色管理（scope: role:read / role:write）

> 来源：`server/src/api/open/v1/role.py`，服务 `services/role_service.py`（已上提通用目录，管理端 `/api/admin/v1/roles` 与开放接口共用）。
> 权限的绑定/解绑属管理端管理行为（用户态 ROLE_PERMISSION 权限体系），不对外部应用开放。

| 方法 | 路径 | scope | 说明 |
| --- | --- | --- | --- |
| GET | `/api/open/v1/roles` | `role:read` | 分页列表（query: page/page_size/keyword/role_type/status） |
| POST | `/api/open/v1/roles` | `role:write` | 创建角色（201；编码/名称唯一） |
| GET | `/api/open/v1/roles/{role_id}` | `role:read` | 角色详情 |
| PATCH | `/api/open/v1/roles/{role_id}` | `role:write` | 更新角色（role_name/description/status） |
| DELETE | `/api/open/v1/roles/{role_id}` | `role:write` | 软删除角色（有关联用户的角色不可删） |
| GET | `/api/open/v1/roles/{role_id}/permissions` | `role:read` | 角色绑定的权限列表 |

### 文件管理（scope: file:read / file:write）

> 来源：`server/src/api/open/v1/file.py`，服务 `services/file_service.py`（已上提通用目录，管理端 `/api/admin/v1/files` 与开放接口共用）。
> 上传约定：开放接口签名串固定 `Content-Type: application/json` 并对 body 做 SHA256 摘要，multipart 无法进入签名体系，
> 故文件内容以 Base64 内嵌 JSON body（`OpenFileUploadRequest`，见 `schemas/open/file.py`），落库归属走 `files.uploaded_by_app`（应用 ID），
> 不占用用户外键列 `files.uploaded_by`。

| 方法 | 路径 | scope | 说明 |
| --- | --- | --- | --- |
| GET | `/api/open/v1/files` | `file:read` | 分页列表（query: folder/keyword/page/page_size） |
| POST | `/api/open/v1/files` | `file:write` | 上传文件（201；body: filename/content_base64/folder） |
| GET | `/api/open/v1/files/{file_path:path}` | `file:read` | 下载文件（本地存储返回文件流，云存储 302 重定向） |
| DELETE | `/api/open/v1/files/{file_id}` | `file:write` | 软删除文件，返回 `{deleted: true}` |

> scope 元数据唯一来源：`server/src/constants/scopes.py` 的 `OpenApiScopeCode`（启动时对账到 openapi_scopes 表；role/file 模块 scope 自动同步）。

---

## 三、前端页面 ↔ 接口映射

| 页面 | 门户接口（/api/open-portal/v1） | 备注 |
| --- | --- | --- |
| 登录 `/login` | auth/login | 登录成功存 access+refresh 令牌 |
| 注册 `/register` | auth/register | — |
| 首页 `/home` | developer/profile、apps、scopes | — |
| 应用管理 `/apps` | apps CRUD、apps/{id}/scopes、apps/{id}/rotate-key、scopes | 新应用创建后进入审批流 |
| 开放接口 `/docs` | —（静态目录展示，健康/用户类接口示例走 /api/open/v1 网关） | docs/catalog 动态数据源接口尚未实现 |
| 站内信（右上角铃铛） | messages/unread-count、messages、messages/{id}/read、messages/read-all | 铃铛角标 15s 轮询未读数；左侧导航与 /messages 独立页已移除 |
| 个人中心 `/profile` | developer/profile、developer/certification、auth/change-password | 改密成功需重新登录 |

---

## 四、管理端可复用接口（审批流依赖，双路径兼容）

> 管理端已实现，`/api/v1` 与 `/api/admin/v1` 双路径均可访问（同 handler）。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/admin/apps/scopes` | scope 目录（open 前端 listScopes 当前即走此接口） |
| POST | `/api/v1/admin/apps` | 管理员创建应用（owner=admin，创建即 approved；返回 app_key 一次） |
| GET | `/api/v1/admin/apps` | 应用分页列表（含 owner_type/owner_name/approval_status） |
| GET/PUT/DELETE | `/api/v1/admin/apps/{id}` | 应用详情 / 更新 / 删除 |
| PUT | `/api/v1/admin/apps/{id}/approval` | **审批端点**：approved=true/false + note，通过/驳回开发者申请（未通过的应用网关一律 403） |
| PUT | `/api/v1/admin/apps/{id}/scopes` | 覆盖式调整应用 scope（审批落地，置 approved） |
| PUT | `/api/v1/admin/apps/{id}/status` | 启用/禁用 |
| POST | `/api/v1/admin/apps/{id}/rotate-key` | 重置密钥 |

> 衔接点：开发者提交应用/scope 申请（approval_status=pending）→ 管理端 `admin/apps/{id}/approval` 审批 → 通过后应用方可调用 /api/open/v1 开放接口。
