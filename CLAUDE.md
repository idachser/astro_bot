# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Telegram bot (aiogram 2.x, long polling) that serves upcoming celestial events from the In-The-Sky.org iCal feed, on demand and as a weekly Saturday broadcast. Storage is SQLite. PLAN.md documents the completed migration off HTML scraping; its stage 7 plans the switch to `skyevents` — a standalone celestial-events HTTP API (separate repository, deployed on its own) the bot will reach via `EVENTS_API_URL` only.

## Commands

```bash
uv sync                            # deps (creates .venv)
uv run python -m astro_bot         # run the bot
uv run pytest                      # tests (offline, use fixtures)
uv run flake8 astro_bot tests      # lint
docker compose up -d --build       # deploy (db and log persist in ./data/)
```

CI/CD: `.github/workflows/ci-cd.yml` runs flake8 + pytest on every push/PR; pushes to `main` then deploy to the server over SSH (git pull + compose rebuild), gated on green tests.

Python is pinned to 3.11 (`.python-version`): aiogram 2.x requires aiohttp <3.9, which does not build on 3.12+. Upgrading to aiogram 3 would lift this.

Requires a `.env` in the repo root: `TELEGRAM_BOT_TOKEN`, `DB` (SQLite filename), `NASA_IMAGE_OF_THE_DAY_TOKEN` (for "Image of the day"; NASA's `DEMO_KEY` works for light use). Logs go to `astrobot.log` (overwritten each start).

## Architecture

Three layers, one direction of imports: `handlers/` → `services/` → `db.py`.

- **`__main__.py`** builds Bot/Dispatcher, runs `init_storage()` + `sync_events()`, calls each handler module's `register_handler_*(dp)`, and starts `autosend_events.scheduler(bot)` as a background task before polling.
- **Handlers match button text, not slash commands.** The reply keyboard in `keyboards/reply_keyboard.py` shows buttons ("Week", "Today", …) and each handler filters on `Text(equals=...)`. The only real slash command is `/start`. `specific_date.py` registers a catch-all message handler (free-text "July 15" lookups), so it must be registered last.
- **Data flow:** `services/ics_feed.py` downloads the In-The-Sky.org yearly iCal feed (plus next year's in December) and normalizes VEVENTs; `services/events.py` upserts them into the `events` table keyed by feed `uid`, with times as ISO-8601 UTC strings (`dt_utc`). Sync happens at startup and every Saturday. `init_storage()` drops a legacy events table (pre-migration string-date schema) if it finds one.
- **Timezones and location:** `/start` stores the user's IANA timezone plus lat/lon (from a shared location via timezonefinder; empty/NULL for "Default time"). Day handlers anchor "today" with `get_user_today(user_id)` (the user's local date, not the server's) and call `get_message_for_day(day, user_id)`, which resolves the profile so a "day" is the user's local day (computed as a UTC window in SQL) and event times are labeled with the local zone; `timezones.py::resolve_timezone` falls back to UTC on empty/unknown names, and `timezones.py::is_date_only` is the single home of the "midnight UTC = date-only event" feed convention.
- **Weather footers:** `services/weather.py` asks Open-Meteo (no API key) for hourly cloud cover and visibility at the user's stored coordinates; day messages get an "Observing conditions" footer for upcoming timed events within 7 days. Forecasts are cached in memory for ~1h (expired entries pruned on access); API failures and null hourly values just drop the footer, never the message. Day handlers run `get_message_for_day` via `asyncio.to_thread` — the weather HTTP call must never block the event loop, keep it that way. The "Weather data by Open-Meteo.com" line is a CC-BY license requirement — keep it.
- **Week pagination is stateless:** the `<`/`>` inline buttons carry the target day as `week_YYYY-MM-DD` in callback_data, wrapping Mon↔Sun within the shown day's week.
- **All user-facing text lives in `templates.py`** (HTML parse mode; escape feed text with `quote_html`). The In-The-Sky.org attribution in the greeting and digest footer is a license requirement (data is © Dominic Ford, non-commercial use with attribution) — keep it when editing texts.
- **The Saturday broadcast** (`handlers/autosend_events.py`) wraps each send in try/except so users who blocked the bot don't kill the scheduler loop.
- Tests in `tests/` run offline: the ICS parser is tested against `tests/fixtures/newscal_2026.ics`, DB code against temp files (service functions accept a `db=` path override).
