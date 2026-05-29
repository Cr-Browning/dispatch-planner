"""User-facing date/time formatting (MM-DD-YYYY)."""

from __future__ import annotations

from datetime import date, datetime


def format_display_date(value: date | datetime | str | None) -> str:
    """Format a date as MM-DD-YYYY."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    elif isinstance(value, str):
        text = value.strip()
        if "T" in text:
            text = text.split("T", 1)[0]
        if len(text) >= 10 and text[4] == "-":
            year, month, day = (int(part) for part in text[:10].split("-"))
            return f"{month:02d}-{day:02d}-{year:04d}"
        return text
    return f"{value.month:02d}-{value.day:02d}-{value.year:04d}"


def format_display_datetime(value: datetime | None) -> str:
    """Format a datetime as MM-DD-YYYY h:mm AM/PM."""
    if value is None:
        return ""
    hour = value.hour % 12 or 12
    am_pm = "AM" if value.hour < 12 else "PM"
    return f"{format_display_date(value)} {hour}:{value.minute:02d} {am_pm}"


def format_display_time(value: datetime | None) -> str:
    """Format clock time as h:mm AM/PM."""
    if value is None:
        return ""
    hour = value.hour % 12 or 12
    am_pm = "AM" if value.hour < 12 else "PM"
    return f"{hour}:{value.minute:02d} {am_pm}"
