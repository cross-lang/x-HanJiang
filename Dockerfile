# 寒江（HanJiang）Dockerfile
# 多阶段构建：builder（安装依赖）+ runtime（运行应用）

# ==========================================
# Stage 1: Builder - 安装依赖
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装 uv 包管理器
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 复制依赖声明文件
COPY pyproject.toml ./

# 安装生产依赖（不含开发依赖）
RUN uv sync --frozen --no-dev --no-install-project

# ==========================================
# Stage 2: Runtime - 运行应用
# ==========================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# 从 builder 阶段复制已安装的依赖
COPY --from=builder /app/.venv /app/.venv

# 设置 Python 路径使用虚拟环境
ENV PATH="/app/.venv/bin:$PATH"
ENV APP_ENV=production

# 复制应用源代码
COPY src/ ./src/
COPY config/ ./config/

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

# 使用 Gunicorn + Uvicorn Worker 启动
CMD ["gunicorn", "src.main:app", \
     "-w", "4", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
