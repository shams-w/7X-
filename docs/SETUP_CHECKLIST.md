# Setup checklist

Tick each line in order. Do **not** switch anything to production in this checklist.

## A. Accounts (manual, see docs/META_SETUP_COEXISTENCE.md)
- [ ] A1 Phone: WhatsApp Business app updated, chat backup made
- [ ] A2 You are an admin (Full control) of the 7X Business Portfolio
- [ ] A3 Make.com account created, profile time zone = Asia/Dubai
- [ ] A4 Make → WhatsApp Business Cloud connection created with **Coexistence** (NOT "Cloud API")
- [ ] A5 Phone app still works after connecting (send yourself a normal message)
- [ ] A6 Payment method added in WhatsApp Manager
- [ ] A7 Templates `employee_birthday` and `work_anniversary` show **Active / Approved**
- [ ] A8 Workbook `7X_Employees.xlsx` in a restricted OneDrive/SharePoint folder, Make connected to Microsoft 365

## B. Make scenario
- [ ] B1 Data store `7X_Event_Log` created (make/SCENARIO_DESIGN.md)
- [ ] B2 Blueprint imported, all placeholders replaced (make/PLACEHOLDERS.md)
- [ ] B3 Module 1: `APP_MODE` = `TEST`, `TEST_PHONE_NUMBER` = your own mobile
- [ ] B4 Scenario settings: Sequential ON, Data is confidential ON, incomplete executions OFF
- [ ] B5 "Run this module only" on module 2 shows the Employees rows

## C. Test with yourself (TEST mode)
- [ ] C1 Add a row: `EMP900 | Shams Test | <your phone> | Birthday = today (any year) | Joining_Date = today 3 years ago | YES | YES | EN`
- [ ] C2 Click **Run once**
- [ ] C3 You receive **2** WhatsApp messages from the 7X number: birthday + "3 years" anniversary
- [ ] C4 Row shows `Send_Status = TEST_SENT`, `Birthday_Sent_Year` still empty
- [ ] C5 `Event_Log` sheet has 2 rows with Status SENT and a message ID (`wamid...`)
- [ ] C6 Click **Run once** again → **no** new messages (duplicate protection works)
- [ ] C7 Change the Shams Test row to `WhatsApp_Consent = NO`, delete the 2 TEST records in the Data store, run once → **no** message
- [ ] C8 Put a real executive's row in the sheet (with their number), run in TEST → the message still arrives **on your phone only**

## D. Python fallback (optional, only if used)
- [ ] D1 `pip install -r requirements.txt` and `python -m pytest` → all tests pass
- [ ] D2 `.env` created from `.env.example`, `APP_MODE=TEST`, `DRY_RUN=true`
- [ ] D3 `python -m app.main --dry-run` shows the "Would send ..." lines
- [ ] D4 `python -m app.main --send-test birthday` → message arrives on TEST phone
- [ ] D5 `DRY_RUN=false`, run with the Shams Test row → 2 messages to TEST phone; second run → duplicates

When every box in A–C is ticked → go to `PRODUCTION_LAUNCH_CHECKLIST.md`.
