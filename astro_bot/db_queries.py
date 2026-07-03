create_users_table = """CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    user_name TEXT NOT NULL,
    name TEXT,
    timezone TEXT
    )"""

create_events_table = """CREATE TABLE IF NOT EXISTS events (
    uid TEXT PRIMARY KEY,
    dt_utc TEXT NOT NULL,
    summary TEXT NOT NULL,
    description TEXT,
    url TEXT
    )"""

create_user_ins = """INSERT INTO
    users (telegram_id, user_name, name, timezone)
    VALUES (?, ?, ?, ?)"""

upsert_event = """INSERT INTO
    events (uid, dt_utc, summary, description, url)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(uid) DO UPDATE SET
        dt_utc=excluded.dt_utc,
        summary=excluded.summary,
        description=excluded.description,
        url=excluded.url"""

select_users_id = "SELECT telegram_id FROM users"

select_events_on_day = """SELECT dt_utc, summary, description, url
    FROM events WHERE date(dt_utc) = ? ORDER BY dt_utc"""

select_events_between = """SELECT dt_utc, summary, description, url
    FROM events WHERE date(dt_utc) BETWEEN ? AND ? ORDER BY dt_utc"""

select_events_columns = "PRAGMA table_info(events)"

drop_events_table = "DROP TABLE events"
