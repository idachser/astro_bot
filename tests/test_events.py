from datetime import date

from astro_bot.services import events


def EV(dt_utc: str, summary: str = "Full Moon") -> tuple:
    return (dt_utc, summary, "The Moon reaches full phase.", "")


def patch_range(monkeypatch, result) -> list:
    """Serve `result` for any range and record what was asked for"""

    asked = []

    def fake_fetch(start, end):
        asked.append((start, end))
        return result

    monkeypatch.setattr(events, "fetch_range", fake_fetch)
    return asked


class TestEventsOnDay:
    def test_keeps_only_the_events_of_the_day(self, monkeypatch) -> None:
        patch_range(
            monkeypatch,
            [
                EV("2026-07-02T23:00:00+00:00"),
                EV("2026-07-03T10:00:00+00:00"),
                EV("2026-07-03T22:00:00+00:00"),
                EV("2026-07-04T10:00:00+00:00"),
            ],
        )

        result = events.get_events_on_day(date(2026, 7, 3))
        assert [row[0] for row in result] == [
            "2026-07-03T10:00:00+00:00",
            "2026-07-03T22:00:00+00:00",
        ]

    def test_day_respects_timezone(self, monkeypatch) -> None:
        patch_range(monkeypatch, [EV("2026-07-03T23:30:00+00:00")])

        moscow = "Europe/Moscow"
        assert len(events.get_events_on_day(date(2026, 7, 3))) == 1
        assert events.get_events_on_day(date(2026, 7, 3), tz=moscow) == []
        assert len(events.get_events_on_day(date(2026, 7, 4), tz=moscow)) == 1

    def test_unknown_timezone_falls_back_to_utc(self, monkeypatch) -> None:
        patch_range(monkeypatch, [EV("2026-07-03T23:30:00+00:00")])
        result = events.get_events_on_day(
            date(2026, 7, 3), tz="Mars/Olympus"
        )
        assert len(result) == 1

    def test_asks_for_every_utc_date_the_local_day_touches(
        self, monkeypatch
    ) -> None:
        """Kiritimati is UTC+14, so its 3 July starts on 2 July UTC"""

        asked = patch_range(monkeypatch, [])
        events.get_events_on_day(date(2026, 7, 3), tz="Pacific/Kiritimati")

        start, end = asked[0]
        assert start == date(2026, 7, 2)
        assert end > date(2026, 7, 3)  # exclusive, must cover the 3rd

    def test_unavailable_service_is_not_an_empty_day(
        self, monkeypatch
    ) -> None:
        patch_range(monkeypatch, None)
        assert events.get_events_on_day(date(2026, 7, 3)) is None


class TestEventsBetween:
    def test_asks_for_the_inclusive_range(self, monkeypatch) -> None:
        asked = patch_range(monkeypatch, [])
        events.get_events_between(date(2026, 7, 2), date(2026, 7, 8))

        # the service's `to` is exclusive, so the 8th must still be inside
        assert asked == [(date(2026, 7, 2), date(2026, 7, 9))]

    def test_passes_the_events_through(self, monkeypatch) -> None:
        patch_range(monkeypatch, [EV("2026-07-02T10:00:00+00:00")])
        result = events.get_events_between(date(2026, 7, 2), date(2026, 7, 8))
        assert [row[0] for row in result] == ["2026-07-02T10:00:00+00:00"]

    def test_unavailable_service_returns_none(self, monkeypatch) -> None:
        patch_range(monkeypatch, None)
        assert events.get_events_between(
            date(2026, 7, 2), date(2026, 7, 8)
        ) is None
