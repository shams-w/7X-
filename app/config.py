"""Configuration loaded from environment variables (.env file supported).

Nothing secret or employee-specific is hard-coded here. Every value comes from
the environment so the same code can run in TEST and PRODUCTION.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:  # python-dotenv is optional at runtime (e.g. in CI tests)
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# The exact sentence that must be present before real employees can be messaged.
PRODUCTION_CONFIRM_PHRASE = "I_UNDERSTAND_REAL_EMPLOYEES_WILL_RECEIVE_MESSAGES"

VALID_MODES = ("TEST", "PRODUCTION")


class ConfigError(ValueError):
    """Raised when configuration is missing or unsafe."""


def _bool(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "y", "on")


def _resolve_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


@dataclass
class Settings:
    app_mode: str = "TEST"
    dry_run: bool = True
    automation_enabled: bool = True
    production_confirm: str = ""

    whatsapp_access_token: str = field(default="", repr=False)
    whatsapp_phone_number_id: str = ""
    whatsapp_business_account_id: str = ""
    whatsapp_api_version: str = "v23.0"
    whatsapp_api_base_url: str = "https://graph.facebook.com"
    request_timeout_seconds: float = 20.0
    max_retries: int = 3
    send_delay_seconds: float = 1.0

    test_phone_number: str = ""

    spreadsheet_path: Path = PROJECT_ROOT / "employee_data" / "7X_Employees.xlsx"
    spreadsheet_id: str = ""  # informational only (OneDrive/SharePoint ID used by Make.com)
    employees_sheet: str = "Employees"
    event_log_sheet: str = "Event_Log"

    event_db_path: Path = PROJECT_ROOT / "data" / "event_log.db"
    audit_csv_path: Path = PROJECT_ROOT / "logs" / "audit_log.csv"
    log_file_path: Path = PROJECT_ROOT / "logs" / "automation.log"
    stop_file_path: Path = PROJECT_ROOT / "STOP"

    timezone: str = "Asia/Dubai"

    birthday_template_en: str = "employee_birthday"
    anniversary_template_en: str = "work_anniversary"
    birthday_template_ar: str = "employee_birthday_ar"
    anniversary_template_ar: str = "work_anniversary_ar"
    template_language_en: str = "en"
    template_language_ar: str = "ar"
    arabic_enabled: bool = False
    # "number" -> {{2}} = "5" (matches the approved template text "{{2}} years")
    # "phrase" -> {{2}} = "1 year" / "5 years" (use with a template that says "completing {{2}} with 7X")
    anniversary_years_format: str = "number"

    # ------------------------------------------------------------------ helpers
    @property
    def is_test(self) -> bool:
        return self.app_mode == "TEST"

    @property
    def is_production(self) -> bool:
        return self.app_mode == "PRODUCTION"

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def validate(self, require_whatsapp: bool | None = None) -> None:
        """Fail loudly on unsafe or incomplete configuration."""
        errors: list[str] = []

        if self.app_mode not in VALID_MODES:
            errors.append(f"APP_MODE must be TEST or PRODUCTION (got '{self.app_mode}').")

        if self.is_production and self.production_confirm != PRODUCTION_CONFIRM_PHRASE:
            errors.append(
                "APP_MODE=PRODUCTION requires PRODUCTION_CONFIRM="
                f"{PRODUCTION_CONFIRM_PHRASE} (explicit safety switch)."
            )

        if self.is_test:
            from app.models import normalize_phone  # local import avoids a cycle

            if not self.test_phone_number:
                errors.append("APP_MODE=TEST requires TEST_PHONE_NUMBER (e.g. +971501234567).")
            else:
                ok, _, err = normalize_phone(self.test_phone_number)
                if not ok:
                    errors.append(f"TEST_PHONE_NUMBER is invalid: {err}")

        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            errors.append(f"TIMEZONE '{self.timezone}' is not a valid IANA timezone.")

        if require_whatsapp is None:
            require_whatsapp = not self.dry_run
        if require_whatsapp:
            if not self.whatsapp_access_token:
                errors.append("WHATSAPP_ACCESS_TOKEN is missing.")
            if not self.whatsapp_phone_number_id:
                errors.append("WHATSAPP_PHONE_NUMBER_ID is missing.")

        if errors:
            raise ConfigError("Configuration problem(s):\n  - " + "\n  - ".join(errors))

    def describe(self) -> str:
        """Safe one-line summary for logs (never includes the token)."""
        token_state = "set" if self.whatsapp_access_token else "MISSING"
        return (
            f"mode={self.app_mode} dry_run={self.dry_run} enabled={self.automation_enabled} "
            f"tz={self.timezone} token={token_state} phone_number_id="
            f"{'set' if self.whatsapp_phone_number_id else 'MISSING'} "
            f"arabic={self.arabic_enabled} spreadsheet={self.spreadsheet_path.name}"
        )


def load_settings(env_file: str | os.PathLike | None = None, **overrides) -> Settings:
    """Build Settings from environment variables (and an optional .env file)."""
    if load_dotenv is not None:
        load_dotenv(env_file or PROJECT_ROOT / ".env", override=False)

    env = os.environ.get
    s = Settings(
        app_mode=(env("APP_MODE") or "TEST").strip().upper(),
        dry_run=_bool(env("DRY_RUN"), True),
        automation_enabled=_bool(env("AUTOMATION_ENABLED"), True),
        production_confirm=(env("PRODUCTION_CONFIRM") or "").strip(),
        whatsapp_access_token=(env("WHATSAPP_ACCESS_TOKEN") or "").strip(),
        whatsapp_phone_number_id=(env("WHATSAPP_PHONE_NUMBER_ID") or "").strip(),
        whatsapp_business_account_id=(env("WHATSAPP_BUSINESS_ACCOUNT_ID") or "").strip(),
        whatsapp_api_version=(env("WHATSAPP_API_VERSION") or "v23.0").strip(),
        request_timeout_seconds=float(env("REQUEST_TIMEOUT_SECONDS") or 20),
        max_retries=int(env("MAX_RETRIES") or 3),
        send_delay_seconds=float(env("SEND_DELAY_SECONDS") or 1),
        test_phone_number=(env("TEST_PHONE_NUMBER") or "").strip(),
        spreadsheet_path=_resolve_path(env("SPREADSHEET_PATH") or "employee_data/7X_Employees.xlsx"),
        spreadsheet_id=(env("SPREADSHEET_ID") or "").strip(),
        event_db_path=_resolve_path(env("EVENT_DB_PATH") or "data/event_log.db"),
        audit_csv_path=_resolve_path(env("AUDIT_CSV_PATH") or "logs/audit_log.csv"),
        log_file_path=_resolve_path(env("LOG_FILE_PATH") or "logs/automation.log"),
        timezone=(env("TIMEZONE") or "Asia/Dubai").strip(),
        birthday_template_en=env("BIRTHDAY_TEMPLATE_EN") or "employee_birthday",
        anniversary_template_en=env("ANNIVERSARY_TEMPLATE_EN") or "work_anniversary",
        birthday_template_ar=env("BIRTHDAY_TEMPLATE_AR") or "employee_birthday_ar",
        anniversary_template_ar=env("ANNIVERSARY_TEMPLATE_AR") or "work_anniversary_ar",
        template_language_en=env("TEMPLATE_LANGUAGE_EN") or "en",
        template_language_ar=env("TEMPLATE_LANGUAGE_AR") or "ar",
        arabic_enabled=_bool(env("ARABIC_TEMPLATES_ENABLED"), False),
        anniversary_years_format=(env("ANNIVERSARY_YEARS_FORMAT") or "number").strip().lower(),
    )
    for key, value in overrides.items():
        setattr(s, key, value)
    return s
