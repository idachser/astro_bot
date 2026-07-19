import asyncio
from datetime import date

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Text

from astro_bot.handlers.get_specific_date_event import get_message_for_day
from astro_bot.keyboards.inline_keyboard import get_inline_week_keyboard
from astro_bot.services.users import get_user_today


async def get_week_msg_text(message: types.Message) -> None:
    user_id = message.from_user.id
    day = get_user_today(user_id)
    msg = await asyncio.to_thread(get_message_for_day, day, user_id)
    await message.answer(
        msg,
        reply_markup=get_inline_week_keyboard(day),
        disable_web_page_preview=True,
    )


async def switch_week_day(call: types.CallbackQuery) -> None:
    day = date.fromisoformat(call.data.removeprefix("week_"))
    msg = await asyncio.to_thread(
        get_message_for_day, day, call.from_user.id
    )
    await call.message.edit_text(
        msg,
        reply_markup=get_inline_week_keyboard(day),
        disable_web_page_preview=True,
    )
    await call.answer()


def register_handler_week(dp: Dispatcher) -> None:
    dp.register_message_handler(get_week_msg_text, Text(equals="Week"))
    dp.register_callback_query_handler(
        switch_week_day, Text(startswith="week_")
    )
