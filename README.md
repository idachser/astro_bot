# [Astrobot](https://t.me/astroadventurebot)

<img src="astro_bot_logo.jpg" width="200" height="200" >

### Telegram-bot for recieving masseges about upcoming celestial events.
***Astrobot takes celestial and astronomical events from the
[skyevents](../skyevents) service (computed with Skyfield and JPL DE440s
ephemerides) and pushes a weekly digest to users every Saturday.***

## Bot commands:
- `Help` - get message with commands list;
- `Week` - browse events of the week day by day;
- `Today` - get events for today;
- `Yesterday` - get events for yesterday;
- `Tomorrow` - get events for tomorrow;
- `Image of the day` - get astronomy picture of the day from NASA;
- send a date like `July 15` - get events for a specific date.

Share your location on `/start` and event times will be shown
in your local timezone (UTC otherwise), with observing conditions
— cloud cover and visibility at the event's hour — under the
day's upcoming events.

## Development
```bash
uv sync                       # install dependencies
uv run python -m astro_bot    # run the bot
uv run pytest                 # run tests
```

## Deployment
The bot reaches the [skyevents](../skyevents) service over a shared
external Docker network, so create it once on the host before the first
deploy (skyevents' own compose joins the same network):
```bash
docker network create astronet
```
Put a `.env` file next to `docker-compose.yml`:
```
TELEGRAM_BOT_TOKEN=<your bot token>
NASA_IMAGE_OF_THE_DAY_TOKEN=<api.nasa.gov key or DEMO_KEY>
```
and run:
```bash
docker compose up -d --build
```
The SQLite database, the log and a one-line `last_digest` marker (which
Saturday broadcast already went out, so a redeploy right after one does
not repeat it) persist in `./data/` on the host. The bot
talks to skyevents at `http://skyevents:8000` (`SKYEVENTS_URL`); that
container is deployed separately from the skyevents repo.

Pushes to `main` are deployed automatically by GitHub Actions
(lint + tests, then `git pull` and `docker compose up -d --build`
on the server over SSH). Required repository secrets:
`DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_PATH`.

Using: Aiogram and SQLite.

Event data computed by the [skyevents](../skyevents) service with
[Skyfield](https://rhodesmill.org/skyfield/) and JPL DE440s ephemerides.

Weather data by [Open-Meteo.com](https://open-meteo.com/).
