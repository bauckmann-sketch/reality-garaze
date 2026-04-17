"""Rule-based analysis of listing data — no AI needed.

Extracts fees, VAT status from structured Sreality API fields.
"""

from __future__ import annotations

import re
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from src.models import Listing

logger = logging.getLogger(__name__)


def analyze_listing_rules(listing: Listing) -> dict:
    """
    Analyze a listing using rule-based extraction from structured fields.
    """
    result = {}

    price_note = (listing.price_note or "").strip()
    description = (listing.description or "").strip()
    pn_lower = price_note.lower()
    desc_lower = description.lower()

    # ─── Fees from price_note ───
    result["ai_fees"] = _extract_fees(pn_lower, desc_lower)

    # ─── VAT from price_note + description ───
    result["ai_vat_status"] = _extract_vat(pn_lower, desc_lower)

    # ─── Price note (raw) ───
    if price_note:
        result["ai_price_note_analysis"] = price_note

    result["ai_analyzed_at"] = datetime.utcnow()

    return result


def _extract_fees(price_note: str, description: str) -> str:
    """Extract fee information from price note and description."""

    # Check price_note first (most reliable)
    if price_note:
        # "vč. poplatků" / "včetně poplatků"
        if re.search(r"v[čc][\.\s]+poplat|včetně\s+poplat", price_note):
            return "včetně v ceně"

        # "bez poplatků"
        if "bez poplat" in price_note:
            return "0 Kč"

        # "+ poplatky/energie/služby" with number
        m = re.search(r"(?:poplatky|energie|služby)[:\s]+(\d[\d\s]*)", price_note)
        if m:
            num = m.group(1).replace(" ", "").replace("\xa0", "")
            return f"{num} Kč/měs"

        # "+ energie" / "+ poplatky" without number
        if re.search(r"\+\s*(?:energie|poplatky|služby)", price_note):
            return "energie navíc"

        # "včetně provize" (for sale — commission included)
        if "včetně provize" in price_note or "zahrnuje" in price_note:
            return "vč. provize"

        # If price_note exists but no fee pattern matched
        if "konečná" in price_note or "finální" in price_note:
            return "konečná cena"

    # Check description for fee info
    if description:
        if re.search(r"v[čc][\.\s]+poplat|včetně\s+poplat|poplatky\s+0|bez\s+poplat", description):
            return "včetně v ceně"

        m = re.search(r"(?:poplatky|energie|služby)\s*(?:činí|jsou)?\s*(\d[\d\s]*)\s*(?:Kč|kč)", description)
        if m:
            num = m.group(1).replace(" ", "").replace("\xa0", "")
            return f"{num} Kč/měs"

    return "neuvedeno"


def _extract_vat(price_note: str, description: str) -> str:
    """Extract VAT status from price note and description."""
    combined = f"{price_note} {description}"

    # Check for DPH mentions
    if re.search(r"(?:včetně|vč\.?|zahrnuje)\s+(?:\d+%?\s*)?DPH", combined, re.IGNORECASE):
        return "s DPH"

    if re.search(r"(?:bez|plus|\+)\s+DPH", combined, re.IGNORECASE):
        return "bez DPH"

    if re.search(r"\d+%\s*DPH", combined, re.IGNORECASE):
        return "s DPH"

    if re.search(r"nepl[áa]tce|osvobozen\w*\s*(?:od\s*)?DPH", combined, re.IGNORECASE):
        return "neplátce"

    return "neuvedeno"


def analyze_all_listings(session: Session, filter_id: int = None) -> dict:
    """Run rule-based analysis on all listings."""
    query = session.query(Listing)
    if filter_id:
        query = query.filter_by(filter_id=filter_id)

    listings = query.all()
    analyzed = 0

    for listing in listings:
        try:
            result = analyze_listing_rules(listing)
            listing.ai_fees = result.get("ai_fees")
            listing.ai_vat_status = result.get("ai_vat_status")
            listing.ai_price_note_analysis = result.get("ai_price_note_analysis")
            listing.ai_analyzed_at = result.get("ai_analyzed_at")
            analyzed += 1
        except Exception as e:
            logger.error(f"Analysis failed for {listing.sreality_id}: {e}")

    session.commit()
    logger.info(f"Rule-based analysis complete: {analyzed} listings analyzed")
    return {"analyzed": analyzed}
