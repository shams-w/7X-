# Troubleshooting

Look at `Send_Status` / `Error_Message` in the Employees sheet, the `Event_Log` sheet, or
Make → scenario → **History**. For Python, look at `logs/automation.log` and `logs/audit_log.csv`.

| Symptom / error | Meaning | Fix |
|---|---|---|
| Nobody received anything today | No birthday/anniversary today, or scenario OFF | Check the dates in the sheet; check the toggle is ON; check History ran at 09:00 |
| Ran at the wrong hour | Time zone | Make → Profile → Time zone = Asia/Dubai. Python: computer clock / `CRON_TZ=Asia/Dubai` |
| `TEST_SENT` but no message on my phone | TEST_PHONE_NUMBER wrong | Use the `+9715…` format; the phone must have WhatsApp |
| `DATA_ERROR` – Invalid phone | Phone not in `+country` format | Fix to `+971501234567` (no spaces, no leading 0) |
| Birthday missing / invalid date | Cell empty or text | Type a real date, e.g. `1985-07-22` |
| `Joining_Date is in the future` | Typing mistake | Correct the date |
| Skipped: no WhatsApp consent / not Active | Working as designed | Set YES only with real consent |
| `TEMPLATE ERROR (132001)` | Template name or language doesn't exist / not approved | WhatsApp Manager → Message templates: name must be exactly `employee_birthday` / `work_anniversary`, language `en`, status Active |
| `TEMPLATE ERROR (132000)` | Wrong number of `{{ }}` values | Birthday needs 1 value, anniversary needs 2 |
| `AUTH ERROR (190)` / connection invalid | Token expired or revoked | Make: Connections → reauthorize. Python: create a new system user token (SECURITY.md) |
| `RATE LIMIT (130429 / 131056 / 80007)` | Sending too fast | Automatic retry; if it repeats, rerun later today |
| `131049` | Meta held back a marketing message for this person (too many recent marketing messages from businesses) | Nothing to fix on our side. Rerun later or tomorrow, or send a personal message from the phone app |
| `131026` | Recipient can't receive (no WhatsApp on that number, or old app) | Check the number with the employee |
| Payment / `131042` | No valid payment method | WhatsApp Manager → Payment methods |
| `UNKNOWN` status | The send timed out: WhatsApp *may* have delivered it. Not resent automatically, to avoid duplicates | Check the phone app: is the message in the chat? If **not**, Python: `python -m app.main --reset-event EMP001_BIRTHDAY_2026` then run again. Make: delete that key from the Data store and run once |
| Duplicate message received | Should not happen | Stop (EMERGENCY_STOP.md); check both Make and Python weren't live at the same time |
| "Spreadsheet unavailable" | File moved, renamed, or open/locked | Python: check `SPREADSHEET_PATH`; close Excel. Make: re-select the workbook in modules |
| Make: "Resource not found" / 400 during Coexistence signup | Known Meta/Make signup issue | Wait an hour and retry with Coexistence. Make sure you picked the existing 7X portfolio; do NOT switch to "Cloud API" |
| Make: blueprint module shows as unknown | Module ID changed in Make | Replace the module with the one of the same name (make/SCENARIO_DESIGN.md table) |
| Phone app disconnected from API | App not opened for a long time | Open the WhatsApp Business app; reconnect the Coexistence connection in Make if needed |

## Re-sending a message on purpose
Duplicates are blocked on purpose. To send again (e.g. after a wrong name):
1. Fix the sheet.
2. Make: Data stores → `7X_Event_Log` → delete the key `PRODUCTION_EMP001_BIRTHDAY_2026`, and clear `Birthday_Sent_Year` for that row → Run once.
3. Python: clear `Birthday_Sent_Year`, then `python -m app.main --reset-event EMP001_BIRTHDAY_2026`. This works only for FAILED/UNKNOWN events. A SENT event is never resent by the tool, so send it by hand from the phone app.
