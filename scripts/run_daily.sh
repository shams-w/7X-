#!/usr/bin/env bash
# Daily run for Linux/macOS cron. Example crontab line (09:00 Asia/Dubai):
#   CRON_TZ=Asia/Dubai
#   0 9 * * * /opt/7x-executive-connect/scripts/run_daily.sh
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -d .venv ]; then source .venv/bin/activate; fi
exec python -m app.main "$@"
