import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from aiogram import Bot

from astro_bot.config import (
    DIGEST_CATCHUP_HOURS,
    DIGEST_HOUR_UTC,
    DIGEST_RETRY_DELAYS,
    SATURDAY,
)
from astro_bot.keyboards.inline_keyboard import get_inline_week_keyboard
from astro_bot.services.digest_state import read_last_slot, record_slot
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


async def send_weekly_digest(bot: Bot) -> bool:
    """Broadcast the week to every user. Returns whether it actually went
    out, which is what the slot marker records: an outage or a quiet week
    sends nothing and stays unrecorded, so a restart inside the catch-up
    window gets to try again."""

    # UTC, like the slot the scheduler fires on and like the dates
    # `get_events_between` asks skyevents for -- the server's local day
    # is nobody's here
    today = datetime.now(timezone.utc).date()
    events = await _fetch_week(today)
    if events is None:
        logging.error("skyevents unreachable, weekly digest not sent")
        return False
    if not events:
        logging.warning("No events for the weekly digest, nothing sent")
        return False

    digest = WEEK_DIGEST_MESSAGE(events)
    for user_id in get_users_ids():
        try:
            await bot.send_message(
                user_id,
                digest,
                # anchored to the digest's own week (today..today+6), not
                # to the Mon-Sun one today falls in -- the arrows have to
                # page through the days the message actually lists
                reply_markup=get_inline_week_keyboard(today, anchor=today),
                disable_web_page_preview=True,
            )
        except Exception as err:
            logging.error(f"Digest was not sent to {user_id}: {err}")

    return True


def last_digest_slot(now: datetime) -> datetime:
    """The most recent Saturday DIGEST_HOUR_UTC at or before `now`"""

    slot = now.replace(
        hour=DIGEST_HOUR_UTC, minute=0, second=0, microsecond=0
    )
    slot -= timedelta(days=(slot.weekday() - SATURDAY) % 7)
    if slot > now:
        slot -= timedelta(weeks=1)
    return slot


def missed_digest_slot(now: datetime) -> bool:
    """Whether a process starting at `now` still owes the last slot a
    broadcast: the slot went by less than DIGEST_CATCHUP_HOURS ago and
    the marker does not already name it.

    Without the marker this could only guess. A restart just after the
    slot means either "was down while it passed, nobody got the digest"
    or "sent it, then CI redeployed" -- indistinguishable from the clock
    alone, and guessing "send" turned a Saturday crash loop into N copies
    for every user. `read_last_slot` settles it, so the window is now
    only about how late a catch-up is still worth doing.

    The window is measured back from the last slot rather than by asking
    whether today is Saturday: it may run past midnight into Sunday,
    which it does as soon as DIGEST_HOUR_UTC + DIGEST_CATCHUP_HOURS goes
    over 24, and a weekday test would quietly stop catching up there.
    """

    slot = last_digest_slot(now)
    if now >= slot + timedelta(hours=DIGEST_CATCHUP_HOURS):
        return False
    return read_last_slot() != slot


def next_digest_time(now: datetime) -> datetime:
    """The next Saturday DIGEST_HOUR_UTC, strictly after `now`"""

    target = now.replace(
        hour=DIGEST_HOUR_UTC, minute=0, second=0, microsecond=0
    )
    target += timedelta(days=(SATURDAY - target.weekday()) % 7)
    if target <= now:
        # the gap between two Saturdays -- unrelated to how many days the
        # pagination window happens to span, so not that constant
        target += timedelta(weeks=1)
    return target


async def _broadcast(bot: Bot, slot: datetime) -> None:
    """Send, and on success record the slot so no restart repeats it"""

    if await send_weekly_digest(bot):
        record_slot(slot)


async def scheduler(bot: Bot) -> None:
    """Broadcast the digest every Saturday at DIGEST_HOUR_UTC.

    Sleeps until the next slot rather than waking daily to ask whether it
    is Saturday today. That older shape broadcast immediately whenever
    the process started on a Saturday -- and CI rebuilds the container on
    every push to main, so a Saturday deploy mailed every user a second
    copy at whatever hour the deploy happened. It also drifted: a flat
    24h sleep plus up to 21 minutes of fetch retries pushed the broadcast
    later week after week, until it would eventually step over midnight
    and skip a Saturday outright.

    Sleeping to a slot alone would swap that for the opposite failure --
    a restart spanning the slot skips the week in silence -- so startup
    catches up inside `missed_digest_slot`'s window. What makes the
    catch-up safe is the slot marker: it is written only after a
    broadcast really goes out, so a redeploy (or a crash loop) behind one
    sees its own slot on record and stays quiet, while a process that was
    down through the slot finds nothing and sends. Both halves are load
    bearing -- drop the marker and the catch-up multiplies copies, drop
    the catch-up and a deploy across the slot loses the week.

    Nothing inside the loop may take the task down: this coroutine is the
    only thing that ever broadcasts, and it dies unnoticed -- polling
    keeps working, so the bot looks healthy while going silent.
    """

    now = datetime.now(timezone.utc)
    if missed_digest_slot(now):
        logging.warning("Started just past the digest slot, sending now")
        try:
            await _broadcast(bot, last_digest_slot(now))
        except Exception as err:
            logging.exception(f"Catch-up digest failed: {err}")

    while True:
        now = datetime.now(timezone.utc)
        target = next_digest_time(now)
        logging.info(f"Next weekly digest at {target.isoformat()}")
        await asyncio.sleep((target - now).total_seconds())

        # asyncio.sleep counts monotonic seconds while the slot is wall
        # clock: an NTP or host step backwards during the week lands us
        # here early, and sending anyway would mail a second copy to
        # everyone. Recompute and wait the remainder out instead.
        if datetime.now(timezone.utc) < target:
            logging.warning("Woke before the digest slot, waiting again")
            continue

        try:
            await _broadcast(bot, target)
        except Exception as err:
            logging.exception(f"Weekly digest failed: {err}")
