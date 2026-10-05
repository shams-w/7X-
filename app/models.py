"""Data models and input validation helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum

EMPLOYEE_COLUMNS = [
    "Employee_ID",
    "Name",
    "Phone",
    "Birthday",
    "Joining_Date",
    "WhatsApp_Consent",
    "Active",
    "Language",
    "Birthday_Sent_Year",
    "Anniversary_Sent_Year",
    "Last_Message_Type",
    "Last_Message_Date",
    "Send_Status",
    "Error_Message",
]

# Helper formula columns used by the Make.com scenario (Python ignores them).
HELPER_COLUMNS = ["Birthday_MMDD", "Joining_MMDD", "Joining_Year", "Row_No"]

EVENT_LOG_COLUMNS = [
    "Event_ID",
    "Employee_ID",
    "Event_Type",
    "Event_Year",
    "Scheduled_Date",
    "Mode",
    "Recipient",
    "Message_ID",
    "Status",
    "Created_At",
    "Sent_At",
    "Error",
]


class EventType(str, Enum):
    BIRTHDAY = "BIRTHDAY"
    ANNIVERSARY = "ANNIVERSARY"

    @property
    def label(self) -> str:
        return "Birthday" if self is EventType.BIRTHDAY else "Anniversary"


class EventStatus(str, Enum):
    PENDING = "PENDING"  # claimed, send in progress
    SENT = "SENT"
    FAILED = "FAILED"  # definitely NOT delivered -> may be retried
    UNKNOWN = "UNKNOWN"  # outcome unclear (e.g. timeout after sending) -> never auto-retried


@dataclass
class Employee:
    row_number: int
    employee_id: str
    name: str
    phone_raw: str = ""
    phone: str | None = None  # normalised E.164 (+971...) or None when invalid
    phone_error: str | None = None
    birthday: date | None = None
    birthday_error: str | None = None
    joining_date: date | None = None
    joining_error: str | None = None
    consent: bool = False
    active: bool = False
    language: str = "EN"
    birthday_sent_year: int | None = None
    anniversary_sent_year: int | None = None

    @property
    def first_name(self) -> str:
        return self.name.split()[0] if self.name else ""

    @property
    def eligible(self) -> bool:
        return self.consent and self.active


@dataclass
class CelebrationEvent:
    employee: Employee
    event_type: EventType
    year: int
    scheduled_date: date
    years_completed: int | None = None  # anniversaries only

    @property
    def event_id(self) -> str:
        return make_event_id(self.employee.employee_id, self.event_type, self.year)

    def describe(self) -> str:
        if self.event_type is EventType.ANNIVERSARY:
            return f"Anniversary to {self.employee.name} - {self.years_completed} years"
        return f"Birthday to {self.employee.name}"


@dataclass
class SendResult:
    success: bool
    message_id: str | None = None
    error: str | None = None
    error_code: int | None = None
    retryable: bool = True  # False => outcome unknown, never resend automatically
    fatal: bool = False  # True => stop the whole run (e.g. expired token)
    recipient: str | None = None
    dry_run: bool = False


@dataclass
class RunSummary:
    run_date: date
    mode: str
    dry_run: bool
    rows_read: int = 0
    events_found: int = 0
    sent: list[str] = field(default_factory=list)
    would_send: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    data_errors: list[str] = field(default_factory=list)
    aborted: str | None = None

    def lines(self) -> list[str]:
        out = [
            f"Run date: {self.run_date.isoformat()} | mode={self.mode} | dry_run={self.dry_run}",
            f"Rows read: {self.rows_read} | celebration events today: {self.events_found}",
        ]
        for title, items in (
            ("SENT", self.sent),
            ("WOULD SEND (dry run)", self.would_send),
            ("DUPLICATE - not sent again", self.duplicates),
            ("FAILED", self.failed),
            ("UNKNOWN - check manually, will not auto-resend", self.unknown),
            ("SKIPPED", self.skipped),
            ("DATA ERRORS", self.data_errors),
        ):
            if items:
                out.append(f"{title}: {len(items)}")
                out.extend(f"   - {item}" for item in items)
        if self.aborted:
            out.append(f"RUN ABORTED: {self.aborted}")
        return out


def make_event_id(employee_id: str, event_type: EventType, year: int) -> str:
    """Unique idempotency key, e.g. EMP001_BIRTHDAY_2026."""
    return f"{employee_id.strip().upper()}_{event_type.value}_{year}"


# --------------------------------------------------------------------------- phone
_E164 = re.compile(r"^\+[1-9]\d{7,14}$")


def normalize_phone(raw) -> tuple[bool, str | None, str | None]:
    """Return (ok, e164_phone, error). Accepts '+971 50 123 4567', '00971501234567'."""
    if raw is None or str(raw).strip() == "":
        return False, None, "Missing phone"
    text = str(raw).strip()
    if isinstance(raw, float) and raw.is_integer():  # Excel stored the number as a number
        text = str(int(raw))
    cleaned = re.sub(r"[\s\-().]", "", text)
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if not cleaned.startswith("+"):
        return False, None, "Invalid phone: must start with + and country code (e.g. +971501234567)"
    if not _E164.match(cleaned):
        return False, None, "Invalid phone: must be + followed by 8-15 digits"
    return True, cleaned, None


def mask_phone(phone: str | None) -> str:
    """+971501234567 -> +97150****567 (safe for logs)."""
    if not phone:
        return "-"
    if len(phone) <= 7:
        return "****"
    return phone[:6] + "*" * (len(phone) - 9) + phone[-3:]


# --------------------------------------------------------------------------- dates
_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %b %Y", "%d %B %Y")


def parse_date(value) -> tuple[date | None, str | None]:
    """Parse a spreadsheet date cell. Day-first (UAE style) for slash formats."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None, "missing"
    if isinstance(value, datetime):
        return value.date(), None
    if isinstance(value, date):
        return value, None
    text = str(value).strip()
    iso_datetime = re.match(r"^(\d{4}-\d{2}-\d{2})[T ]\d{2}:\d{2}", text)
    if iso_datetime:  # e.g. "2026-10-05T00:00:00" or "2026-10-05 00:00:00"
        text = iso_datetime.group(1)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date(), None
        except ValueError:
            continue
    return None, f"invalid date '{text}' (use YYYY-MM-DD or DD/MM/YYYY)"


def parse_yes(value) -> bool:
    return str(value).strip().upper() in ("YES", "Y", "TRUE", "1") if value is not None else False


def parse_year(value) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return None


def celebration_date_in_year(month: int, day: int, year: int) -> date:
    """Date of a yearly celebration; 29 Feb falls back to 28 Feb in non-leap years."""
    try:
        return date(year, month, day)
    except ValueError:
        return date(year, 2, 28)
