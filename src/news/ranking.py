"""랭킹뉴스 fetcher — 네이버 뉴스 직접 파싱."""
from __future__ import annotations

import logging

import requests
from bs4 import BeautifulSoup

from src.news.base import NewsCategory, NewsItem

logger = logging.getLogger(__name__)

NAVER_RANKING_URL = "https://news.naver.com/main/ranking/popularDay.naver"
REQUEST_TIMEOUT = 15


def fetch_ranking_news(max_items: int = 5) -> list[NewsItem]:
    """Fetch ranking news from Naver News."""
    items: list[NewsItem] = []
    
    try:
        response = requests.get(
            NAVER_RANKING_URL,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "ko-KR,ko;q=0.9",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        ranking_items = soup.select('ul.ranking_list li a')
        
        if not ranking_items:
            ranking_items = soup.select('div.ranking_box a')
        
        if not ranking_items:
            ranking_items = soup.select('a[href*="article"]')
        
        for idx, a_tag in enumerate(ranking_items[:max_items]):
            title = a_tag.get_text(strip=True)
            href = a_tag.get('href', '')
            
            if title and href and len(title) > 5:
                if not href.startswith('http'):
                    href = 'https://news.naver.com' + href
                    
                items.append(
                    NewsItem(
                        title=title,
                        summary=f"실시간 인기 뉴스 {idx + 1}위",
                        url=href,
                        source="네이버 뉴스",
                        category=NewsCategory.RANKING,
                    )
                )
                
    except Exception:
        logger.warning("Failed to fetch ranking news", exc_info=True)
    
    return items
