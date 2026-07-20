import logging
import threading
import time
from datetime import date, datetime, timedelta, timezone

import requests

from astro_bot.config import WEATHER_URL
from astro_bot.timezones import is_date_only, resolve_timezone

REQUEST_TIMEOUT = 10
CACHE_TTL_SECONDS = 3600
FORECAST_HORIZON_DAYS = 7
COORD_PRECISION = 2  # ~1 km, plenty for a weather forecast

# Day handlers call into here from asyncio.to_thread, so the cache is
# shared by worker threads: every read, prune and write goes through
# the lock or a concurrent insert breaks the prune mid-iteration
_cache: dict = {}
_cache_lock = threading.Lock()


def _fetch_day_forecast(
    lat: float, lon: float, day: date, tz: str
) -> dict | None:
    """Local "YYYY-MM-DDTHH:00" -> (cloud cover %, visibility m)
    for one day from Open-Meteo; hours with incomplete data (the API
    returns nulls when a model lacks a value) are dropped"""

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "cloud_cover,visibility",
        "timezone": tz,
        "start_date": day.isoformat(),
        "end_date": day.isoformat(),
    }
    try:
        response = requests.get(
            WEATHER_URL, params=params, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        hourly = response.json()["hourly"]
        return {
            hour: (cloud, visibility)
            for hour, cloud, visibility in zip(
                hourly["time"],
                hourly["cloud_cover"],
                hourly["visibility"],
            )
            if cloud is not None and visibility is not None
        }
    except (
        requests.RequestException,
        ValueError,
        KeyError,
        TypeError,
    ) as err:
        logging.exception(f"Weather request failed: {err}")


def _prune_expired(now: float) -> None:
    """Caller must hold _cache_lock"""

    expired = [
        key
        for key, (stored_at, _) in _cache.items()
        if now - stored_at >= CACHE_TTL_SECONDS
    ]
    for key in expired:
        del _cache[key]


def get_day_forecast(
    lat: float, lon: float, day: date, tz: str = "UTC"
) -> dict | None:
    """Cached for an hour so week browsing doesn't hit the API on
    every click; failures are not cached. Expired entries are pruned
    on every call to keep the cache bounded. The request itself runs
    outside the lock: two threads may fetch the same day at once, but
    holding it across a 10s HTTP call would stall every other user."""

    key = (
        round(lat, COORD_PRECISION),
        round(lon, COORD_PRECISION),
        day,
        tz,
    )
    now = time.monotonic()
    with _cache_lock:
        _prune_expired(now)
        cached = _cache.get(key)
    if cached:
        return cached[1]

    forecast = _fetch_day_forecast(lat, lon, day, tz)
    if forecast is not None:
        with _cache_lock:
            _cache[key] = (now, forecast)
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
    # Ask Open-Meteo for the zone we actually resolved to, not the
    # stored name: on an unknown name resolve_timezone falls back to
    # UTC, and the forecast keys must be in the same zone as ours
    zone_name = str(zone)
    now = now or datetime.now(timezone.utc)
    horizon = now.astimezone(zone).date() + timedelta(
        days=FORECAST_HORIZON_DAYS
    )

    rows = []
    for event in events:
        dt = datetime.fromisoformat(event[0])
        if is_date_only(dt):
            continue
        local = dt.astimezone(zone)
        if dt < now or local.date() > horizon:
            continue
        forecast = get_day_forecast(lat, lon, local.date(), zone_name)
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
