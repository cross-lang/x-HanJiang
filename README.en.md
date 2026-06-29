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
- **Standardized Response Format** — Unified JSON responses with code, message, data, timestamp, and request ID
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
│   └── architecture.md      # Architecture documentation
├── examples/                # Usage examples
│   ├── basic_usage.py       # Basic usage
│   ├── custom_api.py        # Custom API example
│   └── di_usage.py          # Dependency injection example
├── scripts/                 # Deployment and utility scripts
│   ├── start_dev.sh/bat     # Development startup
│   ├── start_prod.sh/bat    # Production startup
│   └── run_tests.sh/bat     # Test runner
├── src/                     # Core business code
│   ├── api/                 # API route layer
│   ├── common/              # Shared components (constants, response, base models)
│   ├── constants/           # Business constants
│   ├── core/                # Core infrastructure (config, logger, exceptions, DI, middleware)
│   ├── models/              # Data models (Pydantic DTOs)
│   ├── repository/          # Data access layer
│   ├── service/             # Business logic layer
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
│        Service Layer (service/)      │
│    Business Rules │ Validation       │
└──────────────┬───────────────────────┘
               │ Service → Repository
               ▼
┌──────────────────────────────────────┐
│      Repository Layer (repository/)  │
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
Standard Response (success/error/paginated)
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
# Linux / macOS
bash scripts/start_dev.sh

# Windows
scripts\start_dev.bat

# Or use uvicorn directly
uv run uvicorn src.main:app --reload
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
