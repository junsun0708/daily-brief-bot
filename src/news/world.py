"""세계뉴스 fetcher — International news RSS feeds."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser

from src.news.base import NewsCategory, NewsItem

logger = logging.getLogger(__name__)

WORLD_RSS_FEEDS: list[dict[str, str]] = [
    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "Reuters", "url": "https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best"},
    {"name": "NPR World", "url": "https://feeds.npr.org/1004/rss.xml"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
]

FEED_REQUEST_TIMEOUT = 15
FEED_USER_AGENT = "DailyBriefBot/1.0 (+https://github.com/daily-brief-bot)"


def _parse_published(entry: dict) -> datetime | None:
    for key in ("published", "updated", "created"):
        raw = entry.get(key)
        if raw:
            try:
                return parsedate_to_datetime(raw)
            except Exception:
                pass
    return None


def fetch_world_news(max_per_source: int = 5) -> list[NewsItem]:
    """Fetch international news from RSS feeds."""
    items: list[NewsItem] = []

    for feed_info in WORLD_RSS_FEEDS:
        try:
            feed = feedparser.parse(
                feed_info["url"],
                request_headers={"User-Agent": FEED_USER_AGENT},
            )
            for entry in feed.entries[:max_per_source]:
                summary = entry.get("summary", entry.get("description", ""))
                if "<" in summary:
                    import re
                    summary = re.sub(r"<[^>]+>", "", summary).strip()
                if len(summary) > 200:
                    summary = summary[:200] + "..."

                items.append(
                    NewsItem(
                        title=entry.get("title", "No title"),
                        summary=summary,
                        url=entry.get("link", ""),
                        source=feed_info["name"],
                        category=NewsCategory.WORLD,
                        published_at=_parse_published(entry),
                    )
                )
        except Exception:
            logger.warning("Failed to fetch from %s", feed_info["name"], exc_info=True)

    items.sort(
        key=lambda x: x.published_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return items
