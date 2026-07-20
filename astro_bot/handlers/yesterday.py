import asyncio
from datetime import timedelta

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Text

from astro_bot.handlers.get_specific_date_event import get_day_message


async def get_yesterday(message: types.Message) -> None:
    _, msg = await asyncio.to_thread(
        get_day_message,
        message.from_user.id,
        lambda today: today - timedelta(days=1),
    )
    await message.reply(msg, disable_web_page_preview=True)


def register_handler_yesterday(dp: Dispatcher) -> None:
    dp.register_message_handler(get_yesterday, Text(equals="Yesterday"))
