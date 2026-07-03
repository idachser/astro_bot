import asyncio
import logging
from datetime import date, timedelta

from aiogram import Bot

from astro_bot.config import SATURDAY, SECONDS_PER_DAY
from astro_bot.keyboards.inline_keyboard import get_inline_week_keyboard
from astro_bot.services.events import get_events_between, sync_events
from astro_bot.services.users import get_users_ids
from astro_bot.templates import WEEK_DIGEST_MESSAGE


async def send_weekly_digest(bot: Bot) -> None:
    sync_events()

    today = date.today()
    events = get_events_between(today, today + timedelta(days=6))
    if not events:
        logging.warning("No events for the weekly digest, nothing sent")
        return

    digest = WEEK_DIGEST_MESSAGE(events)
    for user_id in get_users_ids():
        try:
            await bot.send_message(
                user_id,
                digest,
                reply_markup=get_inline_week_keyboard(today),
                disable_web_page_preview=True,
            )
        except Exception as err:
            logging.error(f"Digest was not sent to {user_id}: {err}")


async def scheduler(bot: Bot) -> None:
    """Scheduler for syncing events and sending digest every saturday"""

    while True:
        if date.today().weekday() == SATURDAY:
            await send_weekly_digest(bot)

        await asyncio.sleep(SECONDS_PER_DAY)
