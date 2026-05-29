"""Display date formatting tests."""

from datetime import UTC, date, datetime

from app.utils.display_dates import format_display_date, format_display_datetime


def test_format_display_date_from_date() -> None:
    assert format_display_date(date(2026, 6, 15)) == "06-15-2026"


def test_format_display_date_from_iso_string() -> None:
    assert format_display_date("2026-06-15") == "06-15-2026"


def test_format_display_datetime() -> None:
    dt = datetime(2026, 6, 15, 14, 30, tzinfo=UTC)
    assert format_display_datetime(dt) == "06-15-2026 2:30 PM"
