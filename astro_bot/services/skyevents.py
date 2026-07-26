import logging
from datetime import date, datetime

import requests

from astro_bot.config import SKYEVENTS_URL

DECEMBER = 12
REQUEST_TIMEOUT = 30


def sync_years() -> list[int]:
    """Years to sync now: the current one, plus next year in December."""

    today = date.today()
    years = [today.year]
    if today.month == DECEMBER:
        years.append(today.year + 1)
    return years


def fetch_year(year: int) -> list[dict] | None:
    """Fetch one year of events from the skyevents /v1/events endpoint.

    Returns event dicts shaped like the DB rows the bot stores
    (uid, dt_utc, summary, description, url) when the year was served,
    or ``None`` when it was *not* — a network error, a non-2xx response
    (skyevents answers 503 while a year is still generating), or
    ``coverage: null`` (the year lies outside the generated range).

    The None-vs-list distinction matters to the caller's pruning: a year
    that could not be synced must not have its stored events deleted as
    "no longer returned". A year <= 366 days is well inside the
    endpoint's 400-day window cap, so one request per year is enough.
    """

    params = {"from": f"{year}-01-01", "to": f"{year + 1}-01-01"}
    try:
        response = requests.get(
            f"{SKYEVENTS_URL}/v1/events",
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as err:
        logging.exception(f"skyevents request failed for {year}: {err}")
        return None
    except ValueError as err:
        logging.exception(f"skyevents returned invalid JSON for {year}: {err}")
        return None

    if payload.get("coverage") is None:
        logging.warning(f"skyevents has not generated {year} yet, skipping")
        return None

    return [
        {
            "uid": event["uid"],
            "dt_utc": datetime.fromisoformat(event["dt_utc"]),
            "summary": event["summary"],
            "description": event.get("description", ""),
            "url": event.get("url", ""),
        }
        for event in payload.get("events", [])
    ]
