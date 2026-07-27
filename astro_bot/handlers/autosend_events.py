import asyncio
import logging
from datetime import date, timedelta

from aiogram import Bot

from astro_bot.config import DIGEST_RETRY_DELAYS, SATURDAY, SECONDS_PER_DAY
from astro_bot.keyboards.inline_keyboard import get_inline_week_keyboard
from astro_bot.services.events import get_events_between
from astro_bot.services.users import get_users_ids
from astro_bot.templates import WEEK_DIGEST_MESSAGE


async def _fetch_week(today: date) -> list | None:
    """The week's events, retrying while skyevents cannot answer.

    Worth retrying only here: a user who gets "try later" presses the
    button again, but a missed broadcast is missed for a week. Runs in a
    worker thread (the request is blocking), and a raise counts as a
    failed attempt -- letting it escape would take the scheduler task
    down with it.
    """

    for delay in (*DIGEST_RETRY_DELAYS, None):
        try:
            events = await asyncio.to_thread(
                get_events_between, today, today + timedelta(days=6)
            )
        except Exception as err:
            logging.exception(f"Weekly events request raised: {err}")
            events = None

        if events is not None:
            return events
        if delay is not None:
            logging.warning(f"No events for the digest, retrying in {delay}s")
            await asyncio.sleep(delay)

    return None


async def send_weekly_digest(bot: Bot) -> None:
    today = date.today()
    events = await _fetch_week(today)
    if events is None:
        logging.error("skyevents unreachable, weekly digest not sent")
        return
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
    """Scheduler for sending the digest every saturday.

    Nothing inside the loop may take the task down: this coroutine is the
    only thing that ever broadcasts, and it dies unnoticed -- polling
    keeps working, so the bot looks healthy while going silent.
    """

    while True:
        if date.today().weekday() == SATURDAY:
            try:
                await send_weekly_digest(bot)
            except Exception as err:
                logging.exception(f"Weekly digest failed: {err}")

        await asyncio.sleep(SECONDS_PER_DAY)
