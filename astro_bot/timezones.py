import logging
from datetime import date, datetime, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def resolve_timezone(tz_name: str) -> tzinfo:
    """User timezone by IANA name, falling back to UTC"""

    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, ValueError):
            logging.warning(f"Unknown timezone: {tz_name}")
    return timezone.utc


def today_in(tz_name: str) -> date:
    """Today's date in the given zone: a user's "today" is their own
    local day, never the server's"""

    return datetime.now(resolve_timezone(tz_name)).date()


def is_date_only(dt: datetime) -> bool:
    """The ICS feed normalizes date-only events to exactly midnight
    UTC (see ics_feed.parse_calendar); treat that instant as "time
    unknown". The feed's timed events carry second precision, so a
    real event landing on 00:00:00 sharp is the rare blind spot."""

    return (dt.hour, dt.minute, dt.second) == (0, 0, 0)
