from astro_bot.config import DB
from astro_bot.db import read_from_db, write_into_db
from astro_bot.db_queries import (
    select_user_timezone,
    select_users_id,
    upsert_user,
)


def add_user(user: dict, db: str = DB) -> None:
    data = (
        user["id"],
        user["username"] or "",
        user["name"],
        user["timezone"] or "",
    )
    write_into_db(db, upsert_user, data)


def get_users_ids(db: str = DB) -> list:
    return [row[0] for row in read_from_db(db, select_users_id)]


def get_user_timezone(telegram_id: int, db: str = DB) -> str:
    rows = read_from_db(db, select_user_timezone, (telegram_id,))
    return rows[0][0] if rows else ""
