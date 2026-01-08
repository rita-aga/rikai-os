"""
Tests for messaging utilities.

Tests image description and message preparation for Tama.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rikai.connectors.messaging import (
    ProcessedMessage,
    describe_image,
    get_media_type,
    prepare_message_for_tama,
)


class TestGetMediaType:
    """Test media type detection."""

    def test_png(self):
        assert get_media_type("image.png") == "image/png"

    def test_jpg(self):
        assert get_media_type("photo.jpg") == "image/jpeg"

    def test_jpeg(self):
        assert get_media_type("photo.jpeg") == "image/jpeg"

    def test_gif(self):
        assert get_media_type("animation.gif") == "image/gif"

    def test_webp(self):
        assert get_media_type("modern.webp") == "image/webp"

    def test_unknown(self):
        assert get_media_type("file.xyz") == "image/png"  # Default

    def test_none(self):
        assert get_media_type(None) == "image/png"

    def test_uppercase(self):
        assert get_media_type("IMAGE.PNG") == "image/png"


class TestDescribeImage:
    """Test image description with Claude Vision."""

    @pytest.mark.asyncio
    async def test_describe_image_success(self):
        """Test successful image description."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="A screenshot of a terminal window showing error logs")]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        import sys
        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        sys.modules["anthropic"] = mock_anthropic

        try:
            result = await describe_image(b"fake_image_bytes", "image/png")

            assert result == "A screenshot of a terminal window showing error logs"
            mock_client.messages.create.assert_called_once()
        finally:
            del sys.modules["anthropic"]

    @pytest.mark.asyncio
    async def test_describe_image_with_context(self):
        """Test image description with additional context."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="An architecture diagram")]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        import sys
        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        sys.modules["anthropic"] = mock_anthropic

        try:
            result = await describe_image(
                b"fake_image_bytes",
                "image/png",
                context="From Telegram, sent by user123",
            )

            assert result == "An architecture diagram"
            # Verify the context was included in the prompt
            call_args = mock_client.messages.create.call_args
            messages = call_args.kwargs["messages"]
            text_content = [c for c in messages[0]["content"] if c["type"] == "text"][0]
            assert "From Telegram" in text_content["text"]
        finally:
            del sys.modules["anthropic"]

    @pytest.mark.asyncio
    async def test_describe_image_error(self):
        """Test error handling in image description."""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API error")

        import sys
        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        sys.modules["anthropic"] = mock_anthropic

        try:
            result = await describe_image(b"fake_image_bytes")

            assert result == "[Unable to process image]"
        finally:
            del sys.modules["anthropic"]


class TestPrepareMessageForTama:
    """Test message preparation for Tama."""

    @pytest.mark.asyncio
    async def test_text_only(self):
        """Test preparing text-only message."""
        result = await prepare_message_for_tama(
            text="Hello Tama!",
            platform="telegram",
            sender="user123",
        )

        assert isinstance(result, ProcessedMessage)
        assert result.text == "Hello Tama!"
        assert result.platform == "telegram"
        assert result.sender == "user123"
        assert result.metadata["has_image"] is False

    @pytest.mark.asyncio
    async def test_image_only(self):
        """Test preparing image-only message."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="A photo of a cat")]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        import sys
        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        sys.modules["anthropic"] = mock_anthropic

        try:
            result = await prepare_message_for_tama(
                image_bytes=b"fake_image",
                platform="slack",
                sender="alice",
            )

            assert "[User sent an image: A photo of a cat]" in result.text
            assert result.metadata["has_image"] is True
            assert result.metadata["image_description"] == "A photo of a cat"
        finally:
            del sys.modules["anthropic"]

    @pytest.mark.asyncio
    async def test_image_with_text(self):
        """Test preparing message with both image and text."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="A bug report screenshot")]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        import sys
        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        sys.modules["anthropic"] = mock_anthropic

        try:
            result = await prepare_message_for_tama(
                text="Check out this bug",
                image_bytes=b"fake_image",
                platform="telegram",
                sender="dev123",
            )

            assert "[User sent an image: A bug report screenshot]" in result.text
            assert "Check out this bug" in result.text
            assert result.metadata["has_image"] is True
        finally:
            del sys.modules["anthropic"]

    @pytest.mark.asyncio
    async def test_empty_message(self):
        """Test preparing empty message."""
        result = await prepare_message_for_tama(
            platform="unknown",
            sender="unknown",
        )

        assert result.text == ""
        assert result.metadata["has_image"] is False
