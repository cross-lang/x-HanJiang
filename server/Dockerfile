# 汉江（HanJiang）Dockerfile
# 多阶段构建：builder（安装依赖）+ runtime（运行应用）

# ==========================================
# Stage 1: Builder - 安装依赖
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装 uv 包管理器（固定版本确保构建可复现）
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /usr/local/bin/uv

# 复制依赖声明文件（含 lock 以支持 --frozen）
COPY pyproject.toml uv.lock ./

# 使用清华 PyPI 镜像加速国内构建，加大超时避免网络抖动
ENV UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple/ \
    UV_HTTP_TIMEOUT=300

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
# HOME 显式覆盖为容器内可写目录：防止宿主机（如 Windows）的 HOME 环境
# 变量泄漏进容器，导致 gunicorn 26 的控制 socket 写到非法路径而报
# "Control server error: Permission denied"。
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app" \
    APP_ENV=production \
    GUNICORN_WORKERS=4 \
    HOME=/tmp

# 复制应用源代码
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser config*.yaml ./
# pyproject.toml 用于 _find_project_root() 定位项目根目录
COPY --chown=appuser:appuser pyproject.toml ./

# 创建运行期目录（logs 日志、statics 本地文件存储根目录）并授权给 appuser
# 说明：LocalStorage 初始化时会 mkdir base_dir（默认 statics），缺目录且 /app 归 root 所有会抛 PermissionError
RUN mkdir -p /app/logs /app/statics && chown -R appuser:appuser /app/logs /app/statics

USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查（带超时，避免挂起）
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request, socket; socket.setdefaulttimeout(3); urllib.request.urlopen('http://localhost:8000/api/admin/v1/health')" || exit 1

# 使用 Gunicorn + Uvicorn Worker 启动（shell form 支持环境变量替换）
CMD gunicorn src.main:app \
    -w ${GUNICORN_WORKERS:-4} \
    -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile - \
    --timeout 60 \
    --graceful-timeout 30 \
    --keep-alive 5
