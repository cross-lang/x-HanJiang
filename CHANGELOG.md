# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-09-20

### Added

- Standard three-layer architecture (API → Service → Repository) with strictly unidirectional dependencies
- Dependency injection container with auto-wiring, singleton/transient lifecycle, and decorator registration
- Dual configuration system supporting `.env` environment variables and `config.yaml` files with automatic multi-environment switching
- Unified response format: `{ code, message, data, timestamp, request_id }`
- Global exception handling with custom exception hierarchy (Business 4xx / System 5xx)
- Unified Bearer Token authentication with JWT (access token + refresh token)
- Interface-level RBAC access control via `require_role` / `require_permission` guards with Redis caching
- Structured logging based on loguru with request ID tracking, dual file+console output, and log rotation
- Business audit logging for write operations with operator, timestamp, IP, and before/after data
- File storage abstraction layer supporting local filesystem and S3-compatible object storage (Qiniu Kodo / AWS S3 / MinIO)
- MFA/TOTP basic capability
- Idempotent seed data auto-initialization (superadmin role and user)
- Docker deployment with multi-stage Dockerfile and docker-compose.yml (App + MySQL + Redis)
- Alembic database migration support
- API modules: Health Check, Authentication, User Management, Role Management, Audit Logs, File Upload, Login Logs
- Comprehensive test suite with pytest