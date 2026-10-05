"""Acceptance simulation: 'Shams Test' has a birthday AND a 3-year work anniversary today.

Runs the real daily pipeline twice in APP_MODE=TEST against a temporary workbook.
The Meta API is replaced by an OFFLINE fake that only records what would be posted,
so this script is safe to run anywhere and never contacts WhatsApp.

    python scripts/simulate_shams_test.py
"""

from __future__ import annotations

import logging
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from openpyxl import Workbook  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import run_daily  # noqa: E402
from app.models import EMPLOYEE_COLUMNS, EVENT_LOG_COLUMNS, celebration_date_in_year  # noqa: E402
from app.whatsapp import WhatsAppService  # noqa: E402

TEST_PHONE = "+971500009999"  # fake test handset for the simulation
EMPLOYEE_PHONE = "+971555000111"  # fake "executive" number that must NEVER be used


class OfflineMetaAPI:
    """Pretends to be graph.facebook.com and records every request."""

    def __init__(self):
        self.requests = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.requests.append(json)
        n = len(self.requests)

        class R:
            status_code = 200

            @staticmethod
            def json():
                return {"messages": [{"id": f"wamid.SIMULATED{n:03d}"}]}
        return R()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s", stream=sys.stdout)
    tmp = Path(tempfile.mkdtemp(prefix="7x_sim_"))
    settings = Settings(
        app_mode="TEST", dry_run=False,
        whatsapp_access_token="SIMULATION-NOT-A-REAL-TOKEN", whatsapp_phone_number_id="SIMULATED",
        test_phone_number=TEST_PHONE,
        spreadsheet_path=tmp / "employees.xlsx", event_db_path=tmp / "event_log.db",
        audit_csv_path=tmp / "audit_log.csv", log_file_path=tmp / "automation.log",
        stop_file_path=tmp / "STOP", send_delay_seconds=0,
    )
    today = datetime.now(settings.tz).date()
    # 29 Feb safe: same day/month (or 28 Feb) N years ago
    joining = celebration_date_in_year(today.month, today.day, today.year - 3)
    birthday = celebration_date_in_year(today.month, today.day, today.year - 32)

    wb = Workbook()
    ws = wb.active
    ws.title = "Employees"
    ws.append(EMPLOYEE_COLUMNS)
    row = {"Employee_ID": "EMP900", "Name": "Shams Test", "Phone": EMPLOYEE_PHONE,
           "Birthday": birthday, "Joining_Date": joining, "WhatsApp_Consent": "YES",
           "Active": "YES", "Language": "EN"}
    ws.append([row.get(c) for c in EMPLOYEE_COLUMNS])
    wb.create_sheet("Event_Log").append(EVENT_LOG_COLUMNS)
    wb.save(settings.spreadsheet_path)

    api = OfflineMetaAPI()
    wa = WhatsAppService(settings, session=api, sleep=lambda s: None)

    print("=" * 72)
    print(f"SIMULATION  today={today} (Asia/Dubai)  APP_MODE=TEST  TEST_PHONE_NUMBER={TEST_PHONE}")
    print(f"Employee: Shams Test | Phone {EMPLOYEE_PHONE} | Birthday {birthday} | Joined {joining}")
    print("=" * 72)

    print("\n---------------- RUN 1 ----------------")
    s1 = run_daily(settings, today, wa)
    print("\n---------------- RUN 2 (same day) ----------------")
    s2 = run_daily(settings, today, wa)

    print("\n================ RESULT ================")
    print(f"Run 1 events found : {s1.events_found}")
    for line in s1.sent:
        print(f"Run 1 SENT         : {line}")
    print(f"Run 2 sent         : {len(s2.sent)}")
    for line in s2.duplicates:
        print(f"Run 2 DUPLICATE    : {line}")
    print("Requests that reached the (simulated) Meta API:")
    for req in api.requests:
        params = [p["text"] for p in req["template"]["components"][0]["parameters"]]
        print(f"   to=+{req['to']} template={req['template']['name']} params={params}")

    recipients = {"+" + r["to"] for r in api.requests}
    ok = (
        s1.events_found == 2 and len(s1.sent) == 2 and len(s2.sent) == 0
        and len(s2.duplicates) == 2 and recipients == {TEST_PHONE} and len(api.requests) == 2
    )
    print(f"\nAll messages went only to TEST_PHONE_NUMBER: {recipients == {TEST_PHONE}}")
    print(f"Executive number used: {EMPLOYEE_PHONE.lstrip('+') in [r['to'] for r in api.requests]}")
    print("SIMULATION PASSED" if ok else "SIMULATION FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
