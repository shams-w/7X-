"""Birthday rules: match DAY + MONTH only, ignore birth year."""

from __future__ import annotations

from datetime import date

from app.models import CelebrationEvent, Employee, EventType, celebration_date_in_year


def is_birthday_today(birthday: date | None, today: date) -> bool:
    if birthday is None:
        return False
    return celebration_date_in_year(birthday.month, birthday.day, today.year) == today


def birthday_event(employee: Employee, today: date) -> CelebrationEvent | None:
    """Return a birthday event if one is due today and not yet marked as sent this year."""
    if not is_birthday_today(employee.birthday, today):
        return None
    if employee.birthday_sent_year == today.year:
        return None
    return CelebrationEvent(employee, EventType.BIRTHDAY, today.year, today)
