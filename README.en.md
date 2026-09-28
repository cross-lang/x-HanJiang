[中文](README.md) | English

# HanJiang — Full-Stack Rapid Development Platform

## Project Introduction

HanJiang is a full-stack rapid development platform built on FastAPI + Vue 3 + TypeScript, deeply packaging the common capabilities of enterprise-grade web applications so developers can focus on business logic.

**Key Features:**

- Frontend-backend separation: FastAPI + Vue 3 + Element Plus, full-stack TypeScript
- Built-in JWT auth + RBAC + audit logging + login logs, out-of-the-box
- Auto-register permissions via `@permission` decorator, synced to DB on startup
- Open platform HanJiang-1 HMAC signature, supporting plain and signed modes, with built-in app management (AppId/AppKey lifecycle, scope authorization, key rotation)
- Event-driven multi-channel notification system (station / email / DingTalk / Feishu / SMS) with per-user preferences and automatic retry
- System notice broadcast: publish normal / maintenance notices to all users, station message broadcast + multi-channel push per user configs
- Layered architecture: API routes → Business logic → Data access
- Production-grade security (constant-time comparison, replay protection, password hashing, email verification code for sensitive operations)
- Built-in dashboard (user/role/app stats + login trend + audit trend + ECharts)
- File management (local / S3-compatible storage), global search, profile center, system alerts, announcement management (homepage board / banner)
- Great developer experience (Swagger docs, Alembic migrations, unified error handling, GitHub Actions CI)

**Use Cases:**

- Enterprise internal admin systems
- SaaS product backend foundation
- Open platform / API gateway
- Full-stack project boilerplate

## Quick Start

### Backend

```bash
cd server
uv run x-HanJiang
```

See [server/README.md](server/README.md) for details.

### Frontend

```bash
cd web/admin
npm install
npm run dev
```

Open http://localhost:5173. See [web/admin/README.md](web/admin/README.md) for details.

## Project Structure

```
x-HanJiang/
├── server/                  # Backend (FastAPI)
│   ├── src/
│   │   ├── api/              # Routes (v1 user + open/v1 open platform)
│   │   ├── constants/        # Constants & enums (ModuleCode, BaseEnum)
│   │   ├── core/             # Core (config/middleware/exceptions/security)
│   │   ├── infras/           # Infrastructure (database/cache/storage/notification channels)
│   │   ├── models/           # SQLAlchemy data models (models/entities)
│   │   ├── notification/     # Notification subsystem (dispatcher/templates/retry)
│   │   ├── repositories/     # Data access layer
│   │   ├── scheduling/       # Scheduled tasks (notification retry worker)
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic layer
│   │   ├── utils/            # Utilities
│   │   └── main.py           # Application entry
│   ├── alembic/              # Database migrations
│   ├── config/               # Configuration
│   ├── docs/                 # Project docs (DDL SQL, Postman collection)
│   ├── examples/             # Usage examples
│   ├── logs/                 # Log output
│   ├── scripts/              # Engineering scripts
│   ├── static/               # Local file storage directory
│   ├── tests/                # Unit tests
│   └── pyproject.toml
├── web/                      # Frontend
│   ├── admin/                # Admin dashboard (Vue3 + TS + Element Plus + ECharts)
│   └── open/                 # Open platform portal (TBD)
├── docker-compose.yml        # Docker orchestration
└── README.md
```

## System Architecture

### Layered Architecture

```mermaid
graph TB
    subgraph Frontend
        A[Admin Dashboard Vue3]
        B[Open Platform Portal]
    end

    subgraph Backend
        C[API Routes]
        D[Business Logic]
        E[Data Access]
    end

    subgraph Infrastructure
        F[(MySQL)]
        G[(Redis)]
        H[(Local/S3 Storage)]
    end

    A -->|HTTP /api/v1| C
    B -->|HTTP /api/open/v1| C
    C --> D
    D --> E
    E --> F
    D --> G
    D --> H
```

### Core Flow: User Login

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant S as Service
    participant DB as Database

    U->>F: Enter username & password
    F->>A: POST /auth/login
    A->>S: Verify credentials
    S->>DB: Query user
    DB-->>S: User record
    S->>S: Verify password hash
    S->>DB: Write login log
    S-->>A: Generate JWT token
    A-->>F: Return access_token
    F->>F: Store in localStorage
```

### Permission Auto-Registration

```mermaid
flowchart LR
    A[@permission Decorator on Routes] --> B[collect_permissions_from_app on Startup]
    B --> C[Scan app.routes for Permission Metadata]
    C --> D[Upsert to permissions Table]
    D --> E[In DB but not in Routes → is_deprecated=True]
```

### Notification Dispatch Flow

```mermaid
flowchart TD
    A[Business Event<br/>e.g. user.password_changed] --> B[Notification Dispatcher]
    B --> C[Resolve User Preferences & Recipients]
    C --> D[Station]
    C --> E[Email]
    C --> F[DingTalk]
    C --> G[Feishu]
    D --> H[Write Notification Record]
    E --> H
    F --> H
    G --> H
    H --> I{Sent Successfully?}
    I -->|No| J[Redis Retry Queue]
    J --> K[Retry Worker]
    K --> D
    I -->|Yes| L[Done]
```

## Tech Stack

| Category | Technology |
|---|---|
| **Backend Language** | Python 3.11+ |
| **Backend Framework** | FastAPI |
| **ORM** | SQLAlchemy 2.0 |
| **Migration** | Alembic |
| **Frontend Framework** | Vue 3 + TypeScript |
| **Build Tool** | Vite 6 |
| **UI Library** | Element Plus |
| **State Management** | Pinia |
| **Charts** | ECharts 6 + vue-echarts |
| **Database** | MySQL |
| **Cache** | Redis |
| **Logging** | Loguru |
| **Auth** | JWT + HMAC Signature |
| **Package Manager** | uv |
| **Deployment** | Docker / docker-compose |

## API Documentation

Once the backend is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Core Endpoints

| Module | Endpoint | Description |
|---|---|---|
| Auth | `POST /api/v1/auth/login` | User login |
| Auth | `POST /api/v1/auth/refresh` | Refresh tokens |
| Auth | `POST /api/v1/auth/logout` | Logout |
| Profile | `GET /api/v1/profile/me` | Current user info |
| Profile | `GET /api/v1/profile/menus` | Current user menu tree |
| Profile | `POST /api/v1/profile/change-password` | Change password (verification code) |
| Users | `GET /api/v1/users` | User list (multi-role) |
| Users | `POST /api/v1/users` | Create user |
| Users | `GET /api/v1/users/export` | Export users (CSV) |
| Users | `POST /api/v1/users/import` | Bulk import users (CSV) |
| Users | `POST /api/v1/users/{id}/update` | Update user |
| Roles | `GET /api/v1/roles` | Role list |
| Roles | `GET /api/v1/roles/{id}/permissions` | Role permissions |
| Roles | `POST /api/v1/roles/{id}/permissions` | Bind permission |
| Permissions | `GET /api/v1/permissions` | Permission list |
| Audit Logs | `GET /api/v1/audit/logs` | Business audit log list |
| Login Logs | `GET /api/v1/audit/login-logs` | Login log list |
| Files | `POST /api/v1/files/upload` | Upload file |
| Files | `GET /api/v1/files` | File list |
| Notifications | `POST /api/v1/notifications/publish` | Publish system notification (normal / maintenance, broadcast to all users) |
| Notifications | `GET /api/v1/notifications/published` | System notice list |
| Notifications | `GET /api/v1/notifications` | Notification list |
| Station | `GET /api/v1/station/messages` | My message list |
| Station | `GET /api/v1/station/messages/unread-count` | Unread message count |
| Announcements | `GET /api/v1/announcements/active` | Active homepage announcements |
| Announcements | `POST /api/v1/announcements` | Create announcement (draft) |
| Announcements | `POST /api/v1/announcements/{id}/publish` | Publish announcement |
| Announcements | `POST /api/v1/announcements/{id}/unpublish` | Unpublish announcement |
| Dashboard | `GET /api/v1/dashboard/stats` | Dashboard stats |
| Global Search | `GET /api/v1/search` | Global search (users/roles/permissions/apps/files) |
| Open API Apps | `POST /api/v1/admin/apps` | Create open app (returns AppId + AppKey) |
| Open API Apps | `POST /api/v1/admin/apps/{app_id}/rotate-key` | Rotate AppKey |
| Open API | `GET /api/open/v1/me` | Current app info |
| Open API | `GET /api/open/v1/users` | Open platform user query |

### Authorization

- **User endpoints**: JWT Bearer Token + `@permission` decorator auto-registration + role/permission check
- **Open platform endpoints**: AppId + AppKey (plain) or HanJiang-1 HMAC signature, scope-based access control

## Storage

### Database

- **Type**: MySQL 8.0+
- **Config**: via `.env` (`MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, etc.)
- **Migrations**: Alembic

### Cache

- **Type**: Redis
- **Usage**: rate limiting, login state cache, notification retry queue
- **Config**: via `.env` (`REDIS_HOST`, `REDIS_PORT`)

### File Storage

Two modes, switch via `STORAGE_PROVIDER` in `.env`:

| Mode | Config | Use Case |
|---|---|---|
| `local` | `STORAGE_LOCAL_BASE_DIR=static` | Local dev, small deployments |
| `s3` | `STORAGE_S3_ENDPOINT_URL` etc. | Production, object storage (Qiniu/AWS S3/MinIO) |

## License

This project is licensed under the [MIT License](LICENSE).

## References

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [uv Docs](https://docs.astral.sh/uv/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [Vue 3 Docs](https://vuejs.org/)
- [Vite Docs](https://vitejs.dev/)
- [Element Plus Docs](https://element-plus.org/)
- [ECharts Docs](https://echarts.apache.org/)
- [Loguru Docs](https://loguru.readthedocs.io/)
- [Docker Docs](https://docs.docker.com/)

## Contact

- **Author**: John Young (夜雨诗来)
- **Email**: john.young@foxmail.com
- **Gitee**: https://gitee.com/cross-lang/x-HanJiang
- **GitHub**: https://github.com/cross-lang/x-HanJiang
- **Project**: https://github.com/cross-lang/x-HanJiang
