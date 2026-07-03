from datetime import date, datetime

from aiogram.utils.markdown import hbold, hlink, quote_html

from astro_bot.timezones import resolve_timezone


GREETING_MESSAGE = f"""Hello, I'm Astrobot!

I will searching and collect celestial events for you.

If you want getting actual time of events for your local, please \
push {hbold("Share location")} key or {hbold("Default time")} key \
for getting default date and time.

Let's start your astro adventure!

P.S. Event data courtesy of In-The-Sky.org, © Dominic Ford. Visit \
https://in-the-sky.org/ if you want more.
"""

COMMANDS_LIST = f"""{hbold("Help")} - get message with commands list;
{hbold("Week")} - browse events of the week day by day;
{hbold("Today")} - get events for today;
{hbold("Yesterday")} - get events for yesterday;
{hbold("Tomorrow")} - get events for tomorrow;
{hbold("Image of the day")} - get astronomy picture of the day from NASA.

You can send me date in {hbold("Month DD")} (e.g. 'July 15') format for \
getting celestial events for specific date.
"""

START_MESSAGE = f"""You can send me commands (press keys):

{COMMANDS_LIST}"""

HELP_MESSAGE = COMMANDS_LIST

NOTHING_NEWS_FOUND = "No events found..."
IMAGE_ERROR_MESSAGE = "Can't get the image of the day now. Try later."
WRONG_DATE_MESSAGE = (
    "I can't understand the date. "
    f"Send it in {hbold('Month DD')} format, e.g. 'July 15'."
)


def format_day_title(day: date) -> str:
    return f"{day:%A}, {day:%B} {day.day}"


def format_event_time(dt_utc: str, tz: str = "") -> str:
    dt = datetime.fromisoformat(dt_utc)
    if (dt.hour, dt.minute) == (0, 0):
        return ""
    local = dt.astimezone(resolve_timezone(tz))
    return f" ({local:%H:%M} {local:%Z})"


def MESSAGE_WITH_DAY_EVENTS(day: date, events: list, tz: str = "") -> str:
    """Message for one day: (dt_utc, summary, description, url) rows"""

    lines = [hbold(format_day_title(day)), ""]
    for dt_utc, summary, description, url in events:
        lines.append(hlink(summary, url) + format_event_time(dt_utc, tz))
        if description:
            lines.append(quote_html(description))
        lines.append("")

    return "\n".join(lines).strip()


def WEEK_DIGEST_MESSAGE(events: list) -> str:
    """One-line-per-event digest for the upcoming week"""

    lines = [hbold("Celestial events for the upcoming week:"), ""]
    for dt_utc, summary, description, url in events:
        dt = datetime.fromisoformat(dt_utc)
        lines.append(f"{dt:%a} {dt.day} {dt:%B} — {quote_html(summary)}")

    lines += ["", "Data courtesy of In-The-Sky.org, © Dominic Ford"]
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
