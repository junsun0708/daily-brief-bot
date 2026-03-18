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

    def validate_channel(self) -> bool:
        """Validate bot has access to the configured channel.

        Uses conversations.info to verify the channel exists and the bot
        is a member. This confirms the target is the correct private channel.
        """
        try:
            response = self._client.conversations_info(channel=self._channel_id)
            channel = response.get("channel", {})
            channel_name = channel.get("name", "unknown")
            is_private = channel.get("is_private", False)
            is_member = channel.get("is_member", False)

            if not is_member:
                logger.error(
                    "Bot is NOT a member of channel #%s (%s). "
                    "Please invite the bot to the channel first.",
                    channel_name,
                    self._channel_id,
                )
                return False

            privacy = "private" if is_private else "public"
            logger.info(
                "Channel validated — #%s (%s, %s, member=True)",
                channel_name,
                self._channel_id,
                privacy,
            )
            return True
        except SlackApiError as e:
            logger.error(
                "Channel validation failed: %s (channel: %s)",
                e.response["error"],
                self._channel_id,
            )
            return False

    def test_connection(self) -> bool:
        """Test the Slack connection and channel access."""
        try:
            response = self._client.auth_test()
            logger.info(
                "Slack connection OK — bot: %s, team: %s",
                response.get("user"),
                response.get("team"),
            )
        except SlackApiError as e:
            logger.error("Slack auth test failed: %s", e.response["error"])
            return False

        return self.validate_channel()
