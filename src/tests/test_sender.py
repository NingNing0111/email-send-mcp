import unittest

from email_service.fastmcp_client import FastMCPClient
from email_service.sender import EmailSender
from email_service.utils import mock_recipient_tool, mock_template_tool, recipient_resolver_from_tool, template_renderer_from_tool


class DummyClient(FastMCPClient):
    def __init__(self):
        super().__init__()
        self.sent = []

    def send(self, email_data: dict) -> bool:
        # record and return True to simulate success
        self.sent.append(email_data)
        return True


class TestEmailSender(unittest.TestCase):

    def setUp(self):
        self.client = DummyClient()
        # use the wrapper functions to convert the mock tools into resolvers
        self.recipient_resolver = lambda tid, ctx: recipient_resolver_from_tool(mock_recipient_tool, tid, ctx)
        self.template_renderer = lambda tid, ctx: template_renderer_from_tool(mock_template_tool, tid, ctx)
        self.sender = EmailSender(self.client, recipient_resolver=self.recipient_resolver, template_renderer=self.template_renderer)

    def test_send_template_email(self):
        summary = self.sender.send_template_email("welcome", {"title": "Hi", "message": "Test"})
        # mock_recipient_tool returns two recipients; both should be in sent
        self.assertEqual(len(summary["sent"]), 2)
        self.assertEqual(len(self.client.sent), 2)


if __name__ == '__main__':
    unittest.main()