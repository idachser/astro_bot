# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Telegram bot (aiogram 2.x, long polling) that collects upcoming celestial events and sends them to users on demand and as a weekly Saturday broadcast. Storage is SQLite. **PLAN.md describes an in-progress migration** of the data source from scraping astronomy.com HTML to the in-the-sky.org iCal feed — read it before touching `services/` or the DB schema.

## Commands

```bash
poetry install                        # deps (Python >=3.10)
poetry run python -m astro_bot        # run the bot
poetry run pytest astro_bot/tests.py  # tests
poetry run flake8 astro_bot           # lint
```

Requires a `.env` in the repo root: `TELEGRAM_BOT_TOKEN`, `DB` (SQLite filename), `NASA_IMAGE_OF_THE_DAY_TOKEN` (reserved, unused). Logs go to `astrobot.log` (overwritten each start).

Caveats: `astro_bot/tests.py` still uses pre-rename flat imports (`import config`) and hits the live website, so the suite is currently broken; scraper needs `user_agents.txt` (gitignored, one User-Agent per line); `handlers/start.py` imports `timezonefinder`, which is missing from `pyproject.toml`.

## Architecture

Three layers, one direction of imports: `handlers/` → `services/` → `db.py`.

- **`__main__.py`** builds Bot/Dispatcher, calls each handler module's `register_handler_*(dp)`, and starts `autosend_events.scheduler(bot)` as a background task before polling.
- **Handlers match button text, not slash commands.** The reply keyboard in `keyboards/reply_keyboard.py` shows buttons ("Week", "Today", …) and each handler filters on `Text(equals=...)`. The only real slash command is `/start`. `specific_date.py` registers a catch-all message handler, so it must be registered last. All user-facing strings live in `templates.py` (HTML parse mode).
- **Data pipeline (current, being replaced):** `services/scrap_data.py` (requests+bs4, random User-Agent) → `parse_data.py` (regex split by date headings) → `extractor.py` → `events.py` writes to SQLite.
- **Dates are display strings.** Events are keyed by strings like `"Friday, July 3"` — no year, no leading zeros. Handlers reproduce this format via `DATE_FORMAT` + `re.sub` zero-stripping to look events up. The events table has `UNIQUE` on date, so re-scraping dedupes by failing inserts (error is logged and swallowed). The PLAN.md migration replaces this with ISO dates.
- **`db.py`** opens a new connection per operation and swallows exceptions into the log; `db_queries.py` holds raw SQL (some via f-strings — replace with parameterized queries when touching them).
- **Week pagination state** (`handlers/week.py`) is an in-memory per-user dict of day counters driven by `week_next`/`week_previous` callbacks — lost on restart.

## Known bugs (fix as part of PLAN.md, don't replicate)

- `services/users.py::get_users_ids` returns only the first row, so the Saturday broadcast reaches one user.
- The week paginator counter can go negative ("next" past day 0).
- README/help advertise "New" and "Image of the day" commands that have no handlers.
