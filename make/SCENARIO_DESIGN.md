# Make.com scenario — 7X Executive Connect (primary automation)

**Scenario name:** `7X Executive Connect - Daily Celebrations`
**Schedule:** once a day, 09:00, Asia/Dubai
**Blueprint:** [`7X_Executive_Connect.blueprint.json`](7X_Executive_Connect.blueprint.json) (rebuild it with `python make/build_blueprint.py`)

## Flow

```
[1] CONFIG (Set multiple variables)  APP_MODE, TEST_PHONE_NUMBER, TODAY_MMDD, THIS_YEAR (Asia/Dubai)
 │
[2] Microsoft 365 Excel › List Worksheet Rows   (sheet "Employees", one bundle per employee)
 │
[3] EMPLOYEE ROW (Set multiple variables)   the only module that reads Excel columns
 │     filter: Employee_ID exists
[4] ROUTER   filter: Active = YES AND WhatsApp_Consent = YES AND phone starts with "+"
 ├── Route A: BIRTHDAY
 │     filter: Birthday_MMDD = today AND Birthday_Sent_Year ≠ this year
 │   [10] Data store › Get a record       key = <MODE>_<EMP>_BIRTHDAY_<YEAR>   (duplicate check)
 │   [11] Data store › Add/replace record  overwrite = NO, status PENDING      (atomic claim)
 │          filter: record does not exist        error handler → Ignore (duplicate = stop)
 │   [12] WhatsApp Business Cloud › Send a Template Message  employee_birthday, {{1}} = name
 │          error handler → delete claim → Excel row FAILED + error → Event_Log FAILED → Ignore
 │   [13] Data store › Add/replace record  status SENT + message id
 │   [14] Excel › Update a Worksheet Row   Birthday_Sent_Year*, Last_Message_*, Send_Status
 │   [15] Excel › Add a Worksheet Row      Event_Log (audit)
 └── Route B: ANNIVERSARY
       filter: Joining_MMDD = today AND (THIS_YEAR − Joining_Year) ≥ 1 AND Anniversary_Sent_Year ≠ this year
     [30]–[35] same steps, template work_anniversary, {{1}} = name, {{2}} = years
```
\* In TEST mode the Sent_Year column keeps its old value and Send_Status becomes
`TEST_SENT`. Test runs can never mark a real executive as already celebrated.

## How duplicates are prevented in Make

| Threat | Protection |
|---|---|
| Scenario runs twice the same day | Data store key `PRODUCTION_EMP001_BIRTHDAY_2026` already exists, so Route stops at [10]/[11] |
| Make retries / "Run once" pressed again | same key check |
| Two runs at the same moment | [11] uses *overwrite = No*, so only one run can create the key; the other gets an error and is ignored |
| Excel update failed after a send | Data store already says SENT, so it is still not resent |
| WhatsApp send failed | claim is deleted, Sent_Year untouched, so a rerun the same day retries |
| Sheet edited by hand | Sent_Year column is a second, independent check |

Also enable **Scenario settings → Sequential processing = ON**. The blueprint already sets this.

## Create the Data store (do this before importing)

Make → **Data stores** → **Add data store**
* Name: `7X_Event_Log`
* Data structure → **Add** → name `7X_Event` with these fields (all type *Text*):
  `event_id`, `employee_id`, `event_type`, `event_year`, `mode`, `status`, `message_id`, `created_at`
* Size: 1 MB is plenty.

## Import the blueprint

1. Make → **Scenarios** → **Create a new scenario**.
2. At the bottom toolbar click **⋯ (More)** → **Import Blueprint** → choose
   `7X_Executive_Connect.blueprint.json` → **Save**.
3. Open each module that shows a warning and fix the placeholder (see [`PLACEHOLDERS.md`](PLACEHOLDERS.md)).

> **Honesty note:** I could not open Make's module catalogue from the build environment.
> The module display names are confirmed ("List Worksheet Rows", "Update a Worksheet Row",
> "Add a Worksheet Row", "Send a Template Message"). The internal IDs in the blueprint are
> my best match and could not be checked. If a module imports as "unknown", delete it and
> add the module with the same name from the app's list. Then map it as shown in the table
> below. The design is the same either way, and all spreadsheet mapping happens in module [3].

## Build or repair by hand (module by module)

| # | App › Module | Settings |
|---|---|---|
| 1 | Tools › **Set multiple variables** | `APP_MODE` = `TEST` · `TEST_PHONE_NUMBER` = your phone `+9715…` · `TODAY_MMDD` = `{{formatDate(now; "MM-DD"; "Asia/Dubai")}}` · `TODAY_ISO` = `{{formatDate(now; "YYYY-MM-DD"; "Asia/Dubai")}}` · `THIS_YEAR` = `{{formatDate(now; "YYYY"; "Asia/Dubai")}}` · `NOW_TEXT` = `{{formatDate(now; "YYYY-MM-DD HH:mm"; "Asia/Dubai")}}` |
| 2 | Microsoft 365 Excel › **List Worksheet Rows** | Connection: your Microsoft 365 work account · Drive/Location: the OneDrive or SharePoint site holding the workbook · Workbook: `7X_Employees.xlsx` · Worksheet: `Employees` · Header row: yes · Limit: 3000 |
| 3 | Tools › **Set multiple variables** | Map from module 2: `employee_id`=Employee_ID (col A) · `name`=Name (B) · `phone`=Phone (C, spaces removed) · `consent`=upper(WhatsApp_Consent) (F) · `active`=upper(Active) (G) · `birthday_sent_year` (I) · `anniversary_sent_year` (J) · `birthday_mmdd` (O) · `joining_mmdd` (P) · `joining_year` (Q) · `row_no` (R) · `recipient` = `{{if(1.APP_MODE = "PRODUCTION"; phone; 1.TEST_PHONE_NUMBER)}}` · `recipient_masked` |
| 4 | Flow control › **Router** | Filter on the link 3→4: `active` = `YES` AND `consent` = `YES` AND `phone` starts with `+` |
| 10/30 | Data store › **Get a record** | Data store `7X_Event_Log` · Key `{{1.APP_MODE}}_{{3.employee_id}}_BIRTHDAY_{{1.THIS_YEAR}}` (ANNIVERSARY on route B). Route filter as in the flow above |
| 11/31 | Data store › **Add/replace a record** | Same key · **Overwrite an existing record = No** · status `PENDING` · Filter on link: `10.status` *Does not exist* · Right-click → Add error handler → **Ignore** |
| 12/32 | WhatsApp Business Cloud › **Send a Template Message** | Connection: the **Coexistence** connection · Sender: the 7X number · Receiver: `{{3.recipient}}` · Template: `employee_birthday` / `work_anniversary` (en) · Body `{{1}}` = `{{3.name}}` · Body `{{2}}` (anniversary) = `{{1.THIS_YEAR - 3.joining_year}}` |
| — | Error handler on 12/32 | Data store › Delete a record (same key) → Excel › Update a Worksheet Row (row `{{3.row_no}}`: Send_Status `FAILED`, Error_Message `{{error.message}}`) → Excel › Add a Worksheet Row (Event_Log, Status FAILED) → **Ignore** |
| 13/33 | Data store › **Add/replace a record** | Same key · Overwrite = Yes · status `SENT` · message_id from module 12 (`messages[1].id`) |
| 14/34 | Microsoft 365 Excel › **Update a Worksheet Row** | Worksheet `Employees` · Row `{{3.row_no}}` · Birthday_Sent_Year (or Anniversary_Sent_Year) = `{{if(1.APP_MODE = "PRODUCTION"; 1.THIS_YEAR; 3.birthday_sent_year)}}` · Last_Message_Type `Birthday`/`Anniversary` · Last_Message_Date `{{1.NOW_TEXT}}` · Send_Status `{{if(1.APP_MODE = "PRODUCTION"; "SENT"; "TEST_SENT")}}` · Error_Message empty |
| 15/35 | Microsoft 365 Excel › **Add a Worksheet Row** | Worksheet `Event_Log` · Event_ID `{{3.employee_id}}_BIRTHDAY_{{1.THIS_YEAR}}` · Employee_ID · Event_Type · Event_Year · Scheduled_Date `{{1.TODAY_ISO}}` · Mode · Recipient (masked) · Message_ID · Status `SENT` · Created_At · Sent_At |

*Phrase format for `{{2}}`* (only if you approved the "completing {{2}} with 7X" variant):
`{{1.THIS_YEAR - 3.joining_year}} {{if(1.THIS_YEAR - 3.joining_year = 1; "year"; "years")}}`

*Arabic (optional):* add a filter `Language = AR` to a copy of each route that uses
`employee_birthday_ar` / `work_anniversary_ar` (language `ar`), and add `Language ≠ AR` to the
English routes. Leave this out until the Arabic templates are approved.

## Schedule (09:00 UAE)

1. Make → your avatar → **Profile** → **Time zone** = `(GMT+04:00) Asia/Dubai`.
   Also check **Organization → Settings → Time zone**.
2. Scenario → clock icon on module 1 → **Run scenario: Every day** → **Time: 09:00**.
3. Switch the scenario **ON** (toggle at bottom left) only after the TEST checks in
   `docs/SETUP_CHECKLIST.md` have passed.

## Scenario settings (gear icon)

* Sequential processing: **ON**
* Data is confidential: **ON** (hides employee data from Make's execution history)
* Allow storing of incomplete executions: **OFF** (prevents automatic re-execution of a half-finished send)
* Number of consecutive errors: 3
