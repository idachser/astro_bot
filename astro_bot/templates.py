from collections import defaultdict
from datetime import date, datetime, timedelta

from aiogram.utils.markdown import hbold, hlink, quote_html

from astro_bot.config import WEEK_LENGTH
from astro_bot.timezones import is_date_only, resolve_timezone


GREETING_MESSAGE = f"""Hello, I'm Astrobot!

I will searching and collect celestial events for you.

Push {hbold("Share location")} key to get event times in your \
local timezone and observing conditions — cloud cover and \
visibility — under the events, or {hbold("Default time")} key \
for UTC times without the weather forecast.

Let's start your astro adventure!

P.S. Event data is computed with Skyfield and JPL DE440s ephemerides.
"""

COMMANDS_LIST = f"""{hbold("Help")} - get message with commands list;
{hbold("Week")} - browse events of the week day by day;
{hbold("Today")} - get events for today;
{hbold("Yesterday")} - get events for yesterday;
{hbold("Tomorrow")} - get events for tomorrow;
{hbold("Image of the day")} - get astronomy picture of the day from NASA.

You can send me date in {hbold("Month DD")} (e.g. 'July 15') format for \
getting celestial events for specific date.

Share your location with the {hbold("Share location")} key at /start \
and event times will be in your timezone, with observing conditions \
(cloud cover and visibility) under upcoming events.
"""

START_MESSAGE = f"""You can send me commands (press keys):

{COMMANDS_LIST}"""

HELP_MESSAGE = COMMANDS_LIST

NOTHING_NEWS_FOUND = "No events found..."
NO_EVENTS_THAT_DAY = "no events"
# Distinct from NOTHING_NEWS_FOUND on purpose: events are read live, and
# an unreachable service must not be reported as a quiet sky
EVENTS_UNAVAILABLE_MESSAGE = "Can't get the events now. Try later."
IMAGE_ERROR_MESSAGE = "Can't get the image of the day now. Try later."
WRONG_DATE_MESSAGE = (
    "I can't understand the date. "
    f"Send it in {hbold('Month DD')} format, e.g. 'July 15'."
)
# Distinct from WRONG_DATE_MESSAGE: the date was understood perfectly,
# it just doesn't exist in this year. Only February 29 gets here.
NO_SUCH_DATE_MESSAGE = (
    "That date doesn't exist this year — "
    f"{hbold('February 29')} only comes round in a leap year."
)


def format_day_title(day: date) -> str:
    return f"{day:%A}, {day:%B} {day.day}"


def format_event_time(dt_utc: str, tz: str = "") -> str:
    dt = datetime.fromisoformat(dt_utc)
    if is_date_only(dt):
        return ""
    local = dt.astimezone(resolve_timezone(tz))
    return f" ({local:%H:%M} {local:%Z})"


def MESSAGE_WITH_DAY_EVENTS(day: date, events: list, tz: str = "") -> str:
    """Message for one day: (dt_utc, summary, description, url) rows.
    An empty day keeps its title."""

    lines = [hbold(format_day_title(day)), ""]
    if not events:
        lines.append(NOTHING_NEWS_FOUND)
    for dt_utc, summary, description, url in events:
        title = hlink(summary, url) if url else hbold(summary)
        lines.append(title + format_event_time(dt_utc, tz))
        if description:
            lines.append(quote_html(description))
        lines.append("")

    return "\n".join(lines).strip()


def WEATHER_FOOTER(weather: list) -> str:
    """Observing conditions per event:
    (local HH:MM, cloud cover %, visibility km) rows"""

    lines = [hbold("Observing conditions:")]
    for time_, cloud, visibility_km in weather:
        lines.append(
            f"{time_} — clouds {cloud}%, visibility {visibility_km} km"
        )
    lines += ["", "Weather data by Open-Meteo.com"]
    return "\n".join(lines)


def WEEK_DIGEST_MESSAGE(start: date, events: list) -> str:
    """Digest for the WEEK_LENGTH days from `start`, one line per event
    and one for every day without any. Dates are UTC, like the window."""

    by_day = defaultdict(list)
    for dt_utc, summary, description, url in events:
        by_day[datetime.fromisoformat(dt_utc).date()].append(summary)

    lines = [hbold("Celestial events for the upcoming week:"), ""]
    for offset in range(WEEK_LENGTH):
        day = start + timedelta(days=offset)
        label = f"{day:%a} {day.day} {day:%B}"
        summaries = by_day.get(day)
        if summaries:
            lines += [
                f"{label} — {quote_html(summary)}" for summary in summaries
            ]
        else:
            lines.append(f"{label} — {NO_EVENTS_THAT_DAY}")

    lines += ["", "Computed with Skyfield and JPL DE440s"]
    return "\n".join(lines)


def MESSAGE_WITH_IMAGE(res_dict: dict) -> tuple:
    img = res_dict["url"]
    message = (
        f"{hbold(res_dict.get('title', ''))}\n\n"
        f"{quote_html(res_dict.get('explanation', ''))}"
    )
    copyright_ = res_dict.get("copyright")
    if copyright_:
        message += f"\n\nCopyright: {quote_html(copyright_.strip())}"

    return img, message
