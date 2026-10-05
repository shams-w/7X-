"""Shared test helpers. All data here is fake."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest
from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings  # noqa: E402
from app.models import EMPLOYEE_COLUMNS, EVENT_LOG_COLUMNS  # noqa: E402
from app.whatsapp import WhatsAppService  # noqa: E402

TODAY = date(2026, 10, 5)
TEST_PHONE = "+971500009999"


def years_ago(d: date, n: int) -> date:
    return d.replace(year=d.year - n)


def make_workbook(path: Path, rows: list[dict]) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Employees"
    ws.append(EMPLOYEE_COLUMNS)
    for row in rows:
        ws.append([row.get(c) for c in EMPLOYEE_COLUMNS])
    log = wb.create_sheet("Event_Log")
    log.append(EVENT_LOG_COLUMNS)
    wb.save(path)
    return path


def employee_row(emp_id="EMP001", name="Test Person", phone="+971500000001",
                 birthday=date(1985, 1, 1), joining=date(2020, 1, 1),
                 consent="YES", active="YES", **extra) -> dict:
    row = {"Employee_ID": emp_id, "Name": name, "Phone": phone, "Birthday": birthday,
           "Joining_Date": joining, "WhatsApp_Consent": consent, "Active": active}
    row.update(extra)
    return row


class FakeResponse:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


class FakeSession:
    """Stands in for requests.Session - records every call, never touches the network."""

    def __init__(self, responses=None):
        self.calls: list[dict] = []
        self.responses = list(responses or [])
        self._counter = 0

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        if self.responses:
            item = self.responses.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        self._counter += 1
        return FakeResponse(200, {"messages": [{"id": f"wamid.FAKE{self._counter:04d}"}]})

    @property
    def recipients(self) -> list[str]:
        return [c["json"]["to"] for c in self.calls]


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        app_mode="TEST",
        dry_run=False,
        whatsapp_access_token="EAAG-SECRET-TOKEN-123",
        whatsapp_phone_number_id="111222333",
        test_phone_number=TEST_PHONE,
        spreadsheet_path=tmp_path / "employees.xlsx",
        event_db_path=tmp_path / "event_log.db",
        audit_csv_path=tmp_path / "audit_log.csv",
        log_file_path=tmp_path / "automation.log",
        stop_file_path=tmp_path / "STOP",
        send_delay_seconds=0,
    )


@pytest.fixture
def fake_session() -> FakeSession:
    return FakeSession()


@pytest.fixture
def wa(settings, fake_session) -> WhatsAppService:
    return WhatsAppService(settings, session=fake_session, sleep=lambda s: None)
