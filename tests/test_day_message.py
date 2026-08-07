import threading
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from astro_bot.handlers import get_specific_date_event as day_message
from astro_bot import templates, timezones
from astro_bot.timezones import (
    resolve_timezone,
    today_in,
    zone_for_location,
)
from tests.harness import serving_events, serving_profile


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

    def test_profile_is_read_once_per_message(self) -> None:
        with serving_events(day_message, [], attr="get_events_on_day"):
            with serving_profile(day_message) as reads:
                _, msg = day_message.get_day_message(
                    42, lambda today: today
                )

        assert reads == [42]
        assert templates.NOTHING_NEWS_FOUND in msg

    def test_picked_day_is_anchored_on_the_user_zone(self) -> None:
        """Kiritimati is UTC+14, so its local date can be a day ahead
        of the server's"""

        expected = datetime.now(ZoneInfo("Pacific/Kiritimati")).date()

        with serving_events(day_message, [], attr="get_events_on_day"):
            with serving_profile(day_message, tz="Pacific/Kiritimati"):
                day, _ = day_message.get_day_message(
                    42, lambda today: today
                )

        assert day == expected

    def test_empty_day_is_titled(self) -> None:
        target = date(2026, 7, 15)

        with serving_events(day_message, [], attr="get_events_on_day"):
            with serving_profile(day_message):
                _, msg = day_message.get_day_message(
                    42, lambda today: target
                )

        assert templates.format_day_title(target) in msg
        assert templates.NOTHING_NEWS_FOUND in msg

    def test_unavailable_service_is_not_an_empty_day(self) -> None:
        """Events are read live now: an outage must not read as a quiet
        sky"""

        with serving_events(day_message, None, attr="get_events_on_day"):
            with serving_profile(day_message):
                _, msg = day_message.get_day_message(
                    42, lambda today: today
                )

        assert msg == day_message.EVENTS_UNAVAILABLE_MESSAGE
        assert templates.NOTHING_NEWS_FOUND not in msg

    def test_pick_day_may_ignore_today(self) -> None:
        """The week arrows carry an explicit target day"""

        target = date(2026, 7, 15)

        with serving_events(day_message, [], attr="get_events_on_day"):
            with serving_profile(day_message):
                day, _ = day_message.get_day_message(
                    42, lambda today: target
                )

        assert day == target


class TestZoneForLocation:
    def test_places_a_point_on_land(self) -> None:
        assert zone_for_location(52.52, 13.40) == "Europe/Berlin"

    def test_open_water_still_resolves(self) -> None:
        # timezonefinder covers the oceans with the nominal offset for
        # the longitude, so a location shared at sea is not "no zone"
        assert zone_for_location(0.0, -140.0) == "Etc/GMT+9"

    def test_the_result_is_always_resolvable(self) -> None:
        # whatever comes back is fed straight to resolve_timezone
        for lat, lon in [(90, 0), (-90, 0), (0, 180), (0, -180)]:
            assert resolve_timezone(zone_for_location(lat, lon)) is not None

    def test_the_finder_is_reused_within_a_thread(self) -> None:
        # the constructor maps the boundary data and costs ~0.7s; /start
        # used to pay it per shared location, on the event loop
        first = timezones._location_finder()

        assert timezones._location_finder() is first

    def test_each_thread_gets_its_own_finder(self) -> None:
        # timezonefinder is explicit that an instance must not be shared
        # between threads, and this runs on asyncio.to_thread workers --
        # a race here writes a wrong zone into the user's profile
        finders = []
        threads = [
            threading.Thread(
                target=lambda: finders.append(timezones._location_finder())
            )
            for _ in range(3)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len({id(finder) for finder in finders}) == 3
        assert timezones._location_finder() not in finders

    def test_concurrent_lookups_agree(self) -> None:
        # kept to three: every thread here builds its own finder, and
        # that costs the better part of a second each
        results = []
        threads = [
            threading.Thread(
                target=lambda: results.append(zone_for_location(52.52, 13.40))
            )
            for _ in range(3)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert results == ["Europe/Berlin"] * 3
