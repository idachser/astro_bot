from datetime import date, timedelta

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Text

from astro_bot.handlers.get_specific_date_event import get_message_for_day


async def get_yesterday(message: types.Message) -> None:
    msg = get_message_for_day(date.today() - timedelta(days=1))
    await message.reply(msg, disable_web_page_preview=True)


def register_handler_yesterday(dp: Dispatcher) -> None:
    dp.register_message_handler(get_yesterday, Text(equals="Yesterday"))
