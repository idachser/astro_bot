from datetime import date, timedelta

from astro_bot import templates
from astro_bot.keyboards.inline_keyboard import (
    get_inline_week_keyboard,
    parse_week_callback,
)
from tests.harness import event_row

EVENT_ROW = event_row(
    "2026-07-03T10:02:46+00:00",
    url="https://in-the-sky.org/news.php?id=1",
)
MIDNIGHT_ROW = event_row(
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

    def test_second_precision_midnight_is_a_real_time(self) -> None:
        time_ = templates.format_event_time("2026-07-03T00:00:45+00:00")
        assert time_ == " (00:00 UTC)"


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
    def get_callbacks(self, day: date, anchor: date = None) -> list:
        keyboard = get_inline_week_keyboard(day, anchor)
        return [
            button.callback_data
            for button in keyboard.inline_keyboard[0]
        ]

    def test_midweek_points_to_neighbours(self) -> None:
        # 2026-07-01 is Wednesday
        assert self.get_callbacks(date(2026, 7, 1)) == [
            "week_2026-06-29_2026-06-30",
            "week_2026-06-29_2026-07-02",
        ]

    def test_monday_wraps_back_to_sunday(self) -> None:
        assert self.get_callbacks(date(2026, 6, 29)) == [
            "week_2026-06-29_2026-07-05",
            "week_2026-06-29_2026-06-30",
        ]

    def test_sunday_wraps_forward_to_monday(self) -> None:
        assert self.get_callbacks(date(2026, 7, 5)) == [
            "week_2026-06-29_2026-07-04",
            "week_2026-06-29_2026-06-29",
        ]

    def test_anchor_wraps_within_its_own_window(self) -> None:
        # the digest's window: Saturday and the six days after it
        saturday = date(2026, 8, 8)
        assert self.get_callbacks(saturday, anchor=saturday) == [
            "week_2026-08-08_2026-08-14",
            "week_2026-08-08_2026-08-09",
        ]
        # ...and the far end wraps back to the Saturday, never into the
        # Mon-Sun week the anchor happens to sit in
        assert self.get_callbacks(date(2026, 8, 14), anchor=saturday) == [
            "week_2026-08-08_2026-08-13",
            "week_2026-08-08_2026-08-08",
        ]

    def test_anchored_arrows_reach_every_day_they_advertise(self) -> None:
        saturday = date(2026, 8, 8)
        window = {saturday + timedelta(days=i) for i in range(7)}

        seen, day = set(), saturday
        for _ in range(7):
            seen.add(day)
            anchor, day = parse_week_callback(
                self.get_callbacks(day, anchor=saturday)[1]
            )

        assert seen == window


class TestWeekCallback:
    def test_round_trips_the_window(self) -> None:
        assert parse_week_callback("week_2026-08-08_2026-08-11") == (
            date(2026, 8, 8),
            date(2026, 8, 11),
        )

    def test_legacy_callback_anchors_to_monday(self) -> None:
        # keyboards sent before the anchor existed still sit in chat
        # histories; pressing one must not blow up the handler
        assert parse_week_callback("week_2026-07-01") == (
            date(2026, 6, 29),
            date(2026, 7, 1),
        )
