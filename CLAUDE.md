# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Telegram bot (aiogram 2.x, long polling) that serves upcoming celestial events from the In-The-Sky.org iCal feed, on demand and as a weekly Saturday broadcast. Storage is SQLite. PLAN.md documents the completed migration off HTML scraping; the only deferred item is location-based event visibility filtering.

## Commands

```bash
uv sync                            # deps (creates .venv)
uv run python -m astro_bot         # run the bot
uv run pytest                      # tests (offline, use fixtures)
uv run flake8 astro_bot tests      # lint
```

Python is pinned to 3.11 (`.python-version`): aiogram 2.x requires aiohttp <3.9, which does not build on 3.12+. Upgrading to aiogram 3 would lift this.

Requires a `.env` in the repo root: `TELEGRAM_BOT_TOKEN`, `DB` (SQLite filename), `NASA_IMAGE_OF_THE_DAY_TOKEN` (for "Image of the day"; NASA's `DEMO_KEY` works for light use). Logs go to `astrobot.log` (overwritten each start).

## Architecture

Three layers, one direction of imports: `handlers/` → `services/` → `db.py`.

- **`__main__.py`** builds Bot/Dispatcher, runs `init_storage()` + `sync_events()`, calls each handler module's `register_handler_*(dp)`, and starts `autosend_events.scheduler(bot)` as a background task before polling.
- **Handlers match button text, not slash commands.** The reply keyboard in `keyboards/reply_keyboard.py` shows buttons ("Week", "Today", …) and each handler filters on `Text(equals=...)`. The only real slash command is `/start`. `specific_date.py` registers a catch-all message handler (free-text "July 15" lookups), so it must be registered last.
- **Data flow:** `services/ics_feed.py` downloads the In-The-Sky.org yearly iCal feed (plus next year's in December) and normalizes VEVENTs; `services/events.py` upserts them into the `events` table keyed by feed `uid`, with times as ISO-8601 UTC strings (`dt_utc`). Sync happens at startup and every Saturday. `init_storage()` drops a legacy events table (pre-migration string-date schema) if it finds one.
- **Timezones:** `/start` stores the user's IANA timezone (from a shared location via timezonefinder, empty for "Default time"). Handlers pass it down so a "day" is the user's local day (computed as a UTC window in SQL) and event times are labeled with the local zone; `timezones.py::resolve_timezone` falls back to UTC on empty/unknown names.
- **Week pagination is stateless:** the `<`/`>` inline buttons carry the target day as `week_YYYY-MM-DD` in callback_data, wrapping Mon↔Sun within the shown day's week.
- **All user-facing text lives in `templates.py`** (HTML parse mode; escape feed text with `quote_html`). The In-The-Sky.org attribution in the greeting and digest footer is a license requirement (data is © Dominic Ford, non-commercial use with attribution) — keep it when editing texts.
- **The Saturday broadcast** (`handlers/autosend_events.py`) wraps each send in try/except so users who blocked the bot don't kill the scheduler loop.
- Tests in `tests/` run offline: the ICS parser is tested against `tests/fixtures/newscal_2026.ics`, DB code against temp files (service functions accept a `db=` path override).
