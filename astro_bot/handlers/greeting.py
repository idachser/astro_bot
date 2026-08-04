from aiogram import Dispatcher, types

from astro_bot.templates import GREETING_MESSAGE
from astro_bot.keyboards.reply_keyboard import location_keyboard


async def greeting(message: types.Message) -> None:
    await message.answer(GREETING_MESSAGE, reply_markup=location_keyboard())


def register_handler_start(dp: Dispatcher) -> None:
    dp.register_message_handler(greeting, commands=["Start", "start"])
