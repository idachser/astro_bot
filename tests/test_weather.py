import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests

from astro_bot.services import weather

FIXTURE = Path(__file__).parent / "fixtures" / "open_meteo.json"

# The fixture holds 2026-07-18: cloud_cover = 4 * hour,
# visibility = hour km; NOW is noon UTC that day
NOW = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
LAT, LON = 52.52, 13.41


def event(dt_utc: str) -> tuple:
    return (dt_utc, "Full Moon", "", "")


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@pytest.fixture()
def api(monkeypatch):
    """Stub Open-Meteo with the fixture, counting requests"""

    payload = json.loads(FIXTURE.read_text())
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        return FakeResponse(payload)

    monkeypatch.setattr(weather.requests, "get", fake_get)
    weather._cache.clear()
    return calls


class TestEventsWeather:
    def test_maps_event_hour_to_forecast(self, api) -> None:
        events = [event("2026-07-18T21:04:00+00:00")]
        rows = weather.get_events_weather(events, LAT, LON, now=NOW)
        assert rows == [("21:04", 84, 21)]

    def test_user_timezone_shifts_forecast_hour(self, api) -> None:
        events = [event("2026-07-18T19:30:00+00:00")]
        rows = weather.get_events_weather(
            events, LAT, LON, tz="Europe/Berlin", now=NOW
        )
        assert rows == [("21:30", 84, 21)]
        assert api[0]["timezone"] == "Europe/Berlin"

    def test_past_events_skipped(self, api) -> None:
        events = [event("2026-07-18T08:00:00+00:00")]
        assert weather.get_events_weather(events, LAT, LON, now=NOW) == []
        assert api == []

    def test_events_beyond_horizon_skipped(self, api) -> None:
        events = [event("2026-07-30T21:00:00+00:00")]
        assert weather.get_events_weather(events, LAT, LON, now=NOW) == []
        assert api == []

    def test_date_only_events_skipped(self, api) -> None:
        events = [event("2026-07-18T00:00:00+00:00")]
        assert weather.get_events_weather(events, LAT, LON, now=NOW) == []
        assert api == []

    def test_no_location_no_weather(self, api) -> None:
        events = [event("2026-07-18T21:04:00+00:00")]
        assert weather.get_events_weather(events, None, None, now=NOW) == []
        assert api == []

    def test_same_day_events_share_one_request(self, api) -> None:
        events = [
            event("2026-07-18T20:30:00+00:00"),
            event("2026-07-18T22:15:00+00:00"),
        ]
        rows = weather.get_events_weather(events, LAT, LON, now=NOW)
        assert rows == [("20:30", 80, 20), ("22:15", 88, 22)]
        assert len(api) == 1

    def test_forecast_is_cached_between_calls(self, api) -> None:
        events = [event("2026-07-18T21:04:00+00:00")]
        weather.get_events_weather(events, LAT, LON, now=NOW)
        weather.get_events_weather(events, LAT, LON, now=NOW)
        assert len(api) == 1


class TestApiFailure:
    def test_request_error_means_no_weather(self, monkeypatch) -> None:
        def fake_get(url, params=None, timeout=None):
            raise requests.ConnectionError("boom")

        monkeypatch.setattr(weather.requests, "get", fake_get)
        weather._cache.clear()

        events = [event("2026-07-18T21:04:00+00:00")]
        assert weather.get_events_weather(events, LAT, LON, now=NOW) == []

    def test_malformed_payload_means_no_weather(self, monkeypatch) -> None:
        monkeypatch.setattr(
            weather.requests,
            "get",
            lambda url, params=None, timeout=None: FakeResponse({}),
        )
        weather._cache.clear()

        events = [event("2026-07-18T21:04:00+00:00")]
        assert weather.get_events_weather(events, LAT, LON, now=NOW) == []
