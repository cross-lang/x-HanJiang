# HanJiang

[中文](README.md) | English

---

## Introduction

HanJiang (汉江) is a production-grade Python Web application framework built on top of FastAPI, following industry best engineering practices. It provides a standardized, modular, highly extensible, and maintainable backend service infrastructure.

The project is ready to use out of the box, featuring a standard three-layer architecture (API → Service → Repository), FastAPI native dependency injection, dual configuration system, unified authentication with RBAC access control, **Open Platform API for external service integration (AppId+AppKey auth, with HMAC upgrade path)**, structured logging, business audit, S3-compatible object storage, and idempotent seed data initialization. It enables rapid development of enterprise-grade RESTful APIs suitable for local development, testing, and multi-environment production deployment.

## Quick Start

### 1. Requirements

| Tool | Version |
|------|---------|
| Python | >= 3.11 |
| uv | latest (recommended) |
| MySQL | >= 8.0 |
| Redis | >= 7.0 |

**Windows:**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone the Repository

```bash
git clone https://github.com/cross-lang/x-HanJiang.git
cd x-HanJiang/server
```

### 3. Install Dependencies

```bash
# Install all dependencies (production + development)
uv sync

# Production only
uv sync --no-dev
```

### 4. Configuration

The project supports both `.env` environment variables and `config.yaml` configuration files. Configuration precedence: **environment variables > environment-specific YAML (config.{env}.yaml) > default YAML (config.yaml) > code defaults**.

**Option 1: Using `.env` file (recommended)**
```bash
cp .env.example .env
```

**Option 2: Using `config.yaml` file**
```bash
cp config.yaml.example config.yaml
```

**Core configuration parameters:**

| Parameter | Environment Variable | Description |
|-----------|---------------------|-------------|
| `APP_ENV` | `APP_ENV` | Runtime environment: `development` / `testing` / `production` |
| `SERVER_HOST` | `server.host` | Listen address, default `0.0.0.0` |
| `SERVER_PORT` | `server.port` | Listen port, default `8000` |
| `AUTH_SECRET_KEY` | `auth.secret_key` | JWT signing key; must be overridden with a random string >= 32 chars in production |
| `MYSQL_HOST` | `database.host` | MySQL host address |
| `MYSQL_PORT` | `database.port` | MySQL port, default `3306` |
| `MYSQL_USER` | `database.user` | MySQL username |
| `MYSQL_PASSWORD` | `database.password` | MySQL password |
| `MYSQL_DATABASE` | `database.database` | MySQL database name, default `hanjiang` |
| `REDIS_HOST` | `redis.host` | Redis host address |
| `REDIS_PORT` | `redis.port` | Redis port, default `6379` |
| `REDIS_PASSWORD` | `redis.password` | Redis password |
| `STORAGE_PROVIDER` | `storage.provider` | Storage backend: `local` (local filesystem) / `s3` (S3-compatible object storage) |

> **Production**: Inject sensitive configuration such as `AUTH_SECRET_KEY`, database password, and Redis password via environment variables to avoid committing secrets to version control.

> **Secret key generation**:
> ```bash
> python -c "from src.utils.security import generate_secret_key; print(generate_secret_key())"
> ```

### 5. Start the Service

#### Option 1: Local Development with Hot Reload (Recommended)

```bash
# Start with CLI command (hot reload)
uv run x-HanJiang --reload

# Or start with uvicorn directly
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### Option 2: Docker Deployment

```bash
docker-compose up --build
```

> Docker deployment requires a `.env` file with `AUTH_SECRET_KEY`, `MYSQL_PASSWORD`, `REDIS_PASSWORD` and other required environment variables configured in advance.

After startup:
- Swagger interactive docs: http://localhost:8000/docs
- ReDoc read-only docs: http://localhost:8000/redoc
- Health check: http://localhost:8000/api/v1/health

### 6. Common Engineering Commands

```bash
# Run unit tests (with coverage report)
uv run pytest tests/ -v --cov=src --cov-report=term-missing

# Code formatting
uv run ruff format src/ tests/

# Static code analysis
uv run ruff check src/ tests/

# Type checking
uv run mypy src/

# Initialize database tables (also done automatically on app startup)
uv run python -c "from src.infras.database import init_db; init_db()"
```

### 7. Usage Examples

**Login to obtain a token:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "superadmin", "password": "admin@123456"}'
```

**Access a protected endpoint with the token:**
```bash
curl http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer <access_token>"
```

**Upload a file:**
```bash
curl -X POST http://localhost:8000/api/v1/files/upload \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@./example.pdf" \
  -F "folder=documents"
```

**Query role permissions:**
```bash
curl http://localhost:8000/api/v1/roles/1/permissions \
  -H "Authorization: Bearer <access_token>"
```

**Create an open platform app:**
```bash
curl -X POST http://localhost:8000/api/v1/admin/apps \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "MyService", "scopes": ["ping:read"], "rate_limit_per_minute": 60, "auth_mode": "plain"}'
```

**Call an open platform endpoint:**
```bash
curl http://localhost:8000/api/open/v1/me \
  -H "X-App-Id: hj_test_xxx" \
  -H "X-App-Key: <app_key>"
```

> After first deployment, you can log in with the default superadmin account: `superadmin` / `admin@123456`. Be sure to change this password in production.

## Project Structure

```
x-HanJiang/
├── .env.example              # Environment variable template
├── config.yaml.example       # YAML configuration file template
├── alembic/                  # Database migration management
│   ├── env.py                # Alembic environment configuration
│   └── versions/             # Migration version scripts
├── docs/                     # Project documentation
│   └── hanjiang.sql          # Database schema definition (9 tables)
├── examples/                 # Usage examples
├── logs/                     # Runtime log output directory
├── scripts/                  # Engineering scripts
│   ├── init_db.py            # Database initialization script
│   └── export_openapi.py     # OpenAPI spec export script
├── src/                      # Core business code
│   ├── main.py               # Application entry point (factory function, lifecycle management)
│   ├── api/                  # API layer
│   │   ├── v1/               # User-facing v1 routes (JWT auth)
│   │   │   ├── health.py     # Health check (with auto-alerting)
│   │   │   ├── user.py       # User management CRUD
│   │   │   ├── auth.py       # Authentication (login/refresh/me/logout)
│   │   │   ├── role.py       # Role management and permission binding
│   │   │   ├── audit.py      # Business audit log query
│   │   │   ├── file.py       # File upload
│   │   │   ├── notification.py # Notification records query and manual sending
│   │   │   ├── alert.py      # System alerts (Webhook + broadcast)
│   │   │   ├── maintenance.py # System maintenance notifications
│   │   │   └── openapi_app.py # Open platform app management (super admin CRUD)
│   │   ├── open/             # Open platform v1 routes (AppId/AppKey auth)
│   │   │   └── v1/
│   │   │       ├── health.py  # Open platform health & version
│   │   │       ├── ping.py    # Connectivity test (requires ping:read scope)
│   │   │       └── app.py     # Current app info
│   │   ├── dependencies.py   # DI dependency functions (Service/Repository/current_user/current_app)
│   │   ├── response.py       # Unified response wrapper
│   │   └── router.py         # Route aggregation registration
│   ├── constants/            # Business constants and enums
│   │   ├── base.py           # Describable enum base class
│   │   ├── constants.py      # Global constant definitions
│   │   └── enums.py          # Business enum definitions
│   ├── core/                 # Core support modules
│   │   ├── config.py         # Configuration loading and parsing
│   │   ├── exceptions.py     # Custom exceptions and global exception handling
│   │   ├── logger.py         # Logger initialization (loguru)
│   │   ├── middleware.py     # Middleware (request ID, logging, CORS, rate limiting)
│   │   ├── seed.py           # Idempotent seed data initialization
│   │   ├── session.py        # Database session management
│   │   └── tokens.py         # JWT token issuance and verification
│   ├── infras/               # Infrastructure layer
│   │   ├── database.py       # Database connection pool and session factory (SQLAlchemy)
│   │   ├── cache.py          # Cache provider (Redis)
│   │   ├── email.py          # Email sending
│   │   ├── http.py           # HTTP client
│   │   ├── notification.py   # Notification channel providers (Email/DingTalk/Feishu/SMS)
│   │   └── storage.py        # Storage abstraction layer (local filesystem / S3-compatible)
│   ├── notification/         # Notification subsystem
│   │   ├── dispatcher.py     # Notification dispatcher (event-driven, routing table, persistence, retry)
│   │   ├── template.py       # Notification template rendering engine
│   │   └── retry_worker.py   # Failed notification retry worker
│   ├── models/               # Data models
│   │   └── entities/         # SQLAlchemy ORM entities (8 tables)
│   ├── repositories/         # Data access layer (Repository pattern)
│   ├── schemas/              # API request/response DTOs (Pydantic BaseModel)
│   ├── services/             # Business logic layer (Service pattern)
│   └── utils/                # Utility functions
│       └── security.py       # Security utils (password hashing / Fernet / HMAC / key generation)
├── tests/                    # Test code
├── Dockerfile                # Docker image build (multi-stage)
├── docker-compose.yml        # Docker orchestration (App + MySQL + Redis)
├── pyproject.toml            # Project dependencies and metadata
├── uv.toml                   # uv package manager configuration
└── LICENSE                   # MIT License
```

## System Architecture

### Layered Architecture

```mermaid
flowchart TB
  Client[Client / Admin Panel] -->|HTTP / JSON| API[API Layer<br/>Route Aggregation · Param Validation · Unified Response]

  subgraph Application[Application Layer]
    API --> Auth[User Auth<br/>Bearer JWT · Current User · RBAC]
    API --> OpenAuth[Open Platform Auth<br/>AppId/AppKey · Scope · HMAC-ready]
    Auth --> Service[Service Layer<br/>User · Role · Permission · Audit · File · Notification]
    OpenAuth --> OpenService[Open Platform Service<br/>App Management · Auth · Signature]
  end

  subgraph Data[Data Access Layer]
    Service --> Repository[Repository Layer<br/>CRUD · Query · Entity Mapping]
    Repository --> Entity[Models / Entities<br/>SQLAlchemy ORM Entities]
    Service --> Schema[Schemas<br/>Pydantic Request & Response DTOs]
  end

  subgraph Support[Core Support & Infrastructure]
    Core[Core<br/>Config · DI · Middleware · Exceptions · Tokens · Logging]
    Infra[Infras<br/>Database · Cache · Email · HTTP · Storage · Notification Providers]
  end

  Core -.Provides cross-cutting concerns.-> API
  Core -.Provides cross-cutting concerns.-> Service
  Repository --> Infra
  Entity --> Infra
  Service -->|File R/W| Infra
  Infra --> DB[(MySQL)]
  Infra --> Redis[(Redis)]
  Infra --> OSS[(S3-Compatible Object Storage / Local Storage)]
```

### Core Business Flow

```mermaid
flowchart TD
  Start([Client sends request]) --> Open{Open platform endpoint?}
  Open -->|Yes| AppKey{AppId/AppKey valid?}
  AppKey -->|No| Unauthorized[Return 401 Unauthorized]
  AppKey -->|Yes| Scope{Has required scope?}
  Scope -->|No| Forbidden[Return 403 Forbidden]
  Scope -->|Yes| Route[API routing & param validation]
  Open -->|No| Public{Public endpoint?}
  Public -->|Yes: login / refresh / health check| Route[API routing & param validation]
  Public -->|No| Token{Bearer Token valid?}
  Token -->|No| Unauthorized[Return 401 Unauthorized]
  Token -->|Yes| Permission{Has required role or permission?}
  Permission -->|No| Forbidden[Return 403 Forbidden]
  Permission -->|Yes| Route

  Route --> Login{Auth request?}
  Login -->|Yes| Verify[Verify account and password]
  Verify -->|Failed| LoginFailed[Record failed login log<br/>Return auth failure]
  Verify -->|Success| IssueToken[Issue access & refresh tokens<br/>Record successful login log]
  Login -->|No| Service[Invoke corresponding Service]
  Service --> Repository[Repository reads/writes data]
  Repository --> Database[(MySQL / Redis)]
  Service --> Audit[Record business audit log<br/>Operator · IP · Before/after data]
  Database --> Result[Assemble business result]
  Audit --> Result
  IssueToken --> Response[Unified response + X-Request-ID]
  Result --> Response
  LoginFailed --> Response
  Unauthorized --> End([Request complete])
  Forbidden --> End
  Response --> End
```

### Module Dependency Graph

```mermaid
flowchart LR
  Main[main.py] --> Router[api.router]
  Router --> API[api.v1 user-facing routes]
  Router --> OpenAPI[api.open open platform routes]
  API --> Dependencies[api.dependencies]
  API --> Schemas[schemas]
  API --> Services[services]

  Dependencies --> Services
  Services --> Repositories[repositories]
  Services --> Schemas
  Services --> Core[core<br/>Config · Exceptions · Logging · Tokens]
  Services --> Infra[infras<br/>Cache · Email · HTTP · Storage · Notification]

  Repositories --> Entities[models.entities]
  Repositories --> Database[infras.database]
  Entities --> Database
  Core --> Infra
  Core --> Constants[constants]
  API --> Constants

  classDef entry fill:#e8f1ff,stroke:#3973c6,color:#16345c;
  classDef app fill:#eaf7ef,stroke:#3b8c5a,color:#1f4d31;
  classDef support fill:#fff4df,stroke:#c68a22,color:#68470f;
  classDef data fill:#f5eafa,stroke:#8b5ba7,color:#4b2d5d;

  class Main,Router entry;
  class API,Dependencies,Services app;
  class Core,Infra,Constants support;
  class Repositories,Entities,Database,Schemas data;
```

## Tech Stack

| Category | Technology | Description |
|----------|------------|-------------|
| **Language** | Python 3.11+ | Strongly typed, async-friendly modern Python |
| **Web Framework** | FastAPI | High-performance async Python web framework |
| **ASGI Server** | Uvicorn | Lightweight ASGI server |
| **Process Manager** | Gunicorn | Production-grade WSGI/ASGI process manager |
| **Database** | MySQL 8.0 | Relational database |
| **ORM** | SQLAlchemy 2.0 | Python SQL toolkit and object-relational mapping |
| **DB Driver** | PyMySQL | Pure Python MySQL driver |
| **DB Migration** | Alembic | SQLAlchemy database migration tool |
| **Cache** | Redis 7 | Token, login state, and notification retry queue |
| **Object Storage** | boto3 | S3-compatible object storage (Qiniu Kodo / AWS S3 / MinIO) |
| **Validation** | Pydantic v2 | Data modeling and validation framework |
| **Config Management** | pydantic-settings | Pydantic-based configuration management |
| **Logging** | Loguru | Modern Python logging library |
| **Rate Limiting** | SlowAPI | Request rate limiting middleware |
| **Password Hashing** | bcrypt | Secure password hashing |
| **Symmetric Encryption** | cryptography (Fernet) | AppKey encryption, HMAC signature support |
| **JWT** | PyJWT | JSON Web Token issuance and verification |
| **HTTP Client** | httpx | Async HTTP client (notification channel API calls) |
| **Package Manager** | uv | High-performance Python package manager |
| **Linting** | Ruff | High-performance Python linter and formatter |
| **Type Checking** | mypy | Static type checker for Python |
| **Testing** | pytest | Python testing framework |
| **Containerization** | Docker | Application containerization |
| **Orchestration** | Docker Compose | Multi-container orchestration and management |

## API Documentation

The project leverages FastAPI's automatic OpenAPI specification generation, providing the following API documentation capabilities:

| Documentation Type | Access URL | Description |
|--------------------|------------|-------------|
| Swagger Interactive Docs | http://localhost:8000/docs | Online debugging, parameter input, request sending |
| ReDoc Read-Only Docs | http://localhost:8000/redoc | Well-structured read-only API documentation |
| OpenAPI JSON Spec | http://localhost:8000/openapi.json | Standard OpenAPI 3.x spec file, importable into Postman and similar tools |

### API Endpoint List

User-facing endpoints are prefixed with `/api/v1` (JWT auth). Open platform endpoints are prefixed with `/api/open/v1` (AppId/AppKey auth).

**Health Check (Public):**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check (database/cache connectivity) |
| GET | `/api/v1/version` | Version information |

**Authentication (login/refresh public, others require authentication):**

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/auth/login` | Username/email + password login | Public |
| POST | `/api/v1/auth/refresh` | Refresh token | Public |
| GET | `/api/v1/auth/me` | Current logged-in user info | Required |
| POST | `/api/v1/auth/logout` | Logout (clear Redis login state) | Required |

**User Management (Requires Authentication):**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/users` | Create user |
| GET | `/api/v1/users` | User list (pagination/keyword/status filter) |
| GET | `/api/v1/users/{id}` | User detail |
| GET | `/api/v1/users/export` | Export users (CSV) |
| POST | `/api/v1/users/{id}/update` | Update user |
| POST | `/api/v1/users/{id}/delete` | Delete user (soft delete) |

**Role Management (Requires Authentication):**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/roles` | Create role |
| GET | `/api/v1/roles` | Role list (pagination/keyword/type/status filter) |
| GET | `/api/v1/roles/{id}` | Role detail |
| POST | `/api/v1/roles/{id}/update` | Update role |
| POST | `/api/v1/roles/{id}/delete` | Delete role (soft delete) |
| GET | `/api/v1/roles/{id}/permissions` | Role permission list (with permission details) |
| POST | `/api/v1/roles/{id}/permissions` | Bind permissions to role |
| POST | `/api/v1/roles/{id}/permissions/{pid}/unbind` | Unbind role permission |

**Business Audit Logs (Requires Authentication):**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/audit/logs` | Query business changes by entity, action, operator, and time range |

**File Upload (Requires Authentication):**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/files/upload` | Upload file; writes to cloud storage when configured, falls back to local storage |

**Login Logs (Requires Authentication):**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/login-logs` | Login log list (pagination/user/result/type/time-range filter) |
| GET | `/api/v1/login-logs/{id}` | Login log detail |

**Notification Management (Requires Authentication):**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/notifications/send` | Manually send notification |
| GET | `/api/v1/notifications` | Notification record list (pagination/event/channel/status filter) |
| GET | `/api/v1/notifications/stats` | Notification delivery statistics |

**System Alerts:**

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/alerts` | Send alert to specified recipients (for external Webhook calls) | Public |
| POST | `/api/v1/alerts/broadcast` | Broadcast alert to all active users | Required |

**System Maintenance Notifications (Requires Authentication):**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/maintenance/notify` | Send maintenance notification to all users |

**Open Platform App Management (Requires super_admin):**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/admin/apps` | Create open platform app (returns AppId + AppKey, Key shown once) |
| GET | `/api/v1/admin/apps` | App list |
| GET | `/api/v1/admin/apps/{id}` | App detail |
| PATCH | `/api/v1/admin/apps/{id}` | Update app (scopes/rate limit/auth mode/status) |
| POST | `/api/v1/admin/apps/{id}/rotate-key` | Rotate AppKey (old key invalidated immediately) |
| DELETE | `/api/v1/admin/apps/{id}` | Delete app (soft delete) |

**Open Platform Endpoints (AppId/AppKey Auth):**

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/open/v1/health` | Open platform health check | Public |
| GET | `/api/open/v1/version` | Open platform version info | Public |
| GET | `/api/open/v1/me` | Current calling app info | AppId/AppKey required |
| GET | `/api/open/v1/ping` | Connectivity test | AppId/AppKey + `ping:read` scope |

### Open Platform Authentication

Open Platform APIs are designed for external service-to-service integration, fully independent from user-facing JWT auth:

- **Auth method**: Send `X-App-Id` and `X-App-Key` headers (plaintext mode to start)
- **Upgrade path**: Each AppKey is stored as both SHA256 hash (fast lookup) and Fernet-encrypted plaintext (for future HMAC mode). The `auth_mode` column (plain/hmac/both) allows switching without key rotation
- **Scope-based authorization**: Each app has a scope list (e.g. `ping:read`); endpoints declare requirements via `require_app_scope("ping:read")`
- **Swagger testing**: Enter `OpenAppId` and `OpenAppKey` in the Authorize dialog to test open platform endpoints

### Access Control

**User-facing (`/api/v1/...`):**
- All endpoints (except login, refresh, health check) require `Authorization: Bearer <token>`
- Endpoints declare requirements via `require_user_role("role_code")` or `require_user_permission("perm_code")`
- The `super_admin` role bypasses role restrictions by default
- Permission evaluation results are cached in Redis by user and permission code

**Open Platform (`/api/open/v1/...`):**
- Requires `X-App-Id` and `X-App-Key` headers (plaintext mode)
- Endpoints declare required scopes via `require_app_scope("scope:name")`
- HMAC signature mode can be enabled per-app (`auth_mode=hmac`), requiring additional Timestamp / Nonce / Signature headers

## Notification System Configuration

The project includes a built-in event-driven multi-channel notification subsystem, supporting Email, DingTalk, Feishu, and SMS channels. Notification events are automatically triggered during business operations (password changes, failed logins, permission changes, etc.), and can also be manually sent or broadcast via API.

### Architecture Overview

```
Business Services (user_service / auth_service / ...)
    ↓ dispatch_for_user(user_id, event_type, variables)
Notification Dispatcher (NotificationDispatcher)
    ↓ Query routing table → Determine channels
    ↓ Query user_notification_configs → Determine recipients
    ↓ Render templates → Call Provider to send
    ↓ Persist records → Write failures to Redis retry queue
Notification Channel Providers
    ├─ EmailProvider (reuses SMTP configuration)
    ├─ DingTalkProvider (Work notification per-user / Webhook group chat)
    ├─ FeishuProvider (App message per-user / Webhook group chat)
    └─ SmsProvider (skeleton, pending integration)
```

### Notification Event Types

| Event | Trigger | Default Channels |
|-------|---------|-----------------|
| `user.password_changed` | User changes password | email |
| `user.profile_updated` | User profile updated | email |
| `user.status_changed` | User status changed | email, dingtalk |
| `user.login_failed` | Consecutive login failures ≥3 | email, dingtalk |
| `role.assigned` | Role assigned | email, dingtalk |
| `permission.granted` | Permission granted | email |
| `permission.revoked` | Permission revoked | email, dingtalk |
| `system.alert` | System alert (health check failure/API call) | email, dingtalk, feishu |
| `system.maintenance` | System maintenance notification | email, dingtalk, feishu |

### Channel Configuration

**DingTalk/Feishu support dual modes:**
- **Work Notification/App Message** (recommended): Configure application credentials for per-user precise delivery
- **Webhook Group Chat** (fallback): Only configure Webhook URL, sends to the group where the bot is located

```yaml
notification:
  enabled: true
  retry_interval_seconds: 60
  alert_email: "ops@example.com"     # Health check alert email
  # DingTalk
  dingtalk_app_key: ""               # Enterprise app AppKey (work notification mode)
  dingtalk_app_secret: ""
  dingtalk_agent_id: ""
  dingtalk_webhook: ""               # Group robot Webhook (group chat mode)
  dingtalk_secret: ""
  # Feishu
  feishu_app_id: ""                  # Custom app AppId (app message mode)
  feishu_app_secret: ""
  feishu_webhook: ""                 # Group robot Webhook (group chat mode)
  feishu_secret: ""
```

> DingTalk/Feishu per-user delivery requires binding users with channel recipients in the `user_notification_configs` table (DingTalk stores `userid`, Feishu stores `open_id`).

## Storage Configuration

The project provides a unified storage abstraction layer. Switch storage backends by changing the `storage.provider` configuration — zero changes to business code.

### Local File Storage

Suitable for development environments and small-scale deployments. Files are stored on the server's local filesystem.

```yaml
storage:
  provider: "local"
  local:
    base_dir: "static"
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `provider` | Storage backend identifier | `local` |
| `local.base_dir` | Local storage root directory | `static` |

### S3-Compatible Object Storage

Suitable for production environments. Supports Qiniu Kodo, AWS S3, MinIO, and other S3-compatible services.

```yaml
storage:
  provider: "s3"
  s3:
    endpoint_url: "https://s3.cn-south-1.qiniucs.com"
    access_key: "<your-access-key>"
    secret_key: "<your-secret-key>"
    bucket: "x-hanjiang"
    region: "cn-south-1"
    prefix: "uploads"
    public_url: ""
    use_ssl: true
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `provider` | Storage backend identifier | `s3` |
| `s3.endpoint_url` | S3-compatible service endpoint | — |
| `s3.access_key` | Access key | — |
| `s3.secret_key` | Secret key | — |
| `s3.bucket` | Bucket name | `x-hanjiang` |
| `s3.region` | Storage region | `cn-south-1` |
| `s3.prefix` | Object key prefix | `uploads` |
| `s3.public_url` | Public access domain (optional, with protocol) | — |
| `s3.use_ssl` | Enable SSL | `true` |

> **Note**: In production, inject `access_key` and `secret_key` via environment variables to avoid committing secrets. The example endpoint `https://s3.cn-south-1.qiniucs.com` is for Qiniu Kodo's South China region. Replace it with the appropriate endpoint for other S3-compatible services.

## License

This project is open-sourced under the [MIT License](LICENSE).

## References

| Technology | Official Documentation |
|------------|----------------------|
| Python | https://www.python.org/ |
| FastAPI | https://fastapi.tiangolo.com/ |
| Pydantic | https://docs.pydantic.dev/ |
| SQLAlchemy | https://docs.sqlalchemy.org/ |
| Alembic | https://alembic.sqlalchemy.org/ |
| Redis | https://redis.io/docs/ |
| uv | https://docs.astral.sh/uv/ |
| Uvicorn | https://www.uvicorn.org/ |
| Gunicorn | https://gunicorn.org/ |
| Docker | https://docs.docker.com/ |
| Docker Compose | https://docs.docker.com/compose/ |
| Loguru | https://loguru.readthedocs.io/ |
| pytest | https://docs.pytest.org/ |
| Ruff | https://docs.astral.sh/ruff/ |

## Contact

- **Author**: John Young（夜雨诗来）
- **Email**: [john.young@foxmail.com](mailto:john.young@foxmail.com)
- **Gitee**: https://gitee.com/yeyushilai
- **GitHub**: https://github.com/yeyushilai
- **Project**: https://github.com/cross-lang/x-HanJiang
