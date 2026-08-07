from datetime import date, timedelta

from aiogram import types

from astro_bot.config import WEEK_LENGTH


def _callback(anchor: date, day: date) -> str:
    return f"week_{anchor.isoformat()}_{day.isoformat()}"


def parse_week_callback(data: str) -> tuple[date, date]:
    """(anchor, day) out of a `week_<anchor>_<day>` callback.

    Messages sent before the window was part of the callback carry a bare
    `week_<day>`, and they keep working: inline keyboards live on in the
    chat history, so users press yesterday's buttons after a deploy.
    Those anchor to the day's Monday, which is what they used to mean.
    """

    parts = data.removeprefix("week_").split("_")
    day = date.fromisoformat(parts[-1])
    if len(parts) > 1:
        return date.fromisoformat(parts[0]), day
    return day - timedelta(days=day.weekday()), day


def get_inline_week_keyboard(
    day: date, anchor: date | None = None
) -> types.InlineKeyboardMarkup:
    """Arrows over the seven days starting at `anchor`, wrapping at both
    ends. `anchor` defaults to the Monday of `day`'s week -- the Mon-Sun
    window the "Week" button browses.

    The Saturday digest passes its own first day instead, because it
    lists `today..today+6` and that straddles a Mon-Sun boundary: with a
    Monday anchor its arrows walked five days it never mentioned (all of
    them past) and could not reach five of the seven it did.

    The anchor rides along in the callback data because pagination keeps
    no state -- the callback is the only thing that can say which seven
    days the message it belongs to was built for.
    """

    if anchor is None:
        anchor = day - timedelta(days=day.weekday())
    end = anchor + timedelta(days=WEEK_LENGTH - 1)
    previous_day = day - timedelta(days=1) if day > anchor else end
    next_day = day + timedelta(days=1) if day < end else anchor

    next_prev_buttons = [
        types.InlineKeyboardButton(
            text="<", callback_data=_callback(anchor, previous_day)
        ),
        types.InlineKeyboardButton(
            text=">", callback_data=_callback(anchor, next_day)
        ),
    ]
    next_prev_keyboard = types.InlineKeyboardMarkup()
    next_prev_keyboard.add(*next_prev_buttons)

    return next_prev_keyboard
