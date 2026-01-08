"""
Telegram Connector for RikaiOS.

Receives messages from Telegram and sends them to Tama.
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
class TelegramConnectorConfig(ConnectorConfig):
    """Configuration for Telegram connector."""

    bot_token: str | None = None
    allowed_chats: list[int] | None = None  # If set, only process these chats
    respond_to_all: bool = True  # Respond to all messages, not just mentions

    def __post_init__(self):
        # Load from env if not provided
        if not self.bot_token:
            self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")


class TelegramConnector(WebhookConnector):
    """
    Telegram connector - receives messages via webhook.

    Messages are sent to Tama for processing. Tama decides
    what to remember and how to respond.
    """

    name = "telegram"
    mode = ConnectorMode.PUSH
    description = "Telegram bot connector for Tama"

    def __init__(
        self,
        config: TelegramConnectorConfig | None = None,
        tama_agent=None,
    ) -> None:
        super().__init__(config or TelegramConnectorConfig())
        self._config: TelegramConnectorConfig = self._config
        self._tama = tama_agent
        self._http_client: httpx.AsyncClient | None = None

    @property
    def bot_token(self) -> str | None:
        return self._config.bot_token

    async def setup(self) -> None:
        """Validate configuration."""
        if not self._config.bot_token:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN not set. Get one from @BotFather on Telegram."
            )
        self._http_client = httpx.AsyncClient()
        logger.info("Telegram connector initialized")

    async def teardown(self) -> None:
        """Clean up HTTP client."""
        if self._http_client:
            await self._http_client.aclose()

    def get_webhook_path(self) -> str:
        """Return the webhook endpoint path."""
        return "/webhooks/telegram"

    async def sync(self) -> IngestResult:
        """Not used for webhook-based connector."""
        return IngestResult(success=True)

    def set_tama_agent(self, tama_agent) -> None:
        """Set the Tama agent for message processing."""
        self._tama = tama_agent

    async def handle_webhook(self, payload: dict[str, Any]) -> IngestResult:
        """
        Handle incoming Telegram webhook.

        Args:
            payload: Telegram Update object

        Returns:
            IngestResult
        """
        if not self._tama:
            logger.error("Tama agent not set")
            return IngestResult(success=False, errors=["Tama agent not configured"])

        try:
            # Parse the update
            message = payload.get("message") or payload.get("edited_message")
            if not message:
                # Not a message update (could be callback, etc.)
                return IngestResult(success=True)

            chat_id = message.get("chat", {}).get("id")
            chat_name = message.get("chat", {}).get("title") or message.get("chat", {}).get("username", "Direct")
            sender = message.get("from", {}).get("username") or message.get("from", {}).get("first_name", "Unknown")
            message_id = message.get("message_id")

            # Check if chat is allowed
            if self._config.allowed_chats and chat_id not in self._config.allowed_chats:
                logger.debug(f"Ignoring message from non-allowed chat: {chat_id}")
                return IngestResult(success=True)

            # Extract content
            text = message.get("text") or message.get("caption")
            photo = message.get("photo")  # Array of PhotoSize, sorted by size

            # Process the message
            if photo:
                # Get largest photo
                largest_photo = photo[-1]
                file_id = largest_photo.get("file_id")

                # Download the image
                image_bytes = await self._download_file(file_id)
                if image_bytes:
                    response = await self._tama.chat_with_image(
                        image_bytes=image_bytes,
                        text=text,
                        image_media_type="image/jpeg",  # Telegram compresses to JPEG
                        platform="telegram",
                        sender=sender,
                    )
                else:
                    # Couldn't download, process text only
                    if text:
                        response = await self._tama.chat(text)
                    else:
                        return IngestResult(success=True)
            elif text:
                response = await self._tama.chat(text)
            else:
                # No text or photo
                return IngestResult(success=True)

            # Send Tama's response back to Telegram
            if response.message and self._config.respond_to_all:
                await self._send_message(chat_id, response.message, reply_to=message_id)

            return IngestResult(
                success=True,
                documents_created=1 if response.metadata.get("tool_results") else 0,
                metadata={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "platform": "telegram",
                },
            )

        except Exception as e:
            logger.error(f"Error processing Telegram webhook: {e}")
            return IngestResult(success=False, errors=[str(e)])

    async def _download_file(self, file_id: str) -> bytes | None:
        """Download a file from Telegram."""
        if not self._http_client or not self._config.bot_token:
            return None

        try:
            # Get file path
            url = f"https://api.telegram.org/bot{self._config.bot_token}/getFile"
            resp = await self._http_client.get(url, params={"file_id": file_id})
            resp.raise_for_status()
            data = resp.json()

            if not data.get("ok"):
                logger.error(f"Failed to get file info: {data}")
                return None

            file_path = data.get("result", {}).get("file_path")
            if not file_path:
                return None

            # Download file
            download_url = f"https://api.telegram.org/file/bot{self._config.bot_token}/{file_path}"
            resp = await self._http_client.get(download_url)
            resp.raise_for_status()
            return resp.content

        except Exception as e:
            logger.error(f"Failed to download Telegram file: {e}")
            return None

    async def _send_message(
        self,
        chat_id: int,
        text: str,
        reply_to: int | None = None,
    ) -> bool:
        """Send a message to Telegram."""
        if not self._http_client or not self._config.bot_token:
            return False

        try:
            url = f"https://api.telegram.org/bot{self._config.bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }
            if reply_to:
                payload["reply_to_message_id"] = reply_to

            resp = await self._http_client.post(url, json=payload)
            resp.raise_for_status()
            return True

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    async def set_webhook(self, webhook_url: str) -> bool:
        """
        Set the Telegram webhook URL.

        Call this after deploying to set up the webhook.

        Args:
            webhook_url: Full URL including the path (e.g., https://your-domain.com/webhooks/telegram)

        Returns:
            True if successful
        """
        if not self._http_client:
            self._http_client = httpx.AsyncClient()

        if not self._config.bot_token:
            raise RuntimeError("Bot token not configured")

        try:
            url = f"https://api.telegram.org/bot{self._config.bot_token}/setWebhook"
            resp = await self._http_client.post(url, json={"url": webhook_url})
            resp.raise_for_status()
            data = resp.json()

            if data.get("ok"):
                logger.info(f"Telegram webhook set to: {webhook_url}")
                return True
            else:
                logger.error(f"Failed to set webhook: {data}")
                return False

        except Exception as e:
            logger.error(f"Failed to set Telegram webhook: {e}")
            return False

    async def delete_webhook(self) -> bool:
        """Remove the Telegram webhook (for switching to polling)."""
        if not self._http_client:
            self._http_client = httpx.AsyncClient()

        if not self._config.bot_token:
            raise RuntimeError("Bot token not configured")

        try:
            url = f"https://api.telegram.org/bot{self._config.bot_token}/deleteWebhook"
            resp = await self._http_client.post(url)
            resp.raise_for_status()
            return True

        except Exception as e:
            logger.error(f"Failed to delete Telegram webhook: {e}")
            return False
