from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from astro_bot.handlers import get_specific_date_event as day_message
from astro_bot.timezones import today_in


class TestTodayIn:
    def test_today_is_the_local_date(self) -> None:
        expected = datetime.now(ZoneInfo("Pacific/Kiritimati")).date()
        assert today_in("Pacific/Kiritimati") == expected

    def test_unknown_zone_falls_back_to_utc(self) -> None:
        expected = datetime.now(timezone.utc).date()
        assert today_in("Mars/Olympus") == expected
        assert today_in("") == expected


class TestDayMessageProfileReads:
    """The profile feeds the day window, the event times and the
    forecast; reading it more than once means an extra DB round trip
    per message, and reading it in a handler puts it on the event loop
    """

    def profile_counter(self, monkeypatch, tz: str = ""):
        reads = []

        def fake_profile(user_id, db=None):
            reads.append(user_id)
            return (tz, None, None)

        monkeypatch.setattr(
            day_message, "get_user_profile", fake_profile
        )
        monkeypatch.setattr(
            day_message, "get_events_on_day", lambda day, tz="": []
        )
        return reads

    def test_profile_is_read_once_per_message(self, monkeypatch) -> None:
        reads = self.profile_counter(monkeypatch)

        day, msg = day_message.get_day_message(42, lambda today: today)

        assert reads == [42]
        assert msg == day_message.NOTHING_NEWS_FOUND

    def test_picked_day_is_anchored_on_the_user_zone(
        self, monkeypatch
    ) -> None:
        """Kiritimati is UTC+14, so its local date can be a day ahead
        of the server's"""

        self.profile_counter(monkeypatch, tz="Pacific/Kiritimati")
        expected = datetime.now(ZoneInfo("Pacific/Kiritimati")).date()

        day, _ = day_message.get_day_message(42, lambda today: today)

        assert day == expected

    def test_pick_day_may_ignore_today(self, monkeypatch) -> None:
        """The week arrows carry an explicit target day"""

        self.profile_counter(monkeypatch)
        target = date(2026, 7, 15)

        day, _ = day_message.get_day_message(42, lambda today: target)

        assert day == target
