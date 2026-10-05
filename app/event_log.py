"""Idempotency store + audit trail.

* SQLite table `events` with PRIMARY KEY (mode, event_id) is the single source of
  truth for "has this celebration already been sent?". A row is CLAIMED (PENDING)
  *before* the WhatsApp call, inside a transaction, so a second run - parallel,
  retried, restarted or manual - cannot send the same event again.
* `audit_log.csv` is an append-only, human-readable record of every attempt.

Event_ID format: EMP001_BIRTHDAY_2026. TEST and PRODUCTION use separate
namespaces so test runs never block real messages after go-live.
"""

from __future__ import annotations

import csv
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from app.models import CelebrationEvent, EventStatus

AUDIT_COLUMNS = [
    "Timestamp", "Mode", "Event_ID", "Employee_ID", "Event_Type", "Year",
    "Result", "Recipient", "WhatsApp_Message_ID", "Error",
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    mode            TEXT NOT NULL,
    event_id        TEXT NOT NULL,
    employee_id     TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    event_year      INTEGER NOT NULL,
    scheduled_date  TEXT NOT NULL,
    recipient       TEXT,
    message_id      TEXT,
    status          TEXT NOT NULL,
    attempts        INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL,
    sent_at         TEXT,
    error           TEXT,
    PRIMARY KEY (mode, event_id)
);
"""


class ClaimOutcome(str, Enum):
    CLAIMED = "CLAIMED"  # new event (or retry of a definite failure) -> go ahead and send
    ALREADY_SENT = "ALREADY_SENT"
    IN_PROGRESS_OR_UNKNOWN = "IN_PROGRESS_OR_UNKNOWN"  # PENDING/UNKNOWN -> never resend automatically


@dataclass
class EventRecord:
    event_id: str
    status: str
    message_id: str | None
    attempts: int
    error: str | None


class EventLog:
    def __init__(self, db_path: Path, audit_csv_path: Path, mode: str):
        self.db_path = Path(db_path)
        self.audit_csv_path = Path(audit_csv_path)
        self.mode = mode
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.audit_csv_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        return conn

    @staticmethod
    def _now() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")

    # ------------------------------------------------------------------ reads
    def get(self, event_id: str) -> EventRecord | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT event_id, status, message_id, attempts, error FROM events "
                "WHERE mode=? AND event_id=?", (self.mode, event_id),
            ).fetchone()
        return EventRecord(*row) if row else None

    def check(self, event_id: str) -> ClaimOutcome:
        """Read-only duplicate check (used by dry runs)."""
        rec = self.get(event_id)
        if rec is None or rec.status == EventStatus.FAILED.value:
            return ClaimOutcome.CLAIMED
        if rec.status == EventStatus.SENT.value:
            return ClaimOutcome.ALREADY_SENT
        return ClaimOutcome.IN_PROGRESS_OR_UNKNOWN

    # ----------------------------------------------------------------- writes
    def claim(self, event: CelebrationEvent, recipient: str) -> ClaimOutcome:
        """Atomically reserve an event before sending it."""
        now = self._now()
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")  # exclusive write lock across processes
            try:
                row = conn.execute(
                    "SELECT status FROM events WHERE mode=? AND event_id=?",
                    (self.mode, event.event_id),
                ).fetchone()
                if row is None:
                    conn.execute(
                        "INSERT INTO events (mode, event_id, employee_id, event_type, event_year,"
                        " scheduled_date, recipient, status, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                        (self.mode, event.event_id, event.employee.employee_id,
                         event.event_type.value, event.year, event.scheduled_date.isoformat(),
                         recipient, EventStatus.PENDING.value, now),
                    )
                    outcome = ClaimOutcome.CLAIMED
                elif row[0] == EventStatus.FAILED.value:
                    conn.execute(
                        "UPDATE events SET status=?, attempts=attempts+1, error=NULL, recipient=? "
                        "WHERE mode=? AND event_id=?",
                        (EventStatus.PENDING.value, recipient, self.mode, event.event_id),
                    )
                    outcome = ClaimOutcome.CLAIMED
                elif row[0] == EventStatus.SENT.value:
                    outcome = ClaimOutcome.ALREADY_SENT
                else:
                    outcome = ClaimOutcome.IN_PROGRESS_OR_UNKNOWN
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        return outcome

    def _finish(self, event_id: str, status: EventStatus, message_id=None, error=None) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE events SET status=?, message_id=?, error=?, sent_at=? "
                "WHERE mode=? AND event_id=?",
                (status.value, message_id, error,
                 self._now() if status is EventStatus.SENT else None, self.mode, event_id),
            )

    def mark_sent(self, event_id: str, message_id: str) -> None:
        self._finish(event_id, EventStatus.SENT, message_id=message_id)

    def mark_failed(self, event_id: str, error: str) -> None:
        self._finish(event_id, EventStatus.FAILED, error=error)

    def mark_unknown(self, event_id: str, error: str) -> None:
        self._finish(event_id, EventStatus.UNKNOWN, error=error)

    def reset(self, event_id: str) -> bool:
        """Manual override: mark an UNKNOWN/PENDING event as FAILED so it may be resent."""
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "UPDATE events SET status=?, error=COALESCE(error,'') || ' [manually reset]' "
                "WHERE mode=? AND event_id=? AND status IN (?,?)",
                (EventStatus.FAILED.value, self.mode, event_id,
                 EventStatus.PENDING.value, EventStatus.UNKNOWN.value),
            )
            return cur.rowcount > 0

    # ------------------------------------------------------------------ audit
    def audit(self, event: CelebrationEvent, result: str, recipient: str | None = None,
              message_id: str | None = None, error: str | None = None) -> None:
        """Append one line to the CSV audit trail (no birthdays / no full phone numbers)."""
        from app.models import mask_phone

        new_file = not self.audit_csv_path.exists()
        with self.audit_csv_path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            if new_file:
                writer.writerow(AUDIT_COLUMNS)
            writer.writerow([
                self._now(), self.mode, event.event_id, event.employee.employee_id,
                event.event_type.value, event.year, result, mask_phone(recipient),
                message_id or "", (error or "")[:500],
            ])
