import asyncio

from astro_bot.config import DIGEST_RETRY_DELAYS
from astro_bot.handlers import autosend_events


EVENTS = [("2026-07-03T10:00:00+00:00", "Full moon", "", "")]


class FakeBot:
    def __init__(self) -> None:
        self.sent = []

    async def send_message(self, user_id, text, **kwargs) -> None:
        self.sent.append((user_id, text))


def run_digest(monkeypatch, outcomes: list) -> tuple:
    """Send a digest with a canned sequence of fetch outcomes, returning
    the bot's sent messages and the delays waited (without waiting)"""

    calls = iter(outcomes)
    slept = []

    async def fake_sleep(delay) -> None:
        slept.append(delay)

    def fake_fetch(start, end):
        outcome = next(calls)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(autosend_events, "get_events_between", fake_fetch)
    monkeypatch.setattr(autosend_events, "get_users_ids", lambda: [1, 2])
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    bot = FakeBot()
    asyncio.run(autosend_events.send_weekly_digest(bot))
    return bot.sent, slept


class TestWeeklyDigest:
    def test_sends_to_every_user(self, monkeypatch) -> None:
        sent, slept = run_digest(monkeypatch, [EVENTS])

        assert [user_id for user_id, _ in sent] == [1, 2]
        assert "Full moon" in sent[0][1]
        assert slept == []

    def test_retries_while_skyevents_is_cold(self, monkeypatch) -> None:
        sent, slept = run_digest(monkeypatch, [None, None, EVENTS])

        assert [user_id for user_id, _ in sent] == [1, 2]
        assert slept == list(DIGEST_RETRY_DELAYS[:2])

    def test_unreachable_service_sends_nothing(self, monkeypatch) -> None:
        # never a "no events this week" digest to everyone on an outage
        attempts = len(DIGEST_RETRY_DELAYS) + 1
        sent, slept = run_digest(monkeypatch, [None] * attempts)

        assert sent == []
        assert slept == list(DIGEST_RETRY_DELAYS)

    def test_empty_week_sends_nothing(self, monkeypatch) -> None:
        sent, slept = run_digest(monkeypatch, [[]])

        assert sent == []
        assert slept == []

    def test_raising_fetch_is_a_failed_attempt(self, monkeypatch) -> None:
        # a raise must not escape and kill the scheduler task
        sent, slept = run_digest(
            monkeypatch, [RuntimeError("connect failed"), EVENTS]
        )

        assert [user_id for user_id, _ in sent] == [1, 2]
        assert slept == [DIGEST_RETRY_DELAYS[0]]
