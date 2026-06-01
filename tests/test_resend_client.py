import json
import unittest
from datetime import date
from io import BytesIO
from urllib.error import HTTPError

from nick_engine.daily_digest import DailyDigest
from nick_engine.resend_client import ResendClient


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return b'{"id":"email_123"}'


class ResendClientTests(unittest.TestCase):
    def test_missing_api_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "RESEND_API_KEY"):
            ResendClient(api_key="", from_email="research@example.com")

    def test_missing_from_email_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "RESEND_FROM_EMAIL"):
            ResendClient(api_key="re_test", from_email="")

    def test_send_uses_expected_payload_and_daily_idempotency_key(self):
        captured = {}

        def fake_open(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["payload"] = json.loads(request.data)
            captured["timeout"] = timeout
            return FakeResponse()

        client = ResendClient(
            api_key="re_test",
            from_email="Nick Research <research@example.com>",
            opener=fake_open,
        )

        response = client.send_digest(
            DailyDigest(subject="Morning", html="<p>Report</p>", text="Report"),
            to_email="marko@advertra.ca",
            send_date=date(2026, 6, 1),
        )

        self.assertEqual({"id": "email_123"}, response)
        self.assertEqual("https://api.resend.com/emails", captured["url"])
        self.assertEqual("Bearer re_test", captured["headers"]["Authorization"])
        self.assertRegex(
            captured["headers"]["Idempotency-key"],
            r"^nick-research-2026-06-01-marko-advertra-ca-[0-9a-f]{12}$",
        )
        self.assertEqual(["marko@advertra.ca"], captured["payload"]["to"])
        self.assertEqual("Morning", captured["payload"]["subject"])
        self.assertEqual(20, captured["timeout"])

    def test_resend_http_error_includes_response_body(self):
        def fake_open(request, timeout):
            raise HTTPError(
                request.full_url,
                403,
                "Forbidden",
                hdrs=None,
                fp=BytesIO(b'{"message":"domain is not verified"}'),
            )

        client = ResendClient(
            api_key="re_test",
            from_email="research@example.com",
            opener=fake_open,
        )

        with self.assertRaisesRegex(RuntimeError, "domain is not verified"):
            client.send_digest(
                DailyDigest(subject="Morning", html="<p>Report</p>", text="Report"),
                to_email="marko@advertra.ca",
                send_date=date(2026, 6, 1),
            )


if __name__ == "__main__":
    unittest.main()
