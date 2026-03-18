"""Aggregate all news fetchers."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.news.base import NewsBatch, NewsCategory
from src.news.korean import fetch_korean_news
from src.news.world import fetch_world_news
from src.news.tech import fetch_tech_news

logger = logging.getLogger(__name__)


def fetch_all_news() -> dict[NewsCategory, NewsBatch]:
    """Fetch news from all categories in parallel.

    Returns a dict mapping each category to its NewsBatch.
    """
    fetchers = {
        NewsCategory.KOREAN: fetch_korean_news,
        NewsCategory.WORLD: fetch_world_news,
        NewsCategory.TECH: fetch_tech_news,
    }

    results: dict[NewsCategory, NewsBatch] = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_category = {
            executor.submit(fn): category
            for category, fn in fetchers.items()
        }

        for future in as_completed(future_to_category):
            category = future_to_category[future]
            try:
                items = future.result()
                results[category] = NewsBatch(category=category, items=items)
                logger.info(
                    "Fetched %d items for %s",
                    len(items),
                    category.display_name,
                )
            except Exception:
                logger.error("Failed to fetch %s", category.value, exc_info=True)
                results[category] = NewsBatch(category=category, items=[])

    return results
