import asyncio

from astro_bot import timezones
from astro_bot.handlers import get_specific_date_event as day_message
from astro_bot.handlers.week import get_week_msg_text
from tests.harness import frozen_now, serving_events, serving_profile, utc


class FakeMessage:
    """The one message the "Week" button answers, keeping the keyboard
    it was answered with."""

    def __init__(self, user_id: int = 42) -> None:
        self.from_user = type("User", (), {"id": user_id})()
        self.markup = None

    async def answer(self, text, reply_markup=None, **kwargs) -> None:
        self.markup = reply_markup


class TestWeekButton:
    def press(self) -> list:
        message = FakeMessage()
        with frozen_now(timezones, utc(2026, 8, 8, 9, 30)):
            with serving_events(day_message, [], attr="get_events_on_day"):
                with serving_profile(day_message):
                    asyncio.run(get_week_msg_text(message))

        return [
            button.callback_data
            for button in message.markup.inline_keyboard[0]
        ]

    def test_window_starts_at_today_not_at_monday(self) -> None:
        # Saturday 8 August. This used to answer with the Mon-Sun week
        # today falls in, so the digest listed 8-14 August while the
        # arrows under the very next message walked 3-9.
        assert self.press() == [
            "week_2026-08-08_2026-08-14",
            "week_2026-08-08_2026-08-09",
        ]
