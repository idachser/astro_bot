from datetime import date

import pytest
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

JULY = (date(2026, 7, 1), date(2026, 7, 8))


@pytest.fixture(autouse=True)
def clear_cache():
    skyevents._cache.clear()
    yield
    skyevents._cache.clear()


def patch_get(monkeypatch, *responses) -> list:
    """Answer each request with the next response, recording the calls"""

    calls = []
    queue = list(responses)

    def fake_get(url, params, timeout):
        calls.append((url, params))
        return queue.pop(0) if len(queue) > 1 else queue[0]

    monkeypatch.setattr(skyevents.requests, "get", fake_get)
    return calls


class TestFetchRange:
    def test_requests_the_range_as_given(self, monkeypatch) -> None:
        calls = patch_get(monkeypatch, FakeResponse(_payload()))
        skyevents.fetch_range(*JULY)

        url, params = calls[0]
        assert url.endswith("/v1/events")
        assert params == {"from": "2026-07-01", "to": "2026-07-08"}

    def test_parses_event_rows(self, monkeypatch) -> None:
        patch_get(monkeypatch, FakeResponse(_payload(EVENT)))
        assert skyevents.fetch_range(*JULY) == [
            ("2026-07-03T10:00:00+00:00", "Full moon", "", "")
        ]

    def test_orders_by_time(self, monkeypatch) -> None:
        later = dict(EVENT, dt_utc="2026-07-05T09:00:00+00:00")
        earlier = dict(EVENT, dt_utc="2026-07-02T09:00:00.123456+00:00")
        patch_get(monkeypatch, FakeResponse(_payload(later, EVENT, earlier)))

        assert [row[0] for row in skyevents.fetch_range(*JULY)] == [
            "2026-07-02T09:00:00.123456+00:00",
            "2026-07-03T10:00:00+00:00",
            "2026-07-05T09:00:00+00:00",
        ]

    def test_null_coverage_returns_none(self, monkeypatch) -> None:
        # None, not [] -- an ungenerated range is not an empty sky
        patch_get(
            monkeypatch, FakeResponse(_payload(EVENT, coverage=False))
        )
        assert skyevents.fetch_range(*JULY) is None

    def test_non_2xx_returns_none(self, monkeypatch) -> None:
        patch_get(
            monkeypatch, FakeResponse(_payload(EVENT), status_ok=False)
        )
        assert skyevents.fetch_range(*JULY) is None

    def test_network_error_returns_none(self, monkeypatch) -> None:
        def fake_get(url, params, timeout):
            raise requests.ConnectionError("network down")

        monkeypatch.setattr(skyevents.requests, "get", fake_get)
        assert skyevents.fetch_range(*JULY) is None

    def test_unexpected_shape_returns_none(self, monkeypatch) -> None:
        patch_get(monkeypatch, FakeResponse({"events": [{}], "coverage": {}}))
        assert skyevents.fetch_range(*JULY) is None


class TestCache:
    def test_range_is_fetched_once(self, monkeypatch) -> None:
        calls = patch_get(monkeypatch, FakeResponse(_payload(EVENT)))

        first = skyevents.fetch_range(*JULY)
        second = skyevents.fetch_range(*JULY)

        assert first == second
        assert len(calls) == 1

    def test_other_ranges_are_fetched_separately(self, monkeypatch) -> None:
        calls = patch_get(monkeypatch, FakeResponse(_payload(EVENT)))

        skyevents.fetch_range(*JULY)
        skyevents.fetch_range(date(2026, 8, 1), date(2026, 8, 8))

        assert len(calls) == 2

    def test_failures_are_not_cached(self, monkeypatch) -> None:
        calls = patch_get(
            monkeypatch,
            FakeResponse(_payload(EVENT), status_ok=False),
            FakeResponse(_payload(EVENT)),
        )

        assert skyevents.fetch_range(*JULY) is None
        assert skyevents.fetch_range(*JULY) is not None
        assert len(calls) == 2

    def test_expired_entries_are_dropped(self, monkeypatch) -> None:
        calls = patch_get(monkeypatch, FakeResponse(_payload(EVENT)))
        skyevents.fetch_range(*JULY)

        stored_at, events = skyevents._cache[JULY]
        aged = stored_at - skyevents.EVENTS_CACHE_TTL_SECONDS
        skyevents._cache[JULY] = (aged, events)

        skyevents.fetch_range(*JULY)
        assert len(calls) == 2
