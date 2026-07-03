from datetime import date

from astro_bot.services.events import get_events_on_day
from astro_bot.templates import MESSAGE_WITH_DAY_EVENTS, NOTHING_NEWS_FOUND


def get_message_for_day(day: date, tz: str = "") -> str:
    events = get_events_on_day(day, tz=tz)
    if events:
        return MESSAGE_WITH_DAY_EVENTS(day, events, tz=tz)
    return NOTHING_NEWS_FOUND
