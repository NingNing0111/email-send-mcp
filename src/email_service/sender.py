import logging
from typing import Callable, Iterable, Tuple

from .utils import validate_email


class EmailSender:
    """EmailSender which delegates recipient resolution and template
    rendering to injected tool-callables.

    Constructor args:
    - fastmcp_client: client with a send(email_data: dict) -> bool method
    - recipient_resolver: callable(template_id, context) -> iterable of emails
    - template_renderer: callable(template_id, context) -> (subject, body)
    """

    def __init__(self, fastmcp_client, recipient_resolver: Callable = None, template_renderer: Callable = None):
        self.fastmcp_client = fastmcp_client
        self.recipient_resolver = recipient_resolver
        self.template_renderer = template_renderer
        self.logger = logging.getLogger(self.__class__.__name__)

    def send_email(self, to_address: str, subject: str, body: str) -> bool:
        """Send a single email to `to_address` with subject and body."""
        if not validate_email(to_address):
            self.logger.warning("Invalid recipient email: %s", to_address)
            return False
        email_data = {
            "to": to_address,
            "subject": subject,
            "body": body,
        }
        return self.fastmcp_client.send(email_data)

    def send_template_email(self, template_id: str, context: dict = None) -> dict:
        """Resolve recipients and template via the injected tools then send.

        Returns a summary dict: {"sent": [...], "failed": [...]}.
        """
        context = context or {}
        if not self.recipient_resolver or not self.template_renderer:
            raise RuntimeError("recipient_resolver and template_renderer must be provided")

        recipients = list(self.recipient_resolver(template_id, context))
        subject, body = self.template_renderer(template_id, context)

        sent = []
        failed = []
        for r in recipients:
            if not validate_email(r):
                self.logger.warning("Skipping invalid email: %s", r)
                failed.append({"to": r, "reason": "invalid_email"})
                continue
            ok = self.send_email(r, subject, body)
            if ok:
                sent.append(r)
            else:
                failed.append({"to": r, "reason": "send_failed"})

        return {"sent": sent, "failed": failed}