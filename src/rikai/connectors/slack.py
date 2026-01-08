"""
Slack Connector for RikaiOS.

Receives messages from Slack via Events API and sends them to Tama.
Supports text and images (multimodal).
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any

import httpx

from rikai.connectors.base import (
    ConnectorConfig,
    ConnectorMode,
    IngestResult,
    WebhookConnector,
)
from rikai.connectors.messaging import get_media_type

logger = logging.getLogger(__name__)


@dataclass
class SlackConnectorConfig(ConnectorConfig):
    """Configuration for Slack connector."""

    bot_token: str | None = None  # xoxb-...
    app_token: str | None = None  # xapp-... for Socket Mode (optional)
    signing_secret: str | None = None  # For webhook verification
    channels: list[str] | None = None  # If set, only process these channels
    respond_to_all: bool = True  # Respond to all messages

    def __post_init__(self):
        # Load from env if not provided
        if not self.bot_token:
            self.bot_token = os.getenv("SLACK_BOT_TOKEN")
        if not self.app_token:
            self.app_token = os.getenv("SLACK_APP_TOKEN")
        if not self.signing_secret:
            self.signing_secret = os.getenv("SLACK_SIGNING_SECRET")


class SlackConnector(WebhookConnector):
    """
    Slack connector - receives messages via Events API webhook.

    Messages are sent to Tama for processing. Tama decides
    what to remember and how to respond.
    """

    name = "slack"
    mode = ConnectorMode.PUSH
    description = "Slack bot connector for Tama"

    def __init__(
        self,
        config: SlackConnectorConfig | None = None,
        tama_agent=None,
    ) -> None:
        super().__init__(config or SlackConnectorConfig())
        self._config: SlackConnectorConfig = self._config
        self._tama = tama_agent
        self._http_client: httpx.AsyncClient | None = None
        self._bot_user_id: str | None = None

    @property
    def bot_token(self) -> str | None:
        return self._config.bot_token

    async def setup(self) -> None:
        """Validate configuration and get bot info."""
        if not self._config.bot_token:
            raise RuntimeError(
                "SLACK_BOT_TOKEN not set. Create a Slack App at https://api.slack.com/apps"
            )

        self._http_client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self._config.bot_token}"}
        )

        # Get bot user ID (to ignore our own messages)
        try:
            resp = await self._http_client.get("https://slack.com/api/auth.test")
            data = resp.json()
            if data.get("ok"):
                self._bot_user_id = data.get("user_id")
                logger.info(f"Slack connector initialized as bot: {self._bot_user_id}")
            else:
                logger.warning(f"Could not get bot info: {data.get('error')}")
        except Exception as e:
            logger.warning(f"Could not get bot info: {e}")

    async def teardown(self) -> None:
        """Clean up HTTP client."""
        if self._http_client:
            await self._http_client.aclose()

    def get_webhook_path(self) -> str:
        """Return the webhook endpoint path."""
        return "/webhooks/slack"

    async def sync(self) -> IngestResult:
        """Not used for webhook-based connector."""
        return IngestResult(success=True)

    def set_tama_agent(self, tama_agent) -> None:
        """Set the Tama agent for message processing."""
        self._tama = tama_agent

    async def handle_webhook(self, payload: dict[str, Any]) -> IngestResult | dict:
        """
        Handle incoming Slack Events API webhook.

        Args:
            payload: Slack event payload

        Returns:
            IngestResult or dict (for URL verification challenge)
        """
        # Handle URL verification challenge
        if payload.get("type") == "url_verification":
            return {"challenge": payload.get("challenge")}

        # Handle events
        if payload.get("type") == "event_callback":
            event = payload.get("event", {})
            return await self._handle_event(event)

        return IngestResult(success=True)

    async def _handle_event(self, event: dict[str, Any]) -> IngestResult:
        """Handle a Slack event."""
        event_type = event.get("type")

        if event_type == "message":
            return await self._handle_message(event)
        elif event_type == "file_shared":
            # File shared in channel
            return await self._handle_file_shared(event)

        return IngestResult(success=True)

    async def _handle_message(self, event: dict[str, Any]) -> IngestResult:
        """Handle a message event."""
        if not self._tama:
            logger.error("Tama agent not set")
            return IngestResult(success=False, errors=["Tama agent not configured"])

        try:
            # Ignore bot messages and our own messages
            if event.get("bot_id") or event.get("user") == self._bot_user_id:
                return IngestResult(success=True)

            # Ignore message subtypes (edits, deletes, etc.) except file_share
            subtype = event.get("subtype")
            if subtype and subtype not in ["file_share"]:
                return IngestResult(success=True)

            channel_id = event.get("channel")
            user_id = event.get("user")
            text = event.get("text", "")
            thread_ts = event.get("thread_ts") or event.get("ts")
            ts = event.get("ts")
            files = event.get("files", [])

            # Check if channel is allowed
            if self._config.channels and channel_id not in self._config.channels:
                logger.debug(f"Ignoring message from non-allowed channel: {channel_id}")
                return IngestResult(success=True)

            # Get channel and user info
            channel_name = await self._get_channel_name(channel_id)
            username = await self._get_username(user_id)

            # Process files (images)
            if files:
                for file_info in files:
                    if file_info.get("mimetype", "").startswith("image/"):
                        # Download and process image
                        image_bytes = await self._download_file(file_info)
                        if image_bytes:
                            response = await self._tama.chat_with_image(
                                image_bytes=image_bytes,
                                text=text,
                                image_media_type=file_info.get("mimetype", "image/png"),
                                platform="slack",
                                sender=username,
                            )
                            break
                else:
                    # No image files, process as text
                    if text:
                        response = await self._tama.chat(text)
                    else:
                        return IngestResult(success=True)
            elif text:
                response = await self._tama.chat(text)
            else:
                return IngestResult(success=True)

            # Send Tama's response back to Slack (in thread)
            if response.message and self._config.respond_to_all:
                await self._send_message(channel_id, response.message, thread_ts=thread_ts)

            return IngestResult(
                success=True,
                documents_created=1 if response.metadata.get("tool_results") else 0,
                metadata={
                    "channel_id": channel_id,
                    "ts": ts,
                    "platform": "slack",
                },
            )

        except Exception as e:
            logger.error(f"Error processing Slack message: {e}")
            return IngestResult(success=False, errors=[str(e)])

    async def _handle_file_shared(self, event: dict[str, Any]) -> IngestResult:
        """Handle file_shared event (for files shared without message)."""
        # Usually handled via message event with subtype file_share
        return IngestResult(success=True)

    async def _download_file(self, file_info: dict[str, Any]) -> bytes | None:
        """Download a file from Slack."""
        if not self._http_client:
            return None

        url = file_info.get("url_private_download") or file_info.get("url_private")
        if not url:
            return None

        try:
            resp = await self._http_client.get(url)
            resp.raise_for_status()
            return resp.content

        except Exception as e:
            logger.error(f"Failed to download Slack file: {e}")
            return None

    async def _send_message(
        self,
        channel: str,
        text: str,
        thread_ts: str | None = None,
    ) -> bool:
        """Send a message to Slack."""
        if not self._http_client:
            return False

        try:
            payload = {
                "channel": channel,
                "text": text,
            }
            if thread_ts:
                payload["thread_ts"] = thread_ts

            resp = await self._http_client.post(
                "https://slack.com/api/chat.postMessage",
                json=payload,
            )
            data = resp.json()

            if not data.get("ok"):
                logger.error(f"Failed to send Slack message: {data.get('error')}")
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False

    async def _get_channel_name(self, channel_id: str) -> str:
        """Get channel name from ID."""
        if not self._http_client:
            return channel_id

        try:
            resp = await self._http_client.get(
                "https://slack.com/api/conversations.info",
                params={"channel": channel_id},
            )
            data = resp.json()
            if data.get("ok"):
                return data.get("channel", {}).get("name", channel_id)
        except Exception:
            pass

        return channel_id

    async def _get_username(self, user_id: str) -> str:
        """Get username from user ID."""
        if not self._http_client:
            return user_id

        try:
            resp = await self._http_client.get(
                "https://slack.com/api/users.info",
                params={"user": user_id},
            )
            data = resp.json()
            if data.get("ok"):
                user = data.get("user", {})
                return user.get("real_name") or user.get("name", user_id)
        except Exception:
            pass

        return user_id
