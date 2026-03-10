import os


class Config:
    """SMTP 与发件人配置，均来自环境变量。"""

    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = os.getenv("SMTP_PORT")
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        # 发件人地址：优先 DEFAULT_SENDER，否则 EMAIL_FROM（兼容 .env 里常见命名）
        self.default_sender = os.getenv("DEFAULT_SENDER") or os.getenv("EMAIL_FROM")

    def validate(self):
        if not all(
            [self.smtp_server, self.smtp_port, self.smtp_user, self.smtp_password, self.default_sender]
        ):
            raise ValueError(
                "Missing one or more required environment variables: "
                "SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, "
                "DEFAULT_SENDER or EMAIL_FROM."
            )
