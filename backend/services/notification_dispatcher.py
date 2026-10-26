import json
import logging
import smtplib
import time
from email.message import EmailMessage
from typing import Any, Dict, Optional
from urllib.error import URLError
from urllib.request import Request as UrlRequest, urlopen

logger = logging.getLogger(__name__)


def dispatch_notification(
    message: str,
    audience: str,
    *,
    webhook_url: Optional[str] = None,
    smtp_host: Optional[str] = None,
    smtp_port: int = 25,
    smtp_username: Optional[str] = None,
    smtp_password: Optional[str] = None,
    smtp_from: str = "resq-ai@localhost",
    smtp_to: Optional[str] = None,
    attempts: int = 2,
    timeout_seconds: int = 5,
) -> Dict[str, Any]:
    payload = {
        "audience": audience,
        "message": message,
        "status": "queued_local",
        "delivery_channel": "local_console",
    }

    if webhook_url:
        try:
            request = UrlRequest(
                webhook_url,
                data=json.dumps({"audience": audience, "message": message}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=timeout_seconds) as response:
                if 200 <= response.status < 300:
                    payload["status"] = "delivered"
                    payload["delivery_channel"] = "webhook"
                    payload["status_code"] = response.status
                    return payload
                payload["error"] = f"Webhook returned HTTP {response.status}"
                logger.warning("Webhook notification returned HTTP %s for %s", response.status, audience)
        except (OSError, URLError, ValueError) as exc:
            payload["error"] = str(exc)
            logger.warning("Webhook notification failed for %s: %s", audience, exc)
            if attempts > 1:
                time.sleep(0.1)
                return dispatch_notification(message, audience, webhook_url=webhook_url, smtp_host=smtp_host, smtp_port=smtp_port, smtp_username=smtp_username, smtp_password=smtp_password, smtp_from=smtp_from, smtp_to=smtp_to, attempts=attempts - 1, timeout_seconds=timeout_seconds)

    if smtp_host and smtp_to:
        try:
            msg = EmailMessage()
            msg["Subject"] = "RESQ-AI local alert"
            msg["From"] = smtp_from
            msg["To"] = smtp_to
            msg.set_content(message)
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if smtp_username and smtp_password:
                    server.login(smtp_username, smtp_password)
                server.send_message(msg)
            payload["status"] = "delivered"
            payload["delivery_channel"] = "smtp"
            return payload
        except Exception as exc:  # pragma: no cover - operational fallback
            payload["status"] = "queued_local"
            payload["delivery_channel"] = "local_console"
            payload["error"] = str(exc)
            logger.warning("SMTP notification failed for %s: %s", audience, exc)
            return payload

    logger.info("LOCAL_NOTIFICATION :: audience=%s :: message=%s", audience, message)
    payload["status"] = "queued_local"
    return payload
