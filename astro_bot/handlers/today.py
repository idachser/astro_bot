from datetime import date

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Text

from astro_bot.handlers.get_specific_date_event import get_message_for_day
from astro_bot.services.users import get_user_timezone


async def get_today(message: types.Message) -> None:
    tz = get_user_timezone(message.from_user.id)
    msg = get_message_for_day(date.today(), tz=tz)
    await message.reply(msg, disable_web_page_preview=True)


def register_handler_today(dp: Dispatcher):
    dp.register_message_handler(get_today, Text(equals="Today"))
