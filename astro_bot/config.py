import os
from dotenv import load_dotenv


BASE_PATH = os.path.dirname(os.path.abspath(__name__))

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
LOGGING_FORMAT = "%(asctime)s | (line: %(lineno)s) %(levelname)s: %(message)s"

# Logging configuration
LOGGING_FILE = os.getenv("LOGGING_FILE", "astrobot.log")
LOGGING_MODE = "w"

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
