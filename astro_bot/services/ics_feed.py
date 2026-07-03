import html
import logging
from datetime import date, datetime, timezone

import requests
from icalendar import Calendar

from astro_bot.config import ICS_FEED_URL

DECEMBER = 12
REQUEST_TIMEOUT = 30


def fetch_calendar(year: int) -> Calendar | None:
    """Download the in-the-sky.org events calendar for the given year"""

    url = ICS_FEED_URL.format(year=year)
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return Calendar.from_ical(response.content)
    except requests.RequestException as err:
        logging.exception(f"ICS feed request failed: {err}")
    except ValueError as err:
        logging.exception(f"ICS feed is not valid iCalendar: {err}")


def parse_calendar(calendar: Calendar) -> list[dict]:
    """Convert VEVENT components to dicts with UTC datetimes"""

    events = []
    for component in calendar.walk("VEVENT"):
        dt = component["DTSTART"].dt
        if not isinstance(dt, datetime):
            dt = datetime.combine(dt, datetime.min.time(), timezone.utc)

        url = str(component.get("URL", ""))
        description = html.unescape(str(component.get("DESCRIPTION", "")))
        description = description.removesuffix(url).strip()

        events.append(
            {
                "uid": str(component.get("UID", "")),
                "dt_utc": dt.astimezone(timezone.utc),
                "summary": html.unescape(str(component.get("SUMMARY", ""))),
                "description": description,
                "url": url,
            }
        )

    return events


def get_feed_events() -> list[dict]:
    """Get events for the current year, and for the next one in December"""

    today = date.today()
    years = [today.year]
    if today.month == DECEMBER:
        years.append(today.year + 1)

    events = []
    for year in years:
        calendar = fetch_calendar(year)
        if calendar:
            events.extend(parse_calendar(calendar))

    return events
