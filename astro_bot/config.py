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

# User agents file 
AGENTS = "user_agents.txt"

# Formats
LOGGING_FORMAT = "%(asctime)s | (line: %(lineno)s) %(levelname)s: %(message)s"
DATE_FORMAT = "%A, %B %d"

# Logging configuration
LOGGING_FILE = "astrobot.log"
LOGGING_MODE = "w"

# URLs
PAGE_URL = "https://astronomy.com/tags/sky-this-week"
ICS_FEED_URL = (
    "https://in-the-sky.org/newscalyear_ical.php?year={year}&maxdiff=7"
)
IMAGE_OF_THE_DAY_URL = f"https://api.nasa.gov/planetary/apod?api_key={NASA_TOKEN}"

# Scheduler
SATURDAY = 5
SECONDS_PER_DAY = 86400
