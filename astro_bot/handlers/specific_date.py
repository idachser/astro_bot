import asyncio
from datetime import date, datetime

from aiogram import Dispatcher, types

from astro_bot.handlers.get_specific_date_event import get_day_message
from astro_bot.templates import WRONG_DATE_MESSAGE


async def get_day(message: types.Message) -> None:
    try:
        parsed = datetime.strptime(message.text.strip(), "%B %d")
    except ValueError:
        await message.reply(WRONG_DATE_MESSAGE)
        return

    _, msg = await asyncio.to_thread(
        get_day_message,
        message.from_user.id,
        lambda today: date(today.year, parsed.month, parsed.day),
    )

    await message.reply(msg, disable_web_page_preview=True)


def register_handler_specific_day(dp: Dispatcher) -> None:
    dp.register_message_handler(get_day)
