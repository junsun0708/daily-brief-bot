"""국내뉴스 fetcher — Naver News RSS + 주요 한국 언론사 RSS."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser

from src.news.base import NewsCategory, NewsItem

logger = logging.getLogger(__name__)

# Naver News RSS feeds by section
KOREAN_RSS_FEEDS: list[dict[str, str]] = [
    {"name": "연합뉴스", "url": "https://www.yna.co.kr/RSS/news.xml"},
    {"name": "한겨레", "url": "https://www.hani.co.kr/rss/"},
    {"name": "조선일보", "url": "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml"},
    {"name": "KBS뉴스", "url": "https://news.kbs.co.kr/api/getRss.html?rss_id=headline"},
]

FEED_REQUEST_TIMEOUT = 15
FEED_USER_AGENT = "DailyBriefBot/1.0 (+https://github.com/daily-brief-bot)"


def _parse_published(entry: dict) -> datetime | None:
    """Extract publication date from an RSS entry."""
    for key in ("published", "updated", "created"):
        raw = entry.get(key)
        if raw:
            try:
                return parsedate_to_datetime(raw)
            except Exception:
                pass
    return None


def fetch_korean_news(max_per_source: int = 5) -> list[NewsItem]:
    """Fetch Korean domestic news from RSS feeds."""
    items: list[NewsItem] = []

    for feed_info in KOREAN_RSS_FEEDS:
        try:
            feed = feedparser.parse(
                feed_info["url"],
                request_headers={"User-Agent": FEED_USER_AGENT},
            )
            for entry in feed.entries[:max_per_source]:
                summary = entry.get("summary", entry.get("description", ""))
                # Strip HTML tags from summary
                if "<" in summary:
                    import re
                    summary = re.sub(r"<[^>]+>", "", summary).strip()
                # Truncate long summaries
                if len(summary) > 200:
                    summary = summary[:200] + "..."

                items.append(
                    NewsItem(
                        title=entry.get("title", "제목 없음"),
                        summary=summary,
                        url=entry.get("link", ""),
                        source=feed_info["name"],
                        category=NewsCategory.KOREAN,
                        published_at=_parse_published(entry),
                    )
                )
        except Exception:
            logger.warning("Failed to fetch from %s", feed_info["name"], exc_info=True)

    # Sort by published date (newest first), items without date go last
    items.sort(
        key=lambda x: x.published_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return items
