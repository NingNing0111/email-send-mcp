"""
SMTP 邮件客户端：使用 smtplib 真实发送邮件。

支持：
- 端口 465：SMTP_SSL（163 等推荐，避免 587 STARTTLS 被断开）
- 端口 587：SMTP + STARTTLS；若出现 Connection unexpectedly closed 可自动改用 465 重试
- UTF-8 主题与正文（含中文）
- 用户名/密码含非 ASCII 时自动改用 AUTH PLAIN(UTF-8)，避免 smtplib 内部 ascii 编码报错

163 邮箱注意：
- SMTP_USER 必须为完整邮箱，如 user@163.com（不能只有用户名）
- SMTP_PASSWORD 为「客户端授权码」，不是登录密码
- EMAIL_FROM / DEFAULT_SENDER 必须为完整邮箱，与发信账号一致
"""
from __future__ import annotations

import base64
import logging
import os
import smtplib
import ssl
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any

from .utils import validate_email


def _as_int(value: Any, default: int | None = None) -> int | None:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return default


def _is_163_server(host: str | None) -> bool:
    if not host:
        return False
    h = host.lower()
    return "163.com" in h or "126.com" in h or "yeah.net" in h


def _ensure_full_email(addr: str, smtp_server: str | None) -> str:
    """无 @ 时按 SMTP 主机补全域名，避免网易系因账号格式不对直接断连接。"""
    addr = (addr or "").strip()
    if "@" in addr:
        return addr
    if not smtp_server:
        return addr
    h = smtp_server.lower()
    if "126.com" in h:
        return f"{addr}@126.com"
    if "yeah.net" in h:
        return f"{addr}@yeah.net"
    if "163.com" in h or _is_163_server(smtp_server):
        return f"{addr}@163.com"
    return addr


class FastMCPClient:
    """通过 SMTP 发送邮件。email_data 需包含 to、subject、body；可选 from 覆盖默认发件人。"""

    def __init__(
        self,
        smtp_server: str | None = None,
        port: int | str | None = None,
        username: str | None = None,
        password: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
        timeout: int = 60,
    ):
        self.smtp_server = (smtp_server or "").strip() or None
        self.port = _as_int(port, 587)
        self.username = username
        self.password = password
        self.from_email = (from_email or username or "").strip() or None
        self.from_name = (from_name or "").strip() or None
        self.timeout = timeout
        self.logger = logging.getLogger(self.__class__.__name__)

    def connect(self) -> bool:
        self.logger.debug("SMTP configured server=%s port=%s", self.smtp_server, self.port)
        return bool(self.smtp_server and self.port)

    def disconnect(self) -> bool:
        return True

    def _ssl_context(self) -> ssl.SSLContext:
        return ssl.create_default_context()

    def _smtp_login_plain_utf8(self, server: smtplib.SMTP, user: str, password: str) -> None:
        """
        smtplib.login() 在 AUTH 流程里会对 initial_response 做 .encode('ascii')，
        用户名或密码含非 ASCII（如中文、全角符号）会触发 UnicodeEncodeError。
        AUTH PLAIN 允许把「\0user\0password」按 UTF-8 编码后再 Base64，服务端常见可接受。
        """
        server.ehlo_or_helo_if_needed()
        # PLAIN: base64(NUL authz NUL user NUL password)，authz 置空
        auth_bytes = ("\0" + user + "\0" + password).encode("utf-8")
        auth_b64 = base64.b64encode(auth_bytes).decode("ascii")
        code, resp = server.docmd("AUTH", "PLAIN " + auth_b64)
        if code != 235:
            raise smtplib.SMTPAuthenticationError(code, resp)

    def _smtp_login(self, server: smtplib.SMTP) -> None:
        """在凭据含非 ASCII 时改用 PLAIN+UTF-8，避免 smtplib 内部 ascii 编码失败。"""
        user = self.username or ""
        password = self.password or ""
        try:
            user.encode("ascii")
            password.encode("ascii")
        except UnicodeEncodeError:
            self.logger.debug("SMTP 凭据含非 ASCII，使用 AUTH PLAIN (UTF-8)")
            self._smtp_login_plain_utf8(server, user, password)
            return
        try:
            server.login(user, password)
        except UnicodeEncodeError:
            # 极少数环境下 login 仍会走 ascii 编码，统一回退 PLAIN UTF-8
            self.logger.debug("login 仍触发 UnicodeEncodeError，回退 AUTH PLAIN (UTF-8)")
            self._smtp_login_plain_utf8(server, user, password)

    def _send_with_ssl(self, port: int, from_addr: str, to_list: list[str], msg_str: str) -> None:
        ctx = self._ssl_context()
        with smtplib.SMTP_SSL(
            self.smtp_server, port, timeout=self.timeout, context=ctx
        ) as server:
            if os.getenv("SMTP_DEBUG", "").lower() in ("1", "true", "yes"):
                server.set_debuglevel(1)
            self._smtp_login(server)
            server.sendmail(from_addr, to_list, msg_str)

    def _send_with_starttls(self, from_addr: str, to_list: list[str], msg_str: str) -> None:
        with smtplib.SMTP(self.smtp_server, self.port, timeout=self.timeout) as server:
            if os.getenv("SMTP_DEBUG", "").lower() in ("1", "true", "yes"):
                server.set_debuglevel(1)
            server.ehlo()
            if server.has_extn("STARTTLS"):
                server.starttls(context=self._ssl_context())
                server.ehlo()
            self._smtp_login(server)
            server.sendmail(from_addr, to_list, msg_str)

    def send(self, email_data: dict) -> bool:
        if not self.smtp_server or not self.port:
            self.logger.error("SMTP_SERVER / SMTP_PORT 未配置，无法发送")
            return False
        if not self.username or not self.password:
            self.logger.error("SMTP_USER / SMTP_PASSWORD 未配置，无法发送")
            return False

        # 163/126 等：登录名必须是完整邮箱
        self.username = _ensure_full_email(self.username, self.smtp_server)

        to_raw = email_data.get("to")
        subject = email_data.get("subject") or ""
        body = email_data.get("body") or ""
        from_override = email_data.get("from")

        if to_raw is None:
            self.logger.error("email_data 缺少 to")
            return False

        if isinstance(to_raw, (list, tuple)):
            to_list = [str(t).strip() for t in to_raw if str(t).strip()]
        else:
            to_list = [str(to_raw).strip()]
        if not to_list:
            self.logger.error("收件人为空")
            return False

        from_addr = (from_override or self.from_email or self.username or "").strip()
        from_addr = _ensure_full_email(from_addr, self.smtp_server)

        if not validate_email(from_addr):
            self.logger.error(
                "发件人不是合法邮箱: %r。请把 EMAIL_FROM / DEFAULT_SENDER 设为完整地址，例如 user@163.com（不要用授权码填在 FROM）",
                from_addr[:20] + "..." if len(from_addr) > 20 else from_addr,
            )
            return False

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = (
            formataddr((self.from_name, from_addr)) if self.from_name else from_addr
        )
        msg["To"] = ", ".join(to_list)
        msg_str = msg.as_string()

        use_ssl = self.port == 465 or os.getenv("SMTP_SSL", "").lower() in ("1", "true", "yes")
        fallback_465 = os.getenv("SMTP_FALLBACK_465", "1").lower() not in ("0", "false", "no")
        force_starttls = os.getenv("SMTP_USE_STARTTLS", "").lower() in ("1", "true", "yes")

        # 网易系在 587 上常被直接断连接；未强制 STARTTLS 时直接用 465，避免先失败再重试和 WARNING
        ssl_port = self.port  # 465 或显式 SMTP_SSL 且端口与 SSL 一致时使用
        if (
            not use_ssl
            and self.port == 587
            and _is_163_server(self.smtp_server)
            and not force_starttls
        ):
            use_ssl = True
            ssl_port = 465
            self.logger.debug("网易 SMTP 直接使用 465 SSL，跳过 587")

        try:
            if use_ssl:
                self._send_with_ssl(ssl_port, from_addr, to_list, msg_str)
            else:
                try:
                    self._send_with_starttls(from_addr, to_list, msg_str)
                except (smtplib.SMTPServerDisconnected, ConnectionResetError, OSError) as e:
                    err_s = str(e).lower()
                    if fallback_465 and _is_163_server(self.smtp_server) and self.port != 465:
                        if "closed" in err_s or "reset" in err_s or "10054" in err_s:
                            self.logger.warning(
                                "端口 %s 连接被服务端关闭，改用 465 SSL 重试（163 常见）", self.port
                            )
                            self._send_with_ssl(465, from_addr, to_list, msg_str)
                        else:
                            raise
                    else:
                        raise

            self.logger.info("SMTP 发送成功 to=%s subject=%s", to_list, subject)
            return True

        except smtplib.SMTPAuthenticationError as e:
            self.logger.error("SMTP 认证失败: %s（163 请确认使用客户端授权码，且 SMTP_USER 为完整邮箱）", e)
            return False
        except smtplib.SMTPException as e:
            self.logger.error("SMTP 错误: %s", e)
            if _is_163_server(self.smtp_server) and not use_ssl:
                self.logger.error(
                    "提示：163 优先使用 SMTP_PORT=465 并设置 SMTP_SSL=true，或保持当前逻辑会自动尝试 465"
                )
            return False
        except OSError as e:
            self.logger.error("网络连接失败: %s", e)
            return False
        except Exception as e:
            self.logger.exception("发送邮件异常: %s", e)
            return False
