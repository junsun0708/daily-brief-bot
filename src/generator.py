"""LLM-based content generator for briefing.

Uses Claude CLI (subscription) or Anthropic API:
1. Summarize news items per category (Korean)
2. Generate 일상주제 (daily lifestyle topic)
3. Generate 스몰토크 (small talk conversation starter)
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime

from src.config import Config
from src.news.base import NewsBatch, NewsCategory

logger = logging.getLogger(__name__)


@dataclass
class BriefingContent:
    date: str
    news_summaries: dict[NewsCategory, str]
    daily_topic: str
    small_talk: str
    greeting: str


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
    0: "월요일", 1: "화요일", 2: "수요일", 3: "목요일",
    4: "금요일", 5: "토요일", 6: "일요일",
}


def _format_news_for_prompt(batch: NewsBatch, max_items: int = 10) -> str:
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

    def __init__(self, config: Config) -> None:
        self._api_key = config.anthropic_api_key
        self._model = config.anthropic_model
        self._use_cli = not self._api_key
        
        if self._use_cli:
            logger.info("Using Claude CLI subscription (no API key)")
        else:
            import anthropic
            from anthropic.types import TextBlock
            self._client = anthropic.Anthropic(api_key=self._api_key)
            self._text_block = TextBlock

    def _chat_via_cli(self, user_prompt: str) -> str:
        prompt = f"""System: {SYSTEM_PROMPT}

User: {user_prompt}

Respond with JSON only in this format:
{{
    "response": "your response here"
}}"""

        try:
            result = subprocess.run(
                ["claude", "-p", "--output-format", "json"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                logger.error(f"Claude CLI error: {result.stderr}")
                return "Claude CLI 오류가 발생했습니다."
            
            output = result.stdout.strip()
            try:
                parsed = json.loads(output)
                result_data = parsed.get("result", "")
                
                try:
                    result_json = json.loads(result_data)
                    return result_json.get("response", result_data)
                except json.JSONDecodeError:
                    return result_data
            except json.JSONDecodeError:
                return output
                
        except subprocess.TimeoutExpired:
            return "Claude CLI timeout"
        except Exception as e:
            logger.error(f"Claude CLI error: {e}")
            return f"Claude CLI 오류: {str(e)}"

    def _chat_via_api(self, user_prompt: str) -> str:
        import anthropic
        from anthropic.types import TextBlock
        
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        block = response.content[0]
        if not isinstance(block, TextBlock):
            return ""
        return block.text

    def _chat(self, user_prompt: str) -> str:
        if self._use_cli:
            return self._chat_via_cli(user_prompt)
        return self._chat_via_api(user_prompt)

    def summarize_news(self, batch: NewsBatch) -> str:
        if not batch.items:
            return "오늘은 해당 카테고리의 뉴스를 가져오지 못했어요 😅"
        prompt = NEWS_SUMMARY_PROMPT.format(
            category_name=batch.display_name,
            news_items=_format_news_for_prompt(batch),
        )
        return self._chat(prompt)

    def generate_daily_topic(self, date: datetime) -> str:
        date_str = date.strftime("%Y년 %m월 %d일")
        weekday = WEEKDAY_NAMES[date.weekday()]
        return self._chat(DAILY_TOPIC_PROMPT.format(date=f"{date_str} {weekday}"))

    def generate_small_talk(self, date: datetime) -> str:
        date_str = date.strftime("%Y년 %m월 %d일")
        weekday = WEEKDAY_NAMES[date.weekday()]
        return self._chat(SMALL_TALK_PROMPT.format(date=f"{date_str} {weekday}"))

    def generate_greeting(self, date: datetime) -> str:
        date_str = date.strftime("%Y년 %m월 %d일")
        weekday = WEEKDAY_NAMES[date.weekday()]
        return self._chat(GREETING_PROMPT.format(date=date_str, weekday=weekday))

    def generate_briefing(
        self,
        news_batches: dict[NewsCategory, NewsBatch],
        now: datetime | None = None,
    ) -> BriefingContent:
        if now is None:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo("Asia/Seoul"))

        date_str = now.strftime("%Y년 %m월 %d일 (%a)")
        logger.info("Generating briefing for %s", date_str)

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
