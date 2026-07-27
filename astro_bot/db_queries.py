create_users_table = """CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    user_name TEXT NOT NULL,
    name TEXT,
    timezone TEXT,
    lat REAL,
    lon REAL
    )"""

upsert_user = """INSERT INTO
    users (telegram_id, user_name, name, timezone, lat, lon)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(telegram_id) DO UPDATE SET
        user_name=excluded.user_name,
        name=excluded.name,
        timezone=excluded.timezone,
        lat=excluded.lat,
        lon=excluded.lon"""

select_users_id = "SELECT telegram_id FROM users"

select_user_profile = """SELECT timezone, lat, lon
    FROM users WHERE telegram_id = ?"""

select_users_columns = "PRAGMA table_info(users)"

select_journal_mode_wal = "PRAGMA journal_mode=WAL"

select_journal_mode = "PRAGMA journal_mode"

# One-time cleanup for databases written by the versions that kept their
# own copy of the events; the bot reads them from the skyevents service
# now and stores nothing.
drop_events_table = "DROP TABLE IF EXISTS events"

add_users_lat_column = "ALTER TABLE users ADD COLUMN lat REAL"

add_users_lon_column = "ALTER TABLE users ADD COLUMN lon REAL"
