from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Text
from timezonefinder import TimezoneFinder

from astro_bot.services.users import add_user
from astro_bot.templates import START_MESSAGE
from astro_bot.keyboards.reply_keyboard import main_keyboard


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
        tf = TimezoneFinder()
        user_data["timezone"] = tf.timezone_at(
            lng=location.longitude, lat=location.latitude
        )

    add_user(user_data)
    await message.answer(START_MESSAGE, reply_markup=main_keyboard())


def register_handler_start(dp: Dispatcher) -> None:
    dp.register_message_handler(start, content_types=["location"])
    dp.register_message_handler(start, Text(equals="Default time"))
