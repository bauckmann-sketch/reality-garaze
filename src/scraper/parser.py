"""Parse Sreality API responses into database model fields."""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


def parse_listing_from_list(estate: dict) -> dict:
    """
    Parse a listing from the list API response into DB-ready fields.

    Args:
        estate: Single estate dict from /api/cs/v2/estates response.

    Returns:
        Dict of fields ready for Listing model creation/update.
    """
    sreality_id = estate.get("hash_id")
    if not sreality_id:
        logger.warning("Estate without hash_id, skipping")
        return None

    # Extract basic info
    name = estate.get("name", "")
    price_raw = estate.get("price", 0)
    price_czk = estate.get("price_czk", {})
    locality = estate.get("locality", "")

    # GPS
    gps = estate.get("gps", {})
    gps_lat = gps.get("lat")
    gps_lon = gps.get("lon")

    # SEO data for URL building
    seo = estate.get("seo", {})
    category_type_cb = seo.get("category_type_cb")

    # Map category type
    type_map = {1: "prodej", 2: "pronájem", 3: "dražba"}
    category_type = type_map.get(category_type_cb, "neznámý")

    # Extract area from name (e.g. "Prodej garáže 18 m²")
    area_m2 = _extract_area_from_name(name)

    # Build Sreality URL from SEO
    from src.scraper.url_parser import build_sreality_detail_url
    url = build_sreality_detail_url(sreality_id, seo)

    return {
        "sreality_id": sreality_id,
        "name": name,
        "price": Decimal(str(price_raw)) if price_raw else None,
        "area_m2": area_m2,
        "locality": locality,
        "gps_lat": gps_lat,
        "gps_lon": gps_lon,
        "category_type": category_type,
        "url": url,
        "_seo": seo,  # Keep for detail fetching
    }


def parse_listing_detail(detail: dict) -> dict:
    """
    Parse detailed listing data from /api/cs/v2/estates/{id} response.

    Args:
        detail: Full estate detail dict from the API.

    Returns:
        Dict of additional fields to update on the Listing.
    """
    result = {}

    # Full description text
    text_data = detail.get("text", {})
    result["description"] = text_data.get("value", "")

    # Parse structured items
    items = detail.get("items", [])
    for item in items:
        item_name = item.get("name", "")
        item_value = item.get("value", "")
        item_type = item.get("type", "")

        # Price note
        if item_name == "Poznámka k ceně":
            result["price_note"] = item_value

        # Building type (Stavba)
        elif item_name == "Stavba":
            result["building_type"] = item_value

        # Building condition (Stav objektu)
        elif item_name == "Stav objektu":
            result["building_condition"] = item_value

        # Ownership (Vlastnictví)
        elif item_name == "Vlastnictví":
            result["ownership"] = item_value

        # Area (Užitná plocha / Celková plocha)
        elif item_type == "area" and item_name in ("Užitná ploch", "Užitná plocha", "Celková plocha"):
            try:
                area = Decimal(str(item_value).replace(",", "."))
                if not result.get("area_m2") or item_name.startswith("Užitná"):
                    result["area_m2"] = area
            except (ValueError, TypeError):
                pass

        # Price
        elif item_type == "price_czk":
            try:
                raw_value = item.get("value", "").replace("\xa0", "").replace(" ", "")
                result["price"] = Decimal(raw_value)
            except (ValueError, TypeError):
                pass

    # Seller info
    seller = detail.get("_embedded", {}).get("seller", {})
    if seller:
        result["seller_name"] = seller.get("user_name", "")
        result["seller_email"] = seller.get("email", "")

        # Phone
        phones = seller.get("phones", [])
        if phones:
            phone = phones[0]
            result["seller_phone"] = f"+{phone.get('code', '420')}{phone.get('number', '')}"

        # Company
        premise = seller.get("_embedded", {}).get("premise", {})
        if premise:
            result["seller_company"] = premise.get("name", "")

    return result


def _extract_area_from_name(name: str) -> Optional[Decimal]:
    """
    Extract area in m² from listing name.

    Examples:
        "Prodej garáže 18 m²" → Decimal("18")
        "Pronájem garážového stání 12 m²" → Decimal("12")
    """
    # Match patterns like "18 m²", "18 m2", "18m²"  
    # Using \xa0 for non-breaking space that Sreality uses
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:\xa0)?m[²2]", name)
    if match:
        try:
            return Decimal(match.group(1).replace(",", "."))
        except (ValueError, TypeError):
            pass
    return None
