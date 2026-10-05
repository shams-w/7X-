# 🛑 Emergency stop — stop all messages immediately

Use any **one** of these. The first one for your setup is the fastest.

## Make.com (main system) — 10 seconds
1. Open **https://www.make.com** → **Scenarios**.
2. Find **7X Executive Connect - Daily Celebrations**.
3. Click the **ON/OFF toggle** so it shows **OFF**.

Nothing else runs until you turn it back on. If a run is happening right now, open the
scenario and click **Stop** at the bottom.

**Safer intermediate option:** set module 1 `APP_MODE` = `TEST`. All messages then go only to the test phone.

## Python fallback — any one of:
* Create an empty file named **`STOP`** in the project folder. The next run exits without sending.
* In `.env`, set `AUTOMATION_ENABLED=false`.
* Remove the scheduled task (Windows Task Scheduler → disable the task / Linux `crontab -e` → delete the line).

## Cut WhatsApp access completely (strongest)
* **Make:** Make → **Connections** → `7X WhatsApp Coexistence` → **Delete / Revoke**.
  This does **not** affect the phone app.
* **Python token:** https://business.facebook.com/settings → **Users → System users** →
  `7x-automation` → **Revoke tokens**.
* ⚠️ Do **not** disconnect Business Platform in the phone app, and do not delete the WhatsApp
  account, unless you really want to end the API connection. Neither is needed to stop
  messages.

## Wrong person got a message?
1. Stop (above).
2. In the phone app you can delete the message for everyone (normal WhatsApp limits apply).
3. Check `Event_Log` to see who received what, and fix the sheet.
4. Turn back on in `TEST` mode first.
