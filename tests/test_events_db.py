from datetime import date, datetime, timezone

import pytest

from astro_bot import db
from astro_bot import db_queries as q
from astro_bot.services import events


def DT(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


@pytest.fixture()
def db_path(tmp_path) -> str:
    path = str(tmp_path / "test.db")
    db.db_init(path, q.create_events_table)
    return path


def add_event(
    db_path: str,
    uid: str,
    dt_utc: str,
    summary: str = "Full Moon",
    description: str = "The Moon reaches full phase.",
    url: str = "https://in-the-sky.org/news.php?id=1",
) -> None:
    db.write_into_db(
        db_path, q.upsert_event, (uid, dt_utc, summary, description, url)
    )


class TestEventQueries:
    def test_select_events_on_day(self, db_path) -> None:
        add_event(db_path, "e1", "2026-07-03T10:00:00+00:00")
        add_event(db_path, "e2", "2026-07-03T22:00:00+00:00")
        add_event(db_path, "e3", "2026-07-04T10:00:00+00:00")

        result = events.get_events_on_day(date(2026, 7, 3), db=db_path)
        assert [row[0] for row in result] == [
            "2026-07-03T10:00:00+00:00",
            "2026-07-03T22:00:00+00:00",
        ]

    def test_select_events_between(self, db_path) -> None:
        add_event(db_path, "e1", "2026-07-02T10:00:00+00:00")
        add_event(db_path, "e2", "2026-07-05T10:00:00+00:00")
        add_event(db_path, "e3", "2026-07-09T10:00:00+00:00")

        result = events.get_events_between(
            date(2026, 7, 2), date(2026, 7, 5), db=db_path
        )
        assert [row[0] for row in result] == [
            "2026-07-02T10:00:00+00:00",
            "2026-07-05T10:00:00+00:00",
        ]

    def test_day_respects_timezone(self, db_path) -> None:
        add_event(db_path, "e1", "2026-07-03T23:30:00+00:00")

        moscow = "Europe/Moscow"
        assert len(events.get_events_on_day(date(2026, 7, 3), db=db_path)) == 1
        assert events.get_events_on_day(
            date(2026, 7, 3), tz=moscow, db=db_path
        ) == []
        assert len(
            events.get_events_on_day(date(2026, 7, 4), tz=moscow, db=db_path)
        ) == 1

    def test_unknown_timezone_falls_back_to_utc(self, db_path) -> None:
        add_event(db_path, "e1", "2026-07-03T23:30:00+00:00")
        result = events.get_events_on_day(
            date(2026, 7, 3), tz="Mars/Olympus", db=db_path
        )
        assert len(result) == 1

    def test_upsert_replaces_event_with_same_uid(self, db_path) -> None:
        add_event(db_path, "e1", "2026-07-03T10:00:00+00:00", summary="old")
        add_event(db_path, "e1", "2026-07-03T11:00:00+00:00", summary="new")

        result = events.get_events_on_day(date(2026, 7, 3), db=db_path)
        assert len(result) == 1
        assert result[0][1] == "new"


def event_dict(uid: str, dt_utc: datetime) -> dict:
    return {
        "uid": uid,
        "dt_utc": dt_utc,
        "summary": "Full Moon",
        "description": "The Moon reaches full phase.",
        "url": "",
    }


def all_uids(db_path: str) -> list:
    rows = db.read_from_db(db_path, "SELECT uid FROM events ORDER BY dt_utc")
    return [row[0] for row in rows]


class TestSyncEvents:
    def _patch_now(self, monkeypatch, now: datetime) -> None:
        class FakeDateTime(datetime):
            @classmethod
            def now(cls, tz=None) -> datetime:
                return now if tz is None else now.astimezone(tz)

        monkeypatch.setattr(events, "datetime", FakeDateTime)

    def _patch_source(self, monkeypatch, years: list, by_year: dict) -> None:
        monkeypatch.setattr(events, "sync_years", lambda: years)
        monkeypatch.setattr(events, "fetch_year", lambda year: by_year[year])

    def test_writes_events_to_db(self, db_path, monkeypatch) -> None:
        self._patch_now(monkeypatch, DT(2026, 1, 1))
        self._patch_source(
            monkeypatch,
            [2026],
            {2026: [event_dict("e1", DT(2026, 7, 3, 10))]},
        )

        events.sync_events(db=db_path)
        result = events.get_events_on_day(date(2026, 7, 3), db=db_path)
        assert result == [
            (
                "2026-07-03T10:00:00+00:00",
                "Full Moon",
                "The Moon reaches full phase.",
                "",
            )
        ]

    def test_unsynced_year_writes_nothing(self, db_path, monkeypatch) -> None:
        # fetch_year returns None (network/503/uncovered) -> skipped
        self._patch_now(monkeypatch, DT(2026, 1, 1))
        self._patch_source(monkeypatch, [2026], {2026: None})

        events.sync_events(db=db_path)
        assert all_uids(db_path) == []

    def test_prunes_future_phantom_not_returned(
        self, db_path, monkeypatch
    ) -> None:
        add_event(db_path, "phantom", "2026-09-01T10:00:00+00:00")
        self._patch_now(monkeypatch, DT(2026, 7, 15))
        self._patch_source(
            monkeypatch,
            [2026],
            {2026: [event_dict("kept", DT(2026, 8, 1, 9))]},
        )

        events.sync_events(db=db_path)
        assert all_uids(db_path) == ["kept"]

    def test_keeps_past_events_not_returned(
        self, db_path, monkeypatch
    ) -> None:
        add_event(db_path, "history", "2026-03-01T10:00:00+00:00")
        self._patch_now(monkeypatch, DT(2026, 7, 15))
        self._patch_source(
            monkeypatch,
            [2026],
            {2026: [event_dict("kept", DT(2026, 8, 1, 9))]},
        )

        events.sync_events(db=db_path)
        assert all_uids(db_path) == ["history", "kept"]

    def test_unsynced_year_does_not_prune(
        self, db_path, monkeypatch
    ) -> None:
        add_event(db_path, "future", "2026-09-01T10:00:00+00:00")
        self._patch_now(monkeypatch, DT(2026, 7, 15))
        self._patch_source(monkeypatch, [2026], {2026: None})

        events.sync_events(db=db_path)
        assert all_uids(db_path) == ["future"]

    def test_does_not_prune_other_years(self, db_path, monkeypatch) -> None:
        add_event(db_path, "next-year", "2027-02-01T10:00:00+00:00")
        self._patch_now(monkeypatch, DT(2026, 7, 15))
        self._patch_source(
            monkeypatch,
            [2026],
            {2026: [event_dict("kept", DT(2026, 8, 1, 9))]},
        )

        events.sync_events(db=db_path)
        assert all_uids(db_path) == ["kept", "next-year"]


class TestInitStorage:
    def test_creates_tables(self, tmp_path) -> None:
        path = str(tmp_path / "fresh.db")
        events.init_storage(db=path)

        columns = [
            col[1] for col in db.read_from_db(path, q.select_events_columns)
        ]
        assert columns == ["uid", "dt_utc", "summary", "description", "url"]

    def test_drops_legacy_events_table(self, tmp_path) -> None:
        path = str(tmp_path / "legacy.db")
        legacy_table = """CREATE TABLE events (
            row_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL
            )"""
        db.db_init(path, legacy_table)

        events.init_storage(db=path)
        columns = [
            col[1] for col in db.read_from_db(path, q.select_events_columns)
        ]
        assert "uid" in columns and "date" not in columns

    def test_removes_legacy_feed_events(self, tmp_path) -> None:
        path = str(tmp_path / "mixed.db")
        db.db_init(path, q.create_events_table)
        add_event(
            path, "20260101_08_100@in-the-sky.org", "2026-01-01T21:44:19+00:00"
        )
        add_event(path, "full_moon:moon:20260703", "2026-07-03T10:00:00+00:00")

        events.init_storage(db=path)
        assert all_uids(path) == ["full_moon:moon:20260703"]
