"""소셜 미디어 및 한국 커뮤니티 포스트 fetcher."""
from __future__ import annotations

import logging

import requests
from bs4 import BeautifulSoup

from src.news.base import NewsCategory, NewsItem

logger = logging.getLogger(__name__)

REDDIT_HOT_URL = "https://www.reddit.com/r/all/hot/.json?limit=10"
REQUEST_TIMEOUT = 15


def fetch_reddit_posts(max_items: int = 5) -> list[NewsItem]:
    """Fetch popular posts from Reddit."""
    items: list[NewsItem] = []
    
    try:
        response = requests.get(
            REDDIT_HOT_URL,
            headers={"User-Agent": "DailyBriefBot/1.0"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        
        for post in data.get("data", {}).get("children", [])[:max_items]:
            post_data = post.get("data", {})
            title = post_data.get("title", "")
            url = post_data.get("url", "")
            score = post_data.get("score", 0)
            num_comments = post_data.get("num_comments", 0)
            subreddit = post_data.get("subreddit", "reddit")
            
            if title:
                items.append(
                    NewsItem(
                        title=title,
                        summary=f"👍 {score} • 💬 {num_comments}",
                        url=url,
                        source=f"r/{subreddit}",
                        category=NewsCategory.SOCIAL,
                    )
                )

    except Exception:
        logger.warning("Failed to fetch Reddit posts", exc_info=True)

    return items


def fetch_facebook_trending(max_items: int = 5) -> list[NewsItem]:
    """Fetch trending topics from Facebook."""
    items: list[NewsItem] = []

    try:
        # Facebook trending page (public)
        response = requests.get(
            "https://www.facebook.com/trending/",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Facebook often blocks scraping, fallback to meta tags
            titles = soup.select('meta[property="og:title"]')

            for meta in titles[:max_items]:
                content = meta.get("content", "")
                if content and len(content) > 10:
                    items.append(
                        NewsItem(
                            title=content[:100],
                            summary="Facebook 인기 주제",
                            url="https://www.facebook.com/trending/",
                            source="Facebook",
                            category=NewsCategory.SOCIAL,
                        )
                    )
                    
    except Exception:
        logger.warning("Failed to fetch Facebook trending", exc_info=True)
    
    return items


def fetch_twitter_posts(max_items: int = 5) -> list[NewsItem]:
    """Fetch popular posts from Twitter/X using Nitter."""
    items: list[NewsItem] = []
    
    try:
        nitter_instances = [
            "https://nitter.net",
            "https://nitter.privacydev.net",
            "https://nitter.poast.org",
        ]
        
        for instance in nitter_instances:
            try:
                response = requests.get(
                    f"{instance}/explore",
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=10,
                )
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    tweets = soup.select('div.tweet-content')[:max_items]
                    
                    for tweet in tweets:
                        text = tweet.get_text(strip=True)
                        if text and len(text) > 10:
                            items.append(
                                NewsItem(
                                    title=text[:100],
                                    summary="Twitter/X 트렌드",
                                    url=f"{instance}/explore",
                                    source="Twitter/X",
                                    category=NewsCategory.SOCIAL,
                                )
                            )
                    break
            except Exception:
                continue
                
    except Exception:
        logger.warning("Failed to fetch Twitter posts", exc_info=True)
    
    return items


def fetch_dcinside(max_items: int = 5) -> list[NewsItem]:
    """Fetch popular posts from DC Inside."""
    items: list[NewsItem] = []
    
    galleries = ["bestof_bestof", "baseball_new7", "football_stock", "it_news", "humor_best"]
    
    for gallery in galleries[:1]:  # 1개 갤러리만
        try:
            response = requests.get(
                f"https://gall.dcinside.com/board/lists/?id={gallery}",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                titles = soup.select('.gall_tit a')[:max_items]
                
                for title in titles:
                    text = title.get_text(strip=True)
                    if text and len(text) > 5:
                        items.append(
                            NewsItem(
                                title=text[:100],
                                summary=f"디시인사이드 {gallery}",
                                url=f"https://gall.dcinside.com/board/lists/?id={gallery}",
                                source="디시인사이드",
                                category=NewsCategory.SOCIAL,
                            )
                        )
        except Exception:
            continue
    
    return items


def fetch_fmkorea(max_items: int = 5) -> list[NewsItem]:
    """Fetch popular posts from FMKorea."""
    items: list[NewsItem] = []
    
    try:
        response = requests.get(
            "https://www.fmkorea.com/hot",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            titles = soup.select('h3.title a')[:max_items]
            
            for title in titles:
                text = title.get_text(strip=True)
                if text and len(text) > 5:
                    href = title.get("href", "")
                    items.append(
                        NewsItem(
                            title=text[:100],
                            summary="에펨코리아 인기글",
                            url=f"https://www.fmkorea.com{href}" if href else "https://www.fmkorea.com/hot",
                            source="에펨코리아",
                            category=NewsCategory.SOCIAL,
                        )
                    )
    except Exception:
        logger.warning("Failed to fetch FMKorea", exc_info=True)
    
    return items


def fetch_opentalk(max_items: int = 5) -> list[NewsItem]:
    """Fetch popular posts from Opentalk."""
    items: list[NewsItem] = []
    
    try:
        response = requests.get(
            "https://www.opentalk.org/ranking",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            titles = soup.select('div.RankingItem_title__1wL-9 a')[:max_items]
            
            for title in titles:
                text = title.get_text(strip=True)
                if text and len(text) > 5:
                    items.append(
                        NewsItem(
                            title=text[:100],
                            summary="오픈톡 인기 주제",
                            url="https://www.opentalk.org/ranking",
                            source="오픈톡",
                            category=NewsCategory.SOCIAL,
                        )
                    )
    except Exception:
        logger.warning("Failed to fetch Opentalk", exc_info=True)
    
    return items


def fetch_ruliweb(max_items: int = 5) -> list[NewsItem]:
    """Fetch popular posts from Ruliweb."""
    items: list[NewsItem] = []
    
    try:
        response = requests.get(
            "https://m.ruliweb.com/best/hit",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            titles = soup.select('a.subject')[:max_items]
            
            for title in titles:
                text = title.get_text(strip=True)
                if text and len(text) > 5:
                    href = title.get("href", "")
                    items.append(
                        NewsItem(
                            title=text[:100],
                            summary="루리웹 베스트",
                            url=f"https://m.ruliweb.com{href}" if href else "https://m.ruliweb.com/best/hit",
                            source="루리웹",
                            category=NewsCategory.SOCIAL,
                        )
                    )
    except Exception:
        logger.warning("Failed to fetch Ruliweb", exc_info=True)
    
    return items


def fetch_natepann(max_items: int = 5) -> list[NewsItem]:
    """Fetch popular posts from Nate Pann."""
    items: list[NewsItem] = []
    
    try:
        response = requests.get(
            "https://pann.nate.com/hot",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            titles = soup.select('div.tit a')[:max_items]
            
            for title in titles:
                text = title.get_text(strip=True)
                if text and len(text) > 5:
                    items.append(
                        NewsItem(
                            title=text[:100],
                            summary="네이트판 인기글",
                            url="https://pann.nate.com/hot",
                            source="네이트판",
                            category=NewsCategory.SOCIAL,
                        )
                    )
    except Exception:
        logger.warning("Failed to fetch Nate Pann", exc_info=True)
    
    return items


def fetch_social_posts(max_items: int = 5) -> list[NewsItem]:
    """Fetch posts from all social media and Korean communities - each source 5 items."""
    items: list[NewsItem] = []
    
    # International: Reddit - 5개
    try:
        items.extend(fetch_reddit_posts(max_items))
    except Exception:
        pass
    
    # Twitter - 5개 (자주 timeout)
    # try:
    #     items.extend(fetch_twitter_posts(max_items))
    # except Exception:
    #     pass
    
    # Facebook - 5개 (자주 실패)
    # try:
    #     items.extend(fetch_facebook_trending(max_items))
    # except Exception:
    #     pass
    
    # Korean communities - each 5개씩 (Opentalk 제외 - 자주 timeout)
    try:
        items.extend(fetch_dcinside(max_items))
    except Exception:
        pass
    
    try:
        items.extend(fetch_fmkorea(max_items))
    except Exception:
        pass
    
    # try:
    #     items.extend(fetch_opentalk(max_items))  #timeout 자주 발생
    # except Exception:
    #     pass
    
    try:
        items.extend(fetch_ruliweb(max_items))
    except Exception:
        pass
    
    try:
        items.extend(fetch_natepann(max_items))
    except Exception:
        pass
    
    return items
