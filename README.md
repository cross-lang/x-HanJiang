<p align="center">
  <h1 align="center">寒江（HanJiang）</h1>
  <p align="center">
    <strong>一个基于 FastAPI 框架深度封装的生产级 Python Web 项目框架</strong>
  </p>
  <p align="center">
    <a href="README.en.md">English</a> | 中文
  </p>
</p>

---

## 项目简介

寒江（HanJiang）是一个基于 FastAPI 框架深度封装的生产级 Python Web 项目框架，遵循行业最佳工程实践，提供标准化、模块化、高可扩展、高可维护的后端服务基础架构。开箱即用，支持快速搭建企业级 RESTful API 服务，适配多环境部署。

**适用场景：** 中小型企业后端服务、API 网关、微服务基础脚手架、快速原型开发。

## 核心特征

- **标准三层架构** — API 接口层 → 业务逻辑层（Service）→ 数据访问层（Repository），层间依赖严格单向
- **依赖注入容器** — DI 能力，支持自动装配、单例/多例模式、装饰器注册
- **双配置体系** — 支持 `.env` 环境变量 + `config.yaml` 配置文件双来源，多环境自动切换
- **标准化响应** — 统一的 JSON 响应格式，包含状态码、消息、数据、时间戳、请求 ID
- **全局异常处理** — 自定义异常层级（业务异常 4xx / 系统异常 5xx），全局异常中间件
- **结构化日志** — 基于 loguru，支持请求 ID 追踪、文件+控制台双输出、日志轮转
- **Docker 部署** — 提供标准 Dockerfile 和 docker-compose.yml，支持 Gunicorn + Uvicorn 高性能部署
- **完整工程化** — pyproject.toml 统一管理、测试覆盖、CI/CD 就绪
- **数据库支持** — 集成 SQLAlchemy ORM，支持 MySQL 数据库，开箱即用

## 项目结构

```
x-HanJiang/
├── config/                  # 配置文件
│   ├── config.yaml          # 默认配置
│   ├── config.dev.yaml      # 开发环境覆盖
│   ├── config.test.yaml     # 测试环境覆盖
│   ├── config.prod.yaml     # 生产环境覆盖
│   └── .env.example         # 环境变量示例
├── docs/                    # 项目文档
│   ├── architecture.md      # 架构文档
│   └── DATABASE.md          # 数据库配置指南
├── examples/                # 使用示例
│   ├── basic_usage.py       # 基础使用
│   ├── custom_api.py        # 自定义 API 示例
│   └── di_usage.py          # 依赖注入示例
├── migrations/              # 数据库迁移文件
│   └── 001_create_user_table.sql
├── scripts/                 # 工具脚本
│   └── init_db.py           # 数据库初始化脚本
├── src/                     # 核心业务代码
│   ├── api/                 # API 接口层
│   ├── common/              # 公共组件（常量、响应、基础模型）
│   ├── constants/           # 业务常量
│   ├── core/                # 核心支撑（配置、日志、异常、DI、中间件、数据库）
│   ├── models/              # 数据模型
│   │   ├── entities/        # ORM 实体模型
│   │   └── user.py          # Pydantic DTO
│   ├── repositories/        # 数据访问层
│   ├── services/            # 业务逻辑层
│   ├── utils/               # 工具函数
│   └── main.py              # 应用入口
├── tests/                   # 测试代码
├── Dockerfile               # Docker 镜像构建
├── docker-compose.yml       # Docker 编排
├── pyproject.toml           # 项目依赖和元信息
└── LICENSE                  # MIT 许可证
```

## 系统架构

### 分层架构图

```
┌──────────────────────────────────────┐
│              Client                   │
└──────────────┬───────────────────────┘
               │ HTTP Request
               ▼
┌──────────────────────────────────────┐
│          Middleware Layer             │
│   Request ID │ CORS │ Rate Limit     │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│           API Layer (api/)           │
│   health │ user │ custom endpoints   │
│         Pydantic 校验                │
└──────────────┬───────────────────────┘
               │ API → Service
               ▼
┌──────────────────────────────────────┐
│        Service Layer (services/)      │
│    业务规则 │ 数据校验 │ 流程编排      │
└──────────────┬───────────────────────┘
               │ Service → Repository
               ▼
┌──────────────────────────────────────┐
│      Repository Layer (repositories/)  │
│         CRUD │ 查询 │ 数据映射        │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│      External Storage / Database     │
└──────────────────────────────────────┘
```

### 请求处理流程

```
Client Request
    │
    ▼
RequestIDMiddleware (生成 UUID)
    │
    ▼
CORS Middleware (跨域处理)
    │
    ▼
Router (路由匹配)
    │
    ▼
Dependencies (依赖注入)
    │
    ▼
API Endpoint (参数校验)
    │
    ▼
Service (业务逻辑)
    │
    ▼
Repository (数据访问)
    │
    ▼
标准化响应 (success/error/paginated)
    │
    ▼
Client Response (含 X-Request-ID)
```

## 快速开始

### 环境要求

| 工具 | 版本要求 | 安装方式 |
|------|----------|----------|
| Python | >= 3.11 | [python.org](https://www.python.org/downloads/) |
| uv | latest | [docs.astral.sh/uv](https://docs.astral.sh/uv/) |

**Windows 环境：**
```powershell
# 安装 uv
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Linux / macOS 环境：**
```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 项目克隆

```bash
git clone https://gitee.com/cross-lang/x-HanJiang.git
cd x-HanJiang
```

### 依赖安装

```bash
# 安装所有依赖（生产 + 开发）
uv sync

# 仅安装生产依赖
uv sync --no-dev
```

### 配置文件

1. 复制环境变量示例文件：

```bash
cp config/.env.example config/.env
```

2. 根据需要编辑 `config/.env` 和 `config/config.yaml`

3. 配置优先级：**环境变量 > 环境特定 YAML > 默认 YAML > 代码默认值**

主要配置项：

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| 运行环境 | APP_ENV | development | development / testing / production |
| 监听地址 | SERVER_HOST | 0.0.0.0 | 服务监听地址 |
| 监听端口 | SERVER_PORT | 8000 | 服务监听端口 |
| 调试模式 | SERVER_DEBUG | true | 是否开启调试 |
| 日志级别 | LOGGING_LEVEL | INFO | DEBUG / INFO / WARNING / ERROR |
| 认证密钥 | AUTH_SECRET_KEY | change-me-in-production | JWT 签名密钥 |
| 数据库连接 | DATABASE_URL | | MySQL 连接字符串 |
| 连接池大小 | DATABASE_POOL_SIZE | 5 | 数据库连接池大小 |



### 服务启动

#### 方式一：本地开发启动（热重载）

```bash
# 直接使用 uvicorn
uv run uvicorn src.main:app --reload

# 或使用 Python 模块方式
uv run python -m src.main
```

#### 方式二：Docker 启动

```bash
# 构建并启动
docker-compose up --build

# 后台运行
docker-compose up -d --build
```

服务启动后访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/v1/health
- 版本信息：http://localhost:8000/api/v1/version

### 常用命令

```bash
# 运行测试（含覆盖率）
uv run pytest tests/ -v --cov=src --cov-report=term-missing

# 代码格式化
uv run ruff format src/ tests/

# 代码检查
uv run ruff check src/ tests/

# 类型检查
uv run mypy src/
```

## 技术栈

| 分类 | 技术 | 说明 |
|------|------|------|
| Web 框架 | FastAPI | 高性能异步 Python Web 框架 |
| ASGI 服务器 | Uvicorn | 轻量级 ASGI 服务器 |
| 进程管理 | Gunicorn | 生产级 WSGI/ASGI 进程管理器 |
| ORM | SQLAlchemy | Python SQL 工具包和对象关系映射 |
| 数据库驱动 | PyMySQL | MySQL 驱动程序 |
| 数据校验 | Pydantic v2 | 数据模型和校验框架 |
| 配置管理 | pydantic-settings | 基于 Pydantic 的配置管理 |
| 日志 | Loguru | 现代化 Python 日志库 |
| 限流 | SlowAPI | 请求限流中间件 |
| 包管理 | uv | 高速 Python 包管理器 |
| 容器化 | Docker | 应用容器化部署 |
| 测试 | pytest | Python 测试框架 |

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

## 参考资料

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Pydantic 官方文档](https://docs.pydantic.dev/)
- [SQLAlchemy 官方文档](https://docs.sqlalchemy.org/)
- [uv 官方文档](https://docs.astral.sh/uv/)
- [Uvicorn 官方文档](https://www.uvicorn.org/)
- [Python 官方文档](https://docs.python.org/3.11/)
- [数据库配置指南](docs/DATABASE.md)

## 联系方式

- **作者**：John Young（夜雨诗来）
- **邮箱**：john.young@foxmail.com
- **Gitee 地址**：https://gitee.com/yeyushilai
- **GitHub 地址**：https://github.com/yeyushilai
- **项目地址**：https://gitee.com/yeyushilai/x-HanYun
