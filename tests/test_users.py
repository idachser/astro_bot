from astro_bot import db
from astro_bot import db_queries as q
from astro_bot.services import users
from astro_bot.services.users import init_storage
from tests.harness import make_user

create_legacy_users_table = """CREATE TABLE users (
    telegram_id BIGINT PRIMARY KEY,
    user_name TEXT NOT NULL,
    name TEXT,
    timezone TEXT
    )"""


class TestUsers:
    def test_add_and_get_ids(self, user_db) -> None:
        users.add_user(make_user(id=1), db=user_db)
        users.add_user(make_user(id=2), db=user_db)
        assert users.get_users_ids(db=user_db) == [1, 2]

    def test_profile_returns_timezone_and_location(self, user_db) -> None:
        users.add_user(make_user(), db=user_db)
        profile = users.get_user_profile(42, db=user_db)
        assert profile == ("Europe/Berlin", 52.52, 13.41)

    def test_restart_updates_profile(self, user_db) -> None:
        users.add_user(make_user(), db=user_db)
        users.add_user(
            make_user(timezone="Asia/Tokyo", lat=35.68, lon=139.69),
            db=user_db,
        )

        assert users.get_users_ids(db=user_db) == [42]
        profile = users.get_user_profile(42, db=user_db)
        assert profile == ("Asia/Tokyo", 35.68, 139.69)

    def test_default_time_user_has_no_location(self, user_db) -> None:
        users.add_user(
            make_user(timezone="", lat=None, lon=None), db=user_db
        )
        assert users.get_user_profile(42, db=user_db) == ("", None, None)

    def test_none_fields_are_stored_empty(self, user_db) -> None:
        users.add_user(
            make_user(username=None, timezone=None), db=user_db
        )
        assert users.get_users_ids(db=user_db) == [42]
        assert users.get_user_profile(42, db=user_db)[0] == ""

    def test_unknown_user_has_empty_profile(self, user_db) -> None:
        assert users.get_user_profile(99, db=user_db) == ("", None, None)


class TestInitStorage:
    def test_creates_the_users_table(self, tmp_path) -> None:
        path = str(tmp_path / "fresh.db")
        init_storage(db=path)

        columns = [
            col[1] for col in db.read_from_db(path, q.select_users_columns)
        ]
        assert columns == [
            "telegram_id",
            "user_name",
            "name",
            "timezone",
            "lat",
            "lon",
        ]

    def test_enables_wal(self, tmp_path) -> None:
        path = str(tmp_path / "fresh.db")
        init_storage(db=path)

        mode = db.read_from_db(path, q.select_journal_mode)
        assert mode[0][0].lower() == "wal"

    def test_drops_the_events_table_of_older_versions(self, tmp_path) -> None:
        path = str(tmp_path / "with_events.db")
        db.db_init(path, "CREATE TABLE events (uid TEXT PRIMARY KEY)")

        init_storage(db=path)

        tables = db.read_from_db(
            path, "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
        assert [row[0] for row in tables] == ["users"]


class TestLocationMigration:
    def test_lat_lon_added_to_legacy_table(self, tmp_path) -> None:
        path = str(tmp_path / "test.db")
        db.db_init(path, create_legacy_users_table)
        db.write_into_db(
            path,
            "INSERT INTO users VALUES (?, ?, ?, ?)",
            (42, "igor42", "Igor", "Europe/Berlin"),
        )

        init_storage(db=path)

        profile = users.get_user_profile(42, db=path)
        assert profile == ("Europe/Berlin", None, None)


class TestUnopenableDatabase:
    """A connect failure must degrade, not escape: these run inside
    `get_day_message` on a worker thread, in a handler that catches
    nothing, so a raise means the user gets no reply at all"""

    def test_connect_failure_returns_none(self, tmp_path) -> None:
        assert db.create_connection(str(tmp_path)) is None  # a directory

    def test_reads_degrade_to_empty(self, tmp_path) -> None:
        assert db.read_from_db(str(tmp_path), q.select_users_id) == []

    def test_writes_are_swallowed(self, tmp_path) -> None:
        db.write_into_db(str(tmp_path), q.upsert_user, (1, "u", "n", "", 0, 0))

    def test_profile_falls_back_to_the_default(self, tmp_path) -> None:
        profile = users.get_user_profile(42, db=str(tmp_path))

        assert profile == ("", None, None)
