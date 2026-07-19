from datetime import date

from astro_bot import templates
from astro_bot.keyboards.inline_keyboard import get_inline_week_keyboard

EVENT_ROW = (
    "2026-07-03T10:02:46+00:00",
    "Full Moon",
    "The Moon reaches full phase.",
    "https://in-the-sky.org/news.php?id=1",
)
MIDNIGHT_ROW = (
    "2026-07-03T00:00:00+00:00",
    "Meteor shower peak",
    "",
    "https://in-the-sky.org/news.php?id=2",
)


class TestDayMessage:
    def test_contains_title_and_events(self) -> None:
        msg = templates.MESSAGE_WITH_DAY_EVENTS(
            date(2026, 7, 3), [EVENT_ROW, MIDNIGHT_ROW]
        )
        assert "Friday, July 3" in msg
        assert "Full Moon" in msg
        assert "The Moon reaches full phase." in msg
        assert 'href="https://in-the-sky.org/news.php?id=1"' in msg

    def test_shows_time_only_when_known(self) -> None:
        msg = templates.MESSAGE_WITH_DAY_EVENTS(
            date(2026, 7, 3), [EVENT_ROW, MIDNIGHT_ROW]
        )
        assert "(10:02 UTC)" in msg
        assert "(00:00 UTC)" not in msg

    def test_time_in_user_timezone(self) -> None:
        msg = templates.MESSAGE_WITH_DAY_EVENTS(
            date(2026, 7, 3), [EVENT_ROW], tz="Europe/Moscow"
        )
        assert "(13:02 MSK)" in msg


class TestWeatherFooter:
    def test_one_line_per_event_with_attribution(self) -> None:
        msg = templates.WEATHER_FOOTER(
            [("21:04", 84, 21), ("22:15", 88, 22)]
        )
        assert "Observing conditions:" in msg
        assert "21:04 — clouds 84%, visibility 21 km" in msg
        assert "22:15 — clouds 88%, visibility 22 km" in msg
        assert msg.endswith("Weather data by Open-Meteo.com")


class TestImageMessage:
    APOD = {
        "url": "https://apod.nasa.gov/apod/image/x.jpg",
        "title": "Andromeda & Friends",
        "explanation": "A galaxy.",
        "copyright": "\nSome Astronomer\n",
    }

    def test_full_response(self) -> None:
        img, msg = templates.MESSAGE_WITH_IMAGE(self.APOD)
        assert img == self.APOD["url"]
        assert "Andromeda &amp; Friends" in msg
        assert "A galaxy." in msg
        assert "Copyright: Some Astronomer" in msg

    def test_copyright_is_optional(self) -> None:
        apod = {key: value for key, value in self.APOD.items()
                if key != "copyright"}
        img, msg = templates.MESSAGE_WITH_IMAGE(apod)
        assert "Copyright" not in msg


class TestWeekDigest:
    def test_one_line_per_event(self) -> None:
        msg = templates.WEEK_DIGEST_MESSAGE([EVENT_ROW, MIDNIGHT_ROW])
        assert "Fri 3 July — Full Moon" in msg
        assert "Fri 3 July — Meteor shower peak" in msg


class TestWeekKeyboard:
    def get_callbacks(self, day: date) -> list:
        keyboard = get_inline_week_keyboard(day)
        return [
            button.callback_data
            for button in keyboard.inline_keyboard[0]
        ]

    def test_midweek_points_to_neighbours(self) -> None:
        # 2026-07-01 is Wednesday
        assert self.get_callbacks(date(2026, 7, 1)) == [
            "week_2026-06-30",
            "week_2026-07-02",
        ]

    def test_monday_wraps_back_to_sunday(self) -> None:
        assert self.get_callbacks(date(2026, 6, 29)) == [
            "week_2026-07-05",
            "week_2026-06-30",
        ]

    def test_sunday_wraps_forward_to_monday(self) -> None:
        assert self.get_callbacks(date(2026, 7, 5)) == [
            "week_2026-07-04",
            "week_2026-06-29",
        ]
