from datetime import date

import pytest

from astro_bot.handlers.specific_date import (
    DateNotThisYear,
    day_picker,
    parse_month_day,
)


class TestParseMonthDay:
    def test_reads_a_month_and_a_day(self) -> None:
        assert parse_month_day("July 15") == (7, 15)

    def test_tolerates_surrounding_space(self) -> None:
        assert parse_month_day("  July 15  ") == (7, 15)

    def test_accepts_february_29(self) -> None:
        # strptime defaults to 1900, a common year, so the plain
        # "%B %d" parse rejected this outright and a leap-year lookup
        # was impossible no matter which year the user was in
        assert parse_month_day("February 29") == (2, 29)

    def test_rejects_a_day_that_exists_in_no_year(self) -> None:
        assert parse_month_day("February 30") is None

    def test_rejects_ordinary_chatter(self) -> None:
        # this handler is the catch-all, so most messages land here
        assert parse_month_day("hello") is None
        assert parse_month_day("Jul 15") is None
        assert parse_month_day("") is None


class TestDayPicker:
    def test_resolves_into_the_users_own_year(self) -> None:
        pick = day_picker(7, 15)

        assert pick(date(2026, 1, 1)) == date(2026, 7, 15)
        assert pick(date(2028, 12, 31)) == date(2028, 7, 15)

    def test_february_29_resolves_in_a_leap_year(self) -> None:
        assert day_picker(2, 29)(date(2028, 6, 1)) == date(2028, 2, 29)

    def test_february_29_is_flagged_in_a_common_year(self) -> None:
        # the handler answers NO_SUCH_DATE_MESSAGE for this; a bare
        # ValueError here would escape the worker thread instead and the
        # user would get no reply at all
        with pytest.raises(DateNotThisYear):
            day_picker(2, 29)(date(2026, 6, 1))

    def test_the_year_comes_from_the_user_not_the_server(self) -> None:
        # `today` is the user's local today, so around New Year two users
        # asking the same thing resolve into different years
        pick = day_picker(2, 29)

        assert pick(date(2028, 1, 1)) == date(2028, 2, 29)
        with pytest.raises(DateNotThisYear):
            pick(date(2027, 12, 31))
