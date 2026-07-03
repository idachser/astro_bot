from datetime import date, timedelta

from aiogram import types


def get_inline_week_keyboard(day: date) -> types.InlineKeyboardMarkup:
    """Arrows over the days of the week the given day belongs to"""

    monday = day - timedelta(days=day.weekday())
    sunday = monday + timedelta(days=6)
    previous_day = day - timedelta(days=1) if day > monday else sunday
    next_day = day + timedelta(days=1) if day < sunday else monday

    next_prev_buttons = [
        types.InlineKeyboardButton(
            text="<", callback_data=f"week_{previous_day.isoformat()}"
        ),
        types.InlineKeyboardButton(
            text=">", callback_data=f"week_{next_day.isoformat()}"
        ),
    ]
    next_prev_keyboard = types.InlineKeyboardMarkup()
    next_prev_keyboard.add(*next_prev_buttons)

    return next_prev_keyboard
