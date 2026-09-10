<p align="center">
  <h1 align="center">HanJiang (寒江)</h1>
  <p align="center">
    <strong>A Production-Grade FastAPI Python Web Project</strong>
  </p>
  <p align="center">
    <a href="README.md">中文</a> | English
  </p>
</p>

---

## Introduction

HanJiang (寒江) is a production-grade Python Web project built on top of the FastAPI framework, following industry best engineering practices. It provides a standardized, modular, highly extensible, and maintainable backend service infrastructure, ready to use out of the box for rapid development of enterprise-grade RESTful APIs with multi-environment deployment.

The project currently implements core business capabilities including user management, role management, permission management, authentication, and login logging.

## Key Features

- **Standard 3-Layer Architecture** — API Layer → Service Layer → Repository Layer, with strictly unidirectional dependencies
- **Dependency Injection Container** — DI capabilities with auto-wiring, singleton/transient lifecycle, and decorator registration
- **Dual Configuration System** — Supports both `.env` environment variables and `config.yaml` files with automatic multi-environment switching
- **Standardized Response Format** — All endpoints return a unified `{ code, message, data, timestamp, request_id }` structure
- **Global Exception Handling** — Custom exception hierarchy (Business 4xx / System 5xx) with global exception middleware
- **Unified Authentication** — All business endpoints (except login, refresh, and health check) require `Authorization: Bearer <token>`; missing or invalid tokens return 401
- **Structured Logging** — Based on loguru with request ID tracking, dual file+console output, and log rotation
- **Idempotent Seed Data** — On startup, automatically detects and creates the built-in super-admin role and `superadmin` user (skips if already present)
- **Docker Deployment** — Standard Dockerfile and docker-compose.yml with Gunicorn + Uvicorn high-performance deployment
- **Database Support** — Integrated SQLAlchemy ORM, supports MySQL, ready to use

## Project Structure

```
x-HanJiang/
├── config/                  # Configuration files
│   └── config.yaml          # Main configuration (database/redis/auth/server)
├── docs/                    # Project documentation
│   └── hanjiang.sql         # Database schema (5 tables)
├── src/                     # Core business code
│   ├── api/                 # API layer (routes, DI dependencies)
│   │   ├── v1/              # Versioned routes
│   │   │   ├── health.py    # Health check / version
│   │   │   ├── user.py      # User management
│   │   │   ├── auth.py      # Auth (login/refresh/me/logout)
│   │   │   ├── role.py      # Role management + role permission query
│   │   │   └── login_log.py # Login logs
│   │   ├── dependencies.py  # DI dependency functions (service/repository/current_user)
│   │   ├── response.py      # Unified response wrapper
│   │   └── router.py        # Route aggregation
│   ├── constants/           # Business constants and enums
│   ├── core/                # Core support (config, logger, exceptions, DI, middleware, tokens, seed)
│   ├── infras/              # Infrastructure layer (database, cache)
│   ├── models/              # Data models
│   │   └── entities/        # SQLAlchemy ORM entities (5 tables)
│   ├── schemas/             # API request/response DTOs (Pydantic BaseModel)
│   ├── repositories/        # Data access layer (user/role/permission/role_permission/login_log)
│   ├── services/            # Business logic layer (user/auth/role/permission/login_log)
│   └── main.py              # Application entry point
├── tests/                   # Test code
├── Dockerfile               # Docker image build
├── docker-compose.yml       # Docker orchestration
├── pyproject.toml          # Project dependencies and metadata
└── LICENSE                 # MIT License
```

## Data Model

The database consists of 5 tables (defined in `docs/hanjiang.sql`):

| Table | Description | Key Fields |
|-------|-------------|------------|
| `users` | User table | id, username, email, password_hash, phone, avatar_url, role_id, status(active/inactive/locked), last_login_at, last_login_ip, created_at, updated_at, deleted_at |
| `roles` | Role table | id, role_name, role_code, description, role_type(system/custom), status(enabled/disabled), created_at, updated_at, deleted_at |
| `permissions` | Permission table | id, perm_code, perm_name, module, operation(view/create/edit/delete/export/import), description, sort_order |
| `role_permissions` | Role-permission association | id, role_id, permission_id |
| `login_logs` | Login log table | id, user_id, login_type(password/sso), ip_address, status(success/failed), created_at |

All business tables support soft deletion (non-null `deleted_at` indicates deletion).

## System Architecture

### Layered Architecture

```
┌──────────────────────────────────────┐
│              Client                   │
└──────────────┬───────────────────────┘
               │ HTTP Request (Bearer Token)
               ▼
┌──────────────────────────────────────┐
│          Middleware Layer             │
│   Request ID │ CORS │ Rate Limit     │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│   Auth Guard (Depends get_current_user)│  ← Unified Authentication
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│           API Layer (api/)           │
│   health │ user │ auth │ role │ login-log │
│         Pydantic validation          │
└──────────────┬───────────────────────┘
               │ API → Service
               ▼
┌──────────────────────────────────────┐
│        Service Layer (services/)      │
│    Business rules │ validation │ orchestration │
└──────────────┬───────────────────────┘
               │ Service → Repository
               ▼
┌──────────────────────────────────────┐
│      Repository Layer (repositories/)  │
│         CRUD │ query │ mapping        │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│      MySQL + Redis (token/login state) │
└──────────────────────────────────────┘
```

## API Reference

All business endpoints are prefixed with `/api/v1`.

### Health Check (Public)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check (DB/cache connectivity) |
| GET | `/api/v1/version` | Version info |

### Authentication (login/refresh public, others authenticated)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/auth/login` | Username/email + password login | Public |
| POST | `/api/v1/auth/refresh` | Refresh token | Public |
| GET | `/api/v1/auth/me` | Current user info | Required |
| POST | `/api/v1/auth/logout` | Logout (clear Redis login state) | Required |

### User Management (Authenticated)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/users` | Create user |
| GET | `/api/v1/users` | User list (pagination/keyword/status filter) |
| GET | `/api/v1/users/{id}` | User detail |
| GET | `/api/v1/users/export` | Export users (CSV) |
| POST | `/api/v1/users/{id}/update` | Update user |
| POST | `/api/v1/users/{id}/delete` | Delete user (soft delete) |

### Role Management (Authenticated)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/roles` | Create role |
| GET | `/api/v1/roles` | Role list (pagination/keyword/type/status filter) |
| GET | `/api/v1/roles/{id}` | Role detail |
| POST | `/api/v1/roles/{id}/update` | Update role |
| POST | `/api/v1/roles/{id}/delete` | Delete role (soft delete) |
| GET | `/api/v1/roles/{id}/permissions` | Role permission list (with permission details) |

### Login Logs (Authenticated)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/login-logs` | Login log list (pagination/user/status/type/time-range filter) |
| GET | `/api/v1/login-logs/{id}` | Login log detail |

## Quick Start

### Requirements

| Tool | Version |
|------|---------|
| Python | >= 3.11 |
| uv | latest (recommended) |

**Windows:**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Linux / macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Clone

```bash
git clone <your-repo-url>
cd x-HanJiang
```

### Install Dependencies

```bash
uv sync
# Production only
uv sync --no-dev
```

### Configuration

Edit `config/config.yaml` to configure the database, Redis, and auth secret:

```yaml
database:
  url: "mysql://<user>:<password>@<host>:<port>/<db>"
  pool_size: 5

redis:
  url: "redis://:<password>@<host>:<port>/<db>"

auth:
  secret_key: "<random string, at least 32 chars>"
  algorithm: "HS256"
  access_token_expire_minutes: 10080
  refresh_token_expire_days: 30
```

> **Production**: Override sensitive config via environment variables (e.g. `AUTH_SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`) rather than committing secrets. Precedence: **env vars > env-specific YAML > default YAML > code defaults**.
>
> **Note**: If the Redis password contains special characters like `@` or `:`, percent-encode them in the `redis://` URL (e.g. `@` → `%40`).

### Run

#### Local Development (hot reload)

```bash
uv run uvicorn src.main:app --reload
```

#### Docker

```bash
docker-compose up --build
```

After startup:
- Swagger docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

### Seed Data

On startup (`lifespan`), the application automatically detects and initializes built-in seed data, **idempotently** (skips if already present):

1. **Super-admin role** — `role_code=super_admin`, `role_type=system`
2. **Super-admin user** — username `superadmin`, password `admin@123456`, bound to the role above

> After first deployment, log in directly with `superadmin / admin@123456`. Change this password in production.

## API Usage Examples

### 1. Login to obtain a token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "superadmin", "password": "admin@123456"}'
```

### 2. Access a protected endpoint with the token

```bash
curl http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer <access_token>"
```

### 3. Without token (returns 401)

```bash
curl http://localhost:8000/api/v1/users
# → 401 {"code": 401, "message": "Authentication failed: please login first", ...}
```

## Unified Response Format

All responses are wrapped in the following structure:

```json
{
  "code": 200,
  "message": "success",
  "data": { },
  "timestamp": "2026-09-10T14:00:00+00:00",
  "request_id": "uuid"
}
```

## Common Commands

```bash
uv run pytest tests/ -v --cov=src --cov-report=term-missing
uv run ruff format src/ tests/
uv run ruff check src/ tests/
uv run mypy src/
```

## Tech Stack

| Category | Technology |
|----------|------------|
| Web Framework | FastAPI |
| ASGI Server | Uvicorn |
| Process Manager | Gunicorn |
| ORM | SQLAlchemy |
| DB Driver | PyMySQL |
| Cache | Redis |
| Validation | Pydantic v2 |
| Config | pydantic-settings |
| Logging | Loguru |
| Rate Limit | SlowAPI |
| Package Manager | uv |
| Containerization | Docker |
| Testing | pytest |

## Known Limitations

- **Auth granularity**: Currently only validates "whether logged in", without role/permission-level access control (RBAC). Add `require_role` / `require_permission` guards for admin-only endpoints.
- **Audit capability**: Login logs (`login_logs`) record login behavior, but a business-operation audit module is not yet present.

## License

This project is open-sourced under the [MIT License](LICENSE).

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
