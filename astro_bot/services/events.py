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
    delete_legacy_feed_events,
    drop_events_table,
    select_events_between,
    select_events_columns,
    select_events_in_window,
    select_users_columns,
    upsert_event,
)
from astro_bot.services.skyevents import fetch_year, sync_years


def init_storage(db: str = DB) -> None:
    """Create tables and migrate old schemas: drop the legacy events
    table (string dates), add user location columns"""

    columns = [col[1] for col in read_from_db(db, select_events_columns)]
    if columns and "uid" not in columns:
        write_into_db(db, drop_events_table)
    db_init(db, create_events_table)
    write_into_db(db, delete_legacy_feed_events)
    db_init(db, create_users_table)

    user_columns = [
        col[1] for col in read_from_db(db, select_users_columns)
    ]
    if "lat" not in user_columns:
        write_into_db(db, add_users_lat_column)
        write_into_db(db, add_users_lon_column)


def _prune_future_events(
    db: str, year: int, keep_uids: set[str], now_iso: str
) -> None:
    """Delete future events in `year` the service no longer returns.

    Scoped two ways so a normal sync can only ever remove genuine
    phantoms: to `dt_utc >= now` (past events are history and are never
    touched), and to this year's window (other years -- e.g. next year's,
    synced in an earlier December run -- are out of scope). A phantom
    arises because uids are date-based: when a regenerated cache shifts an
    event's date its uid changes, and the old row would otherwise linger.

    An empty `keep_uids` (a covered year that returned nothing -- not a
    real case for a full year) skips pruning rather than risk wiping the
    window, and also sidesteps an empty `NOT IN ()`.
    """

    if not keep_uids:
        return

    lower = max(now_iso, f"{year}-01-01")
    upper = f"{year + 1}-01-01"
    placeholders = ",".join("?" for _ in keep_uids)
    sql = (
        "DELETE FROM events WHERE dt_utc >= ? AND dt_utc < ? "
        f"AND uid NOT IN ({placeholders})"
    )
    write_into_db(db, sql, (lower, upper, *keep_uids))


def sync_events(db: str = DB) -> None:
    """Fetch events from the skyevents service, upsert them, and prune
    future phantoms per successfully-synced year"""

    now_iso = datetime.now(timezone.utc).isoformat()
    for year in sync_years():
        events = fetch_year(year)
        if events is None:
            continue

        rows = [
            (
                event["uid"],
                event["dt_utc"].isoformat(),
                event["summary"],
                event["description"],
                event["url"],
            )
            for event in events
        ]
        if rows:
            write_many_into_db(db, upsert_event, rows)

        _prune_future_events(
            db, year, {event["uid"] for event in events}, now_iso
        )


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
