from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _find_env_file() -> Path | None:
    current = Path.cwd()
    for parent in [current, *current.parents]:
        env_path = parent / ".env"
        if env_path.is_file():
            return env_path
    return None


@dataclass(frozen=True)
class Config:
    slack_bot_token: str
    slack_channel_id: str
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-20250514"
    send_time: str = "08:00"
    timezone: str = "Asia/Seoul"
    news_api_key: str | None = None

    @property
    def send_hour(self) -> int:
        return int(self.send_time.split(":")[0])

    @property
    def send_minute(self) -> int:
        return int(self.send_time.split(":")[1])


def load_config() -> Config:
    env_file = _find_env_file()
    if env_file:
        load_dotenv(env_file)

    slack_bot_token = os.environ.get("SLACK_BOT_TOKEN", "")
    slack_channel_id = os.environ.get("SLACK_CHANNEL_ID", "")
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    missing: list[str] = []
    if not slack_bot_token:
        missing.append("SLACK_BOT_TOKEN")
    if not slack_channel_id:
        missing.append("SLACK_CHANNEL_ID")

    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Copy .env.example to .env and fill in your values."
        )

    return Config(
        slack_bot_token=slack_bot_token,
        slack_channel_id=slack_channel_id,
        anthropic_api_key=anthropic_api_key,
        anthropic_model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        send_time=os.environ.get("SEND_TIME", "08:00"),
        timezone=os.environ.get("TIMEZONE", "Asia/Seoul"),
        news_api_key=os.environ.get("NEWS_API_KEY"),
    )
