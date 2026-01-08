"""
Tests for Tama agent runtime.

Tests agent initialization, message handling, and memory management.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rikaios.tama.agent import TamaConfig, TamaMessage, TamaResponse


class TestTamaConfig:
    """Test Tama configuration."""

    def test_tama_config_defaults(self):
        """Test TamaConfig default values."""
        config = TamaConfig()

        assert config.model == "anthropic/claude-sonnet-4-5-20250929"
        assert config.agent_name == "tama"
        assert config.letta_base_url == "https://api.letta.com"
        assert "Tama" in config.persona
        assert "digital soul" in config.persona.lower()

    def test_tama_config_custom(self):
        """Test TamaConfig with custom values."""
        config = TamaConfig(
            letta_api_key="test-key",
            model="custom/model",
            agent_name="custom-agent",
        )

        assert config.letta_api_key == "test-key"
        assert config.model == "custom/model"
        assert config.agent_name == "custom-agent"


class TestTamaMessage:
    """Test TamaMessage model."""

    def test_tama_message(self):
        """Test creating a TamaMessage."""
        msg = TamaMessage(
            role="user",
            content="Hello Tama",
            metadata={"timestamp": "2024-01-01"},
        )

        assert msg.role == "user"
        assert msg.content == "Hello Tama"
        assert msg.metadata == {"timestamp": "2024-01-01"}

    def test_tama_message_minimal(self):
        """Test TamaMessage with minimal fields."""
        msg = TamaMessage(role="assistant", content="Hello!")

        assert msg.role == "assistant"
        assert msg.content == "Hello!"
        assert msg.metadata == {}


class TestTamaResponse:
    """Test TamaResponse model."""

    def test_tama_response(self):
        """Test creating a TamaResponse."""
        response = TamaResponse(
            message="Here's what I found",
            tool_calls=[{"tool": "search", "args": {"query": "test"}}],
            metadata={"confidence": 0.95},
        )

        assert response.message == "Here's what I found"
        assert len(response.tool_calls) == 1
        assert response.metadata["confidence"] == 0.95

    def test_tama_response_minimal(self):
        """Test TamaResponse with minimal fields."""
        response = TamaResponse(message="Simple response")

        assert response.message == "Simple response"
        assert response.tool_calls == []
        assert response.context_used == []
        assert response.metadata == {}


class TestTamaAgent:
    """Test TamaAgent class."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test creating a TamaAgent."""
        from rikaios.tama.agent import TamaAgent

        config = TamaConfig(letta_api_key="test-key")
        agent = TamaAgent(config)

        assert agent._config.letta_api_key == "test-key"
        assert agent._client is None
        assert agent._agent_id is None

    @pytest.mark.asyncio
    async def test_agent_connect_without_key(self):
        """Test that connect fails without API key."""
        from rikaios.tama.agent import TamaAgent

        config = TamaConfig(letta_api_key=None)
        agent = TamaAgent(config)

        with pytest.raises(RuntimeError, match="LETTA_API_KEY"):
            await agent.connect()

    @pytest.mark.asyncio
    async def test_agent_context_manager(self, mock_letta_client):
        """Test using TamaAgent as context manager."""
        from rikaios.tama.agent import TamaAgent

        with patch("rikaios.tama.agent.Letta", return_value=mock_letta_client):
            config = TamaConfig(letta_api_key="test-key")
            agent = TamaAgent(config)

            # Mock the UmiClient
            with patch("rikaios.tama.agent.UmiClient") as mock_umi:
                mock_umi_instance = AsyncMock()
                mock_umi.return_value = mock_umi_instance

                async with agent as tama:
                    assert tama._client is not None


class TestLocalTamaAgent:
    """Test LocalTamaAgent (Claude-based)."""

    @pytest.mark.asyncio
    async def test_local_tama_initialization(self):
        """Test creating a LocalTamaAgent."""
        from rikaios.tama.agent import LocalTamaAgent

        agent = LocalTamaAgent(api_key="test-key")

        assert agent._anthropic_client is None
        assert agent._conversation_history == []

    @pytest.mark.asyncio
    async def test_local_tama_connect(self, mock_anthropic_client):
        """Test connecting LocalTamaAgent."""
        from rikaios.tama.agent import LocalTamaAgent

        with patch("rikaios.tama.agent.Anthropic", return_value=mock_anthropic_client):
            agent = LocalTamaAgent(api_key="test-key")

            with patch("rikaios.tama.agent.UmiClient") as mock_umi:
                mock_umi_instance = AsyncMock()
                mock_umi.return_value = mock_umi_instance

                await agent.connect()

                assert agent._anthropic_client is not None

    @pytest.mark.asyncio
    async def test_local_tama_chat(self, mock_anthropic_client):
        """Test chatting with LocalTamaAgent."""
        from rikaios.tama.agent import LocalTamaAgent

        with patch("rikaios.tama.agent.Anthropic", return_value=mock_anthropic_client):
            agent = LocalTamaAgent(api_key="test-key")

            with patch("rikaios.tama.agent.UmiClient") as mock_umi:
                mock_umi_instance = AsyncMock()
                mock_umi_instance.search = AsyncMock(return_value=[])
                mock_umi.return_value = mock_umi_instance

                await agent.connect()

                response = await agent.chat("Hello Tama")

                assert response.message is not None
                assert "Test response" in response.message
