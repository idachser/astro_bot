import logging
import asyncio
from aiogram import Bot, Dispatcher, types

from astro_bot.config import TOKEN, LOGGING_FORMAT, LOGGING_FILE, LOGGING_MODE
from astro_bot.services.events import init_storage, sync_events
from astro_bot.handlers import (
    greeting,
    start,
    help_,
    week,
    today,
    yesterday,
    tomorrow,
    specific_date,
    autosend_events,
)


logging.basicConfig(
    format=LOGGING_FORMAT,
    filename=LOGGING_FILE,
    filemode=LOGGING_MODE,
    level=logging.INFO,
)


async def main() -> None:
    logging.info("Start application")
    init_storage()
    sync_events()
    bot = Bot(token=TOKEN, parse_mode=types.ParseMode.HTML)
    dp = Dispatcher(bot)

    greeting.register_handler_start(dp)
    start.register_handler_start(dp)
    help_.register_handler_help(dp)
    week.register_handler_week(dp)
    today.register_handler_today(dp)
    yesterday.register_handler_yesterday(dp)
    tomorrow.register_handler_tomorrow(dp)
    specific_date.register_handler_specific_day(dp)

    loop = asyncio.get_event_loop()
    loop.create_task(autosend_events.scheduler(bot))

    await dp.start_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nApplication closed")
        logging.info("Application closed")

    except Exception as err:
        logging.error(err)
