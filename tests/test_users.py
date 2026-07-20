import pytest

from astro_bot import db
from astro_bot import db_queries as q
from astro_bot.services import users
from astro_bot.services.events import init_storage

create_legacy_users_table = """CREATE TABLE users (
    telegram_id BIGINT PRIMARY KEY,
    user_name TEXT NOT NULL,
    name TEXT,
    timezone TEXT
    )"""


@pytest.fixture()
def db_path(tmp_path) -> str:
    path = str(tmp_path / "test.db")
    db.db_init(path, q.create_users_table)
    return path


def make_user(**overrides) -> dict:
    user = {
        "id": 42,
        "name": "Igor",
        "username": "igor42",
        "timezone": "Europe/Berlin",
        "lat": 52.52,
        "lon": 13.41,
    }
    user.update(overrides)
    return user


class TestUsers:
    def test_add_and_get_ids(self, db_path) -> None:
        users.add_user(make_user(id=1), db=db_path)
        users.add_user(make_user(id=2), db=db_path)
        assert users.get_users_ids(db=db_path) == [1, 2]

    def test_profile_returns_timezone_and_location(self, db_path) -> None:
        users.add_user(make_user(), db=db_path)
        profile = users.get_user_profile(42, db=db_path)
        assert profile == ("Europe/Berlin", 52.52, 13.41)

    def test_restart_updates_profile(self, db_path) -> None:
        users.add_user(make_user(), db=db_path)
        users.add_user(
            make_user(timezone="Asia/Tokyo", lat=35.68, lon=139.69),
            db=db_path,
        )

        assert users.get_users_ids(db=db_path) == [42]
        profile = users.get_user_profile(42, db=db_path)
        assert profile == ("Asia/Tokyo", 35.68, 139.69)

    def test_default_time_user_has_no_location(self, db_path) -> None:
        users.add_user(
            make_user(timezone="", lat=None, lon=None), db=db_path
        )
        assert users.get_user_profile(42, db=db_path) == ("", None, None)

    def test_none_fields_are_stored_empty(self, db_path) -> None:
        users.add_user(
            make_user(username=None, timezone=None), db=db_path
        )
        assert users.get_users_ids(db=db_path) == [42]
        assert users.get_user_profile(42, db=db_path)[0] == ""

    def test_unknown_user_has_empty_profile(self, db_path) -> None:
        assert users.get_user_profile(99, db=db_path) == ("", None, None)


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
