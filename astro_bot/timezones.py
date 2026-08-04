import logging
import threading
from datetime import date, datetime, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from timezonefinder import TimezoneFinder

# One finder per thread, not per process. `zone_for_location` runs on
# asyncio.to_thread workers, and timezonefinder is explicit that an
# instance must not be shared across threads ("can lead to race
# conditions and incorrect results" -- timezonefinder.py). The package
# also ships a "thread-safe" global singleton that does share one, which
# contradicts its own class docs; not worth the bet, because a race here
# writes a wrong zone into the user's profile and silently skews every
# day they ask for afterwards, with nothing in the logs.
_finders = threading.local()


def _location_finder() -> TimezoneFinder:
    """The calling thread's finder, built on first use.

    Building one maps the boundary data and costs the better part of a
    second, against microseconds for a lookup, so it is worth keeping --
    `/start` used to build a fresh one per shared location, on the event
    loop. Per thread the cost lands once, and off the loop.
    """

    finder = getattr(_finders, "finder", None)
    if finder is None:
        finder = _finders.finder = TimezoneFinder()
    return finder


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
