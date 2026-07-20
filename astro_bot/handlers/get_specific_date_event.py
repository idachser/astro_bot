from datetime import date
from typing import Callable

from astro_bot.services.events import get_events_on_day
from astro_bot.services.users import get_user_profile
from astro_bot.services.weather import get_events_weather
from astro_bot.templates import (
    MESSAGE_WITH_DAY_EVENTS,
    NOTHING_NEWS_FOUND,
    WEATHER_FOOTER,
)
from astro_bot.timezones import today_in


def get_day_message(
    user_id: int, pick_day: Callable[[date], date]
) -> tuple[date, str]:
    """Render one day for a user; `pick_day` picks it from the user's
    local today ("today" itself, a neighbouring day, or a date they
    typed). Returns the day too, for the week keyboard.

    The profile is read once here and reused for the day window, the
    event times and the forecast. Handlers call this through
    asyncio.to_thread, so every blocking call — DB and the weather
    HTTP request — stays off the event loop; don't read the profile
    in a handler instead, that puts a DB hit back on the loop.
    """

    tz, lat, lon = get_user_profile(user_id)
    day = pick_day(today_in(tz))

    events = get_events_on_day(day, tz=tz)
    if not events:
        return day, NOTHING_NEWS_FOUND

    message = MESSAGE_WITH_DAY_EVENTS(day, events, tz=tz)
    weather = get_events_weather(events, lat, lon, tz=tz)
    if weather:
        message += "\n\n" + WEATHER_FOOTER(weather)
    return day, message
