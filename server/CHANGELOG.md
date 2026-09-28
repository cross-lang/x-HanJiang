# Changelog

本文件记录 汉江（HanJiang）后端服务 的版本迭代变更，格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.3.0] - 2026-09-28

### 新增

- **AI 助手模块**
  - SSE 流式对话接口（`POST /api/v1/assistant/chat`），事件类型 token / navigate / denied / error / done，仅要求登录
  - 会话管理：创建会话、会话列表、会话消息列表（校验归属）、消息反馈（👍👎，提示词调优数据源）
  - 对话编排：记忆管理（近 N 轮原文 + token 预算压缩，可配摘要模型）、知识库检索（默认关闭，可对接向量检索）、工具调用（多轮工具编排，含导航跳转）
  - LLM 集成（`infras/llm.py`）：openai_compat 兼容协议，base_url 可切换 DeepSeek / 火山方舟 / 通义 / vLLM 等，默认对接小米 MiMo（`mimo-v2.5-pro`，可切图片理解模型）
- **数据表**：新增 `assistant_conversations` / `assistant_messages` / `assistant_feedbacks` 三张表迁移（0008_create_assistant）
- **权限**：`assistant:chat`（对话与会话管理，实际仅要求登录）、`assistant:feedback`（消息反馈），启动时自动注册
- **依赖**：新增 `openai>=3.19.2`
- **前端配套**：管理后台顶栏 AI 助手入口 + 右侧抽屉，SSE 流式渲染（loading 占位）、会话历史恢复、👍👎 反馈选中态（`web/admin/src/api/assistant.ts`）

### 变更

- 前端品牌化：新增 Logo 图标与 All Rights Reserved 版权声明，清理无用代码

## [0.2.0] - 2026-09-28

### 新增

- **公告管理**
  - 首页板块 / 横幅展示位，创建 / 修改 / 删除 / 发布 / 下架全生命周期
  - 有效期（start_at ~ end_at）校验与过期标记，展示排序，Markdown / 富文本正文
  - 首页生效公告接口（登录用户可见）；前端公告管理页（`/announcements`）与正文渲染消毒（marked + DOMPurify）
- **系统通知广播**
  - 面向全体活跃用户发布普通通知 / 系统维护通知，站内信广播产生未读红点
  - 维护通知额外按用户渠道配置推送多渠道（email / 钉钉 / 飞书等），支持发布后撤回
- **数据表**：新增系统通知表（`system_notifications`）与公告表（`announcements`）迁移（0006 / 0007）

### 变更

- 通知接口重构：`admin_notification.py` 与 `maintenance.py` 合并入 `notification.py`（系统通知发布 / 撤回 + 通知记录 + 渠道配置管理），移除原手动发送通知接口
- 个人中心：验证码二次认证文案统一（发送至邮箱的 6 位验证码），修复改密 / 改手机号 / 改邮箱等缺陷；前端个人中心页样式重构
- 前端系统通知页升级：新增系统通知发布 / 撤回与发布记录列表，保留渠道配置 / 测试 / 监控

### 修复

- 修复个人中心、通知子系统相关缺陷（含 e83010e / 45a3ecf / 81bcc9f 等提交）

## [0.1.0] - 2026-09-28

首个正式版本。基于 FastAPI 深度封装的生产级 Web 应用框架，涵盖认证授权、开放平台、通知、文件、审计、监控等企业级通用能力。

### 新增

- **核心框架**
  - 应用工厂模式与生命周期管理（配置加载 → 日志 → 中间件 → 异常处理器 → 路由挂载 → 通知子系统）
  - 中间件洋葱模型：CORS / 请求 ID / 请求日志 / 异常兜底
  - 统一异常处理与统一响应封装（`X-Request-ID` 透传）

- **认证与授权**
  - JWT 登录 / 刷新 / 登出，登录态缓存可即时失效
  - RBAC 角色权限模型，`@permission` 装饰器自动扫描路由注册权限，启动时同步数据库（失效权限标记 `is_deprecated`）
  - 邮箱验证码二次认证（改密 / 改手机号 / 改邮箱）

- **开放平台**
  - AppId / AppKey 明文与 HanJiang-1 HMAC 签名双模式鉴权
  - `@app_scope` scope 自动扫描同步；应用 CRUD / scope 授权 / AppKey 轮换

- **用户与个人中心**
  - 用户管理 CRUD，支持多角色、CSV 批量导入导出
  - 个人中心：资料维护、修改密码、权限菜单树、通知偏好与接收人管理

- **通知子系统**
  - 事件驱动多渠道分发：站内信 / 邮件 / 钉钉 / 飞书 / 短信
  - 用户级通知偏好与接收人管理，系统级渠道配置热更新、渠道测试
  - 失败自动重试：Redis 重试队列 + 调度 Worker（`scheduling/retry_worker.py`）

- **站内信**
  - 未读数、消息列表、单条已读、全部已读

- **文件管理**
  - 上传 / 列表 / 下载 / 删除，支持文件夹分组
  - 统一存储抽象：本地文件系统与 S3 兼容对象存储（七牛 / AWS S3 / MinIO），业务代码零改动切换

- **审计与监控**
  - 业务审计日志与登录日志分离，记录操作者、IP、前后数据，支持 CSV 导出
  - 健康检查（数据库 / 缓存连通状态），故障自动触发告警（带节流，避免重复）
  - 系统告警 Webhook 接入与广播、系统维护通知

- **仪表盘**
  - 统计指标卡片、登录 / 操作趋势、最近记录；我的最近活动

- **全局搜索**
  - 跨用户 / 角色 / 权限 / 开放应用 / 文件关键字搜索，按权限过滤分类

- **基础设施**
  - MySQL 连接池与会话管理、Redis 缓存（限流计数 / 登录态 / 验证码 / 重试队列）
  - Loguru 日志（JSON / console 双格式，支持轮转压缩）、SlowAPI 限流
  - pydantic-settings 配置：`.env` 与 `config.yaml` 双通道，环境变量优先

- **工程化**
  - Alembic 数据库迁移（用户 / 通知 / 开放应用等 5 个版本）
  - Ruff 格式化与静态检查、mypy 类型检查、pytest 单元测试（含覆盖率）
  - uv 依赖管理（`uv.lock` 可复现构建）
  - GitHub Actions CI（lint + test）、Docker 多阶段构建镜像（Gunicorn + Uvicorn Worker）

### 变更

- 项目名称由「汉匠」更名为「汉江（HanJiang）」
- 配置加载重构：支持项目根目录 `.env` / `config.yaml` 双通道加载，环境变量优先
- 认证模块仅保留登录 / 刷新 / 登出闭环，不提供开放注册入口（用户由管理端创建），依赖注入采用 FastAPI 原生函数式 Depends
- 示例配置默认数据库账号统一为 yeyushilai（默认数据库名 hanjiang）

### 修复

- 修复权限自动扫描与同步、通知重试逻辑、审计日志查询与导出等各类缺陷
- 修复并完善 OpenAPI / Postman 文档与健康检查模块
