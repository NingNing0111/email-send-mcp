import logging

from email_service.load_env import load_dotenv_from_project

load_dotenv_from_project()

from email_service.config import Config
from email_service.fastmcp_client import FastMCPClient
from email_service.sender import EmailSender
from email_service.utils import recipient_resolver_from_tool, template_renderer_from_tool, mock_recipient_tool, mock_template_tool


def main():
    logging.basicConfig(level=logging.INFO)
    config = Config()

    client = FastMCPClient(
        smtp_server=config.smtp_server,
        port=int(config.smtp_port) if config.smtp_port else None,
        username=config.smtp_user,
        password=config.smtp_password,
        from_email=config.default_sender,
    )

    # Use the "tool" wrappers. In production, pass real tool callables
    recipient_tool = lambda template_id, context: recipient_resolver_from_tool(mock_recipient_tool)
    template_tool = lambda template_id, context: template_renderer_from_tool(mock_template_tool, template_id, context)

    sender = EmailSender(client, recipient_resolver=recipient_tool, template_renderer=template_tool)

    summary = sender.send_template_email("welcome", {"title": "Welcome!", "message": "Hello from MCP"})
    logging.info("Send summary: %s", summary)


if __name__ == "__main__":
    main()