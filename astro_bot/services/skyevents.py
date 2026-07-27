import logging
import threading
import time as clock
from datetime import date, datetime, time, timezone

import requests

from astro_bot.config import EVENTS_CACHE_TTL_SECONDS, SKYEVENTS_URL

# Windows are days wide, and a user is waiting on the other end: a
# request that hangs holds a worker thread out of the shared to_thread
# pool for the whole timeout
REQUEST_TIMEOUT = 10

# Day handlers reach this from asyncio.to_thread, so the cache is shared
# by worker threads: every read, prune and write goes through the lock or
# a concurrent insert breaks the prune mid-iteration
_cache: dict = {}
_cache_lock = threading.Lock()


def _midnight(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=timezone.utc)


def _covers(coverage: dict, start: date, end: date) -> bool:
    """Whether `coverage` spans the whole window that was asked for.

    A window overlapping the generated years is not refused: the service
    clamps its answer to the overlap (`covered_start = max(...)`,
    `covered_end = min(...)`) and reports that in `coverage`, which is
    then *not* null. So a request straddling the edge -- 31 December
    before next year finished generating, or a January "yesterday" after
    past years dropped out of coverage -- comes back with half its window
    silently missing, and the bot would render that as a quiet sky.
    Anything short of full coverage is "cannot answer".
    """

    return (
        datetime.fromisoformat(coverage["from"]) <= _midnight(start)
        and datetime.fromisoformat(coverage["to"]) >= _midnight(end)
    )


def _request_range(start: date, end: date) -> list | None:
    """Ask skyevents for `start <= dt_utc < end` (`end` exclusive, as the
    endpoint itself defines the window) and return the rows the bot
    renders: (dt_utc, summary, description, url), ordered by time.

    Returns ``None`` -- never an empty list, and never a raise -- when the
    service could not answer: a network error, a non-2xx response (it
    answers 503 while a year is still generating), coverage that does not
    span the request, or a payload shaped unexpectedly. The caller must
    tell that apart from a day that genuinely has no events, and callers
    all the way up sit behind `asyncio.to_thread` in a handler with no
    error handling of its own -- an escaping exception means the user
    gets no reply at all instead of "try later".
    """

    params = {"from": start.isoformat(), "to": end.isoformat()}
    try:
        response = requests.get(
            f"{SKYEVENTS_URL}/v1/events",
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as err:
        logging.exception(f"skyevents request failed for {params}: {err}")
        return None
    except ValueError as err:
        logging.exception(f"skyevents returned invalid JSON: {err}")
        return None

    try:
        coverage = payload["coverage"]
        if coverage is None:
            logging.warning(f"skyevents has not generated {params} yet")
            return None
        if not _covers(coverage, start, end):
            logging.warning(f"skyevents covers only {coverage} of {params}")
            return None

        events = [
            (
                event["dt_utc"],
                event["summary"],
                event.get("description", ""),
                event.get("url", ""),
            )
            for event in payload["events"]
        ]
        return sorted(
            events, key=lambda event: datetime.fromisoformat(event[0])
        )
    except (AttributeError, KeyError, TypeError, ValueError) as err:
        # every field the payload is trusted for is read in here: a null
        # dt_utc, a date that does not parse, a JSON array where an
        # object belongs -- all of it is "the service did not answer"
        logging.exception(f"skyevents returned an unexpected shape: {err}")
        return None


def _prune_expired(now: float) -> None:
    """Caller must hold _cache_lock"""

    expired = [
        key
        for key, (stored_at, _) in _cache.items()
        if now - stored_at >= EVENTS_CACHE_TTL_SECONDS
    ]
    for key in expired:
        del _cache[key]


def fetch_range(start: date, end: date) -> list | None:
    """Cached for an hour, keyed on the exact range: a day re-opened, or
    opened by another user in the same zone, is free, but paging across a
    week asks once per day -- each day is its own window. Coarser keys
    would collapse that into one request; not worth the windowing it
    takes while skyevents is a request away on the same host.

    Failures are not cached, so an outage heals as soon as skyevents is
    back. Expired entries are pruned on every call to keep the cache
    bounded. The request itself runs outside the lock: two threads may
    fetch the same range at once, but holding it across a slow HTTP call
    would stall every other user."""

    key = (start, end)
    now = clock.monotonic()
    with _cache_lock:
        _prune_expired(now)
        cached = _cache.get(key)
    if cached:
        return cached[1]

    events = _request_range(start, end)
    if events is not None:
        with _cache_lock:
            _cache[key] = (now, events)
    return events
