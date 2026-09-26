[中文](README.md) | English

# HanJiang — Full-Stack Rapid Development Platform

## Project Introduction

HanJiang is a full-stack rapid development platform built on FastAPI + Vue 3 + TypeScript, deeply packaging the common capabilities of enterprise-grade web applications so developers can focus on business logic.

**Key Features:**
- Frontend-backend separation: FastAPI + Vue 3 + Element Plus, full-stack TypeScript
- Built-in JWT auth + RBAC + audit logging, out-of-the-box
- Open platform HanJiang-1 HMAC signature, supporting plain and signed modes
- Layered architecture: API routes → Business logic → Data access
- Production-grade security (constant-time comparison, replay protection, password hashing)
- Great developer experience (Swagger docs, Alembic migrations, unified error handling)

**Use Cases:**
- Enterprise internal admin systems
- SaaS product backend foundation
- Open platform / API service gateway
- Full-stack project boilerplate

## Quick Start

### Backend

```bash
cd server
.venv\Scripts\python.exe main.py
```

See [server/README.md](server/README.md) for details.

### Frontend

```bash
cd web\admin
npm install
npm run dev
```

Open http://localhost:5173. See [web/admin/README.md](web/admin/README.md) for details.

## Project Structure

```
x-HanJiang/
├── server/                  # Backend (FastAPI)
│   ├── src/
│   │   ├── api/              # Routes
│   │   ├── constants/        # Constants & enums
│   │   ├── core/             # Core (config/middleware/exceptions)
│   │   ├── infras/           # Infrastructure (database)
│   │   ├── models/           # Data models
│   │   ├── repositories/     # Data access layer
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic layer
│   │   └── utils/             # Utilities
│   ├── alembic/              # Database migrations
│   ├── config/               # Configuration
│   ├── main.py               # Application entry
│   └── pyproject.toml
├── web/                      # Frontend
│   ├── admin/                # Admin dashboard (Vue3 + Element Plus)
│   └── open/                 # Open platform portal (TBD)
├── docker-compose.yml
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
    end

    A -->|HTTP /api/v1| C
    B -->|HTTP /api/open/v1| C
    C --> D
    D --> E
    E --> F
    D --> G
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
    S-->>A: Generate JWT token
    A-->>F: Return access_token
    F->>F: Store in localStorage
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
| **Database** | MySQL |
| **Cache** | Redis |
| **Logging** | Loguru |
| **Auth** | JWT + HMAC Signature |
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
| Auth | `GET /api/v1/auth/me` | Current user info |
| Users | `GET /api/v1/users` | User list |
| Users | `POST /api/v1/users` | Create user |
| Roles | `GET /api/v1/roles` | Role list |
| Open API | `GET /api/open/v1/users` | Open platform user query |
| Open API | `GET /api/open/v1/apps/me` | Current app info |

### Authorization

- **User endpoints**: JWT Bearer Token + role/permission check
- **Open platform endpoints**: AppId + AppKey (plain) or HanJiang-1 HMAC signature

## Storage

### Database

- **Type**: MySQL 8.0+
- **Config**: via `.env` (`MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, etc.)
- **Migrations**: Alembic

### Cache

- **Type**: Redis
- **Usage**: rate limiting, session cache
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
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [Vue 3 Docs](https://vuejs.org/)
- [Vite Docs](https://vitejs.dev/)
- [Element Plus Docs](https://element-plus.org/)
- [Loguru Docs](https://loguru.readthedocs.io/)
- [Docker Docs](https://docs.docker.com/)

## Contact

- **Author**: John Young (夜雨诗来)
- **Email**: john.young@foxmail.com
- **Gitee**: https://gitee.com/yeyushilai
- **GitHub**: https://github.com/yeyushilai
