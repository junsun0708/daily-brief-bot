"""IT뉴스 fetcher — Hacker News API + tech RSS feeds."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import feedparser
import requests

from src.news.base import NewsCategory, NewsItem

logger = logging.getLogger(__name__)

HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"

TECH_RSS_FEEDS: list[dict[str, str]] = [
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index"},
]


def _fetch_hacker_news(max_items: int = 10) -> list[NewsItem]:
    """Fetch top stories from Hacker News API (free, no key needed)."""
    items: list[NewsItem] = []
    try:
        resp = requests.get(HN_TOP_STORIES_URL, timeout=10)
        resp.raise_for_status()
        story_ids = resp.json()[:max_items]

        for story_id in story_ids:
            try:
                item_resp = requests.get(HN_ITEM_URL.format(story_id), timeout=5)
                item_resp.raise_for_status()
                story = item_resp.json()

                if not story or story.get("type") != "story":
                    continue

                url = story.get("url", f"https://news.ycombinator.com/item?id={story_id}")
                published = None
                if story.get("time"):
                    published = datetime.fromtimestamp(story["time"], tz=timezone.utc)

                items.append(
                    NewsItem(
                        title=story.get("title", ""),
                        summary=f"Points: {story.get('score', 0)} | Comments: {story.get('descendants', 0)}",
                        url=url,
                        source="Hacker News",
                        category=NewsCategory.TECH,
                        published_at=published,
                    )
                )
            except Exception:
                logger.debug("Failed to fetch HN item %s", story_id, exc_info=True)
    except Exception:
        logger.warning("Failed to fetch Hacker News top stories", exc_info=True)

    return items


def _fetch_tech_rss(max_per_source: int = 5) -> list[NewsItem]:
    """Fetch tech news from RSS feeds."""
    items: list[NewsItem] = []
    from email.utils import parsedate_to_datetime

    for feed_info in TECH_RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries[:max_per_source]:
                summary = entry.get("summary", entry.get("description", ""))
                if "<" in summary:
                    import re
                    summary = re.sub(r"<[^>]+>", "", summary).strip()
                if len(summary) > 200:
                    summary = summary[:200] + "..."

                published = None
                for key in ("published", "updated"):
                    raw = entry.get(key)
                    if raw:
                        try:
                            published = parsedate_to_datetime(raw)
                            break
                        except Exception:
                            pass

                items.append(
                    NewsItem(
                        title=entry.get("title", "No title"),
                        summary=summary,
                        url=entry.get("link", ""),
                        source=feed_info["name"],
                        category=NewsCategory.TECH,
                        published_at=published,
                    )
                )
        except Exception:
            logger.warning("Failed to fetch from %s", feed_info["name"], exc_info=True)

    return items


def fetch_tech_news(max_hn: int = 10, max_rss_per_source: int = 5) -> list[NewsItem]:
    """Fetch all tech news from Hacker News + RSS feeds."""
    items = _fetch_hacker_news(max_hn) + _fetch_tech_rss(max_rss_per_source)
    items.sort(
        key=lambda x: x.published_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return items
