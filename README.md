# 7X Executive Connect — Employee Celebration Automation

Sends a personal WhatsApp message from the **official 7X WhatsApp Business number** to
selected employees (C-level, Directors and other key people) on their **birthday** and
**work anniversary**. It runs automatically every day at **09:00 UAE time**.

It uses only official Meta tools (WhatsApp Business Platform, Cloud API, Coexistence).
It doesn't use WhatsApp Web, browser robots, or unofficial libraries.

---

## 1. What the project does

Every morning at 09:00 (Asia/Dubai):
1. It reads the employee spreadsheet.
2. It keeps only people with `WhatsApp_Consent = YES` **and** `Active = YES`.
3. If today's day and month match their **Birthday** (the birth year is ignored), it sends:
   > Happy Birthday, *Name*! 🎉 Wishing you a wonderful day and a great year ahead. Best wishes from 7X.
4. If today's day and month match their **Joining_Date** and they have completed at least 1 year, it sends:
   > Congratulations, *Name*, on completing *N* years with 7X! 🎉 Thank you for being part of our journey.
5. It writes the result back into the sheet and adds a line to the `Event_Log` sheet.

**Nobody ever gets the same celebration twice in one year.** This holds even if the
automation runs twice, retries, crashes or is started by hand.

## 2. Architecture

```
Employee spreadsheet (Microsoft 365 Excel, OneDrive/SharePoint)
        │
Make.com scenario — every day 09:00 Asia/Dubai          (main system)
        │   filter Active + Consent → birthday / anniversary check
        │   duplicate check (Data store key EMP001_BIRTHDAY_2026)
        ▼
WhatsApp Business Platform (Cloud API, Coexistence)
        │
Official 7X WhatsApp number  ──►  Employee
        │
Results → Employees sheet + Event_Log sheet
```

The WhatsApp Business **app** on the 7X phone keeps working (Coexistence).
A **Python fallback** does the same job, if Make.com can't be used or as a backup.
Run only one system at a time.

## 3. Files

| Path | What it is |
|---|---|
| `sample_data/7X_Employees_SAMPLE.xlsx` | Spreadsheet template with **fake** employees, validation rules, Event_Log sheet |
| `templates/WHATSAPP_TEMPLATES.md` | The 4 template texts to submit to Meta (EN required, AR optional) |
| `make/SCENARIO_DESIGN.md` | The Make.com scenario, step by step |
| `make/7X_Executive_Connect.blueprint.json` | Make blueprint to import |
| `make/PLACEHOLDERS.md` | What to replace after importing |
| `docs/META_SETUP_COEXISTENCE.md` | Connecting the official number safely (**read first**) |
| `docs/SETUP_CHECKLIST.md` | Setup checklist |
| `docs/PRODUCTION_LAUNCH_CHECKLIST.md` | Go-live checklist |
| `docs/EMERGENCY_STOP.md` | Stop everything immediately |
| `docs/TROUBLESHOOTING.md` | Errors and fixes |
| `docs/EVENT_LOG.md` | Audit trail format |
| `docs/DEPLOYMENT.md` | Where to run it, and why |
| `SECURITY.md` | Credentials, employee data, token rotation, TEST → PRODUCTION |
| `app/` | Python fallback (`config`, `models`, `birthday`, `anniversary`, `whatsapp`, `spreadsheet`, `event_log`, `main`) |
| `tests/` | Automated tests |
| `scripts/` | Spreadsheet generator, Shams Test simulation, daily run scripts |
| `.env.example` | Settings template for the Python fallback |

## 4. How to install

**Make.com (main system):** nothing to install. Follow `docs/META_SETUP_COEXISTENCE.md`, then `make/SCENARIO_DESIGN.md`.

**Python fallback** (Python 3.10 or newer):
```
python -m venv .venv
.venv\Scripts\activate            (Windows)
source .venv/bin/activate         (Mac / Linux)
pip install -r requirements.txt
```

## 5. How to configure

**Make:** open module **1 CONFIG** in the scenario:
* `APP_MODE` = `TEST` (keep it TEST until go-live)
* `TEST_PHONE_NUMBER` = your own mobile, e.g. `+971501234567`

**Python:** copy `.env.example` to `.env` and fill it in. The important lines are:
```
APP_MODE=TEST
DRY_RUN=true
TEST_PHONE_NUMBER=+9715XXXXXXXX
WHATSAPP_ACCESS_TOKEN=        (from Meta, see SECURITY.md)
WHATSAPP_PHONE_NUMBER_ID=     (from WhatsApp Manager)
SPREADSHEET_PATH=employee_data/7X_Employees.xlsx
TIMEZONE=Asia/Dubai
```
Never share or commit `.env`.

## 6. How to test

```
python -m pytest                       # 69 automated tests
python scripts/simulate_shams_test.py  # the "Shams Test" scenario, fully offline
```
For Make, follow section **C** of `docs/SETUP_CHECKLIST.md`. You'll add yourself as
"Shams Test" with today's birthday, then run it twice.

## 7. How to run dry mode (see without sending)

```
python -m app.main --dry-run
```
Example output:
```
Would send Birthday to Ahmed (to +97150****999)
Would send Anniversary to Sara - 4 years (to +97150****999)
```
Dry mode sends nothing and changes nothing in the sheet.
To check another day: `python -m app.main --dry-run --date 2026-12-25`

## 8. How to send one test message

```
python -m app.main --send-test birthday
python -m app.main --send-test anniversary --name "Shams Test"
```
This always goes to `TEST_PHONE_NUMBER`, whatever the mode.
In Make: add the Shams Test row with today's date and click **Run once** (TEST mode).

## 9. How to switch to production

Follow `docs/PRODUCTION_LAUNCH_CHECKLIST.md`. In short:
* **Make:** module 1 → `APP_MODE` = `PRODUCTION` → Save → scenario ON.
* **Python:** `.env` → `APP_MODE=PRODUCTION`, `PRODUCTION_CONFIRM=I_UNDERSTAND_REAL_EMPLOYEES_WILL_RECEIVE_MESSAGES`, `DRY_RUN=false`.
  Without the confirm sentence, the program refuses to start in production.

## 10. How to troubleshoot

1. Look at `Send_Status` and `Error_Message` in the Employees sheet.
2. Look at the `Event_Log` sheet (and Make → History, or `logs/automation.log`).
3. Find the error in `docs/TROUBLESHOOTING.md`.

## 11. How to update employee data

Open `7X_Employees.xlsx` in OneDrive/SharePoint:
* **New person:** add a row at the bottom. Fill the blue columns (Employee_ID, Name, Phone, Birthday, Joining_Date, WhatsApp_Consent, Active, Language). Copy the grey formula cells down from the row above.
* **Phone format:** `+971501234567`, with no spaces and no leading 0.
* **Dates:** real dates such as `1985-07-22`.
* **Someone leaves:** set `Active = NO`. Don't delete the row.
* **Someone withdraws consent:** set `WhatsApp_Consent = NO`.
* Don't type in the green columns. The automation fills them.
* Don't rename the sheets or the column headers.

## 12. How to stop the automation immediately

* **Make:** Scenarios → *7X Executive Connect* → toggle **OFF**.
* **Python:** create an empty file named `STOP` in the project folder, or set `AUTOMATION_ENABLED=false`.

Details: `docs/EMERGENCY_STOP.md`.

---

### Safety features (built in)
* **TEST mode** (default): every message goes only to `TEST_PHONE_NUMBER`, even when the sheet holds real executive numbers. Test runs never mark real employees as celebrated.
* **Production lock:** needs an explicit confirm sentence.
* **Dry run:** shows what would happen and sends nothing.
* **Duplicate protection:** a unique key per person, event and year, claimed *before* sending.
* **Timeouts** are never resent blindly. They're marked UNKNOWN for a person to check.
* **One bad row never stops the run.** Bad phones and dates are reported, and everyone else is still processed.
* **Expired token** stops the run cleanly, without repeating failed calls.
* Tokens are never written to logs. Phone numbers in logs are masked, and birthdays are not logged.
