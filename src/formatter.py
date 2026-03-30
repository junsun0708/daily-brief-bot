"""Slack Block Kit message formatter for daily briefing."""
from __future__ import annotations

from src.generator import BriefingContent
from src.news.base import NewsCategory


def _header_block(text: str) -> dict:
    return {
        "type": "header",
        "text": {"type": "plain_text", "text": text, "emoji": True},
    }


SLACK_SECTION_TEXT_LIMIT = 3000


def _truncate(text: str, limit: int = SLACK_SECTION_TEXT_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _section_block(text: str) -> dict:
    return {
        "type": "section",
        "text": {"type": "mrkdwn", "text": _truncate(text)},
    }


def _divider() -> dict:
    return {"type": "divider"}


def _context_block(text: str) -> dict:
    return {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": text}],
    }


def format_briefing(content: BriefingContent) -> dict:
    """Format BriefingContent into Slack Block Kit message payload.

    Returns a dict with 'blocks' and 'text' (fallback) keys.
    """
    blocks: list[dict] = []

    # Header
    blocks.append(_header_block(f"📋 데일리 브리핑 — {content.date}"))
    blocks.append(_divider())

    # Greeting
    blocks.append(_section_block(content.greeting))
    blocks.append(_divider())

    # News sections
    category_order = [NewsCategory.KOREAN, NewsCategory.WORLD, NewsCategory.TECH, NewsCategory.RANKING, NewsCategory.SOCIAL]
    for category in category_order:
        summary = content.news_summaries.get(category, "뉴스를 불러오지 못했어요.")
        blocks.append(_section_block(f"*{category.display_name}*"))
        blocks.append(_section_block(summary))
        blocks.append(_divider())

    # Daily topic
    blocks.append(_section_block(f"*🌱 오늘의 일상주제*"))
    blocks.append(_section_block(content.daily_topic))
    blocks.append(_divider())

    # Small talk
    blocks.append(_section_block(f"*💬 스몰토크*"))
    blocks.append(_section_block(content.small_talk))
    blocks.append(_divider())

    # Footer
    blocks.append(
        _context_block("🤖 _Daily Brief Bot — 매일 아침 자동 발송됩니다_")
    )

    # Fallback text (for notifications)
    fallback_text = f"📋 데일리 브리핑 — {content.date}"

    return {
        "blocks": blocks,
        "text": fallback_text,
    }
