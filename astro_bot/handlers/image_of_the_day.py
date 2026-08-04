import asyncio

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Text

from astro_bot.services.nasa import get_image_of_the_day
from astro_bot.templates import IMAGE_ERROR_MESSAGE, MESSAGE_WITH_IMAGE


async def get_image(message: types.Message) -> None:
    # Blocking `requests` call with a 30s timeout: run it off the event
    # loop like every other outbound request, or a slow APOD stops
    # polling and nobody gets an answer to anything
    data = await asyncio.to_thread(get_image_of_the_day)
    if not data or "url" not in data:
        await message.reply(IMAGE_ERROR_MESSAGE)
        return

    media_url, text = MESSAGE_WITH_IMAGE(data)
    if data.get("media_type") == "image":
        await message.reply_photo(media_url)
        await message.answer(text, disable_web_page_preview=True)
    else:
        # Videos and other media go as a link so Telegram shows a player
        await message.reply(f"{text}\n\n{media_url}")


def register_handler_image(dp: Dispatcher) -> None:
    dp.register_message_handler(get_image, Text(equals="Image of the day"))
