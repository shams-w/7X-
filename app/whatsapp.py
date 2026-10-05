"""Official WhatsApp Business Platform (Cloud API) client.

Only the official Graph API endpoint is used:
    POST https://graph.facebook.com/{version}/{PHONE_NUMBER_ID}/messages

Safety guarantees implemented here (last line of defence, independent of main.py):
  * APP_MODE=TEST  -> every recipient is replaced by TEST_PHONE_NUMBER.
  * DRY_RUN=true   -> no HTTP request is ever made.
  * The access token is never written to logs or error messages.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

import requests

from app.config import Settings
from app.models import SendResult, mask_phone, normalize_phone

log = logging.getLogger("7x.whatsapp")

# Meta error codes -> how we treat them.
# https://developers.facebook.com/docs/whatsapp/cloud-api/support/error-codes
AUTH_ERROR_CODES = {0, 190, 10, 200, 3}  # token expired/invalid/permission
RATE_LIMIT_CODES = {4, 80007, 130429, 131048, 131056}
TEMPLATE_ERROR_CODES = {132000, 132001, 132005, 132007, 132012, 132015, 132016}
RECIPIENT_ERROR_CODES = {131026, 131049, 131050, 131051}


class WhatsAppService:
    def __init__(
        self,
        settings: Settings,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.settings = settings
        self.session = session or requests.Session()
        self._sleep = sleep

    # ----------------------------------------------------------------- public
    def send_birthday_message(self, phone: str, name: str, language: str = "EN") -> SendResult:
        template, lang = self._template_for("birthday", language)
        return self.send_template_message(phone, template, lang, [name])

    def send_anniversary_message(
        self, phone: str, name: str, years: int, language: str = "EN"
    ) -> SendResult:
        template, lang = self._template_for("anniversary", language)
        if self.settings.anniversary_years_format == "phrase":
            years_text = f"{years} year" if years == 1 else f"{years} years"
        else:
            years_text = str(years)
        return self.send_template_message(phone, template, lang, [name, years_text])

    def resolve_recipient(self, phone: str) -> str:
        """Apply the TEST-mode override. Production numbers never leak in TEST mode."""
        if self.settings.app_mode != "PRODUCTION":
            ok, test_phone, err = normalize_phone(self.settings.test_phone_number)
            if not ok:
                raise ValueError(f"TEST mode active but TEST_PHONE_NUMBER is invalid: {err}")
            return test_phone
        return phone

    def send_template_message(
        self,
        phone: str,
        template_name: str,
        language_code: str,
        body_parameters: list[str],
    ) -> SendResult:
        try:
            recipient = self.resolve_recipient(phone)
        except ValueError as exc:
            return SendResult(False, error=str(exc), retryable=True, fatal=True)

        if self.settings.dry_run:
            log.info(
                "[DRY RUN] would send template '%s' (%s) to %s",
                template_name, language_code, mask_phone(recipient),
            )
            return SendResult(True, message_id="DRY_RUN", recipient=recipient, dry_run=True)

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient.lstrip("+"),
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": p} for p in body_parameters],
                    }
                ],
            },
        }
        result = self._post_with_retries(payload)
        result.recipient = recipient
        return result

    # ---------------------------------------------------------------- internal
    def _template_for(self, kind: str, language: str) -> tuple[str, str]:
        s = self.settings
        use_ar = s.arabic_enabled and (language or "").strip().upper() == "AR"
        if kind == "birthday":
            return (s.birthday_template_ar, s.template_language_ar) if use_ar else (
                s.birthday_template_en, s.template_language_en)
        return (s.anniversary_template_ar, s.template_language_ar) if use_ar else (
            s.anniversary_template_en, s.template_language_en)

    @property
    def _url(self) -> str:
        s = self.settings
        return f"{s.whatsapp_api_base_url}/{s.whatsapp_api_version}/{s.whatsapp_phone_number_id}/messages"

    def _post_with_retries(self, payload: dict) -> SendResult:
        headers = {
            "Authorization": f"Bearer {self.settings.whatsapp_access_token}",
            "Content-Type": "application/json",
        }
        attempts = max(1, self.settings.max_retries)
        last: SendResult | None = None
        for attempt in range(1, attempts + 1):
            try:
                resp = self.session.post(
                    self._url, json=payload, headers=headers,
                    timeout=self.settings.request_timeout_seconds,
                )
            except requests.ConnectionError as exc:
                if not self._never_reached_meta(exc):
                    # Connection dropped after the request was sent -> outcome unknown.
                    return SendResult(False, error="Connection lost during send - delivery status "
                                      "unknown, NOT retried", retryable=False)
                last = SendResult(False, error=f"Network error: {type(exc).__name__}", retryable=True)
            except requests.Timeout:
                # Read timeout: Meta may already have the request.
                return self._read_timeout()
            except requests.RequestException as exc:
                last = SendResult(False, error=f"Request error: {type(exc).__name__}", retryable=True)
            else:
                result = self._parse_response(resp)
                if result.success or not self._should_retry_now(result):
                    return result
                last = result

            if attempt < attempts:
                delay = 2 ** attempt
                log.warning("WhatsApp send attempt %d failed (%s); retrying in %ds",
                            attempt, last.error, delay)
                self._sleep(delay)
        return last

    @staticmethod
    def _never_reached_meta(exc: requests.ConnectionError) -> bool:
        """True when the HTTP request certainly was not delivered (safe to retry)."""
        if isinstance(exc, (requests.ConnectTimeout, requests.exceptions.ProxyError,
                            requests.exceptions.SSLError)):
            return True
        text = repr(exc)
        return any(marker in text for marker in (
            "NewConnectionError", "NameResolutionError", "Failed to establish",
            "Name or service not known", "getaddrinfo failed", "Connection refused",
        ))

    @staticmethod
    def _read_timeout() -> SendResult:
        # Meta may have accepted the message; resending could duplicate it.
        return SendResult(
            False,
            error="Timeout waiting for WhatsApp response - delivery status unknown, NOT retried",
            retryable=False,
        )

    @staticmethod
    def _should_retry_now(result: SendResult) -> bool:
        return result.error_code in RATE_LIMIT_CODES or result.error_code == 429

    def _parse_response(self, resp) -> SendResult:
        try:
            body = resp.json()
        except ValueError:
            body = {}

        if 200 <= resp.status_code < 300:
            messages = body.get("messages") or []
            message_id = messages[0].get("id") if messages else None
            if message_id:
                return SendResult(True, message_id=message_id)
            return SendResult(False, error="Unexpected success response without message id",
                              retryable=False)

        err = body.get("error") or {}
        code = err.get("code")
        message = self._redact(str(err.get("message") or f"HTTP {resp.status_code}"))
        details = (err.get("error_data") or {}).get("details")
        if details:
            message = f"{message} - {self._redact(str(details))}"

        if code in AUTH_ERROR_CODES or resp.status_code == 401:
            return SendResult(False, error=f"AUTH ERROR ({code}): {message}. Token expired or "
                              "missing permission - renew WHATSAPP_ACCESS_TOKEN.",
                              error_code=code, fatal=True)
        if code in TEMPLATE_ERROR_CODES:
            return SendResult(False, error=f"TEMPLATE ERROR ({code}): {message}. Check the template "
                              "exists, is APPROVED and the language code matches.", error_code=code)
        if code in RATE_LIMIT_CODES or resp.status_code == 429:
            return SendResult(False, error=f"RATE LIMIT ({code}): {message}",
                              error_code=code if code is not None else 429)
        if code in RECIPIENT_ERROR_CODES:
            return SendResult(False, error=f"RECIPIENT ERROR ({code}): {message}", error_code=code)
        return SendResult(False, error=f"META API ERROR ({code}, HTTP {resp.status_code}): {message}",
                          error_code=code)

    def _redact(self, text: str) -> str:
        token = self.settings.whatsapp_access_token
        return text.replace(token, "***REDACTED***") if token else text
