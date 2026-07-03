# [Astrobot](https://t.me/astroadventurebot)

<img src="astro_bot_logo.jpg" width="200" height="200" >

### Telegram-bot for recieving masseges about upcoming celestial events.
***Astrobot takes data about celestial and astronomical events from
the In-The-Sky.org iCal feed and pushes a weekly digest to users
every Saturday.***

## Bot commands:
- `Help` - get message with commands list;
- `Week` - browse events of the week day by day;
- `Today` - get events for today;
- `Yesterday` - get events for yesterday;
- `Tomorrow` - get events for tomorrow;
- `Image of the day` - get astronomy picture of the day from NASA;
- send a date like `July 15` - get events for a specific date.

Share your location on `/start` and event times will be shown
in your local timezone (UTC otherwise).

## Development
```bash
uv sync                       # install dependencies
uv run python -m astro_bot    # run the bot
uv run pytest                 # run tests
```

## Deployment
Put a `.env` file next to `docker-compose.yml`:
```
TELEGRAM_BOT_TOKEN=<your bot token>
NASA_IMAGE_OF_THE_DAY_TOKEN=<api.nasa.gov key or DEMO_KEY>
```
and run:
```bash
docker compose up -d --build
```
The SQLite database and log persist in `./data/` on the host.

Pushes to `main` are deployed automatically by GitHub Actions
(lint + tests, then `git pull` and `docker compose up -d --build`
on the server over SSH). Required repository secrets:
`DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_PATH`.

Using: Aiogram, icalendar and SQLite.

Event data courtesy of [In-The-Sky.org](https://in-the-sky.org/),
© Dominic Ford.
