from datetime import date, datetime, timezone

import pytest

from astro_bot import db
from astro_bot import db_queries as q
from astro_bot.services import events


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


class TestSyncEvents:
    def test_writes_feed_events_to_db(self, db_path, monkeypatch) -> None:
        feed = [
            {
                "uid": "e1",
                "dt_utc": datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc),
                "summary": "Full Moon",
                "description": "The Moon reaches full phase.",
                "url": "https://in-the-sky.org/news.php?id=1",
            }
        ]
        monkeypatch.setattr(events, "get_feed_events", lambda: feed)

        events.sync_events(db=db_path)
        result = events.get_events_on_day(date(2026, 7, 3), db=db_path)
        assert result == [
            (
                "2026-07-03T10:00:00+00:00",
                "Full Moon",
                "The Moon reaches full phase.",
                "https://in-the-sky.org/news.php?id=1",
            )
        ]

    def test_empty_feed_writes_nothing(self, db_path, monkeypatch) -> None:
        monkeypatch.setattr(events, "get_feed_events", lambda: [])
        events.sync_events(db=db_path)
        assert events.get_events_between(
            date(2020, 1, 1), date(2030, 1, 1), db=db_path
        ) == []


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
