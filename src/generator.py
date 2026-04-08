"""LLM-based content generator for briefing."""

from __future__ import annotations

import json
import logging
import os
import random
import subprocess
from dataclasses import dataclass
from datetime import datetime

from src.config import Config
from src.news.base import NewsBatch, NewsCategory

logger = logging.getLogger(__name__)


TRIVIA_FACTS = [
    "다리가 2개인 사람이 전 세계에서 약 10%밖에 없다고 합니다. 그래서 엘리베이터에서 만지면 행운이 온대요!",
    "한국에서는 쌀이主食이지만 일본에서는 빵이主食 이에요. 하지만 한국 사람들이 일본에서寿司를 더 좋아한다고 하네요.",
    "손을 비비는 것만으로도 불안감을 줄일 수 있어요. 신경과학에서 확인했대요.",
    "하품은 뇌를 냉각시켜주는 역할을 합니다. 그래서 하품이 떠올라하면 더 집중되는 거예요.",
    "하루에 평균 6~8개의 꿈을 꾸지만 대부분 기억 못한다고 합니다. 그래도 좋은 꿈꾸면 기분이 좋아요.",
]

FUN_JOKES = [
    "왜 피곤한 사람이工作效率이 높을까요? 왜냐하면 일하면 피곤해지는 법!",
    "어제 저녁에 가장 강한 음식을 먹었는데...바로 오뎅이야! 차갑지만 따듯한 마음이 떠올라서 추천해요.",
    "회사에서 내 위치가 어디인지 알려달라고 했더니... 바로 컴퓨터 앞이래요!",
    "친구가 나한테 물었어, '가장 가까운 별이 어디야?' 답은 바로 네 눈이야! 내가 바로 너의 별이니까.",
    "다음에 한국 가면 어디 가야 해? 바로 남대문시장! 남대문에 다 있어.",
]

COOL_STORIES = [
    "한번 회사에 지각했는데, 마침 사장님도 늦게 오셨습니다. 서로 눈치 보면서 같이 커피 마시다가... 그대로 사장님이랑 커피 타임이 되었습니다. 오히려 좋은 인연이 됐어요!",
    "처음 해외 여행 갔을 때, 현지어로 택시 물어봤는데 제대로听不懂 못했어요. 그래서 핸드폰 지도 보여줬더니 그냥 저도 모르는 표정이었죠. 결국 걸어서 호텔 찾았는데그 방법으로居然 3시간 걸렸습니다. 하지만 그 길에서 제일 맛있는 길거리 음식도 먹고, 정말 아름다운 추억이 되었습니다!",
]


@dataclass
class BriefingContent:
    date: str
    news_summaries: dict[NewsCategory, str]
    daily_topic: str
    small_talk: str
    greeting: str
    trivia: str
    joke: str
    story: str


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
- JSON이나 코드블록 없이 일반 텍스트로만 응답

뉴스 목록:
{news_items}"""


DAILY_TOPIC_PROMPT = """다음은 오늘의 랭킹뉴스, 국내뉴스, 세계뉴스 목록입니다.
이 뉴스들을 참고해서 스몰토크 주제를 만들어주세요.

규칙:
- 뉴스 내용과 관련된 재미있는 대화 주제를 3개 만들어주세요
- 각 주제는 1~2문장으로 작성
- 질문 형태로 끝나면 좋음
- 직장인이 공감하고 나눌 수 있는 주제
- 각 주제 뒤에 줄바꿈(엔터)을 추가해서 구분
- 적절한 이모지 사용
- JSON이나 코드블록 없이 일반 텍스트로만 응답

뉴스 목록:
{news_items}"""


SMALL_TALK_PROMPT = """오늘은 {date} ({weekday})입니다.
동료와 나눌 수 있는 스몰토크 주제를 하나 만들어주세요.

규칙:
- 다음 중 무작위로 하나 선택: 음식/취미/문화/트렌드/여행/영화/스포츠/책/게임/가전/패션/건강/경제/직장
- 선택한 주제에 대해 구체적이고 독특한 내용 포함
- 질문 형태로 끝나면 좋음
- 2~3문장
- 너무 개인적이지 않은 주제
- 적절한 이모지 사용
- 매일 다른 주제 선택
- JSON이나 코드블록 없이 일반 텍스트로만 응답"""


GREETING_PROMPT = """오늘은 {date} ({weekday})입니다.
아침 브리핑에 어울리는 짧은 인사말을 만들어주세요.

규칙:
- 1~2문장
- 요일/날씨/계절감을 반영
- 밝고 긍정적인 톤
- 이모지 1~2개 사용
- JSON이나 코드블록 없이 일반 텍스트로만 응답"""


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
            
            if "```json" in output:
                output = output.split("```json")[1].split("```")[0]
            elif "```" in output:
                output = output.split("```")[1].split("```")[0]
            
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
            return "오늘은 해당 지역의 뉴스를 가져오지 못했어요."
        prompt = NEWS_SUMMARY_PROMPT.format(
            category_name=batch.display_name,
            news_items=_format_news_for_prompt(batch),
        )
        return self._chat(prompt)

    def generate_daily_topic(
        self,
        ranking_batch: NewsBatch,
        korean_batch: NewsBatch,
        world_batch: NewsBatch,
    ) -> str:
        combined_news = []
        combined_news.extend(ranking_batch.top(3))
        combined_news.extend(korean_batch.top(3))
        combined_news.extend(world_batch.top(3))
        
        news_items = _format_news_for_prompt(
            NewsBatch(category=NewsCategory.KOREAN, items=combined_news),
            max_items=9
        )
        return self._chat(DAILY_TOPIC_PROMPT.format(news_items=news_items))

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
        for category in [NewsCategory.KOREAN, NewsCategory.WORLD, NewsCategory.TECH, NewsCategory.RANKING, NewsCategory.SOCIAL]:
            batch = news_batches.get(category, NewsBatch(category=category))
            if batch.items:
                news_summaries[category] = self.summarize_news(batch)
                logger.info("Summarized %s", category.display_name)

        greeting = self.generate_greeting(now)
        
        ranking_batch = news_batches.get(NewsCategory.RANKING, NewsBatch(category=NewsCategory.RANKING))
        korean_batch = news_batches.get(NewsCategory.KOREAN, NewsBatch(category=NewsCategory.KOREAN))
        world_batch = news_batches.get(NewsCategory.WORLD, NewsBatch(category=NewsCategory.WORLD))
        daily_topic = self.generate_daily_topic(ranking_batch, korean_batch, world_batch)
        
        small_talk = self.generate_small_talk(now)

        trivia = random.choice(TRIVIA_FACTS)
        joke = random.choice(FUN_JOKES)
        story = random.choice(COOL_STORIES)

        logger.info("Briefing generation complete")

        return BriefingContent(
            date=date_str,
            news_summaries=news_summaries,
            daily_topic=daily_topic,
            small_talk=small_talk,
            greeting=greeting,
            trivia=trivia,
            joke=joke,
            story=story,
        )