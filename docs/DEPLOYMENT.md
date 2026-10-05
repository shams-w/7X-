# Deployment recommendation

## ✅ Recommended: Make.com only

| Need | Make.com |
|---|---|
| Official WhatsApp + Coexistence | Yes, the WhatsApp Business Cloud app has a Coexistence connection type |
| Microsoft 365 Excel | Yes (List / Update / Add Worksheet Row) |
| Daily 09:00 Asia/Dubai | Built-in scheduler |
| Duplicate protection | Data store with unique key per event |
| No server, no code to host | Yes |
| Cost | Volume is a few messages a day, so the Free or Core plan is enough |

No server, no GitHub job, no Render. Nothing to patch.

## Python fallback: when and where

Use it only if Make isn't allowed in 7X, or as a backup. **Never run Make and Python live at the same time.**

The Python job needs the employee workbook on the machine where it runs. Don't use
GitHub Actions or a public cloud job for production, because the real spreadsheet must
never be uploaded to GitHub. Good options:
* a 7X Windows PC or server that is always on → **Task Scheduler**: daily 09:00, action `scripts\run_daily.bat`, "Run whether user is logged on or not"
* a 7X Linux VM → `crontab -e`:
  ```
  CRON_TZ=Asia/Dubai
  0 9 * * * /opt/7x-executive-connect/scripts/run_daily.sh >> /opt/7x-executive-connect/logs/cron.log 2>&1
  ```

Install:
```
python -m venv .venv
.venv\Scripts\activate        (Windows)   |   source .venv/bin/activate   (Linux/macOS)
pip install -r requirements.txt
copy .env.example .env        (Windows)   |   cp .env.example .env
```

## GitHub
The repository holds code, tests, the blueprint and docs only. The included GitHub Actions
workflow (`.github/workflows/tests.yml`) just runs the tests and the offline simulation.
It has no secrets, no employee data, and never sends messages.
