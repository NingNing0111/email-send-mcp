# Mail MCP Server

基于 FastMCP 的邮件发送能力，以 **MCP Streamable HTTP** 传输启动，供支持该协议的客户端通过 HTTP 连接（无需 stdio 子进程）。

## Features

- **传输**：`streamable-http`（FastMCP 内与 `http` / `sse` 并列的 transport）
- **MCP 工具**：`send_email`、`send_template_email`
- **监听**：`MCP_HOST` / `MCP_PORT`（默认 `0.0.0.0:8000`）
- Docker 镜像非 root 运行，依赖层与代码层分离缓存

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Project Structure

```
mail-mcp-server
├── src
│   ├── mcp_server.py          # MCP 入口（streamable-http）
│   ├── main.py
│   ├── email_service/
│   └── tests/
├── pyproject.toml
├── uv.lock
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env.example
└── README.md
```

## 启动

```bash
cd mail-mcp-server
cp .env.example .env
uv sync
uv run python src/mcp_server.py
```

**Streamable HTTP** 端点：`http://<MCP_HOST>:<MCP_PORT>/mcp`（例如 `http://127.0.0.1:8000/mcp`）。

### .env 为何未生效？

见 `.env` 与 `load_env` 说明：需在项目根放置 `.env`，修改后**重启 MCP 进程**。

### 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| `MCP_HOST` / `MCP_PORT` | 监听 | `0.0.0.0` / `8000` |
| `SMTP_*` / `DEFAULT_SENDER` / `EMAIL_FROM` | 发信 | 见 `.env.example` |
| `SMTP_SSL` / `SMTP_USE_STARTTLS` | 465 / 587 | 见 `fastmcp_client.py` 与 README 163 小节 |

### 163 `Connection unexpectedly closed`

| 问题 | 处理 |
|------|------|
| 用户名非完整邮箱 | 使用 `user@163.com` |
| FROM 写成授权码 | FROM 必须是邮箱；授权码只在 `SMTP_PASSWORD` |
| 587 被断开 | 使用 `SMTP_PORT=465` + `SMTP_SSL=true`，或依赖自动走 465 |

### 一次性演示（非 MCP）

```bash
uv run python src/main.py
```

## Docker

### 镜像特点

| 项 | 说明 |
|----|------|
| 分层 | 先 `pyproject.toml` + `uv.lock` + `uv sync`，再 `COPY src/`，改代码不重建依赖层 |
| 环境 | `UV_LINK_MODE=copy`、`--compile-bytecode`，减少告警并略加快启动 |
| 安全 | `USER app`（uid 1000），非 root |
| 布局 | `PYTHONPATH=/app/src`，`CMD` 为 `python -m mcp_server` |

### 构建

```bash
# 默认 bookworm + Python 3.10
docker build -t mail-mcp-server:latest .

# 加快构建（跳过 apt upgrade）
docker build --build-arg SKIP_APT_UPGRADE=1 -t mail-mcp-server:latest .

# 指定 Python 小版本
docker build --build-arg PYTHON_VERSION=3.11 -t mail-mcp-server:py311 .
```

### 运行

```bash
docker run --rm -p 8000:8000 --env-file .env mail-mcp-server:latest
```

### Compose

服务名 **`mail-mcp`**（原 `email-sender` 已更名）：

```bash
docker compose up --build -d
```

- 端口：宿主机 `${MCP_PORT:-8000}` → 容器 `8000`（容器内仍监听 8000，改端口请同时设置环境变量并映射）。
- **healthcheck**：对容器内 `127.0.0.1:8000` 做 TCP 探测（Streamable HTTP 未必有 GET `/`）。
- 重启策略：`unless-stopped`。

## Development

```bash
uv sync --group dev
uv run pytest
uv lock
```

## License

MIT
