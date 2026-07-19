import logging
import time
from datetime import date, datetime, timedelta, timezone

import requests

from astro_bot.config import WEATHER_URL
from astro_bot.timezones import resolve_timezone

REQUEST_TIMEOUT = 10
CACHE_TTL_SECONDS = 3600
FORECAST_HORIZON_DAYS = 7
COORD_PRECISION = 2  # ~1 km, plenty for a weather forecast

_cache: dict = {}


def _fetch_day_forecast(
    lat: float, lon: float, day: date, tz: str
) -> dict | None:
    """Local "YYYY-MM-DDTHH:00" -> (cloud cover %, visibility m)
    for one day from Open-Meteo"""

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "cloud_cover,visibility",
        "timezone": tz or "UTC",
        "start_date": day.isoformat(),
        "end_date": day.isoformat(),
    }
    try:
        response = requests.get(
            WEATHER_URL, params=params, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        hourly = response.json()["hourly"]
        return dict(
            zip(
                hourly["time"],
                zip(hourly["cloud_cover"], hourly["visibility"]),
            )
        )
    except (requests.RequestException, ValueError, KeyError) as err:
        logging.exception(f"Weather request failed: {err}")


def get_day_forecast(
    lat: float, lon: float, day: date, tz: str = ""
) -> dict | None:
    """Cached for an hour so week browsing doesn't hit the API
    on every click; failures are not cached"""

    key = (
        round(lat, COORD_PRECISION),
        round(lon, COORD_PRECISION),
        day,
        tz,
    )
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    forecast = _fetch_day_forecast(lat, lon, day, tz)
    if forecast is not None:
        _cache[key] = (time.monotonic(), forecast)
    return forecast


def get_events_weather(
    events: list,
    lat: float | None,
    lon: float | None,
    tz: str = "",
    now: datetime | None = None,
) -> list:
    """(local HH:MM, cloud cover %, visibility km) for each upcoming
    timed event within the forecast horizon; empty when the user has
    no location or the forecast is unavailable"""

    if lat is None or lon is None:
        return []

    zone = resolve_timezone(tz)
    now = now or datetime.now(timezone.utc)
    horizon = now.astimezone(zone).date() + timedelta(
        days=FORECAST_HORIZON_DAYS
    )

    rows = []
    for event in events:
        dt = datetime.fromisoformat(event[0])
        if (dt.hour, dt.minute) == (0, 0):  # date-only event
            continue
        local = dt.astimezone(zone)
        if dt < now or local.date() > horizon:
            continue
        forecast = get_day_forecast(lat, lon, local.date(), tz)
        if not forecast:
            continue
        hour = forecast.get(local.strftime("%Y-%m-%dT%H:00"))
        if hour is None:
            continue
        cloud, visibility_m = hour
        rows.append(
            (f"{local:%H:%M}", round(cloud), round(visibility_m / 1000))
        )
    return rows
