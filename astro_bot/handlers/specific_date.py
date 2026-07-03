from datetime import date, datetime

from aiogram import Dispatcher, types

from astro_bot.handlers.get_specific_date_event import get_message_for_day
from astro_bot.services.users import get_user_timezone
from astro_bot.templates import WRONG_DATE_MESSAGE


async def get_day(message: types.Message) -> None:
    try:
        parsed = datetime.strptime(message.text.strip(), "%B %d")
    except ValueError:
        await message.reply(WRONG_DATE_MESSAGE)
        return

    day = date(date.today().year, parsed.month, parsed.day)
    tz = get_user_timezone(message.from_user.id)
    msg = get_message_for_day(day, tz=tz)

    await message.reply(msg, disable_web_page_preview=True)


def register_handler_specific_day(dp: Dispatcher) -> None:
    dp.register_message_handler(get_day)
