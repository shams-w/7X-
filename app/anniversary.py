"""Work-anniversary rules."""

from __future__ import annotations

from datetime import date

from app.models import CelebrationEvent, Employee, EventType, celebration_date_in_year


def years_completed(joining_date: date, today: date) -> int:
    """Years_Completed = current year - joining year."""
    return today.year - joining_date.year


def is_anniversary_today(joining_date: date | None, today: date) -> bool:
    if joining_date is None:
        return False
    return celebration_date_in_year(joining_date.month, joining_date.day, today.year) == today


def anniversary_event(employee: Employee, today: date) -> CelebrationEvent | None:
    """Return an anniversary event if due today, >= 1 year, and not yet sent this year."""
    jd = employee.joining_date
    if jd is None or jd > today:
        return None
    if not is_anniversary_today(jd, today):
        return None
    years = years_completed(jd, today)
    if years < 1:
        return None
    if employee.anniversary_sent_year == today.year:
        return None
    return CelebrationEvent(employee, EventType.ANNIVERSARY, today.year, today, years_completed=years)
