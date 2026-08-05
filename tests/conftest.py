"""Fixtures over `tests.harness`, so tests get the same stand-ins a
probe builds by hand."""

import pytest

from tests.harness import FakeBot, users_db


@pytest.fixture()
def user_db(tmp_path) -> str:
    """A users database of its own per test, under pytest's tmp_path."""

    return users_db(str(tmp_path / "test.db"))


@pytest.fixture()
def bot() -> FakeBot:
    return FakeBot()
