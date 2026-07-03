import pytest

from astro_bot import db
from astro_bot import db_queries as q
from astro_bot.services import users


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
    }
    user.update(overrides)
    return user


class TestUsers:
    def test_add_and_get_ids(self, db_path) -> None:
        users.add_user(make_user(id=1), db=db_path)
        users.add_user(make_user(id=2), db=db_path)
        assert users.get_users_ids(db=db_path) == [1, 2]

    def test_restart_updates_timezone(self, db_path) -> None:
        users.add_user(make_user(), db=db_path)
        users.add_user(make_user(timezone="Asia/Tokyo"), db=db_path)

        assert users.get_users_ids(db=db_path) == [42]
        assert users.get_user_timezone(42, db=db_path) == "Asia/Tokyo"

    def test_none_fields_are_stored_empty(self, db_path) -> None:
        users.add_user(make_user(username=None, timezone=None), db=db_path)
        assert users.get_users_ids(db=db_path) == [42]
        assert users.get_user_timezone(42, db=db_path) == ""

    def test_unknown_user_has_no_timezone(self, db_path) -> None:
        assert users.get_user_timezone(99, db=db_path) == ""
