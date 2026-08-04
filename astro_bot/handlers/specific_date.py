import asyncio
from datetime import date, datetime
from typing import Callable

from aiogram import Dispatcher, types

from astro_bot.handlers.get_specific_date_event import get_day_message
from astro_bot.templates import NO_SUCH_DATE_MESSAGE, WRONG_DATE_MESSAGE

# strptime defaults the year to 1900, which is not a leap year, so
# "%B %d" on its own rejects "February 29" outright -- before anyone can
# ask which year the user meant. Parse against a leap year instead and
# let the user's own year decide whether the date exists.
LEAP_YEAR = 2000


class DateNotThisYear(ValueError):
    """A `Month DD` that does not exist in the year it resolves to --
    only ever February 29 outside a leap year"""


def parse_month_day(text: str) -> tuple[int, int] | None:
    """(month, day) out of "July 15", or None when that is not what the
    message is -- this handler is the catch-all, so most text lands here
    and is simply not a date"""

    try:
        parsed = datetime.strptime(f"{text.strip()} {LEAP_YEAR}", "%B %d %Y")
    except ValueError:
        return None
    return parsed.month, parsed.day


def day_picker(month: int, day: int) -> Callable[[date], date]:
    """Resolve month/day into the user's own current year.

    Raises DateNotThisYear rather than a bare ValueError because this
    runs deep inside `get_day_message` on a worker thread: the handler
    has to tell "February 29 in a common year", which is worth a polite
    reply, from any other ValueError coming out of the events code,
    which is not a bad date at all and must not be reported as one.
    """

    def pick(today: date) -> date:
        try:
            return date(today.year, month, day)
        except ValueError as err:
            raise DateNotThisYear(
                f"{month:02d}-{day:02d} is not a date in {today.year}"
            ) from err

    return pick


async def get_day(message: types.Message) -> None:
    month_day = parse_month_day(message.text)
    if month_day is None:
        await message.reply(WRONG_DATE_MESSAGE)
        return

    try:
        _, msg = await asyncio.to_thread(
            get_day_message, message.from_user.id, day_picker(*month_day)
        )
    except DateNotThisYear:
        await message.reply(NO_SUCH_DATE_MESSAGE)
        return

    await message.reply(msg, disable_web_page_preview=True)


def register_handler_specific_day(dp: Dispatcher) -> None:
    dp.register_message_handler(get_day)
