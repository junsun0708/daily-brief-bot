"""LLM-based content generator for briefing.

Uses OpenAI to:
1. Summarize news items per category (Korean)
2. Generate 일상주제 (daily lifestyle topic)
3. Generate 스몰토크 (small talk conversation starter)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from openai import OpenAI

from src.config import Config
from src.news.base import NewsBatch, NewsCategory

logger = logging.getLogger(__name__)


@dataclass
class BriefingContent:
    """Generated briefing content ready for formatting."""
    date: str
    news_summaries: dict[NewsCategory, str]  # category -> summarized text
    daily_topic: str     # 일상주제
    small_talk: str      # 스몰토크
    greeting: str        # 인사말


SYSTEM_PROMPT = """당신은 매일 아침 브리핑을 전달하는 친근하고 전문적인 한국어 뉴스 큐레이터입니다.
말투는 친근하지만 정보는 정확하게 전달합니다. ~요체를 사용합니다.
이모지를 적절히 활용하여 가독성을 높입니다."""


NEWS_SUMMARY_PROMPT = """다음은 오늘의 {category_name} 뉴스 목록입니다.
이 뉴스들을 한국어로 3~5개의 핵심 뉴스로 요약해주세요.

요약 규칙:
- 각 뉴스는 한 줄로 요약 (제목 + 핵심 내용)
- 불릿 포인트(•) 사용
- 중요도 순으로 정렬
- 원문 URL이 있으면 괄호 안에 포함
- 한국어로 작성 (영문 뉴스도 번역)

뉴스 목록:
{news_items}"""


DAILY_TOPIC_PROMPT = """오늘은 {date}입니다.
오늘 날짜에 맞는 재미있는 일상 주제를 하나 만들어주세요.

규칙:
- 계절, 날짜, 요일 등을 고려
- 가볍고 긍정적인 주제
- 2~3문장으로 작성
- 직장인이 공감할 수 있는 내용
- 적절한 이모지 사용"""


SMALL_TALK_PROMPT = """오늘은 {date}입니다.
동료와 나눌 수 있는 스몰토크 주제를 하나 만들어주세요.

규칙:
- 가벼운 대화 주제 (음식, 취미, 문화, 트렌드 등)
- 질문 형태로 끝나면 좋음
- 2~3문장
- 너무 개인적이지 않은 주제
- 적절한 이모지 사용"""


GREETING_PROMPT = """오늘은 {date} ({weekday})입니다.
아침 브리핑에 어울리는 짧은 인사말을 만들어주세요.

규칙:
- 1~2문장
- 요일/날씨/계절감을 반영
- 밝고 긍정적인 톤
- 이모지 1~2개 사용"""


WEEKDAY_NAMES = {
    0: "월요일",
    1: "화요일",
    2: "수요일",
    3: "목요일",
    4: "금요일",
    5: "토요일",
    6: "일요일",
}


def _format_news_for_prompt(batch: NewsBatch, max_items: int = 10) -> str:
    """Format news items into a string for the LLM prompt."""
    lines: list[str] = []
    for item in batch.top(max_items):
        line = f"- [{item.source}] {item.title}"
        if item.summary:
            line += f"\n  요약: {item.summary}"
        if item.url:
            line += f"\n  URL: {item.url}"
        lines.append(line)
    return "\n".join(lines) if lines else "(뉴스를 가져오지 못했습니다)"


class BriefingGenerator:
    """Generates briefing content using OpenAI."""

    def __init__(self, config: Config) -> None:
        self._client = OpenAI(api_key=config.openai_api_key)
        self._model = config.openai_model

    def _chat(self, user_prompt: str) -> str:
        """Send a chat completion request."""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=1000,
        )
        return response.choices[0].message.content or ""

    def summarize_news(self, batch: NewsBatch) -> str:
        """Summarize a batch of news items."""
        if not batch.items:
            return "오늘은 해당 카테고리의 뉴스를 가져오지 못했어요 😅"

        prompt = NEWS_SUMMARY_PROMPT.format(
            category_name=batch.display_name,
            news_items=_format_news_for_prompt(batch),
        )
        return self._chat(prompt)

    def generate_daily_topic(self, date: datetime) -> str:
        """Generate a daily lifestyle topic."""
        date_str = date.strftime("%Y년 %m월 %d일")
        weekday = WEEKDAY_NAMES[date.weekday()]
        prompt = DAILY_TOPIC_PROMPT.format(date=f"{date_str} {weekday}")
        return self._chat(prompt)

    def generate_small_talk(self, date: datetime) -> str:
        """Generate a small talk topic."""
        date_str = date.strftime("%Y년 %m월 %d일")
        weekday = WEEKDAY_NAMES[date.weekday()]
        prompt = SMALL_TALK_PROMPT.format(date=f"{date_str} {weekday}")
        return self._chat(prompt)

    def generate_greeting(self, date: datetime) -> str:
        """Generate a morning greeting."""
        date_str = date.strftime("%Y년 %m월 %d일")
        weekday = WEEKDAY_NAMES[date.weekday()]
        prompt = GREETING_PROMPT.format(date=date_str, weekday=weekday)
        return self._chat(prompt)

    def generate_briefing(
        self,
        news_batches: dict[NewsCategory, NewsBatch],
        now: datetime | None = None,
    ) -> BriefingContent:
        """Generate the full briefing content."""
        if now is None:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo("Asia/Seoul"))

        date_str = now.strftime("%Y년 %m월 %d일 (%a)")

        logger.info("Generating briefing for %s", date_str)

        # Generate all content
        news_summaries: dict[NewsCategory, str] = {}
        for category in [NewsCategory.KOREAN, NewsCategory.WORLD, NewsCategory.TECH]:
            batch = news_batches.get(category, NewsBatch(category=category))
            news_summaries[category] = self.summarize_news(batch)
            logger.info("Summarized %s", category.display_name)

        greeting = self.generate_greeting(now)
        daily_topic = self.generate_daily_topic(now)
        small_talk = self.generate_small_talk(now)

        logger.info("Briefing generation complete")

        return BriefingContent(
            date=date_str,
            news_summaries=news_summaries,
            daily_topic=daily_topic,
            small_talk=small_talk,
            greeting=greeting,
        )
