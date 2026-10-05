@echo off
REM Daily run for Windows Task Scheduler (set the trigger to 09:00, computer clock in UAE time).
cd /d "%~dp0\.."
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python -m app.main %*
