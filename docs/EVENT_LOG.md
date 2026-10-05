# Event log and audit trail

Every celebration has a unique **Event_ID**: `<Employee_ID>_<EVENT_TYPE>_<YEAR>`, for example
`EMP001_BIRTHDAY_2026` or `EMP001_ANNIVERSARY_2026`.
An Event_ID can reach status **SENT** only once per mode (TEST / PRODUCTION).

## Event_Log sheet (in the workbook, written by Make and Python)

| Column | Example | Notes |
|---|---|---|
| Event_ID | EMP001_BIRTHDAY_2026 | unique key |
| Employee_ID | EMP001 | |
| Event_Type | BIRTHDAY / ANNIVERSARY | |
| Event_Year | 2026 | |
| Scheduled_Date | 2026-10-05 | the day it was due |
| Mode | TEST / PRODUCTION | |
| Recipient | +97150****567 | masked |
| Message_ID | wamid.HBgM... | WhatsApp's ID, proof of sending |
| Status | SENT / FAILED / UNKNOWN | |
| Created_At | 2026-10-05 09:00:03 | |
| Sent_At | 2026-10-05 09:00:04 | |
| Error | TEMPLATE ERROR (132001)... | empty when OK |

## Statuses

| Status | Meaning | Resent automatically? |
|---|---|---|
| PENDING | Claimed, send in progress (or the run crashed mid-send) | No, needs a manual check |
| SENT | WhatsApp accepted the message | Never |
| FAILED | WhatsApp definitely did not take it | Yes, on the next run the same day |
| UNKNOWN | Timeout or connection lost after sending, so delivery is unclear | No. Check the phone app, then `--reset-event` |

## Where each system stores it
* **Make:** Data store `7X_Event_Log` (duplicate check) + `Event_Log` sheet (audit).
* **Python:** `data/event_log.db` (SQLite, duplicate check, `PRIMARY KEY (mode, event_id)`)
  + `logs/audit_log.csv` (every attempt, including DRY_RUN and DUPLICATE_SKIPPED)
  + the `Event_Log` sheet.

The logs contain **no birthdays** and only **masked** phone numbers.
