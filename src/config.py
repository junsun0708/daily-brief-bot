from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def _find_env_file() -> Path | None:
    """Walk up from CWD to find .env file."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        env_path = parent / ".env"
        if env_path.is_file():
            return env_path
    return None


@dataclass(frozen=True)
class Config:
    # Slack
    slack_bot_token: str
    slack_channel_id: str

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"

    # Schedule
    send_time: str = "08:00"  # HH:MM format
    timezone: str = "Asia/Seoul"

    # Optional
    news_api_key: str | None = None

    @property
    def send_hour(self) -> int:
        return int(self.send_time.split(":")[0])

    @property
    def send_minute(self) -> int:
        return int(self.send_time.split(":")[1])


def load_config() -> Config:
    """Load configuration from environment variables."""
    env_file = _find_env_file()
    if env_file:
        load_dotenv(env_file)

    slack_bot_token = os.environ.get("SLACK_BOT_TOKEN", "")
    slack_channel_id = os.environ.get("SLACK_CHANNEL_ID", "")
    openai_api_key = os.environ.get("OPENAI_API_KEY", "")

    missing: list[str] = []
    if not slack_bot_token:
        missing.append("SLACK_BOT_TOKEN")
    if not slack_channel_id:
        missing.append("SLACK_CHANNEL_ID")
    if not openai_api_key:
        missing.append("OPENAI_API_KEY")

    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Copy .env.example to .env and fill in your values."
        )

    return Config(
        slack_bot_token=slack_bot_token,
        slack_channel_id=slack_channel_id,
        openai_api_key=openai_api_key,
        openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        send_time=os.environ.get("SEND_TIME", "08:00"),
        timezone=os.environ.get("TIMEZONE", "Asia/Seoul"),
        news_api_key=os.environ.get("NEWS_API_KEY"),
    )
