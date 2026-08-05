import logging

from astro_bot.config import DB
from astro_bot.db import db_init, read_from_db, write_into_db
from astro_bot.db_queries import (
    add_users_lat_column,
    add_users_lon_column,
    create_users_table,
    drop_events_table,
    select_journal_mode_wal,
    select_user_profile,
    select_users_columns,
    select_users_id,
    upsert_user,
)

logger = logging.getLogger(__name__)


def _enable_wal(db: str) -> None:
    """Switch the file to write-ahead logging, where a reader and a
    writer no longer block each other: profiles are read from worker
    threads (day handlers run through asyncio.to_thread) while /start
    writes one from the event loop.

    Run as a read because the pragma answers with the mode it actually
    ended up in -- it silently stays a rollback journal on filesystems
    without shared memory (some network mounts), which is worth a log
    line. The setting lives in the file, so this is a one-time migration.
    """

    mode = read_from_db(db, select_journal_mode_wal)
    if not mode or mode[0][0].lower() != "wal":
        logger.warning(f"Could not switch DB to WAL, journal mode: {mode}")


def init_storage(db: str = DB) -> None:
    """Create the users table and migrate old schemas: switch to WAL,
    add the location columns, and drop the events table left by the
    versions that kept their own copy of the events (they are read from
    the skyevents service now, nothing stores them)"""

    _enable_wal(db)
    write_into_db(db, drop_events_table)
    db_init(db, create_users_table)

    columns = [col[1] for col in read_from_db(db, select_users_columns)]
    if "lat" not in columns:
        write_into_db(db, add_users_lat_column)
        write_into_db(db, add_users_lon_column)


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
