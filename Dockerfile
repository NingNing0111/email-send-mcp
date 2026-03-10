# syntax=docker/dockerfile:1
# -----------------------------------------------------------------------------
# Mail MCP Server — 优化点：
# 1. 依赖层与代码层分离，仅改 src 时不重装依赖
# 2. UV_LINK_MODE=copy 避免跨文件系统 hardlink 警告/异常
# 3. --compile-bytecode 容器冷启动略快
# 4. 非 root 运行
# -----------------------------------------------------------------------------

ARG PYTHON_VERSION=3.10
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

# SKIP_APT_UPGRADE=1 可加快构建（生产可去掉该 ARG 或设为 0 做 apt upgrade）
ARG SKIP_APT_UPGRADE=0
RUN apt-get update \
    && if [ "$SKIP_APT_UPGRADE" != "1" ]; then apt-get upgrade -y --no-install-recommends; fi \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# 仅复制 uv，不装 apt 版 curl；多阶段可进一步瘦身，此处单层保持简单可靠
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# ------------ 依赖层：仅当 pyproject.toml / uv.lock 变更时重建 ------------
COPY pyproject.toml uv.lock ./

# 需要 BuildKit 时可改为缓存 uv：RUN --mount=type=cache,target=/root/.cache/uv uv sync ...
RUN uv sync --frozen --no-dev --no-install-project --compile-bytecode

# ------------ 应用层：仅代码变更 ------------
COPY src/ ./src/

# 运行时与构建时布局一致：工作目录为 /app，Python 路径指向 src
ENV PYTHONPATH=/app/src \
    PATH="/app/.venv/bin:$PATH" \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000

# 非 root
RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin app \
    && chown -R app:app /app
USER app
WORKDIR /app

EXPOSE 8000

LABEL org.opencontainers.image.title="mail-mcp-server" \
      org.opencontainers.image.description="Mail MCP Server (FastMCP streamable-http)"

# 从 src 包运行，与本地 uv run python src/mcp_server.py 一致
CMD ["python", "-m", "mcp_server"]
