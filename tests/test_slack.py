"""
Tests for Slack connector.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rikai.connectors.slack import SlackConnector, SlackConnectorConfig


class TestSlackConnectorConfig:
    """Test Slack connector configuration."""

    def test_default_config(self):
        """Test default configuration."""
        with patch.dict("os.environ", {}, clear=True):
            config = SlackConnectorConfig()
            assert config.bot_token is None
            assert config.app_token is None
            assert config.channels is None
            assert config.respond_to_all is True

    def test_config_from_env(self):
        """Test loading config from environment."""
        with patch.dict("os.environ", {
            "SLACK_BOT_TOKEN": "xoxb-test",
            "SLACK_APP_TOKEN": "xapp-test",
        }):
            config = SlackConnectorConfig()
            assert config.bot_token == "xoxb-test"
            assert config.app_token == "xapp-test"

    def test_explicit_config(self):
        """Test explicit configuration."""
        config = SlackConnectorConfig(
            bot_token="xoxb-my-token",
            channels=["C123", "C456"],
            respond_to_all=False,
        )
        assert config.bot_token == "xoxb-my-token"
        assert config.channels == ["C123", "C456"]
        assert config.respond_to_all is False


class TestSlackConnector:
    """Test Slack connector."""

    @pytest.fixture
    def mock_tama(self):
        """Create mock Tama agent."""
        tama = AsyncMock()
        tama.chat.return_value = MagicMock(
            message="Got it!",
            metadata={},
        )
        tama.chat_with_image.return_value = MagicMock(
            message="I see the image!",
            metadata={},
        )
        return tama

    @pytest.fixture
    def connector(self, mock_tama):
        """Create connector with mock Tama."""
        config = SlackConnectorConfig(bot_token="xoxb-test-token")
        conn = SlackConnector(config=config, tama_agent=mock_tama)
        return conn

    def test_webhook_path(self, connector):
        """Test webhook path."""
        assert connector.get_webhook_path() == "/webhooks/slack"

    @pytest.mark.asyncio
    async def test_setup_without_token(self):
        """Test setup fails without token."""
        config = SlackConnectorConfig(bot_token=None)
        connector = SlackConnector(config=config)

        with pytest.raises(RuntimeError, match="SLACK_BOT_TOKEN"):
            await connector.setup()

    @pytest.mark.asyncio
    async def test_url_verification(self, connector):
        """Test URL verification challenge."""
        payload = {
            "type": "url_verification",
            "challenge": "test-challenge-123",
        }

        result = await connector.handle_webhook(payload)

        assert isinstance(result, dict)
        assert result["challenge"] == "test-challenge-123"

    @pytest.mark.asyncio
    async def test_handle_text_message(self, connector, mock_tama):
        """Test handling text message."""
        # Mock setup
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "user_id": "U123BOT"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.post.return_value = MagicMock(json=lambda: {"ok": True})
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            await connector.setup()

        payload = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "channel": "C123",
                "user": "U456",
                "text": "Hello Tama!",
                "ts": "1234567890.123456",
            },
        }

        result = await connector.handle_webhook(payload)

        assert result.success is True
        mock_tama.chat.assert_called_once_with("Hello Tama!")

    @pytest.mark.asyncio
    async def test_ignore_bot_messages(self, connector, mock_tama):
        """Test ignoring bot messages."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"ok": True, "user_id": "U123BOT"}
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            await connector.setup()

        payload = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "channel": "C123",
                "bot_id": "B123",  # This is a bot message
                "text": "Bot message",
                "ts": "1234567890.123456",
            },
        }

        result = await connector.handle_webhook(payload)

        assert result.success is True
        mock_tama.chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_ignore_own_messages(self, connector, mock_tama):
        """Test ignoring own messages."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"ok": True, "user_id": "UBOT123"}
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            await connector.setup()

        payload = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "channel": "C123",
                "user": "UBOT123",  # Same as bot user
                "text": "My own message",
                "ts": "1234567890.123456",
            },
        }

        result = await connector.handle_webhook(payload)

        assert result.success is True
        mock_tama.chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_ignore_non_allowed_channel(self, mock_tama):
        """Test ignoring messages from non-allowed channels."""
        config = SlackConnectorConfig(
            bot_token="xoxb-test",
            channels=["C111", "C222"],
        )
        connector = SlackConnector(config=config, tama_agent=mock_tama)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"ok": True, "user_id": "UBOT"}
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            await connector.setup()

        payload = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "channel": "C999",  # Not in allowed list
                "user": "U456",
                "text": "Hello!",
                "ts": "1234567890.123456",
            },
        }

        result = await connector.handle_webhook(payload)

        assert result.success is True
        mock_tama.chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_file_message(self, connector, mock_tama):
        """Test handling message with file (image)."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"ok": True, "user_id": "UBOT"}
            mock_response.content = b"fake_image_bytes"
            mock_client.get.return_value = mock_response
            mock_client.post.return_value = MagicMock(json=lambda: {"ok": True})
            mock_client_class.return_value = mock_client

            await connector.setup()

        payload = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "subtype": "file_share",
                "channel": "C123",
                "user": "U456",
                "text": "Check this screenshot",
                "ts": "1234567890.123456",
                "files": [
                    {
                        "id": "F123",
                        "mimetype": "image/png",
                        "url_private_download": "https://files.slack.com/files/image.png",
                    }
                ],
            },
        }

        result = await connector.handle_webhook(payload)

        assert result.success is True
        mock_tama.chat_with_image.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_tama_agent(self):
        """Test handling event without Tama agent."""
        config = SlackConnectorConfig(bot_token="xoxb-test")
        connector = SlackConnector(config=config, tama_agent=None)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"ok": True, "user_id": "UBOT"}
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            await connector.setup()

        payload = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "channel": "C123",
                "user": "U456",
                "text": "Hello!",
                "ts": "1234567890.123456",
            },
        }

        result = await connector.handle_webhook(payload)

        assert result.success is False
        assert "Tama agent not configured" in result.errors
