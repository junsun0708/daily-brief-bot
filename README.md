# Daily Brief Bot

매일 아침 뉴스 브리핑을 Slack 프라이빗 채널로 자동 발송하는 봇.

Anthropic Claude가 뉴스를 요약하고, 일상주제와 스몰토크를 생성합니다.

## 브리핑 구성

| 섹션 | 소스 |
|------|------|
| 🇰🇷 국내뉴스 | 연합뉴스, 한겨레, 조선일보, KBS RSS |
| 🌍 세계뉴스 | BBC, Reuters, NPR, Al Jazeera RSS |
| 💻 IT뉴스 | Hacker News API, TechCrunch, The Verge, Ars Technica |
| 🌱 일상주제 | Claude가 날짜/계절 기반 생성 |
| 💬 스몰토크 | Claude가 가벼운 대화 주제 생성 |

## 설치

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 설정

```bash
cp .env.example .env
```

`.env` 파일에 실제 값 입력:

| 변수 | 설명 |
|------|------|
| `SLACK_BOT_TOKEN` | Slack Bot OAuth Token (`xoxb-...`) |
| `SLACK_CHANNEL_ID` | 프라이빗 채널 ID (`C0XXXXX`) |
| `ANTHROPIC_API_KEY` | Anthropic API Key (`sk-ant-...`) |
| `ANTHROPIC_MODEL` | 모델명 (기본: `claude-sonnet-4-20250514`) |
| `SEND_TIME` | 발송 시각 (기본: `08:00`) |
| `TIMEZONE` | 타임존 (기본: `Asia/Seoul`) |

### Slack 설정

1. [Slack App 생성](https://api.slack.com/apps) → Bot Token Scopes: `chat:write`, `channels:read`, `groups:read`
2. 워크스페이스에 앱 설치
3. 프라이빗 채널에서 `/invite @봇이름`
4. 채널 세부정보에서 Channel ID 복사

## 실행

```bash
source .venv/bin/activate

# Slack 연결 테스트
python -m src.main --test

# 터미널 미리보기 (Slack 미발송)
python -m src.main --dry-run

# 즉시 1회 발송
python -m src.main --now

# 스케줄러 (매일 SEND_TIME에 자동 발송)
python -m src.main
```

## Docker

```bash
docker compose up -d
```

## 아키텍처

```
뉴스 수집 (RSS/API, 병렬) → Claude 요약/생성 → Slack Block Kit 포맷 → 프라이빗 채널 발송
```
