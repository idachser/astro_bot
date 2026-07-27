import logging
import threading
import time
from datetime import date, datetime

import requests

from astro_bot.config import EVENTS_CACHE_TTL_SECONDS, SKYEVENTS_URL

REQUEST_TIMEOUT = 30

# Day handlers reach this from asyncio.to_thread, so the cache is shared
# by worker threads: every read, prune and write goes through the lock or
# a concurrent insert breaks the prune mid-iteration
_cache: dict = {}
_cache_lock = threading.Lock()


def _request_range(start: date, end: date) -> list | None:
    """Ask skyevents for `start <= dt_utc < end` (`end` exclusive, as the
    endpoint itself defines the window) and return the rows the bot
    renders: (dt_utc, summary, description, url), ordered by time.

    Returns ``None`` -- never an empty list -- when the service could not
    answer: a network error, a non-2xx response (it answers 503 while a
    year is still generating), ``coverage: null`` (the range lies outside
    the generated years), or a payload shaped unexpectedly. The caller
    must tell that apart from a day that genuinely has no events.
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

    if payload.get("coverage") is None:
        logging.warning(f"skyevents does not cover {params} yet")
        return None

    try:
        events = [
            (
                event["dt_utc"],
                event["summary"],
                event.get("description", ""),
                event.get("url", ""),
            )
            for event in payload["events"]
        ]
    except (KeyError, TypeError) as err:
        logging.exception(f"skyevents returned an unexpected shape: {err}")
        return None

    return sorted(events, key=lambda event: datetime.fromisoformat(event[0]))


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
    """Cached for an hour so week browsing doesn't hit the service on
    every click; failures are not cached, so an outage heals as soon as
    skyevents is back. Expired entries are pruned on every call to keep
    the cache bounded. The request itself runs outside the lock: two
    threads may fetch the same range at once, but holding it across a
    30s HTTP call would stall every other user."""

    key = (start, end)
    now = time.monotonic()
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
