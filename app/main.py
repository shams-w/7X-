"""Daily runner: spreadsheet -> birthday/anniversary logic -> WhatsApp -> results.

Usage (from the project folder):
    python -m app.main                       # normal daily run (uses .env)
    python -m app.main --dry-run             # show what would be sent, send nothing
    python -m app.main --date 2026-10-05     # pretend today is this date (testing)
    python -m app.main --send-test birthday  # one real test message to TEST_PHONE_NUMBER
    python -m app.main --reset-event EMP001_BIRTHDAY_2026   # allow an UNKNOWN event to be resent
"""

from __future__ import annotations

import argparse
import copy
import logging
import os
import sys
import time
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from app.anniversary import anniversary_event, is_anniversary_today
from app.birthday import birthday_event, is_birthday_today
from app.config import ConfigError, Settings, load_settings
from app.event_log import ClaimOutcome, EventLog
from app.models import (
    CelebrationEvent,
    Employee,
    EventStatus,
    EventType,
    RunSummary,
    make_event_id,
    mask_phone,
)
from app.spreadsheet import EmployeeWorkbook, SpreadsheetUnavailable
from app.whatsapp import WhatsAppService

log = logging.getLogger("7x")


# ------------------------------------------------------------------- logging
class _RedactFilter(logging.Filter):
    def __init__(self, secrets: list[str]):
        super().__init__()
        self.secrets = [s for s in secrets if s]

    def filter(self, record: logging.LogRecord) -> bool:
        if self.secrets:
            msg = record.getMessage()
            for secret in self.secrets:
                msg = msg.replace(secret, "***REDACTED***")
            record.msg, record.args = msg, None
        return True


def setup_logging(settings: Settings, verbose: bool = True) -> None:
    root = logging.getLogger("7x")
    root.handlers.clear()
    root.setLevel(logging.INFO)
    root.propagate = False
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S")
    redact = _RedactFilter([settings.whatsapp_access_token])
    handlers: list[logging.Handler] = []
    if verbose:
        handlers.append(logging.StreamHandler(sys.stdout))
    try:
        settings.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(settings.log_file_path, encoding="utf-8"))
    except OSError:
        pass
    for h in handlers:
        h.setFormatter(fmt)
        h.addFilter(redact)
        root.addHandler(h)


# ---------------------------------------------------------------- run lock
class AlreadyRunning(RuntimeError):
    pass


@contextmanager
def run_lock(lock_path: Path):
    """Prevent two daily runs from executing at the same time (any OS)."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(lock_path, "a+")
    try:
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise AlreadyRunning("Another run is already in progress.") from exc
        yield
    finally:
        fh.close()  # closing releases the lock


def stop_requested(settings: Settings) -> str | None:
    if not settings.automation_enabled:
        return "AUTOMATION_ENABLED=false"
    if settings.stop_file_path.exists():
        return f"STOP file present ({settings.stop_file_path.name})"
    return None


# ------------------------------------------------------------------ the run
def run_daily(settings: Settings, today: date | None = None,
              whatsapp: WhatsAppService | None = None) -> RunSummary:
    today = today or datetime.now(settings.tz).date()
    summary = RunSummary(run_date=today, mode=settings.app_mode, dry_run=settings.dry_run)

    reason = stop_requested(settings)
    if reason:
        summary.aborted = f"Automation stopped: {reason}. Nothing was sent."
        log.warning(summary.aborted)
        return summary

    settings.validate()
    log.info("Starting daily run for %s (%s)", today.isoformat(), settings.describe())
    if settings.is_test:
        log.info("TEST MODE: every message goes ONLY to TEST_PHONE_NUMBER %s",
                 mask_phone(settings.test_phone_number))

    try:
        with run_lock(settings.event_db_path.with_suffix(".lock")):
            _run_locked(settings, today, whatsapp or WhatsAppService(settings), summary)
    except AlreadyRunning as exc:
        summary.aborted = str(exc)
        log.error(summary.aborted)
    return summary


def _run_locked(settings: Settings, today: date, wa: WhatsAppService, summary: RunSummary) -> None:
    try:
        book = EmployeeWorkbook(settings.spreadsheet_path, settings.employees_sheet,
                                settings.event_log_sheet)
        employees = book.read_employees()
    except SpreadsheetUnavailable as exc:
        summary.aborted = f"Spreadsheet unavailable: {exc}"
        log.error(summary.aborted)
        return

    events_log = EventLog(settings.event_db_path, settings.audit_csv_path, settings.app_mode)
    summary.rows_read = len(employees)

    for emp in employees:
        if summary.aborted:
            break
        try:
            _process_employee(emp, today, settings, wa, book, events_log, summary)
        except Exception as exc:  # one bad row never stops the run
            msg = f"{emp.employee_id}: unexpected error {type(exc).__name__}: {exc}"
            log.exception(msg)
            summary.failed.append(msg)

    log.info("Run finished.")
    for line in summary.lines():
        log.info(line)


def _collect_events(emp: Employee, today: date, summary: RunSummary) -> list[CelebrationEvent]:
    events: list[CelebrationEvent] = []

    if emp.birthday is None:
        if emp.eligible:
            summary.data_errors.append(f"{emp.employee_id}: {emp.birthday_error}")
    elif is_birthday_today(emp.birthday, today):
        ev = birthday_event(emp, today)
        if ev:
            events.append(ev)
        else:
            summary.duplicates.append(
                f"{make_event_id(emp.employee_id, EventType.BIRTHDAY, today.year)} "
                "(spreadsheet says already sent this year)")

    jd = emp.joining_date
    if jd is None:
        if emp.eligible:
            summary.data_errors.append(f"{emp.employee_id}: {emp.joining_error}")
    elif jd > today:
        if emp.eligible:
            summary.data_errors.append(f"{emp.employee_id}: Joining_Date is in the future")
    elif is_anniversary_today(jd, today):
        ev = anniversary_event(emp, today)
        if ev:
            events.append(ev)
        elif today.year - jd.year < 1:
            summary.skipped.append(f"{emp.employee_id}: joined today - 0 years, no anniversary")
        else:
            summary.duplicates.append(
                f"{make_event_id(emp.employee_id, EventType.ANNIVERSARY, today.year)} "
                "(spreadsheet says already sent this year)")
    return events


def _process_employee(emp: Employee, today: date, settings: Settings, wa: WhatsAppService,
                      book: EmployeeWorkbook, events_log: EventLog, summary: RunSummary) -> None:
    events = _collect_events(emp, today, summary)
    if not events:
        return
    summary.events_found += len(events)

    if not emp.active:
        summary.skipped.extend(f"{e.event_id}: employee not Active" for e in events)
        return
    if not emp.consent:
        summary.skipped.extend(f"{e.event_id}: no WhatsApp consent" for e in events)
        return
    if emp.phone is None:
        for e in events:
            summary.data_errors.append(f"{e.event_id}: {emp.phone_error}")
        if not settings.dry_run:
            book.record_result(emp, status="DATA_ERROR", error=emp.phone_error or "Invalid phone")
            _safe_save(book)
        return

    for event in events:
        if summary.aborted:
            return
        _process_event(event, settings, wa, book, events_log, summary)


def _send(wa: WhatsAppService, event: CelebrationEvent):
    emp = event.employee
    if event.event_type is EventType.BIRTHDAY:
        return wa.send_birthday_message(emp.phone, emp.name, emp.language)
    return wa.send_anniversary_message(emp.phone, emp.name, event.years_completed, emp.language)


def _process_event(event: CelebrationEvent, settings: Settings, wa: WhatsAppService,
                   book: EmployeeWorkbook, events_log: EventLog, summary: RunSummary) -> None:
    emp = event.employee
    recipient = wa.resolve_recipient(emp.phone)

    # ---------------- DRY RUN: read-only duplicate check, no writes, no API call
    if settings.dry_run:
        state = events_log.check(event.event_id)
        if state is not ClaimOutcome.CLAIMED:
            summary.duplicates.append(f"{event.event_id} ({state.value})")
            log.info("[DRY RUN] Duplicate - would NOT send %s", event.describe())
            return
        log.info("Would send %s (to %s)", event.describe(), mask_phone(recipient))
        summary.would_send.append(f"{event.describe()} -> {mask_phone(recipient)}")
        events_log.audit(event, "DRY_RUN", recipient)
        return

    # ---------------- idempotency claim BEFORE sending
    claim = events_log.claim(event, recipient)
    if claim is ClaimOutcome.ALREADY_SENT:
        summary.duplicates.append(f"{event.event_id} (already SENT - not sent again)")
        log.info("Duplicate detected, NOT sending: %s", event.event_id)
        events_log.audit(event, "DUPLICATE_SKIPPED", recipient)
        return
    if claim is ClaimOutcome.IN_PROGRESS_OR_UNKNOWN:
        summary.unknown.append(f"{event.event_id} (previous attempt status unknown - not resent)")
        log.warning("Event %s has PENDING/UNKNOWN status; not resending automatically.",
                    event.event_id)
        events_log.audit(event, "SKIPPED_UNKNOWN", recipient)
        return

    log.info("Sending %s (to %s)", event.describe(), mask_phone(recipient))
    result = _send(wa, event)
    now = datetime.now(settings.tz)
    type_label = event.event_type.label
    sent_col = "Birthday_Sent_Year" if event.event_type is EventType.BIRTHDAY else "Anniversary_Sent_Year"

    if result.success:
        events_log.mark_sent(event.event_id, result.message_id)
        events_log.audit(event, "SENT", recipient, result.message_id)
        summary.sent.append(f"{event.describe()} -> {mask_phone(recipient)} "
                            f"(message id {result.message_id})")
        if settings.is_production:
            book.record_result(emp, message_type=type_label, status="SENT",
                               sent_year_column=sent_col, year=event.year, when=now)
        else:  # TEST mode never marks the real employee as celebrated
            book.record_result(emp, message_type=type_label, status="TEST_SENT", when=now)
        status, error = EventStatus.SENT.value, ""
        if settings.send_delay_seconds > 0:
            time.sleep(settings.send_delay_seconds)
    else:
        if result.retryable:
            events_log.mark_failed(event.event_id, result.error)
            status = EventStatus.FAILED.value
            summary.failed.append(f"{event.event_id}: {result.error}")
        else:
            events_log.mark_unknown(event.event_id, result.error)
            status = EventStatus.UNKNOWN.value
            summary.unknown.append(f"{event.event_id}: {result.error}")
        error = result.error or "Unknown error"
        log.error("Send failed for %s: %s", event.event_id, error)
        events_log.audit(event, status, recipient, error=error)
        book.record_result(emp, status=status, error=error)  # Sent_Year is NOT touched
        if result.fatal:
            summary.aborted = f"Stopped after fatal error: {error}"

    book.append_event_log({
        "Event_ID": event.event_id, "Employee_ID": emp.employee_id,
        "Event_Type": event.event_type.value, "Event_Year": event.year,
        "Scheduled_Date": event.scheduled_date.isoformat(), "Mode": settings.app_mode,
        "Recipient": mask_phone(recipient), "Message_ID": result.message_id or "",
        "Status": status, "Created_At": now.strftime("%Y-%m-%d %H:%M:%S"),
        "Sent_At": now.strftime("%Y-%m-%d %H:%M:%S") if result.success else "",
        "Error": error,
    })
    _safe_save(book)


def _safe_save(book: EmployeeWorkbook) -> None:
    """Saving the sheet must never cause a resend: the SQLite log already holds the truth."""
    try:
        book.save()
    except SpreadsheetUnavailable as exc:
        log.error("%s - results are still safe in the event log database.", exc)


# ------------------------------------------------------------- send one test
def send_test_message(settings: Settings, kind: str, name: str, years: int = 3) -> int:
    test_settings = copy.copy(settings)
    test_settings.app_mode = "TEST"  # force: a test message can only reach TEST_PHONE_NUMBER
    test_settings.dry_run = False
    test_settings.validate(require_whatsapp=True)
    wa = WhatsAppService(test_settings)
    if kind == "birthday":
        result = wa.send_birthday_message(test_settings.test_phone_number, name)
    else:
        result = wa.send_anniversary_message(test_settings.test_phone_number, name, years)
    if result.success:
        log.info("Test %s message sent to %s - WhatsApp message id %s",
                 kind, mask_phone(result.recipient), result.message_id)
        return 0
    log.error("Test message FAILED: %s", result.error)
    return 1


# ----------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="7X Executive Connect daily celebration run")
    parser.add_argument("--dry-run", action="store_true", help="force dry run (send nothing)")
    parser.add_argument("--date", help="pretend today is YYYY-MM-DD (for testing)")
    parser.add_argument("--env-file", help="path to an alternative .env file")
    parser.add_argument("--send-test", choices=["birthday", "anniversary"],
                        help="send ONE real test message to TEST_PHONE_NUMBER and exit")
    parser.add_argument("--name", default="Shams Test", help="name used with --send-test")
    parser.add_argument("--reset-event", metavar="EVENT_ID",
                        help="mark an UNKNOWN/PENDING event as FAILED so the next run may resend it")
    args = parser.parse_args(argv)

    settings = load_settings(args.env_file)
    if args.dry_run:
        settings.dry_run = True
    setup_logging(settings)

    try:
        if args.send_test:
            return send_test_message(settings, args.send_test, args.name)
        if args.reset_event:
            ok = EventLog(settings.event_db_path, settings.audit_csv_path,
                          settings.app_mode).reset(args.reset_event.strip().upper())
            log.info("Reset %s: %s", args.reset_event, "done" if ok else "nothing to reset")
            return 0 if ok else 1
        today = date.fromisoformat(args.date) if args.date else None
        summary = run_daily(settings, today=today)
    except ConfigError as exc:
        log.error(str(exc))
        return 2

    if summary.aborted:
        return 0 if summary.aborted.startswith("Automation stopped") else 2
    return 1 if (summary.failed or summary.unknown) else 0


if __name__ == "__main__":
    sys.exit(main())
