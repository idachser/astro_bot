import logging
from datetime import timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def resolve_timezone(tz_name: str) -> tzinfo:
    """User timezone by IANA name, falling back to UTC"""

    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, ValueError):
            logging.warning(f"Unknown timezone: {tz_name}")
    return timezone.utc
