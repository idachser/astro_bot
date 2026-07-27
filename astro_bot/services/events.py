from datetime import date, datetime, time, timedelta, timezone

from astro_bot.services.skyevents import fetch_range
from astro_bot.timezones import resolve_timezone


def get_events_on_day(day: date, tz: str = "") -> list | None:
    """Events of the day in the given timezone (UTC by default) as
    (dt_utc, summary, description, url) tuples, or None when skyevents
    could not answer -- which the caller must not render as "no events".

    A local day is not a whole UTC day: it maps to a UTC interval that
    straddles two UTC dates (three across a DST shift, which stretches
    the day to 25 hours). The service takes whole dates, so ask for every
    date the interval touches and cut to the exact instants here.
    """

    start = datetime.combine(day, time.min, resolve_timezone(tz))
    end = start + timedelta(days=1)
    start_utc = start.astimezone(timezone.utc)
    end_utc = end.astimezone(timezone.utc)

    events = fetch_range(start_utc.date(), end_utc.date() + timedelta(days=1))
    if events is None:
        return None

    return [
        event
        for event in events
        if start_utc <= datetime.fromisoformat(event[0]) < end_utc
    ]


def get_events_between(start: date, end: date) -> list | None:
    """Events for a UTC date range (inclusive), ordered by time, or None
    when skyevents could not answer. `fetch_range` is exclusive at the
    top, so ask for the day after `end`."""

    return fetch_range(start, end + timedelta(days=1))
