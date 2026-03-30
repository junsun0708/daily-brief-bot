from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class NewsCategory(str, Enum):
    KOREAN = "korean"       # 국내뉴스
    WORLD = "world"         # 세계뉴스
    TECH = "tech"           # IT뉴스
    RANKING = "ranking"     # 랭킹뉴스
    SOCIAL = "social"       # 소셜 미디어/커뮤니티

    @property
    def display_name(self) -> str:
        names = {
            "korean": "🇰🇷 국내뉴스",
            "world": "🌍 세계뉴스",
            "tech": "💻 IT뉴스",
            "ranking": "🔥 랭킹뉴스",
            "social": "💬 소셜/커뮤니티",
        }
        return names[self.value]


@dataclass
class NewsItem:
    title: str
    summary: str
    url: str
    source: str
    category: NewsCategory
    published_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "source": self.source,
            "category": self.category.value,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }


@dataclass
class NewsBatch:
    """A collection of news items grouped by category."""
    category: NewsCategory
    items: list[NewsItem] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        return self.category.display_name

    def top(self, n: int = 5) -> list[NewsItem]:
        """Return top N items."""
        return self.items[:n]
