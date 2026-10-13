"""Holiday calendar + weekly-holiday settings (Sunday and Saturday are both admin-configurable)."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import AttendanceSettings, Holiday

SUNDAY = 6  # date.weekday(): Monday=0 ... Sunday=6
SATURDAY = 5


def get_settings_row(db: Session) -> AttendanceSettings:
    row = db.get(AttendanceSettings, 1)
    if row is None:
        row = AttendanceSettings(id=1, sunday_holiday=True, saturday_holiday=False)
        db.add(row)
        db.commit()
    return row


def is_weekly_holiday(db: Session, d: date) -> bool:
    settings = get_settings_row(db)
    if d.weekday() == SUNDAY:
        return settings.sunday_holiday
    return d.weekday() == SATURDAY and settings.saturday_holiday


def holiday_dates(db: Session, date_from: date, date_to: date) -> set[date]:
    """One-off admin-added holidays in range, as a set for O(1) membership checks."""
    rows = db.scalars(select(Holiday.date).where(Holiday.date >= date_from, Holiday.date <= date_to))
    return set(rows)


def is_holiday(db: Session, d: date) -> bool:
    if is_weekly_holiday(db, d):
        return True
    return db.scalar(select(Holiday).where(Holiday.date == d)) is not None
