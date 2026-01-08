"""
Tests for Telegram connector.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rikai.connectors.telegram import TelegramConnector, TelegramConnectorConfig


class TestTelegramConnectorConfig:
    """Test Telegram connector configuration."""

    def test_default_config(self):
        """Test default configuration."""
        with patch.dict("os.environ", {}, clear=True):
            config = TelegramConnectorConfig()
            assert config.bot_token is None
            assert config.allowed_chats is None
            assert config.respond_to_all is True

    def test_config_from_env(self):
        """Test loading config from environment."""
        with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test-token"}):
            config = TelegramConnectorConfig()
            assert config.bot_token == "test-token"

    def test_explicit_config(self):
        """Test explicit configuration."""
        config = TelegramConnectorConfig(
            bot_token="my-token",
            allowed_chats=[123, 456],
            respond_to_all=False,
        )
        assert config.bot_token == "my-token"
        assert config.allowed_chats == [123, 456]
        assert config.respond_to_all is False


class TestTelegramConnector:
    """Test Telegram connector."""

    @pytest.fixture
    def mock_tama(self):
        """Create mock Tama agent."""
        tama = AsyncMock()
        tama.chat.return_value = MagicMock(
            message="Got it!",
            metadata={},
        )
        tama.chat_with_image.return_value = MagicMock(
            message="I see the screenshot!",
            metadata={},
        )
        return tama

    @pytest.fixture
    def connector(self, mock_tama):
        """Create connector with mock Tama."""
        config = TelegramConnectorConfig(bot_token="test-token")
        conn = TelegramConnector(config=config, tama_agent=mock_tama)
        return conn

    def test_webhook_path(self, connector):
        """Test webhook path."""
        assert connector.get_webhook_path() == "/webhooks/telegram"

    @pytest.mark.asyncio
    async def test_setup_without_token(self):
        """Test setup fails without token."""
        config = TelegramConnectorConfig(bot_token=None)
        connector = TelegramConnector(config=config)

        with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
            await connector.setup()

    @pytest.mark.asyncio
    async def test_handle_text_message(self, connector, mock_tama):
        """Test handling text message."""
        await connector.setup()

        payload = {
            "message": {
                "message_id": 123,
                "chat": {"id": 456, "title": "Test Chat"},
                "from": {"username": "testuser"},
                "text": "Hello Tama!",
            }
        }

        result = await connector.handle_webhook(payload)

        assert result.success is True
        mock_tama.chat.assert_called_once_with("Hello Tama!")

    @pytest.mark.asyncio
    async def test_handle_photo_message(self, connector, mock_tama):
        """Test handling photo message."""
        await connector.setup()

        # Mock the file download
        connector._download_file = AsyncMock(return_value=b"fake_image_bytes")

        payload = {
            "message": {
                "message_id": 123,
                "chat": {"id": 456, "title": "Test Chat"},
                "from": {"username": "testuser"},
                "caption": "Check this out",
                "photo": [
                    {"file_id": "small", "width": 100, "height": 100},
                    {"file_id": "large", "width": 800, "height": 600},
                ],
            }
        }

        result = await connector.handle_webhook(payload)

        assert result.success is True
        mock_tama.chat_with_image.assert_called_once()
        # Verify it used the largest photo
        call_args = mock_tama.chat_with_image.call_args
        assert call_args.kwargs["platform"] == "telegram"

    @pytest.mark.asyncio
    async def test_ignore_non_message(self, connector, mock_tama):
        """Test ignoring non-message updates."""
        await connector.setup()

        payload = {
            "callback_query": {"id": "123", "data": "button_click"}
        }

        result = await connector.handle_webhook(payload)

        assert result.success is True
        mock_tama.chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_ignore_non_allowed_chat(self, mock_tama):
        """Test ignoring messages from non-allowed chats."""
        config = TelegramConnectorConfig(
            bot_token="test-token",
            allowed_chats=[111, 222],
        )
        connector = TelegramConnector(config=config, tama_agent=mock_tama)
        await connector.setup()

        payload = {
            "message": {
                "message_id": 123,
                "chat": {"id": 999},  # Not in allowed list
                "from": {"username": "testuser"},
                "text": "Hello!",
            }
        }

        result = await connector.handle_webhook(payload)

        assert result.success is True
        mock_tama.chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_tama_agent(self):
        """Test handling webhook without Tama agent."""
        config = TelegramConnectorConfig(bot_token="test-token")
        connector = TelegramConnector(config=config, tama_agent=None)
        await connector.setup()

        payload = {
            "message": {
                "message_id": 123,
                "chat": {"id": 456},
                "from": {"username": "testuser"},
                "text": "Hello!",
            }
        }

        result = await connector.handle_webhook(payload)

        assert result.success is False
        assert "Tama agent not configured" in result.errors


class TestTelegramWebhookSetup:
    """Test webhook setup methods."""

    @pytest.mark.asyncio
    async def test_set_webhook(self):
        """Test setting Telegram webhook."""
        config = TelegramConnectorConfig(bot_token="test-token")
        connector = TelegramConnector(config=config)

        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await connector.set_webhook("https://example.com/webhooks/telegram")

            assert result is True
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_webhook(self):
        """Test deleting Telegram webhook."""
        config = TelegramConnectorConfig(bot_token="test-token")
        connector = TelegramConnector(config=config)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await connector.delete_webhook()

            assert result is True
