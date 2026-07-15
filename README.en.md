<p align="center">
  <h1 align="center">X-HanJiang</h1>
  <p align="center">
    <strong>A Production-Grade FastAPI Project Template</strong>
  </p>
  <p align="center">
    English | <a href="README.md">中文</a>
  </p>
</p>

---

## Introduction

x-HanJiang is a production-grade Python Web project template built on top of the FastAPI framework, following industry best engineering practices. It provides a standardized, modular, highly extensible, and maintainable backend service infrastructure. Ready to use out of the box, it supports rapid development of enterprise-grade RESTful API services with multi-environment deployment.

**Use Cases:** Small to medium enterprise backend services, API gateways, microservice scaffolding, rapid prototyping.

## Key Features

- **Standard 3-Layer Architecture** — API Layer → Service Layer → Repository Layer, with strictly unidirectional dependencies
- **Dependency Injection Container** — Go Wire-like DI capabilities with auto-wiring, singleton/transient lifecycle, decorator registration
- **Dual Configuration System** — Supports both `.env` environment variables and `config.yaml` files with automatic multi-environment switching
- **Standardized Response Format** — Pydantic `response_model` for response structure, returning model instances directly
- **Global Exception Handling** — Custom exception hierarchy (Business 4xx / System 5xx) with global exception middleware
- **Structured Logging** — Based on loguru with request ID tracking, dual file+console output, and log rotation
- **Docker Deployment** — Standard Dockerfile and docker-compose.yml with Gunicorn + Uvicorn high-performance deployment
- **Full Engineering** — pyproject.toml unified management, test coverage, CI/CD ready

## Project Structure

```
x-HanJiang/
├── config/                  # Configuration files
│   ├── config.yaml          # Default configuration
│   ├── config.dev.yaml      # Development overrides
│   ├── config.test.yaml     # Testing overrides
│   ├── config.prod.yaml     # Production overrides
│   └── .env.example         # Environment variable template
├── docs/                    # Project documentation
│   ├── architecture.md      # Architecture documentation
│   └── DATABASE.md          # Database configuration guide
├── examples/                # Usage examples
│   ├── basic_usage.py       # Basic usage
│   ├── custom_api.py        # Custom API example
│   └── di_usage.py          # Dependency injection example
├── migrations/              # Database migration files
│   └── 001_create_user_table.sql
├── src/                     # Core business code
│   ├── api/                 # API route layer (routes, dependencies)
│   ├── constants/           # Business constants
│   ├── core/                # Core infrastructure (config, logger, exceptions, DI, middleware)
│   ├── infra/               # Infrastructure layer (database, cache, HTTP client)
│   ├── models/              # Data models (pure table mappings, no business logic)
│   │   └── entities/        # SQLAlchemy ORM entity models
│   ├── schemas/             # API request/response DTOs (Pydantic BaseModel)
│   ├── repositories/        # Data access layer
│   ├── services/            # Business logic layer
│   ├── utils/               # Utility functions
│   └── main.py              # Application entry point
├── tests/                   # Test code
├── Dockerfile               # Docker image build
├── docker-compose.yml       # Docker orchestration
├── pyproject.toml           # Project dependencies and metadata
└── LICENSE                  # MIT License
```

## System Architecture

### Layer Architecture Diagram

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
│         Pydantic Validation          │
└──────────────┬───────────────────────┘
               │ API → Service
               ▼
┌──────────────────────────────────────┐
│        Service Layer (services/)      │
│    Business Rules │ Validation       │
└──────────────┬───────────────────────┘
               │ Service → Repository
               ▼
┌──────────────────────────────────────┐
│      Repository Layer (repositories/)  │
│         CRUD │ Query │ Mapping       │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│      External Storage / Database     │
└──────────────────────────────────────┘
```

### Request Processing Flow

```
Client Request
    │
    ▼
RequestIDMiddleware (Generate UUID)
    │
    ▼
CORS Middleware (Cross-origin handling)
    │
    ▼
Router (Route matching)
    │
    ▼
Dependencies (Dependency injection)
    │
    ▼
API Endpoint (Parameter validation)
    │
    ▼
Service (Business logic)
    │
    ▼
Repository (Data access)
    │
    ▼
Pydantic Response (response_model serialization)
    │
    ▼
Client Response (with X-Request-ID)
```

## Quick Start

### Prerequisites

| Tool | Version | Installation |
|------|---------|--------------|
| Python | >= 3.11 | [python.org](https://www.python.org/downloads/) |
| uv | latest | [docs.astral.sh/uv](https://docs.astral.sh/uv/) |

**Windows:**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Linux / macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Clone the Project

```bash
git clone https://gitee.com/cross-lang/x-HanJiang.git
cd x-HanJiang
```

### Install Dependencies

```bash
# Install all dependencies (production + development)
uv sync

# Install production dependencies only
uv sync --no-dev
```

### Configuration

1. Copy the environment variable template:

```bash
cp config/.env.example config/.env
```

2. Edit `config/.env` and `config/config.yaml` as needed

3. Configuration priority: **Environment Variables > Environment-specific YAML > Default YAML > Code Defaults**

Key configuration items:

| Setting | Env Variable | Default | Description |
|---------|-------------|---------|-------------|
| Environment | APP_ENV | development | development / testing / production |
| Host | SERVER_HOST | 0.0.0.0 | Server bind address |
| Port | SERVER_PORT | 8000 | Server bind port |
| Debug | SERVER_DEBUG | true | Enable debug mode |
| Log Level | LOGGING_LEVEL | INFO | DEBUG / INFO / WARNING / ERROR |
| Secret Key | AUTH_SECRET_KEY | change-me-in-production | JWT signing key |

### Start the Server

**Option 1: Local Development (with hot reload)**

```bash
# Using uv (recommended)
uv run uvicorn src.main:app --reload

# Or using Python module mode
uv run python -m src.main

# Without uv (using pip)
python -m uvicorn src.main:app --reload
python -m src.main
```

**Option 2: Docker**

```bash
# Build and start
docker-compose up --build

# Run in background
docker-compose up -d --build
```

After starting, visit:
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/v1/health
- Version Info: http://localhost:8000/api/v1/version
- User List: http://localhost:8000/api/v1/users

### Common Commands

```bash
# Run tests with coverage
uv run pytest tests/ -v --cov=src --cov-report=term-missing

# Code formatting
uv run ruff format src/ tests/

# Code linting
uv run ruff check src/ tests/

# Type checking
uv run mypy src/

# Alternative commands without uv
python -m pytest tests/ -v
python -m ruff format src/ tests/
python -m ruff check src/ tests/
python -m mypy src/
```

## Tech Stack

| Category | Technology | Description |
|----------|-----------|-------------|
| Web Framework | FastAPI | High-performance async Python web framework |
| ASGI Server | Uvicorn | Lightweight ASGI server |
| Process Manager | Gunicorn | Production-grade WSGI/ASGI process manager |
| Data Validation | Pydantic v2 | Data modeling and validation framework |
| Configuration | pydantic-settings | Pydantic-based configuration management |
| Logging | Loguru | Modern Python logging library |
| Rate Limiting | SlowAPI | Request rate limiting middleware |
| Package Manager | uv | High-speed Python package manager |
| Containerization | Docker | Application containerization |
| Testing | pytest | Python testing framework |

## License

This project is licensed under the [MIT License](LICENSE).

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [Python Documentation](https://docs.python.org/3.11/)

## Contact

**John Young** — john.young@foxmail.com
