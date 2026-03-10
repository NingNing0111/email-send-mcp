"""
Mail MCP Server — 使用 MCP Streamable HTTP 传输启动，供支持该协议的客户端连接。

运行：
  uv run python src/mcp_server.py

环境变量：
  MCP_HOST  监听地址，默认 0.0.0.0
  MCP_PORT  监听端口，默认 8000
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

# 必须在 Config / FastMCPClient 之前加载 .env（否则 os.getenv 读不到）
from email_service.load_env import load_dotenv_from_project

load_dotenv_from_project()

from fastmcp import FastMCP

from email_service.config import Config
from email_service.fastmcp_client import FastMCPClient
from email_service.sender import EmailSender
from email_service.utils import (
    mock_recipient_tool,
    mock_template_tool,
    recipient_resolver_from_tool,
    template_renderer_from_tool,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 与 main.py 相同的客户端与 Sender 组装方式
_config = Config()
_client = FastMCPClient(
    smtp_server=_config.smtp_server,
    port=int(_config.smtp_port) if _config.smtp_port else None,
    username=_config.smtp_user,
    password=_config.smtp_password,
    from_email=_config.default_sender,
)
# 与 main.py 一致：演示用 mock；生产可换成真实 tool
_recipient_tool = lambda template_id, context: recipient_resolver_from_tool(
    mock_recipient_tool
)
_template_tool = lambda template_id, context: template_renderer_from_tool(
    mock_template_tool, template_id, context
)
_sender = EmailSender(
    _client,
    recipient_resolver=_recipient_tool,
    template_renderer=_template_tool,
)

mcp = FastMCP(
    name="mail-mcp-server",
    instructions=(
        "邮件发送 MCP：支持按地址发送纯文本邮件，以及按模板 ID + 上下文发送。"
        "SMTP 配置来自环境变量 SMTP_SERVER / SMTP_PORT / SMTP_USER / SMTP_PASSWORD。"
    ),
    
)


@mcp.tool()
def send_email(to_address: str, subject: str, body: str) -> dict[str, Any]:
    """向单个邮箱发送一封邮件（主题 + 正文）。"""
    ok = _sender.send_email(to_address, subject, body)
    return {"success": ok, "to": to_address, "subject": subject}



def main() -> None:
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    # Streamable HTTP（MCP 规范中的 HTTP 流式传输）
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
    )


if __name__ == "__main__":
    main()
