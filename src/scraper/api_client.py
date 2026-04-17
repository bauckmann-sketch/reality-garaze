"""Sreality REST API client with anti-bot measures."""

import logging
import random
import time
from typing import Iterator

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.config import get_settings

logger = logging.getLogger(__name__)

# Realistic User-Agent rotation pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
]


class SrealityApiClient:
    """Client for the Sreality REST API with rate limiting and retry logic."""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.sreality_api_base
        self._client = None

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client with realistic headers."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=30.0,
                follow_redirects=True,
                headers=self._get_headers(),
            )
        return self._client

    def _get_headers(self) -> dict:
        """Generate realistic browser headers."""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.sreality.cz/",
            "Origin": "https://www.sreality.cz",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

    def _delay(self):
        """Random delay between requests to avoid detection."""
        delay = random.uniform(
            self.settings.request_delay_min,
            self.settings.request_delay_max,
        )
        logger.debug(f"Waiting {delay:.1f}s before next request...")
        time.sleep(delay)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=5, max=60),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)),
        before_sleep=lambda retry_state: logger.warning(
            f"Request failed, retrying in {retry_state.next_action.sleep}s... "
            f"(attempt {retry_state.attempt_number})"
        ),
    )
    def _request(self, endpoint: str, params: dict = None) -> dict:
        """Make a single API request with retry logic."""
        client = self._get_client()
        # Rotate User-Agent on each request
        client.headers["User-Agent"] = random.choice(USER_AGENTS)

        url = f"{self.base_url}{endpoint}"
        logger.debug(f"GET {url} params={params}")

        response = client.get(url, params=params)

        # Don't retry on 410 Gone — listing was removed, not a transient error
        if response.status_code == 410:
            return None

        response.raise_for_status()

        return response.json()

    def fetch_listings(self, api_params: dict) -> Iterator[dict]:
        """
        Fetch all listings for given API parameters, handling pagination.

        Args:
            api_params: Dict of API query params (from url_parser).

        Yields:
            Individual estate dicts from the API response.
        """
        page = 1
        per_page = self.settings.sreality_per_page
        total_fetched = 0

        while True:
            params = {**api_params, "per_page": per_page, "page": page}

            self._delay()
            data = self._request("/estates", params=params)

            result_size = data.get("result_size", 0)
            estates = data.get("_embedded", {}).get("estates", [])

            if not estates:
                logger.info(f"No more listings on page {page}. Total fetched: {total_fetched}")
                break

            for estate in estates:
                total_fetched += 1
                yield estate

            logger.info(
                f"Page {page}: fetched {len(estates)} listings "
                f"({total_fetched}/{result_size} total)"
            )

            # Check if we've fetched all results
            if total_fetched >= result_size:
                break

            page += 1

        logger.info(f"Finished fetching. Total listings: {total_fetched}")

    def fetch_listing_detail(self, sreality_id: int) -> dict:
        """
        Fetch detailed info for a single listing.

        Args:
            sreality_id: The hash_id of the listing.

        Returns:
            Full estate detail dict from the API.
        """
        self._delay()
        return self._request(f"/estates/{sreality_id}")

    def close(self):
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
