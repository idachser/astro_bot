import logging
from datetime import date, datetime, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from timezonefinder import TimezoneFinder

_finder = None


def _location_finder() -> TimezoneFinder:
    """Built once and kept. The constructor maps the boundary data and
    costs the better part of a second, against microseconds for a
    lookup -- `/start` used to build a fresh one per shared location."""

    global _finder
    if _finder is None:
        _finder = TimezoneFinder()
    return _finder


def zone_for_location(lat: float, lon: float) -> str:
    """IANA zone name for a shared location, "" if it cannot be placed.

    timezonefinder covers open water as well as land (at sea it answers
    with the nominal `Etc/GMT±N` for the longitude), so in practice this
    always resolves. The empty string is kept as the same "no zone, show
    UTC" that the Default time button stores, not as an error.
    """

    return _location_finder().timezone_at(lng=lon, lat=lat) or ""


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
    """skyevents emits date-only events (meteor shower peaks, some
    comet dates) at exactly midnight UTC; treat that instant as "time
    unknown". Timed events carry sub-second precision, so a real event
    landing on 00:00:00 sharp is the rare blind spot."""

    return (dt.hour, dt.minute, dt.second) == (0, 0, 0)
