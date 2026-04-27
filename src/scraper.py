"""
scraper.py

YouTube history page scraping helpers.
"""
import asyncio
import logging
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

from playwright.async_api import Page, Response

logger = logging.getLogger(__name__)


async def handle_response(response: Response, subtitle_store: Dict[str, Any]) -> None:
    """
    Capture timedtext responses that happen naturally while browsing.

    This is intentionally passive. Subtitle fetching that requires opening watch
    pages or extra YouTube tokens should be handled by a later post-processing
    step, not in the history scraper.
    """
    if "timedtext" not in response.url or response.request.method != "GET":
        return

    try:
        if response.status != 200:
            return

        json_data = await response.json()
        parsed_url = urlparse(response.url)
        video_id = parse_qs(parsed_url.query).get("v", [None])[0]

        if video_id:
            subtitle_store[video_id] = json_data
            logger.info("Captured subtitle response for video %s.", video_id)
    except Exception as e:
        logger.warning("Failed to parse timedtext response: %s", e)


async def scroll_to_load_more(page: Page, max_scrolls: int = 5) -> None:
    """
    Scroll the YouTube history page to load more records.
    """
    logger.info("Start scrolling history page, max_scrolls=%s.", max_scrolls)
    for i in range(max_scrolls):
        await page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight);")
        await page.wait_for_timeout(2000)
        logger.info("Finished scroll %s/%s.", i + 1, max_scrolls)


async def extract_history_items(page: Page) -> List[Dict[str, str]]:
    """
    Extract visible history video title and URL pairs from the current page.
    """
    logger.info("Extracting history items from DOM.")

    video_elements = await page.locator("a#video-title").all()
    results: List[Dict[str, str]] = []

    for el in video_elements:
        href = await el.get_attribute("href")
        if not href:
            continue

        title = await el.get_attribute("title")
        if not title:
            title = await el.text_content()

        if title and href:
            full_url = f"https://www.youtube.com{href}" if href.startswith("/") else href
            results.append(
                {
                    "title": title.strip(),
                    "url": full_url,
                }
            )

    logger.info("Extracted %s history items.", len(results))
    return results
