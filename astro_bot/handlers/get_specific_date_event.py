from datetime import date

from astro_bot.services.events import get_events_on_day
from astro_bot.services.users import get_user_profile
from astro_bot.services.weather import get_events_weather
from astro_bot.templates import (
    MESSAGE_WITH_DAY_EVENTS,
    NOTHING_NEWS_FOUND,
    WEATHER_FOOTER,
)


def get_message_for_day(day: date, user_id: int) -> str:
    tz, lat, lon = get_user_profile(user_id)
    events = get_events_on_day(day, tz=tz)
    if not events:
        return NOTHING_NEWS_FOUND

    message = MESSAGE_WITH_DAY_EVENTS(day, events, tz=tz)
    weather = get_events_weather(events, lat, lon, tz=tz)
    if weather:
        message += "\n\n" + WEATHER_FOOTER(weather)
    return message
