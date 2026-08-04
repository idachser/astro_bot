import asyncio
from datetime import datetime, timezone

import pytest

from astro_bot.config import (
    DIGEST_CATCHUP_HOURS,
    DIGEST_HOUR_UTC,
    DIGEST_RETRY_DELAYS,
)
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


def utc(year, month, day, hour=0, minute=0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


class TestNextDigestTime:
    """2026-08-08 is a Saturday"""

    def test_waits_for_the_slot_earlier_that_saturday(self) -> None:
        now = utc(2026, 8, 8, DIGEST_HOUR_UTC - 1)
        assert autosend_events.next_digest_time(now) == utc(
            2026, 8, 8, DIGEST_HOUR_UTC
        )

    def test_restart_after_the_slot_waits_a_whole_week(self) -> None:
        # the bug: a Saturday deploy used to broadcast a second copy to
        # every user the moment the container came back up
        now = utc(2026, 8, 8, DIGEST_HOUR_UTC, 1)
        assert autosend_events.next_digest_time(now) == utc(
            2026, 8, 15, DIGEST_HOUR_UTC
        )

    def test_slot_does_not_drift_after_a_slow_send(self) -> None:
        # 21 minutes of fetch retries must not move next week's slot
        now = utc(2026, 8, 8, DIGEST_HOUR_UTC, 21)
        assert autosend_events.next_digest_time(now) == utc(
            2026, 8, 15, DIGEST_HOUR_UTC
        )

    def test_midweek_start_finds_the_coming_saturday(self) -> None:
        now = utc(2026, 8, 5, 23, 30)  # Wednesday
        assert autosend_events.next_digest_time(now) == utc(
            2026, 8, 8, DIGEST_HOUR_UTC
        )

    def test_sunday_start_finds_the_next_saturday(self) -> None:
        now = utc(2026, 8, 9, 10)
        assert autosend_events.next_digest_time(now) == utc(
            2026, 8, 15, DIGEST_HOUR_UTC
        )


@pytest.fixture(autouse=True)
def blank_marker(monkeypatch):
    """No slot on record unless a test says otherwise -- and never the
    real file, which lives next to the production DB"""

    monkeypatch.setattr(autosend_events, "read_last_slot", lambda: None)
    monkeypatch.setattr(autosend_events, "record_slot", lambda slot: None)


class TestMissedDigestSlot:
    """A restart spanning the slot must not skip the week in silence,
    and must not repeat a slot the marker already names"""

    def test_restart_just_after_the_slot_catches_up(self) -> None:
        now = utc(2026, 8, 8, DIGEST_HOUR_UTC, 3)
        assert autosend_events.missed_digest_slot(now) is True

    def test_the_slot_itself_counts(self) -> None:
        now = utc(2026, 8, 8, DIGEST_HOUR_UTC)
        assert autosend_events.missed_digest_slot(now) is True

    def test_before_the_slot_waits_for_it(self) -> None:
        # the scheduler's own sleep will fire it; catching up here would
        # send an hour early
        now = utc(2026, 8, 8, DIGEST_HOUR_UTC - 1, 59)
        assert autosend_events.missed_digest_slot(now) is False

    def test_past_the_window_does_not_catch_up(self) -> None:
        now = utc(2026, 8, 8, DIGEST_HOUR_UTC + DIGEST_CATCHUP_HOURS, 1)
        assert autosend_events.missed_digest_slot(now) is False

    def test_other_weekdays_never_catch_up(self) -> None:
        now = utc(2026, 8, 9, DIGEST_HOUR_UTC, 3)  # Sunday
        assert autosend_events.missed_digest_slot(now) is False

    def test_window_may_run_past_midnight(self, monkeypatch) -> None:
        # a late slot pushes the window into Sunday; testing the weekday
        # instead of the slot used to drop the catch-up silently there
        monkeypatch.setattr(autosend_events, "DIGEST_HOUR_UTC", 23)
        monkeypatch.setattr(autosend_events, "DIGEST_CATCHUP_HOURS", 2)

        assert autosend_events.missed_digest_slot(
            utc(2026, 8, 8, 23, 30)
        ) is True
        assert autosend_events.missed_digest_slot(
            utc(2026, 8, 9, 0, 15)
        ) is True
        assert autosend_events.missed_digest_slot(
            utc(2026, 8, 9, 1, 30)
        ) is False

    def test_marker_on_this_slot_suppresses_the_catch_up(
        self, monkeypatch
    ) -> None:
        # "sent at 09:00, CI redeployed at 09:03" -- the case a clock
        # alone cannot tell from "was down through the slot"
        slot = utc(2026, 8, 8, DIGEST_HOUR_UTC)
        monkeypatch.setattr(autosend_events, "read_last_slot", lambda: slot)

        assert autosend_events.missed_digest_slot(
            utc(2026, 8, 8, DIGEST_HOUR_UTC, 3)
        ) is False

    def test_marker_from_a_previous_week_still_catches_up(
        self, monkeypatch
    ) -> None:
        stale = utc(2026, 8, 1, DIGEST_HOUR_UTC)
        monkeypatch.setattr(autosend_events, "read_last_slot", lambda: stale)

        assert autosend_events.missed_digest_slot(
            utc(2026, 8, 8, DIGEST_HOUR_UTC, 3)
        ) is True


class TestSchedulerStartup:
    """The catch-up must fire before the loop's first sleep, and exactly
    once -- the loop then waits out a whole week"""

    def run_scheduler(
        self, monkeypatch, now: datetime, sends: bool = True, last=None
    ) -> tuple:
        sent, slept, recorded = [], [], []

        class FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return now

        async def fake_send(bot) -> bool:
            sent.append(now)
            return sends

        async def fake_sleep(delay) -> None:
            slept.append(delay)
            raise SystemExit  # stop at the first scheduled wait

        monkeypatch.setattr(autosend_events, "datetime", FrozenDatetime)
        monkeypatch.setattr(autosend_events, "send_weekly_digest", fake_send)
        monkeypatch.setattr(autosend_events, "read_last_slot", lambda: last)
        monkeypatch.setattr(autosend_events, "record_slot", recorded.append)
        monkeypatch.setattr(asyncio, "sleep", fake_sleep)

        try:
            asyncio.run(autosend_events.scheduler(None))
        except SystemExit:
            pass
        return sent, slept, recorded

    def test_restart_inside_the_window_sends_before_sleeping(
        self, monkeypatch
    ) -> None:
        sent, slept, recorded = self.run_scheduler(
            monkeypatch, utc(2026, 8, 8, DIGEST_HOUR_UTC, 3)
        )

        assert len(sent) == 1
        # the slot goes on record, so the next restart stays quiet
        assert recorded == [utc(2026, 8, 8, DIGEST_HOUR_UTC)]
        # ...and then stands down for a full week, not for the same slot
        assert slept == [(utc(2026, 8, 15, DIGEST_HOUR_UTC)
                          - utc(2026, 8, 8, DIGEST_HOUR_UTC, 3))
                         .total_seconds()]

    def test_marker_stops_the_redeploy_from_repeating(
        self, monkeypatch
    ) -> None:
        # the crash-loop case: every restart inside the window used to
        # mail another copy to every user
        sent, _, recorded = self.run_scheduler(
            monkeypatch,
            utc(2026, 8, 8, DIGEST_HOUR_UTC, 3),
            last=utc(2026, 8, 8, DIGEST_HOUR_UTC),
        )

        assert sent == []
        assert recorded == []

    def test_a_send_that_went_nowhere_is_not_recorded(
        self, monkeypatch
    ) -> None:
        # an outage sent nothing, so the slot stays open for a retry
        sent, _, recorded = self.run_scheduler(
            monkeypatch, utc(2026, 8, 8, DIGEST_HOUR_UTC, 3), sends=False
        )

        assert len(sent) == 1
        assert recorded == []

    def test_restart_outside_the_window_only_sleeps(
        self, monkeypatch
    ) -> None:
        sent, slept, _ = self.run_scheduler(
            monkeypatch, utc(2026, 8, 8, DIGEST_HOUR_UTC + 4)
        )

        assert sent == []
        assert slept == [(utc(2026, 8, 15, DIGEST_HOUR_UTC)
                          - utc(2026, 8, 8, DIGEST_HOUR_UTC + 4))
                         .total_seconds()]
