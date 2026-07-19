import asyncio
from datetime import timedelta

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Text

from astro_bot.handlers.get_specific_date_event import get_message_for_day
from astro_bot.services.users import get_user_today


async def get_yesterday(message: types.Message) -> None:
    user_id = message.from_user.id
    day = get_user_today(user_id) - timedelta(days=1)
    msg = await asyncio.to_thread(get_message_for_day, day, user_id)
    await message.reply(msg, disable_web_page_preview=True)


def register_handler_yesterday(dp: Dispatcher) -> None:
    dp.register_message_handler(get_yesterday, Text(equals="Yesterday"))
