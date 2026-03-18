"""Slack client for sending briefing messages."""
from __future__ import annotations

import logging

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from src.config import Config

logger = logging.getLogger(__name__)


class SlackBriefingClient:
    """Send formatted messages to a Slack channel."""

    def __init__(self, config: Config) -> None:
        self._client = WebClient(token=config.slack_bot_token)
        self._channel_id = config.slack_channel_id

    def send_message(self, payload: dict) -> bool:
        """Send a Block Kit message to the configured channel.

        Args:
            payload: Dict with 'blocks' and 'text' keys.

        Returns:
            True if message was sent successfully.
        """
        try:
            response = self._client.chat_postMessage(
                channel=self._channel_id,
                blocks=payload["blocks"],
                text=payload.get("text", "Daily Briefing"),
                unfurl_links=False,
                unfurl_media=False,
            )
            logger.info(
                "Message sent to channel %s (ts: %s)",
                self._channel_id,
                response.get("ts"),
            )
            return True
        except SlackApiError as e:
            logger.error(
                "Slack API error: %s (response: %s)",
                e.response["error"],
                e.response,
            )
            return False
        except Exception:
            logger.exception("Unexpected error sending Slack message")
            return False

    def test_connection(self) -> bool:
        """Test the Slack connection by calling auth.test."""
        try:
            response = self._client.auth_test()
            logger.info(
                "Slack connection OK — bot: %s, team: %s",
                response.get("user"),
                response.get("team"),
            )
            return True
        except SlackApiError as e:
            logger.error("Slack auth test failed: %s", e.response["error"])
            return False
