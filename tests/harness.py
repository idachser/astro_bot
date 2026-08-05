"""Stand-ins for the five things a test or a probe has to fake: the
clock, the events, the profile, the bot and the database.

Every module in this project imports its collaborators by name
(`from astro_bot.services.events import get_events_on_day`), so a stub
has to replace the attribute **on the module under test**, not on the
module that defines it — patching `services.events.fetch_range` does
nothing for a handler that already bound the name. That is why each
helper here takes the module to patch as its first argument.

These are deliberately thin: they substitute a value and restore it,
and hold no logic of their own. A harness with opinions is a harness
that can lie about the code under it.
"""

from contextlib import contextmanager
from datetime import datetime, timezone

from astro_bot import db
from astro_bot import db_queries as q


def utc(year, month, day, hour=0, minute=0) -> datetime:
    """An aware UTC instant. Naive datetimes are rejected downstream,
    so probes must not hand-roll `datetime(...)` without a tzinfo."""

    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def event_row(
    dt_utc: str,
    summary: str = "Full Moon",
    description: str = "The Moon reaches full phase.",
    url: str = "",
) -> tuple:
    """One row in the shape `fetch_range` returns and the templates
    render. `url` is empty for anything skyevents serves — it emits no
    links, and the day view renders the summary bold instead."""

    return (dt_utc, summary, description, url)


class FakeBot:
    """Telegram without Telegram. `refuse=True` is the bot every user
    has blocked: each send raises, so nothing is delivered."""

    def __init__(self, refuse: bool = False) -> None:
        self.sent = []
        self.refuse = refuse

    async def send_message(self, user_id, text, **kwargs) -> None:
        if self.refuse:
            raise RuntimeError("Telegram unreachable")
        self.sent.append((user_id, text))


@contextmanager
def frozen_now(module, moment: datetime):
    """Freeze `datetime.now()` inside `module` at `moment`.

    Subclassing datetime and rebinding the module's name is the only
    form that leaves `datetime.now(tz)`, arithmetic and comparisons
    intact. Assigning a lambda to `datetime.now` fails outright (the
    type is immutable), and a plain object with a `now` breaks every
    other use of the name in the module.
    """

    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None) -> datetime:
            return moment

    original = module.datetime
    module.datetime = Frozen
    try:
        yield moment
    finally:
        module.datetime = original


@contextmanager
def serving_events(module, result, attr: str = "fetch_range"):
    """Serve `result` for any range `module` asks for, yielding the
    list of positional arguments it asked with — (start, end) for
    `fetch_range` and `get_events_between`, (day,) for
    `get_events_on_day`. Keyword arguments (`tz=`) are not recorded;
    assert on the events that come back instead.

    `result=None` is the outage — the one value that must never reach
    the user as a quiet sky. `[]` is a genuinely empty window.
    """

    asked = []

    def fake(*args, **kwargs):
        asked.append(args)
        return result

    original = getattr(module, attr)
    setattr(module, attr, fake)
    try:
        yield asked
    finally:
        setattr(module, attr, original)


@contextmanager
def serving_profile(module, tz: str = "", lat=None, lon=None):
    """Give `module` a user profile without a database, yielding the
    list of user ids it was read for.

    An empty `tz` with no coordinates is the "Default time" user: UTC
    days and no weather footer.
    """

    reads = []

    def fake(user_id, db=None):
        reads.append(user_id)
        return (tz, lat, lon)

    original = module.get_user_profile
    module.get_user_profile = fake
    try:
        yield reads
    finally:
        module.get_user_profile = original


def make_user(**overrides) -> dict:
    """The dict `/start` hands to `add_user`."""

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


def users_db(path: str) -> str:
    """A fresh users table at `path`, returned for the `db=` override
    every service function takes. Point probes at a temp file: the real
    database is the one the running bot is holding open."""

    db.db_init(path, q.create_users_table)
    return path
