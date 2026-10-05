# Security & data protection

This project handles **employee personal data** (names, phone numbers, birth dates) and a
**credential that can send messages from the official 7X number**. Treat both as confidential.

## Where credentials belong

| Credential | Where it lives | Never |
|---|---|---|
| Make → WhatsApp connection | Inside Make (Connections), created by the Coexistence signup | Exported, screenshotted or shared |
| Make → Microsoft 365 connection | Inside Make (Connections) | Using a personal Microsoft account |
| Python `WHATSAPP_ACCESS_TOKEN` | `.env` on the one machine that runs the job (file readable only by the service account), or a secrets manager | In git, email, chat, tickets, screenshots, or the spreadsheet |
| Meta Business Portfolio admin | Named 7X staff with 2-factor authentication | Shared logins |

* `.env`, `secrets/`, `*.xlsx`, `employee_data/`, `logs/*` and `data/*` are listed in `.gitignore`.
  The only spreadsheet allowed in git is `sample_data/7X_Employees_SAMPLE.xlsx`, which has **fake** people.
* The code never prints the token. Log lines pass through a redaction filter, and Meta error messages are cleaned before they're stored.
* Turn on **two-factor authentication** for Facebook/Meta, Make.com and Microsoft 365 accounts that can reach this setup.

## How employee data is handled

* **Store** the real workbook only in a restricted 7X OneDrive/SharePoint folder (HR + automation owner). Turn off "anyone with the link" sharing.
* **Minimum data:** only the columns in the template. Don't add national ID, salary, address or similar.
* **Consent:** send only when `WhatsApp_Consent = YES`. Record consent through HR's normal process. If someone says stop, set `NO` the same day.
* **Leavers:** set `Active = NO`. Remove their row once HR's retention period ends.
* **Logs** (`Event_Log`, `audit_log.csv`, `automation.log`) contain Employee_ID, event type, year, a masked phone (`+97150****567`), the WhatsApp message ID and errors. They contain **no birth dates** and no full phone numbers.
* **Make:** enable *Data is confidential* in the scenario settings, so execution history doesn't keep the employee data.
* **Test data:** tests and the simulation use fake people only. Never copy the real workbook into `tests/` or `sample_data/`.
* Keep audit logs for 12 months (or per 7X policy), then delete them.

## How to rotate WhatsApp credentials

**Make (Coexistence connection):**
1. Make → **Connections** → `7X WhatsApp Coexistence` → **Reauthorize**. Do this whenever Meta or Make reports the connection as invalid, and whenever an admin leaves.

**Python system-user token** (rotate every 90 days, and immediately if exposed):
1. https://business.facebook.com/settings → **Users → System users** → `7x-automation`.
2. **Generate new token** → same app → permissions `whatsapp_business_messaging`, `whatsapp_business_management`.
3. Paste it into `.env` on the server (`WHATSAPP_ACCESS_TOKEN=`).
4. Test: `python -m app.main --send-test birthday` (goes to the TEST phone).
5. Back on the System user page → **Revoke** the old token.

**If a token leaks:** revoke it first (step 5), then create a new one. Check WhatsApp Manager → Insights for unexpected sends.

## How to switch TEST → PRODUCTION safely

1. Finish `docs/SETUP_CHECKLIST.md` (TEST mode, duplicate test included).
2. Have a second person review `docs/PRODUCTION_LAUNCH_CHECKLIST.md`.
3. Run a dry run on the real sheet (`python -m app.main --dry-run`, or check today's and tomorrow's dates by hand for Make).
4. Make: set `APP_MODE` = `PRODUCTION` in module 1. Python: set `APP_MODE=PRODUCTION` **and**
   `PRODUCTION_CONFIRM=I_UNDERSTAND_REAL_EMPLOYEES_WILL_RECEIVE_MESSAGES` and `DRY_RUN=false`.
   Anything else (typos, other values) makes the Python program refuse to start.
5. Only one system live: Make **or** Python.
6. To go back: set `APP_MODE=TEST`. Messages then go only to the test phone again.

## Meta account safety (the official 7X number)

* Never delete the WhatsApp account, the number, or the business profile while working on this.
* Never use the "Cloud API" connection type with the existing number (migration). Use **Coexistence**.
* Don't change the display name or verify a new number without management approval.
* Template messages respect Meta's policies: opted-in recipients only, and no promotional content in these greetings.

## Reporting a problem
Tell the automation owner, and switch the scenario OFF (`docs/EMERGENCY_STOP.md`) if messages may be going to the wrong people.
