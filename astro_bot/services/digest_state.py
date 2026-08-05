import logging
from datetime import datetime

from astro_bot.config import DIGEST_STATE_FILE

logger = logging.getLogger(__name__)


def read_last_slot(path: str = DIGEST_STATE_FILE) -> datetime | None:
    """The digest slot that last went out, or None if none is on record.

    Every failure reads as None, not just a missing file (which is the
    normal first-run state): the marker can only ever *suppress* a
    broadcast, so losing it costs one duplicate, while raising here would
    take down the scheduler task that is the bot's only broadcaster.
    """

    try:
        with open(path) as state:
            return datetime.fromisoformat(state.read().strip())
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as err:
        logger.warning(f"Could not read the digest marker at {path}: {err}")
        return None


def record_slot(slot: datetime, path: str = DIGEST_STATE_FILE) -> None:
    """Remember that `slot` was broadcast. Best effort for the same
    reason: a failed write costs at most one duplicate on the next
    restart, and must not kill the scheduler."""

    try:
        with open(path, "w") as state:
            state.write(slot.isoformat())
    except OSError as err:
        logger.warning(f"Could not record the digest marker at {path}: {err}")
