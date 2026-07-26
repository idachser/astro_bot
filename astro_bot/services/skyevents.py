import logging
from datetime import date, datetime

import requests

from astro_bot.config import SKYEVENTS_URL

DECEMBER = 12
REQUEST_TIMEOUT = 30


def fetch_year(year: int) -> list[dict]:
    """Fetch one year of events from the skyevents /v1/events endpoint.

    Returns event dicts shaped like the DB rows the bot stores
    (uid, dt_utc, summary, description, url), or an empty list on any
    condition where syncing this year is not safe:

    - a network error or non-2xx response (skyevents answers 503 while a
      requested year is still being generated in the background);
    - `coverage: null`, which means the year lies outside the generated
      range -- "not computed", *not* "no events", so we skip it rather
      than let an empty result look authoritative. Upsert-only sync means
      a skipped year simply keeps whatever is already stored.
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
        return []
    except ValueError as err:
        logging.exception(f"skyevents returned invalid JSON for {year}: {err}")
        return []

    if payload.get("coverage") is None:
        logging.warning(f"skyevents has not generated {year} yet, skipping")
        return []

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


def fetch_events() -> list[dict]:
    """Events for the current year, and for the next one in December.

    A year is <= 366 days, comfortably inside the endpoint's 400-day
    window cap, so one request per year is enough.
    """

    today = date.today()
    years = [today.year]
    if today.month == DECEMBER:
        years.append(today.year + 1)

    events = []
    for year in years:
        events.extend(fetch_year(year))

    return events
