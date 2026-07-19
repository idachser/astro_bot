from datetime import date, datetime, time, timedelta, timezone

from astro_bot.config import DB
from astro_bot.timezones import resolve_timezone
from astro_bot.db import (
    db_init,
    read_from_db,
    write_into_db,
    write_many_into_db,
)
from astro_bot.db_queries import (
    add_users_lat_column,
    add_users_lon_column,
    create_events_table,
    create_users_table,
    drop_events_table,
    select_events_between,
    select_events_columns,
    select_events_in_window,
    select_users_columns,
    upsert_event,
)
from astro_bot.services.ics_feed import get_feed_events


def init_storage(db: str = DB) -> None:
    """Create tables and migrate old schemas: drop the legacy events
    table (string dates), add user location columns"""

    columns = [col[1] for col in read_from_db(db, select_events_columns)]
    if columns and "uid" not in columns:
        write_into_db(db, drop_events_table)
    db_init(db, create_events_table)
    db_init(db, create_users_table)

    user_columns = [
        col[1] for col in read_from_db(db, select_users_columns)
    ]
    if "lat" not in user_columns:
        write_into_db(db, add_users_lat_column)
        write_into_db(db, add_users_lon_column)


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


def get_events_on_day(day: date, tz: str = "", db: str = DB) -> list:
    """Events of the day in the given timezone (UTC by default)
    as (dt_utc, summary, description, url) tuples"""

    start = datetime.combine(day, time.min, resolve_timezone(tz))
    end = start + timedelta(days=1)
    return read_from_db(
        db,
        select_events_in_window,
        (
            start.astimezone(timezone.utc).isoformat(),
            end.astimezone(timezone.utc).isoformat(),
        ),
    )


def get_events_between(start: date, end: date, db: str = DB) -> list:
    """Events for a date range (inclusive), ordered by time"""

    return read_from_db(
        db, select_events_between, (start.isoformat(), end.isoformat())
    )
