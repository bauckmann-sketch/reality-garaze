"""AI analysis of listing descriptions using OpenAI GPT-4o-mini."""

import json
import logging
from datetime import datetime
from decimal import Decimal

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_settings

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """Jsi expert na český realitní trh. Analyzuj následující inzerát nemovitosti a extrahuj strukturovaná data.

TEXT INZERÁTU:
{description}

POZNÁMKA K CENĚ:
{price_note}

UVEDENÁ CENA: {price} Kč
UVEDENÁ VÝMĚRA: {area} m²

Extrahuj následující informace a vrať je jako JSON objekt:

1. "vat_status" — DPH status ceny. Možné hodnoty:
   - "s_dph" — cena je včetně DPH
   - "bez_dph" — cena je bez DPH (k ceně se přičítá DPH)
   - "neplatce" — prodávající není plátce DPH
   - "neuvedeno" — v textu není žádná zmínka o DPH

2. "fees" — Informace o poplatcích/energiích/službách. Možné hodnoty:
   - Konkrétní částka v Kč (např. "3500 Kč/měsíc")
   - "vcetne_poplatku" — poplatky jsou zahrnuty v ceně
   - "neuvedeno" — v textu není zmínka o poplatcích

3. "fees_detail" — Podrobnější popis poplatků, pokud je uveden (volný text, česky)

4. "validated_area" — Skutečná výměra v m², pokud je v textu uvedena jiná než v parametrech. Pokud se shoduje nebo není zmíněna, vlož null.

5. "condition_summary" — Krátký standardizovaný popis stavu objektu (česky, max 50 znaků). Např. "Dobrý stav, cihlová stavba" nebo "Po rekonstrukci, zatepleno".

6. "investment_notes" — Krátká poznámka relevantní pro investora (max 100 znaků, česky). Např. "Vlastní pozemek, vhodné k pronájmu" nebo "Družstevní vlastnictví, omezený převod".

Odpověz POUZE validním JSON objektem, bez dalšího textu.
"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
)
def _call_openai(description: str, price_note: str, price: str, area: str) -> dict:
    """Call OpenAI API with retry logic."""
    settings = get_settings()

    client = OpenAI(api_key=settings.openai_api_key)

    prompt = ANALYSIS_PROMPT.format(
        description=description or "(prázdný popis)",
        price_note=price_note or "(neuvedeno)",
        price=price or "neuvedeno",
        area=area or "neuvedeno",
    )

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {
                "role": "system",
                "content": "Jsi pomocník pro analýzu realitních inzerátů. Vždy odpovídáš validním JSON objektem.",
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=500,
    )

    raw_response = response.choices[0].message.content
    return json.loads(raw_response)


def analyze_listing(listing, session=None) -> dict:
    """
    Analyze a listing's description using OpenAI and update the listing fields.

    Args:
        listing: Listing ORM instance.
        session: Optional SQLAlchemy session (for committing).

    Returns:
        The parsed AI analysis dict.
    """
    if not listing.description and not listing.price_note:
        logger.info(f"Listing {listing.sreality_id} has no description to analyze")
        return {}

    logger.info(f"Analyzing listing {listing.sreality_id}: {listing.name}")

    try:
        result = _call_openai(
            description=listing.description or "",
            price_note=listing.price_note or "",
            price=str(listing.price) if listing.price else "",
            area=str(listing.area_m2) if listing.area_m2 else "",
        )

        # Map results to listing fields
        listing.ai_vat_status = result.get("vat_status", "neuvedeno")
        listing.ai_fees = result.get("fees", "neuvedeno")
        listing.ai_price_note_analysis = result.get("fees_detail", "")
        listing.ai_condition = result.get("condition_summary", "")
        listing.ai_raw_response = json.dumps(result, ensure_ascii=False)
        listing.ai_analyzed_at = datetime.utcnow()

        # Validated area
        validated_area = result.get("validated_area")
        if validated_area is not None:
            try:
                listing.ai_validated_area = Decimal(str(validated_area))
            except (ValueError, TypeError):
                pass

        logger.info(
            f"AI analysis complete for {listing.sreality_id}: "
            f"DPH={listing.ai_vat_status}, fees={listing.ai_fees}"
        )

        return result

    except Exception as e:
        logger.error(f"AI analysis failed for {listing.sreality_id}: {e}", exc_info=True)
        raise
