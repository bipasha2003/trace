"""
TRACE - Outgoing mail (DEVELOPMENT.md Phase 8 step 1, PROJECT.md §11.8)

The SMTP server comes from Admin → Configuration (`system_settings` category
`mail`), falling back to `.env` (`SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM` — Mailpit
locally). So an Admin can move TRACE to a real mail server without a redeploy:
every send resolves the settings afresh.

    config = await mail_config(db)     # async — reads the database
    send(config, to, subject, text)     # sync — smtplib, from the Celery worker
"""

import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.system_settings import resolve_setting

SECURITY = ("none", "starttls", "ssl")


@dataclass
class MailConfig:
    host: str
    port: int
    from_address: str
    username: str = ""
    password: str = ""
    security: str = "none"


async def mail_config(db: AsyncSession) -> MailConfig:
    port = await resolve_setting(db, "mail", "port")
    security = await resolve_setting(db, "mail", "security")
    return MailConfig(
        host=await resolve_setting(db, "mail", "host"),
        port=int(port) if port.isdigit() else 25,
        from_address=await resolve_setting(db, "mail", "from_address"),
        username=await resolve_setting(db, "mail", "username"),
        password=await resolve_setting(db, "mail", "password"),
        security=security if security in SECURITY else "none",
    )


def _connect(config: MailConfig, timeout: int = 10) -> smtplib.SMTP:
    if config.security == "ssl":
        smtp = smtplib.SMTP_SSL(config.host, config.port, timeout=timeout)
    else:
        smtp = smtplib.SMTP(config.host, config.port, timeout=timeout)
        if config.security == "starttls":
            smtp.starttls()
    if config.username:
        smtp.login(config.username, config.password)
    return smtp


def render(subject: str, body: str) -> tuple[str, str]:
    """Plain text and a minimal HTML version; the body is user text, so it is escaped."""
    html = (
        '<html><body style="font-family: sans-serif; line-height: 1.6;">'
        f"<h3>{escape(subject)}</h3><p>{escape(body).replace(chr(10), '<br>')}</p>"
        '<p style="color: #888; font-size: 12px;">Sent by TRACE</p></body></html>'
    )
    return body, html


def send(config: MailConfig, to: str, subject: str, body: str) -> None:
    text, html = render(subject, body)
    msg = MIMEMultipart("alternative")
    msg["From"], msg["To"], msg["Subject"] = config.from_address, to, subject
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))
    with _connect(config) as smtp:
        smtp.sendmail(config.from_address, [to], msg.as_string())


def check(config: MailConfig) -> list[dict]:
    """The Configuration connection test: reach the server, then log in if a username is set."""
    if not config.host:
        return [{"name": "Server", "ok": False, "detail": "No SMTP host is set"}]
    checks = []
    try:
        with _connect(config, timeout=8) as smtp:
            code, _ = smtp.noop()
            checks.append({"name": "Server", "ok": code == 250,
                           "detail": f"{config.host}:{config.port} answered ({config.security})"})
            if config.username:
                checks.append({"name": "Login", "ok": True, "detail": f"Signed in as {config.username}"})
    except smtplib.SMTPAuthenticationError:
        checks += [{"name": "Server", "ok": True, "detail": f"{config.host}:{config.port} answered"},
                   {"name": "Login", "ok": False, "detail": "The username or password was refused"}]
    except (OSError, smtplib.SMTPException) as exc:
        checks.append({"name": "Server", "ok": False, "detail": f"{config.host}:{config.port} — {exc}"})
    return checks
