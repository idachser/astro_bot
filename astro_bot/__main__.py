import logging
import asyncio
import sys
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher, types

from astro_bot.config import (
    TOKEN,
    LOGGING_FORMAT,
    LOGGING_FILE,
    LOGGING_MODE,
    LOGGING_MAX_BYTES,
    LOGGING_BACKUP_COUNT,
)
from astro_bot.services.users import init_storage
from astro_bot.handlers import (
    greeting,
    start,
    help_,
    week,
    today,
    yesterday,
    tomorrow,
    image_of_the_day,
    specific_date,
    autosend_events,
)


# The handlers are built by hand rather than left to basicConfig's
# `filename=`, which installs a FileHandler and nothing else: in Docker
# that left `docker logs astro-bot` empty, so the only way to see what
# the bot was doing was to open the file inside the mounted volume.
# Everything now goes to both, and stdout is what the container reports.
# The file handler appends and rotates: it is the durable record, since
# `docker logs` only survives until the next CI deploy recreates the
# container. Rotation is what keeps appending from growing without bound
# in the mounted volume -- the bot writes a handful of lines a day, so
# 3 backups of 5 MB is months of history, not a retention policy.
logging.basicConfig(
    format=LOGGING_FORMAT,
    level=logging.INFO,
    handlers=[
        RotatingFileHandler(
            LOGGING_FILE,
            mode=LOGGING_MODE,
            maxBytes=LOGGING_MAX_BYTES,
            backupCount=LOGGING_BACKUP_COUNT,
            encoding="utf-8",
        ),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("Start application")
    init_storage()
    bot = Bot(token=TOKEN, parse_mode=types.ParseMode.HTML)
    dp = Dispatcher(bot)

    greeting.register_handler_start(dp)
    start.register_handler_start(dp)
    help_.register_handler_help(dp)
    week.register_handler_week(dp)
    today.register_handler_today(dp)
    yesterday.register_handler_yesterday(dp)
    tomorrow.register_handler_tomorrow(dp)
    image_of_the_day.register_handler_image(dp)
    specific_date.register_handler_specific_day(dp)

    loop = asyncio.get_event_loop()
    loop.create_task(autosend_events.scheduler(bot))

    await dp.start_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nApplication closed")
        logger.info("Application closed")

    except Exception as err:
        # .exception, not .error: this is the one record that explains why
        # the bot died, and str(err) alone gives neither the type nor the
        # frame it came from -- it would point at this line, not the fault.
        logger.exception(f"Application crashed: {err}")
