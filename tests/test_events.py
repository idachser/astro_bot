from datetime import date

from astro_bot.services import events
from tests.harness import event_row, serving_events


class TestEventsOnDay:
    def test_keeps_only_the_events_of_the_day(self) -> None:
        day = [
            event_row("2026-07-02T23:00:00+00:00"),
            event_row("2026-07-03T10:00:00+00:00"),
            event_row("2026-07-03T22:00:00+00:00"),
            event_row("2026-07-04T10:00:00+00:00"),
        ]

        with serving_events(events, day):
            result = events.get_events_on_day(date(2026, 7, 3))

        assert [row[0] for row in result] == [
            "2026-07-03T10:00:00+00:00",
            "2026-07-03T22:00:00+00:00",
        ]

    def test_day_respects_timezone(self) -> None:
        moscow = "Europe/Moscow"

        with serving_events(
            events, [event_row("2026-07-03T23:30:00+00:00")]
        ):
            assert len(events.get_events_on_day(date(2026, 7, 3))) == 1
            assert events.get_events_on_day(date(2026, 7, 3), tz=moscow) == []
            assert len(
                events.get_events_on_day(date(2026, 7, 4), tz=moscow)
            ) == 1

    def test_unknown_timezone_falls_back_to_utc(self) -> None:
        with serving_events(
            events, [event_row("2026-07-03T23:30:00+00:00")]
        ):
            result = events.get_events_on_day(
                date(2026, 7, 3), tz="Mars/Olympus"
            )

        assert len(result) == 1

    def test_asks_for_every_utc_date_the_local_day_touches(self) -> None:
        """Kiritimati is UTC+14, so its 3 July starts on 2 July UTC"""

        with serving_events(events, []) as asked:
            events.get_events_on_day(
                date(2026, 7, 3), tz="Pacific/Kiritimati"
            )

        start, end = asked[0]
        assert start == date(2026, 7, 2)
        assert end > date(2026, 7, 3)  # exclusive, must cover the 3rd

    def test_utc_day_asks_for_exactly_that_day(self) -> None:
        """A window ending at midnight touches one UTC date. Asking for
        the day after would demand coverage of 1 January to show
        31 December, and fetch_range wants the whole range covered."""

        with serving_events(events, []) as asked:
            events.get_events_on_day(date(2026, 12, 31))

        assert asked == [(date(2026, 12, 31), date(2027, 1, 1))]

    def test_unavailable_service_is_not_an_empty_day(self) -> None:
        with serving_events(events, None):
            assert events.get_events_on_day(date(2026, 7, 3)) is None


class TestEventsBetween:
    def test_asks_for_the_inclusive_range(self) -> None:
        with serving_events(events, []) as asked:
            events.get_events_between(date(2026, 7, 2), date(2026, 7, 8))

        # the service's `to` is exclusive, so the 8th must still be inside
        assert asked == [(date(2026, 7, 2), date(2026, 7, 9))]

    def test_passes_the_events_through(self) -> None:
        with serving_events(
            events, [event_row("2026-07-02T10:00:00+00:00")]
        ):
            result = events.get_events_between(
                date(2026, 7, 2), date(2026, 7, 8)
            )

        assert [row[0] for row in result] == ["2026-07-02T10:00:00+00:00"]

    def test_unavailable_service_returns_none(self) -> None:
        with serving_events(events, None):
            assert events.get_events_between(
                date(2026, 7, 2), date(2026, 7, 8)
            ) is None
