import logging
import time

import schedule
from flask import current_app

from aggregator import engine

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@schedule.repeat(schedule.every().minute.at(':00'))
def update_feeds():
    logger.info("Updating feeds")
    with current_app.app_context():
        engine.update_feeds()


@schedule.repeat(schedule.every().day.at('03:00'))
def update_favicons():
    logger.info("Updating favicons")
    with current_app.app_context():
        engine.update_favicons()


def start():
    while True:
        logger.info(f"Sleep for {schedule.idle_seconds()} seconds")
        time.sleep(schedule.idle_seconds())

        logger.info(f"Run pending jobs")
        schedule.run_pending()
