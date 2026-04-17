"""Scraper scheduler — orchestrates the full scrape + analyze pipeline."""

import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from src.config import get_settings
from src.database import get_engine, get_session_factory
from src.models import Filter, Listing, PriceHistory
from src.scraper.api_client import SrealityApiClient
from src.scraper.url_parser import parse_sreality_url
from src.scraper.parser import parse_listing_from_list, parse_listing_detail
from src.ai.analyzer import analyze_listing

logger = logging.getLogger(__name__)


def run_scrape_for_filter(filter_obj: Filter, session: Session) -> dict:
    """
    Run a full scrape cycle for a single filter.

    Process:
    1. Parse filter URL → API params
    2. Fetch all listings from API
    3. For each listing:
       - New → insert into DB + record initial price
       - Existing → update last_seen, check for price change
    4. Mark missing listings as inactive
    5. Trigger AI analysis for new/changed listings

    Returns:
        Stats dict with counts of new, updated, deactivated, price_changed listings.
    """
    stats = {
        "new": 0,
        "updated": 0,
        "deactivated": 0,
        "price_changed": 0,
        "ai_analyzed": 0,
        "errors": 0,
    }

    # Parse filter URL to list of API param dicts (one per category type)
    api_params_list = parse_sreality_url(filter_obj.url)
    logger.info(
        f"Scraping filter '{filter_obj.name}' — "
        f"{len(api_params_list)} category type(s) to fetch"
    )

    # Extract bounding box for GPS filtering (API boundary param doesn't actually filter!)
    bbox = _extract_bbox(api_params_list[0]) if api_params_list else None
    if bbox:
        logger.info(
            f"  GPS filter active: lat({bbox['lat_min']:.4f}–{bbox['lat_max']:.4f}), "
            f"lon({bbox['lon_min']:.4f}–{bbox['lon_max']:.4f})"
        )

    # Track which sreality_ids we see in this run
    seen_ids = set()
    listings_to_analyze = []
    skipped_gps = 0

    with SrealityApiClient() as client:
        # Iterate over each category type (prodej, pronájem, dražby)
        for api_params in api_params_list:
            type_cb = api_params.get("category_type_cb", "?")
            type_names = {"1": "prodej", "2": "pronájem", "3": "dražby"}
            logger.info(f"  Fetching type: {type_names.get(type_cb, type_cb)}")

            for estate_data in client.fetch_listings(api_params):
                try:
                    parsed = parse_listing_from_list(estate_data)
                    if not parsed:
                        continue

                    # GPS bounding box filter — skip listings outside target area
                    if bbox and parsed.get("gps_lat") and parsed.get("gps_lon"):
                        if not (bbox["lat_min"] <= parsed["gps_lat"] <= bbox["lat_max"] and
                                bbox["lon_min"] <= parsed["gps_lon"] <= bbox["lon_max"]):
                            skipped_gps += 1
                            continue

                    sreality_id = parsed["sreality_id"]
                    seen_ids.add(sreality_id)

                    # Check if listing already exists
                    existing = session.query(Listing).filter_by(
                        sreality_id=sreality_id
                    ).first()

                    if existing:
                        # Update last_seen
                        existing.last_seen = datetime.utcnow()
                        existing.is_active = True

                        # Check for price change
                        if parsed.get("price") and existing.price != parsed["price"]:
                            old_price = existing.price
                            existing.price = parsed["price"]

                            # Record price change
                            price_history = PriceHistory(
                                listing_id=existing.id,
                                price=parsed["price"],
                                price_per_m2=(
                                    round(parsed["price"] / existing.area_m2, 2)
                                    if existing.area_m2 and existing.area_m2 > 0
                                    else None
                                ),
                            )
                            session.add(price_history)
                            stats["price_changed"] += 1
                            logger.info(
                                f"Price changed for {sreality_id}: "
                                f"{old_price} → {parsed['price']}"
                            )

                        stats["updated"] += 1

                    else:
                        # New listing — fetch detail
                        try:
                            detail_data = client.fetch_listing_detail(sreality_id)
                            if detail_data:
                                detail_fields = parse_listing_detail(detail_data)
                                parsed.update(detail_fields)
                            else:
                                logger.debug(f"Detail unavailable (removed?) for {sreality_id}")
                        except Exception as e:
                            logger.warning(f"Failed to fetch detail for {sreality_id}: {e}")

                        # Remove internal fields
                        parsed.pop("_seo", None)

                        # Create new listing
                        new_listing = Listing(
                            filter_id=filter_obj.id,
                            **parsed,
                        )
                        session.add(new_listing)
                        session.flush()  # Get the ID

                        # Record initial price
                        if parsed.get("price"):
                            price_history = PriceHistory(
                                listing_id=new_listing.id,
                                price=parsed["price"],
                                price_per_m2=(
                                    round(parsed["price"] / parsed["area_m2"], 2)
                                    if parsed.get("area_m2") and parsed["area_m2"] > 0
                                    else None
                                ),
                            )
                            session.add(price_history)

                        listings_to_analyze.append(new_listing)
                        stats["new"] += 1
                        logger.info(f"New listing: {sreality_id} - {parsed.get('name', 'N/A')}")

                except Exception as e:
                    logger.error(f"Error processing estate: {e}", exc_info=True)
                    stats["errors"] += 1

        # Deactivate listings not seen in this run
        active_listings = session.query(Listing).filter_by(
            filter_id=filter_obj.id,
            is_active=True,
        ).all()

        for listing in active_listings:
            if listing.sreality_id not in seen_ids:
                listing.is_active = False
                stats["deactivated"] += 1
                logger.info(f"Deactivated listing: {listing.sreality_id} - {listing.name}")

    # Commit scraping results before analysis
    session.commit()

    # Run rule-based analysis on new listings (no AI/API key needed)
    from src.ai.rule_analyzer import analyze_listing_rules
    for listing in listings_to_analyze:
        try:
            result = analyze_listing_rules(listing)
            listing.ai_fees = result.get("ai_fees")
            listing.ai_vat_status = result.get("ai_vat_status")
            listing.ai_price_note_analysis = result.get("ai_price_note_analysis")
            listing.ai_analyzed_at = result.get("ai_analyzed_at")
            stats["ai_analyzed"] += 1
        except Exception as e:
            logger.error(f"Analysis failed for {listing.sreality_id}: {e}")
            stats["errors"] += 1

    session.commit()

    # Update filter's last_scraped_at
    filter_obj.last_scraped_at = datetime.utcnow()
    session.commit()

    logger.info(
        f"Scrape complete for '{filter_obj.name}': "
        f"new={stats['new']}, updated={stats['updated']}, "
        f"deactivated={stats['deactivated']}, price_changed={stats['price_changed']}, "
        f"ai_analyzed={stats['ai_analyzed']}, errors={stats['errors']}, "
        f"skipped_outside_bbox={skipped_gps}"
    )

    return stats


def run_all_scrapes():
    """Run scrape for all active filters."""
    Session = get_session_factory()
    session = Session()

    try:
        filters = session.query(Filter).filter_by(is_active=True).all()

        if not filters:
            logger.warning("No active filters found. Add a filter first.")
            return

        logger.info(f"Starting scrape for {len(filters)} active filter(s)")

        for filter_obj in filters:
            try:
                stats = run_scrape_for_filter(filter_obj, session)
            except Exception as e:
                logger.error(f"Scrape failed for filter '{filter_obj.name}': {e}", exc_info=True)
                session.rollback()

    finally:
        session.close()


def _extract_bbox(api_params: dict) -> dict:
    """
    Extract bounding box coordinates from API params.

    The Sreality API's 'boundary' parameter does NOT filter listings
    server-side — it only affects map clustering. So we extract the
    bbox here and use it for client-side GPS filtering.

    Returns dict with lat_min, lat_max, lon_min, lon_max or None.
    """
    import json
    boundary_str = api_params.get("boundary")
    if not boundary_str:
        return None

    try:
        boundary = json.loads(boundary_str)
        # boundary is [[{lat, lng}, {lat, lng}, ...]]
        points = boundary[0]
        lats = [p["lat"] for p in points]
        lngs = [p["lng"] for p in points]
        return {
            "lat_min": min(lats),
            "lat_max": max(lats),
            "lon_min": min(lngs),
            "lon_max": max(lngs),
        }
    except (json.JSONDecodeError, KeyError, IndexError):
        return None
