import json
import re
from hashlib import sha1
from datetime import date
from typing import Callable, Dict
from urllib.request import Request, urlopen

from .daily_digest import DailyDigest


RESEND_EMAILS_URL = "https://api.resend.com/emails"


def _idempotency_key(send_date: date, recipient: str, digest: DailyDigest) -> str:
    normalized_recipient = re.sub(r"[^a-z0-9]+", "-", recipient.lower()).strip("-")
    fingerprint_source = f"{digest.subject}\n{digest.html}\n{digest.text}".encode("utf-8")
    fingerprint = sha1(fingerprint_source).hexdigest()[:12]
    return f"nick-research-{send_date.isoformat()}-{normalized_recipient}-{fingerprint}"


class ResendClient:
    def __init__(
        self,
        *,
        api_key: str,
        from_email: str,
        opener: Callable = urlopen,
    ) -> None:
        if not api_key:
            raise ValueError("RESEND_API_KEY is required for live sends")
        if not from_email:
            raise ValueError("RESEND_FROM_EMAIL is required for live sends")
        self.api_key = api_key
        self.from_email = from_email
        self.opener = opener

    def send_digest(
        self,
        digest: DailyDigest,
        *,
        to_email: str,
        send_date: date,
    ) -> Dict[str, str]:
        payload = json.dumps(
            {
                "from": self.from_email,
                "to": [to_email],
                "subject": digest.subject,
                "html": digest.html,
                "text": digest.text,
            }
        ).encode("utf-8")
        request = Request(
            RESEND_EMAILS_URL,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Idempotency-Key": _idempotency_key(send_date, to_email, digest),
                "User-Agent": "nick-thesis-research-engine/1.0",
            },
        )
        with self.opener(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
