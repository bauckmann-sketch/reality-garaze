"""CLI script to run the scraper manually or as a cron/scheduled service."""

import sys
import os
import logging
import argparse
import time

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db, get_session_factory
from src.models import Filter
from src.scraper.scheduler import run_all_scrapes, run_scrape_for_filter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Sreality Tracker — Scraper")
    parser.add_argument(
        "--mode",
        choices=["once", "loop"],
        default="once",
        help="'once' = single run, 'loop' = continuous with interval",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Override scrape interval in hours (for loop mode)",
    )
    parser.add_argument(
        "--filter-id",
        type=int,
        default=None,
        help="Run scrape only for a specific filter ID",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize database tables before running",
    )

    args = parser.parse_args()

    # Initialize DB if requested
    if args.init_db:
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized.")

    if args.mode == "once":
        if args.filter_id:
            Session = get_session_factory()
            session = Session()
            try:
                filter_obj = session.query(Filter).get(args.filter_id)
                if not filter_obj:
                    logger.error(f"Filter with ID {args.filter_id} not found.")
                    sys.exit(1)
                run_scrape_for_filter(filter_obj, session)
            finally:
                session.close()
        else:
            run_all_scrapes()

    elif args.mode == "loop":
        from src.config import get_settings
        settings = get_settings()
        interval_hours = args.interval or settings.scrape_interval_hours
        interval_seconds = interval_hours * 3600

        logger.info(f"Starting scraper loop with {interval_hours}h interval")

        while True:
            try:
                run_all_scrapes()
            except Exception as e:
                logger.error(f"Scrape cycle failed: {e}", exc_info=True)

            logger.info(f"Next scrape in {interval_hours} hours...")
            time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
