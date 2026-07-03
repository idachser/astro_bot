from datetime import date, datetime

from aiogram.utils.markdown import hbold, hlink, quote_html


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
{hbold("Tomorrow")} - get events for tomorrow.

You can send me date in {hbold("Month DD")} (e.g. 'July 15') format for \
getting celestial events for specific date.
"""

START_MESSAGE = f"""You can send me commands (press keys):

{COMMANDS_LIST}"""

HELP_MESSAGE = COMMANDS_LIST

SCRAPING_ERROR_MESSAGE = "No content found."
ERROR_MESSAGE = "Something went wrong. Please, try later."
NOTHING_NEWS_FOUND = "No events found..."
WRONG_DATE_MESSAGE = (
    "I can't understand the date. "
    f"Send it in {hbold('Month DD')} format, e.g. 'July 15'."
)


def format_day_title(day: date) -> str:
    return f"{day:%A}, {day:%B} {day.day}"


def format_event_time(dt_utc: str) -> str:
    dt = datetime.fromisoformat(dt_utc)
    if (dt.hour, dt.minute) == (0, 0):
        return ""
    return f" ({dt:%H:%M} UTC)"


def MESSAGE_WITH_DAY_EVENTS(day: date, events: list) -> str:
    """Message for one day: (dt_utc, summary, description, url) rows"""

    lines = [hbold(format_day_title(day)), ""]
    for dt_utc, summary, description, url in events:
        lines.append(hlink(summary, url) + format_event_time(dt_utc))
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
        f"{hbold(res_dict['title'])}\n\n"
        f"{res_dict['explanation']}\n\n"
        f"Copyright: {res_dict['copyright']}"
    )

    return img, message
