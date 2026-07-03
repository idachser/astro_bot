from datetime import date, datetime, timezone
from pathlib import Path

import pytest
import requests
from icalendar import Calendar

from astro_bot.services import ics_feed

FIXTURE = Path(__file__).parent / "fixtures" / "newscal_2026.ics"


@pytest.fixture()
def calendar() -> Calendar:
    return Calendar.from_ical(FIXTURE.read_bytes())


class TestParseCalendar:
    def test_parses_all_events(self, calendar) -> None:
        assert len(ics_feed.parse_calendar(calendar)) == 4

    def test_event_fields(self, calendar) -> None:
        event = ics_feed.parse_calendar(calendar)[0]
        assert event["uid"] == "20260101_08_100@in-the-sky.org"
        assert event["dt_utc"] == datetime(
            2026, 1, 1, 21, 44, 19, tzinfo=timezone.utc
        )
        assert event["summary"] == "The Moon at perigee"
        assert event["url"] == (
            "https://in-the-sky.org/news.php?id=20260101_08_100"
        )

    def test_html_entities_are_unescaped(self, calendar) -> None:
        event = ics_feed.parse_calendar(calendar)[0]
        assert "&ndash;" not in event["description"]
        assert "–" in event["description"]

    def test_url_is_stripped_from_description(self, calendar) -> None:
        for event in ics_feed.parse_calendar(calendar):
            assert not event["description"].endswith(event["url"])

    def test_date_only_dtstart_becomes_utc_midnight(self, calendar) -> None:
        event = ics_feed.parse_calendar(calendar)[3]
        assert event["dt_utc"] == datetime(
            2026, 7, 28, 0, 0, tzinfo=timezone.utc
        )


class TestGetFeedEvents:
    def _patch_today(self, monkeypatch, today: date) -> None:
        class FakeDate(date):
            @classmethod
            def today(cls) -> date:
                return today

        monkeypatch.setattr(ics_feed, "date", FakeDate)

    def _patch_fetch(self, monkeypatch, calendar) -> list:
        requested_years = []

        def fake_fetch(year: int):
            requested_years.append(year)
            return calendar

        monkeypatch.setattr(ics_feed, "fetch_calendar", fake_fetch)
        return requested_years

    def test_fetches_current_year(self, monkeypatch, calendar) -> None:
        years = self._patch_fetch(monkeypatch, calendar)
        self._patch_today(monkeypatch, date(2026, 7, 3))

        events = ics_feed.get_feed_events()
        assert years == [2026]
        assert len(events) == 4

    def test_fetches_next_year_in_december(
        self, monkeypatch, calendar
    ) -> None:
        years = self._patch_fetch(monkeypatch, calendar)
        self._patch_today(monkeypatch, date(2026, 12, 5))

        events = ics_feed.get_feed_events()
        assert years == [2026, 2027]
        assert len(events) == 8

    def test_failed_fetch_gives_empty_list(self, monkeypatch) -> None:
        self._patch_fetch(monkeypatch, None)
        self._patch_today(monkeypatch, date(2026, 7, 3))

        assert ics_feed.get_feed_events() == []


class TestFetchCalendar:
    def test_returns_none_on_network_error(self, monkeypatch) -> None:
        def fake_get(url, timeout):
            raise requests.ConnectionError("network down")

        monkeypatch.setattr(ics_feed.requests, "get", fake_get)
        assert ics_feed.fetch_calendar(2026) is None

    def test_returns_none_on_invalid_payload(self, monkeypatch) -> None:
        class FakeResponse:
            content = b"<html>not an ics</html>"

            def raise_for_status(self) -> None:
                pass

        monkeypatch.setattr(
            ics_feed.requests, "get", lambda url, timeout: FakeResponse()
        )
        assert ics_feed.fetch_calendar(2026) is None
