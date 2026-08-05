import logging

import requests

from astro_bot.config import IMAGE_OF_THE_DAY_URL

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30


def get_image_of_the_day() -> dict | None:
    """Fetch NASA APOD metadata: title, explanation, url, media_type"""

    try:
        response = requests.get(IMAGE_OF_THE_DAY_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as err:
        logger.exception(f"APOD request failed: {err}")
