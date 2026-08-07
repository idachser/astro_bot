import os
from dotenv import load_dotenv


# The repo root, resolved from this file rather than from `__name__` --
# that was the *module name* string, so it silently resolved to whatever
# the working directory happened to be. It matched only because Docker's
# WORKDIR is /app; running from anywhere else lost the .env and pointed
# DB (and with it the digest marker) at the wrong place.
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

dotenv_path = os.path.join(BASE_PATH, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Tokens
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
NASA_TOKEN = os.getenv("NASA_IMAGE_OF_THE_DAY_TOKEN", "")

# DBs
DB = os.path.join(BASE_PATH, os.getenv("DB", ""))

# Which digest slot last went out, so a restart inside the catch-up
# window does not broadcast it twice. A plain file next to the DB in the
# mounted ./data/ volume, deliberately not a table: the schema stays
# "users and nothing else", and this is scheduler state, not user data.
DIGEST_STATE_FILE = os.path.join(os.path.dirname(DB), "last_digest")

# Formats
# %(name)s is the logging module path (`astro_bot.db`, `aiogram.dispatcher`),
# without which a bare line number says nothing about whose code emitted
# the record -- every module logs through its own `getLogger(__name__)`.
LOGGING_FORMAT = (
    "%(asctime)s | %(name)s (line: %(lineno)s) %(levelname)s: %(message)s"
)

# Logging configuration
# Joined onto BASE_PATH for the same reason DB is: a bare filename is
# relative to the working directory, and that only lined up with the
# mounted ./data/ volume because Docker's WORKDIR happens to be /app.
# An absolute LOGGING_FILE still wins -- os.path.join keeps it.
LOGGING_FILE = os.path.join(
    BASE_PATH, os.getenv("LOGGING_FILE", "astrobot.log")
)
# Appended to, not truncated at start. The file used to be opened "w",
# which made a crash loop erase its own evidence: the bot dies writing a
# traceback, `restart: unless-stopped` brings it back seconds later, and
# the log an operator opens afterwards holds nothing but "Start
# application". Rotation is what makes appending safe to leave running.
LOGGING_MODE = "a"
LOGGING_MAX_BYTES = 5 * 1024 * 1024
LOGGING_BACKUP_COUNT = 3

# URLs
# skyevents computes the celestial events itself and serves them over
# HTTP; reached by service name over the shared `astronet` docker bridge.
SKYEVENTS_URL = os.getenv("SKYEVENTS_URL", "http://skyevents:8000")
IMAGE_OF_THE_DAY_URL = (
    f"https://api.nasa.gov/planetary/apod?api_key={NASA_TOKEN}"
)
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# Events
EVENTS_CACHE_TTL_SECONDS = 3600

WEEK_LENGTH = 7

# Scheduler
SATURDAY = 5
# The broadcast goes out at a fixed UTC slot rather than "whenever the
# process happens to wake up": the scheduler sleeps until the next one.
DIGEST_HOUR_UTC = 9
# How long after the slot a starting process still sends the digest, for
# the case where it was down while the slot passed. Deliberately errs
# towards a duplicate over a silent miss -- see `missed_digest_slot`.
DIGEST_CATCHUP_HOURS = 1
# Backoff before giving up on the weekly digest. It is the one thing that
# cannot simply be asked for again later: a user pressing a button retries
# by pressing it again, the broadcast only comes round next Saturday.
DIGEST_RETRY_DELAYS = (60, 300, 900)
