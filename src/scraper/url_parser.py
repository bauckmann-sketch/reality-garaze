"""Parse Sreality.cz filter URLs into API query parameters."""

from __future__ import annotations

import json
import re
from typing import Optional
from urllib.parse import urlparse, parse_qs


# Mapping from URL path segments to API category codes
CATEGORY_TYPE_MAP = {
    "prodej": 1,
    "pronajem": 2,
    "drazby": 3,
}

CATEGORY_MAIN_MAP = {
    "byty": 1,
    "domy": 2,
    "pozemky": 3,
    "komercni": 4,
    "ostatni": 5,
}

CATEGORY_SUB_MAP = {
    # Ostatní
    "garaze": 34,
    "garazova-stani": 52,
    # Byty
    "1+kk": 2,
    "1+1": 3,
    "2+kk": 4,
    "2+1": 5,
    "3+kk": 6,
    "3+1": 7,
    "4+kk": 8,
    "4+1": 9,
    "5+kk": 10,
    "5+1": 11,
    "6-a-vice": 12,
    "atypicky": 16,
}


def parse_sreality_url(url: str) -> list:
    """
    Parse a Sreality.cz search URL into a list of API query parameter dicts.

    The Sreality API does NOT support pipe-separated category_type_cb values
    (e.g. "1|2|3"). It silently uses only the first value. So when the URL
    contains multiple types (prodej,pronajem,drazby), we return one param dict
    per type so the caller can make separate API calls.

    Example URL:
    https://www.sreality.cz/hledani/drazby,prodej,pronajem/ostatni/garaze,garazova-stani/vsechny-staty?lat-max=50.069&lat-min=49.994&lon-max=14.469&lon-min=14.386

    Returns list of dicts, e.g.:
    [
        {"category_type_cb": "1", "category_main_cb": "5", "category_sub_cb": "34|52", ...},
        {"category_type_cb": "2", "category_main_cb": "5", "category_sub_cb": "34|52", ...},
        {"category_type_cb": "3", "category_main_cb": "5", "category_sub_cb": "34|52", ...},
    ]
    """
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    # Parse path segments: /hledani/{types}/{main}/{sub}/{location}
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]

    base_params = {}
    type_codes = []

    if len(path_parts) >= 2:
        # Category types (prodej, pronajem, drazby)
        types_segment = path_parts[1]
        for t in types_segment.split(","):
            t = t.strip()
            if t in CATEGORY_TYPE_MAP:
                type_codes.append(str(CATEGORY_TYPE_MAP[t]))
        if not type_codes:
            type_codes = ["1"]  # default to prodej

    if len(path_parts) >= 3:
        # Category main (byty, domy, ostatni, etc.)
        main_segment = path_parts[2]
        if main_segment in CATEGORY_MAIN_MAP:
            base_params["category_main_cb"] = str(CATEGORY_MAIN_MAP[main_segment])

    if len(path_parts) >= 4:
        # Category sub (garaze, garazova-stani, etc.)
        sub_segment = path_parts[3]
        sub_codes = []
        for s in sub_segment.split(","):
            s = s.strip()
            if s in CATEGORY_SUB_MAP:
                sub_codes.append(str(CATEGORY_SUB_MAP[s]))
        if sub_codes:
            base_params["category_sub_cb"] = "|".join(sub_codes)

    # Parse bounding box from query params → boundary JSON
    lat_max = _get_first(query_params, "lat-max")
    lat_min = _get_first(query_params, "lat-min")
    lon_max = _get_first(query_params, "lon-max")
    lon_min = _get_first(query_params, "lon-min")

    if all([lat_max, lat_min, lon_max, lon_min]):
        boundary = [[
            {"lat": float(lat_max), "lng": float(lon_min)},
            {"lat": float(lat_max), "lng": float(lon_max)},
            {"lat": float(lat_min), "lng": float(lon_max)},
            {"lat": float(lat_min), "lng": float(lon_min)},
        ]]
        base_params["boundary"] = json.dumps(boundary)

    # Create one param dict per category type
    result = []
    for tc in type_codes:
        params = {**base_params, "category_type_cb": tc}
        result.append(params)

    return result


def _get_first(params: dict, key: str) -> Optional[str]:
    """Get first value from query params dict."""
    values = params.get(key, [])
    return values[0] if values else None


def build_sreality_detail_url(sreality_id: int, seo: Optional[dict] = None) -> str:
    """
    Build a human-readable Sreality detail URL.

    Args:
        sreality_id: The hash_id of the listing.
        seo: Optional SEO dict from the API with category codes and locality.

    Returns:
        URL like https://www.sreality.cz/detail/prodej/ostatni/garaze/praha/4291276876
    """
    if seo:
        type_map = {1: "prodej", 2: "pronajem", 3: "drazby"}
        main_map = {1: "byt", 2: "dum", 3: "pozemek", 4: "komercni", 5: "ostatni"}
        sub_map = {34: "garaz", 52: "garazove-stani"}

        category_type = type_map.get(seo.get("category_type_cb"), "prodej")
        category_main = main_map.get(seo.get("category_main_cb"), "ostatni")
        category_sub = sub_map.get(seo.get("category_sub_cb"), "garaz")
        locality = seo.get("locality", "ceska-republika").replace(" ", "-")

        return f"https://www.sreality.cz/detail/{category_type}/{category_main}/{category_sub}/{locality}/{sreality_id}"

    return f"https://www.sreality.cz/detail/-/-/-/-/{sreality_id}"
