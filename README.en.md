# HanJiang — Full-Stack Rapid Development Platform

[中文](README.md) | English

An **out-of-the-box** enterprise full-stack platform built on **FastAPI + Vue 3**. It encapsulates the common capabilities of backend admin systems (auth, permissions, audit, notifications, AI, open platform) so developers can focus on their business.

<!-- TOC -->
- [Why HanJiang?](#why-hanjiang)
- [Core Capabilities](#core-capabilities)
- [UI Preview](#ui-preview)
- [Quick Start](#quick-start)
  - [Backend](#backend)
  - [Frontend](#frontend)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [API Docs](#api-docs)
- [License](#license)
- [Contact](#contact)
<!-- /TOC -->

## Why HanJiang?

| What you need | HanJiang | Bare FastAPI DIY | Generic front-end template |
| --- | --- | --- | --- |
| Out-of-the-box admin system | ✅ | ⚠️ Build it yourself | ❌ UI only |
| Async high-performance FastAPI backend | ✅ | ✅ But you build it | ❌ No backend |
| RBAC menu/button permissions + auto-registration | ✅ | ⚠️ Build it yourself | ❌ |
| AI assistant (SSE streaming / tool orchestration) | ✅ | ❌ | ❌ |
| Open platform signature auth (HMAC / anti-replay) | ✅ | ❌ | ❌ |
| Multi-channel notifications (in-app/email/DingTalk/Feishu) | ✅ | ❌ | ❌ |
| Audit logs + login logs | ✅ | ❌ | ❌ |
| One-click Docker deployment | ✅ | ⚠️ | ⚠️ |

## Core Capabilities

- **Auth & Permissions**: JWT auth + RBAC permission model, declarative registration via the `@permission` decorator, auto-scanned and synced to the database at startup
- **AI Assistant**: SSE streaming chat (token / navigate / done events), conversation management, memory compaction, knowledge-base retrieval and tool orchestration; the `openai_compat` protocol works with DeepSeek, Volcano Ark, Qwen, vLLM and more
- **Open Platform**: HanJiang-1 HMAC signature auth (plain/signature dual mode), AppId/AppKey lifecycle management, scope authorization, key rotation
- **Notification System**: event-driven multi-channel delivery (in-app/email/DingTalk/Feishu), template variable interpolation, per-user preferences, automatic retry on failure
- **Observability**: business audit logs, login logs, operation-log trends, system alerts
- **Engineering**: layered architecture (API → Service → Repository), unified exception handling, Swagger docs, Alembic migrations, GitHub Actions CI

## UI Preview

![Login](./me/login.png)

![Admin](./me/admin.png) ![System](./me/admin_system.png)
![AI Assistant](./me/admin_assistant.png) ![Open Apps](./me/admin_openapp.png)

## Quick Start

### Backend

```bash
cd server
uv run x-HanJiang --reload
```

See [server/README.md](server/README.md) for configuration.

### Frontend

```bash
cd web/admin
npm install
npm run dev
```

Open <http://localhost:5173>. See [web/admin/README.md](web/admin/README.md).

## Project Structure

```
x-HanJiang/
├── server/            # Backend (FastAPI)
│   ├── src/
│   │   ├── api/       # Routes (v1 user-facing + open/v1 open platform)
│   │   ├── assistant/ # AI assistant (dialog orchestration/memory/retrieval/tools)
│   │   ├── constants/ # Constants and enums (ModuleCode, BaseEnum)
│   │   ├── core/      # Config/middleware/exceptions/security
│   │   ├── infras/    # Infrastructure (database/cache/storage/notifications/LLM)
│   │   ├── models/    # SQLAlchemy data models
│   │   ├── notification/  # Notification subsystem (dispatcher/templates/retry)
│   │   ├── repositories/  # Data access layer
│   │   ├── scheduling/    # Scheduled tasks (notification retry worker)
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── services/  # Business logic layer
│   │   ├── utils/     # Utility functions
│   │   └── main.py    # Application entry
│   ├── alembic/       # Database migrations
│   ├── tests/         # Unit tests
│   └── pyproject.toml
├── web/
│   ├── admin/         # Admin console (Vue3 + TS + Element Plus)
│   └── open/          # Open platform portal (WIP)
├── docker-compose.yml # Docker orchestration
└── README.md
```

## Tech Stack

| Category | Technology |
| --- | --- |
| Backend | Python 3.11+ / FastAPI / SQLAlchemy 2.0 / Alembic |
| Frontend | Vue 3 + TypeScript / Vite / Element Plus / Pinia / ECharts |
| Storage | MySQL / Redis |
| Auth | JWT + HMAC signature |
| AI | OpenAI SDK (openai_compat protocol) |
| Tooling | uv / Ruff / mypy / pytest / Loguru |
| Deployment | Docker / docker-compose |

## API Docs

After starting the backend:

- **Swagger UI**: <http://localhost:8000/docs>
- **ReDoc**: <http://localhost:8000/redoc>
- **OpenAPI JSON**: <http://localhost:8000/openapi.json>

## License

This project is released under the [MIT License](LICENSE).

## Contact

- **Author**: John Young
- **Email**: <john.young@foxmail.com>
- **GitHub**: <https://github.com/cross-lang/x-HanJiang>