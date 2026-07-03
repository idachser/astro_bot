from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def location_kayboard() -> ReplyKeyboardMarkup:
    location_key = KeyboardButton("Share location", request_location=True)
    default_key = KeyboardButton("Default time")

    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True
    )
    keyboard.add(location_key, default_key)
    return keyboard


def main_keyboard() -> None:
    buttons = [
        "Help",
        "Week",
        "Yesterday",
        "Today",
        "Tomorrow",
    ]

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(*buttons)
    return keyboard
