import asyncio

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Text

from astro_bot.services.users import add_user
from astro_bot.templates import START_MESSAGE
from astro_bot.keyboards.reply_keyboard import main_keyboard
from astro_bot.timezones import zone_for_location


async def start(message: types.Message) -> None:
    user_data = {
        "id": message.from_user.id,
        "name": message.from_user.full_name,
        "username": message.from_user.username,
        "timezone": "",
        "lat": None,
        "lon": None,
    }

    if message.text != "Default time":
        location = message.location
        user_data["lat"] = location.latitude
        user_data["lon"] = location.longitude
        # Both of these block: the very first lookup builds the boundary
        # data, and the write is SQLite. Same rule as every other handler
        # -- nothing blocking runs on the event loop.
        user_data["timezone"] = await asyncio.to_thread(
            zone_for_location, location.latitude, location.longitude
        )

    await asyncio.to_thread(add_user, user_data)
    await message.answer(START_MESSAGE, reply_markup=main_keyboard())


def register_handler_start(dp: Dispatcher) -> None:
    dp.register_message_handler(start, content_types=["location"])
    dp.register_message_handler(start, Text(equals="Default time"))
