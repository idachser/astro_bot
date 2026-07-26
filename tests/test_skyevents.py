from datetime import date, datetime, timezone

import requests

from astro_bot.services import skyevents


class FakeResponse:
    def __init__(self, payload, status_ok=True):
        self._payload = payload
        self._status_ok = status_ok

    def raise_for_status(self) -> None:
        if not self._status_ok:
            raise requests.HTTPError("503 Service Unavailable")

    def json(self):
        return self._payload


def _payload(*events, coverage=True):
    return {
        "events": list(events),
        "coverage": {"from": "x", "to": "y"} if coverage else None,
    }


EVENT = {
    "uid": "full_moon:moon:20260703",
    "type": "moon_phase",
    "dt_utc": "2026-07-03T10:00:00+00:00",
    "bodies": ["moon"],
    "params": {"phase": "full"},
    "summary": "Full moon",
    "description": "",
    "url": "",
}


class TestFetchYear:
    def _patch_get(self, monkeypatch, response):
        captured = {}

        def fake_get(url, params, timeout):
            captured["url"] = url
            captured["params"] = params
            return response

        monkeypatch.setattr(skyevents.requests, "get", fake_get)
        return captured

    def test_requests_the_year_window(self, monkeypatch) -> None:
        captured = self._patch_get(monkeypatch, FakeResponse(_payload()))
        skyevents.fetch_year(2026)
        assert captured["url"].endswith("/v1/events")
        assert captured["params"] == {"from": "2026-01-01", "to": "2027-01-01"}

    def test_parses_event_fields(self, monkeypatch) -> None:
        self._patch_get(monkeypatch, FakeResponse(_payload(EVENT)))
        event = skyevents.fetch_year(2026)[0]
        assert event == {
            "uid": "full_moon:moon:20260703",
            "dt_utc": datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc),
            "summary": "Full moon",
            "description": "",
            "url": "",
        }

    def test_null_coverage_returns_none(self, monkeypatch) -> None:
        # None, not [] -- the caller must not prune an unsynced year
        self._patch_get(
            monkeypatch, FakeResponse(_payload(EVENT, coverage=False))
        )
        assert skyevents.fetch_year(2026) is None

    def test_non_2xx_returns_none(self, monkeypatch) -> None:
        self._patch_get(
            monkeypatch, FakeResponse(_payload(EVENT), status_ok=False)
        )
        assert skyevents.fetch_year(2026) is None

    def test_network_error_returns_none(self, monkeypatch) -> None:
        def fake_get(url, params, timeout):
            raise requests.ConnectionError("network down")

        monkeypatch.setattr(skyevents.requests, "get", fake_get)
        assert skyevents.fetch_year(2026) is None


class TestSyncYears:
    def _patch_today(self, monkeypatch, today: date) -> None:
        class FakeDate(date):
            @classmethod
            def today(cls) -> date:
                return today

        monkeypatch.setattr(skyevents, "date", FakeDate)

    def test_current_year_only(self, monkeypatch) -> None:
        self._patch_today(monkeypatch, date(2026, 7, 3))
        assert skyevents.sync_years() == [2026]

    def test_next_year_in_december(self, monkeypatch) -> None:
        self._patch_today(monkeypatch, date(2026, 12, 5))
        assert skyevents.sync_years() == [2026, 2027]
