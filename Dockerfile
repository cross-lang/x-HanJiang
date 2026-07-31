# 寒江（HanJiang）Dockerfile
# 多阶段构建：builder（安装依赖）+ runtime（运行应用）

# ==========================================
# Stage 1: Builder - 安装依赖
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装 uv 包管理器
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 复制依赖声明文件（含 lock 以支持 --frozen）
COPY pyproject.toml uv.lock ./

# 仅安装生产依赖，且基于 lock 文件确保可复现
RUN uv sync --frozen --no-dev --no-install-project

# ==========================================
# Stage 2: Runtime - 运行应用
# ==========================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# 创建非 root 用户运行应用
RUN groupadd --system --gid 1001 appuser \
    && useradd --system --uid 1001 --gid appuser --home /app appuser

# 从 builder 阶段复制已安装的依赖
COPY --from=builder /app/.venv /app/.venv

# 设置 Python 路径使用虚拟环境
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production

# 复制应用源代码
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser config/ ./config/

# 创建 logs 目录并授权给 appuser
RUN mkdir -p /app/logs && chown -R appuser:appuser /app/logs

USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查（带超时，避免挂起）
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request, socket; socket.setdefaulttimeout(3); urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

# 使用 Gunicorn + Uvicorn Worker 启动
CMD ["gunicorn", "src.main:app", \
     "-w", "4", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--timeout", "60", \
     "--graceful-timeout", "30"]