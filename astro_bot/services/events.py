from datetime import date

from astro_bot.config import DB
from astro_bot.db import (
    db_init,
    read_from_db,
    write_into_db,
    write_many_into_db,
)
from astro_bot.db_queries import (
    create_events_table,
    create_users_table,
    drop_events_table,
    select_events_between,
    select_events_columns,
    select_events_on_day,
    upsert_event,
)
from astro_bot.services.ics_feed import get_feed_events


def init_storage(db: str = DB) -> None:
    """Create tables, dropping the legacy events table (string dates)"""

    columns = [col[1] for col in read_from_db(db, select_events_columns)]
    if columns and "uid" not in columns:
        write_into_db(db, drop_events_table)
    db_init(db, create_events_table)
    db_init(db, create_users_table)


def sync_events(db: str = DB) -> None:
    """Fetch the ICS feed and upsert its events into the database"""

    rows = [
        (
            event["uid"],
            event["dt_utc"].isoformat(),
            event["summary"],
            event["description"],
            event["url"],
        )
        for event in get_feed_events()
    ]
    if rows:
        write_many_into_db(db, upsert_event, rows)


def get_events_on_day(day: date, db: str = DB) -> list:
    """Events for one day as (dt_utc, summary, description, url) tuples"""

    return read_from_db(db, select_events_on_day, (day.isoformat(),))


def get_events_between(start: date, end: date, db: str = DB) -> list:
    """Events for a date range (inclusive), ordered by time"""

    return read_from_db(
        db, select_events_between, (start.isoformat(), end.isoformat())
    )


# Temporary shims until handlers are migrated to the new API (stage 3)
def write_events() -> None:
    sync_events()


def get_events(date=None, count=None) -> list:
    return []
