from datetime import date, datetime, timezone

from astro_bot.config import DB
from astro_bot.db import read_from_db, write_into_db
from astro_bot.db_queries import (
    select_user_profile,
    select_users_id,
    upsert_user,
)
from astro_bot.timezones import resolve_timezone


def add_user(user: dict, db: str = DB) -> None:
    data = (
        user["id"],
        user["username"] or "",
        user["name"],
        user["timezone"] or "",
        user.get("lat"),
        user.get("lon"),
    )
    write_into_db(db, upsert_user, data)


def get_users_ids(db: str = DB) -> list:
    return [row[0] for row in read_from_db(db, select_users_id)]


def get_user_profile(telegram_id: int, db: str = DB) -> tuple:
    """(timezone, lat, lon) of the user; ("", None, None) if unknown
    or the user chose "Default time" (no location shared)"""

    rows = read_from_db(db, select_user_profile, (telegram_id,))
    return rows[0] if rows else ("", None, None)


def get_user_today(telegram_id: int, db: str = DB) -> date:
    """Current date in the user's timezone (UTC for unknown users):
    "today" must be the user's local day, not the server's"""

    tz, _, _ = get_user_profile(telegram_id, db=db)
    now = datetime.now(timezone.utc)
    return now.astimezone(resolve_timezone(tz)).date()
