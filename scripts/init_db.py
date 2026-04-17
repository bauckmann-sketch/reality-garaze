"""Initialize database and optionally seed with default filter."""

import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from src.database import init_db, get_session_factory
from src.models import Filter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# Default filter from the project specification
DEFAULT_FILTER = {
    "name": "Garáže Praha (prodej+pronájem+dražby)",
    "url": "https://www.sreality.cz/hledani/drazby,prodej,pronajem/ostatni/garaze,garazova-stani/vsechny-staty?lat-max=50.06870949468981&lat-min=49.99350510595579&lon-max=14.469304166147776&lon-min=14.385705075571604",
    "category_type": "smíšený",
    "scrape_interval_hours": 24,
}


def main():
    logger.info("Creating database tables...")
    init_db()
    logger.info("✅ Database tables created.")

    # Seed default filter if none exist
    Session = get_session_factory()
    session = Session()

    try:
        existing = session.query(Filter).count()
        if existing == 0:
            logger.info("No filters found. Seeding default filter...")
            default = Filter(**DEFAULT_FILTER)
            session.add(default)
            session.commit()
            logger.info(f"✅ Default filter created: '{DEFAULT_FILTER['name']}'")
        else:
            logger.info(f"Database already has {existing} filter(s). Skipping seed.")
    finally:
        session.close()

    logger.info("🎉 Database initialization complete!")


if __name__ == "__main__":
    main()
