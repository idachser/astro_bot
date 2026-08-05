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

logger = logging.getLogger(__name__)


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
            logger.exception(f"Weekly events request raised: {err}")
            events = None

        if events is not None:
            return events
        if delay is not None:
            logger.warning(f"No events for the digest, retrying in {delay}s")
            await asyncio.sleep(delay)

    return None


async def send_weekly_digest(bot: Bot, today: date) -> bool:
    """Broadcast the week starting at `today` to every user. Returns
    whether it actually reached anyone, which is what the slot marker
    records: an outage, a quiet week or a Telegram that refuses every
    send stays unrecorded, so a restart inside the catch-up window gets
    to try again.

    `today` is the slot's own UTC date, passed in rather than read off
    the clock here. With a catch-up window that runs past midnight the
    two differ -- a Sunday catch-up serves Saturday's slot -- and the
    digest has to cover the week it is filed under.
    """

    events = await _fetch_week(today)
    if events is None:
        logger.error("skyevents unreachable, weekly digest not sent")
        return False
    if not events:
        logger.warning("No events for the weekly digest, nothing sent")
        return False

    digest = WEEK_DIGEST_MESSAGE(events)
    delivered = 0
    # Small read, but it is still SQLite: the only blocking DB call left
    # on the event loop was this one
    for user_id in await asyncio.to_thread(get_users_ids):
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
            delivered += 1
        except Exception as err:
            logger.error(f"Digest was not sent to {user_id}: {err}")

    if not delivered:
        # Every send failed (an unreachable Telegram, a rejected token):
        # reporting success here would file the slot as broadcast and
        # talk the catch-up out of the retry it exists for
        logger.error("Weekly digest reached nobody")
    return delivered > 0


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
    """Whether `now` is still inside the last slot's catch-up window --
    late enough that a starting process should consider broadcasting it,
    early enough that the digest is still worth sending.

    Purely a question about the clock. Whether that slot *actually* still
    needs sending is the marker's job, and `_broadcast` asks it, so the
    two paths into a broadcast cannot disagree about it.

    The window is measured back from the last slot rather than by asking
    whether today is Saturday: it may run past midnight into Sunday,
    which it does as soon as DIGEST_HOUR_UTC + DIGEST_CATCHUP_HOURS goes
    over 24, and a weekday test would quietly stop catching up there.
    """

    return now < last_digest_slot(now) + timedelta(
        hours=DIGEST_CATCHUP_HOURS
    )


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
    """Send the digest for `slot`, unless it already went out, and record
    it when it reaches someone.

    Every broadcast goes through here -- the startup catch-up and the
    scheduled one alike -- so the marker guards both. It has to guard the
    scheduled path too: `asyncio.sleep` counts monotonic seconds, so a
    wall clock stepped back after a send puts `next_digest_time` right
    back on the slot that just fired, and every user would get the same
    digest a second time.
    """

    if read_last_slot() == slot:
        logger.info(f"Digest for {slot.isoformat()} already sent, skipping")
        return
    if await send_weekly_digest(bot, slot.date()):
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
        logger.warning("Started just past the digest slot, sending now")
        try:
            await _broadcast(bot, last_digest_slot(now))
        except Exception as err:
            logger.exception(f"Catch-up digest failed: {err}")

    while True:
        now = datetime.now(timezone.utc)
        target = next_digest_time(now)
        logger.info(f"Next weekly digest at {target.isoformat()}")
        await asyncio.sleep((target - now).total_seconds())

        # asyncio.sleep counts monotonic seconds while the slot is wall
        # clock: an NTP or host step backwards during the week lands us
        # here early, and sending anyway would mail a second copy to
        # everyone. Recompute and wait the remainder out instead.
        if datetime.now(timezone.utc) < target:
            logger.warning("Woke before the digest slot, waiting again")
            continue

        try:
            await _broadcast(bot, target)
        except Exception as err:
            logger.exception(f"Weekly digest failed: {err}")
