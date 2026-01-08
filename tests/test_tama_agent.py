"""
Tests for Tama agent runtime.

Tests agent initialization, message handling, and memory management.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rikai.tama.agent import TamaConfig, TamaMessage, TamaResponse


class TestTamaConfig:
    """Test Tama configuration."""

    def test_tama_config_defaults(self):
        """Test TamaConfig default values."""
        config = TamaConfig()

        assert config.model == "anthropic/claude-sonnet-4-5-20250929"
        assert config.agent_name == "tama"
        assert config.letta_base_url is None  # Now defaults to None
        assert "Tama" in config.persona
        assert "digital soul" in config.persona.lower()

    def test_tama_config_custom(self):
        """Test TamaConfig with custom values."""
        config = TamaConfig(
            letta_api_key="test-key",
            model="custom/model",
            agent_name="custom-agent",
            letta_base_url="http://localhost:8283",
        )

        assert config.letta_api_key == "test-key"
        assert config.model == "custom/model"
        assert config.agent_name == "custom-agent"
        assert config.letta_base_url == "http://localhost:8283"

    def test_get_letta_base_url_from_config(self):
        """Test get_letta_base_url returns config value when set."""
        config = TamaConfig(letta_base_url="http://my-server:8283")
        assert config.get_letta_base_url() == "http://my-server:8283"

    def test_get_letta_base_url_from_env(self):
        """Test get_letta_base_url returns env var when config not set."""
        config = TamaConfig()
        with patch.dict(os.environ, {"LETTA_BASE_URL": "http://env-server:8283"}):
            assert config.get_letta_base_url() == "http://env-server:8283"

    def test_get_letta_base_url_default(self):
        """Test get_letta_base_url returns cloud URL as default."""
        config = TamaConfig()
        with patch.dict(os.environ, {}, clear=True):
            # Remove LETTA_BASE_URL if it exists
            os.environ.pop("LETTA_BASE_URL", None)
            assert config.get_letta_base_url() == "https://api.letta.com"


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
        from rikai.tama.agent import TamaAgent

        config = TamaConfig(letta_api_key="test-key")
        agent = TamaAgent(config)

        assert agent._config.letta_api_key == "test-key"
        assert agent._client is None
        assert agent._agent_id is None

    @pytest.mark.asyncio
    async def test_agent_connect_without_key(self):
        """Test that connect fails without API key."""
        from rikai.tama.agent import TamaAgent

        config = TamaConfig(letta_api_key=None)
        agent = TamaAgent(config)

        with pytest.raises(RuntimeError, match="LETTA_API_KEY"):
            await agent.connect()

    @pytest.mark.asyncio
    async def test_agent_context_manager(self, mock_letta_client):
        """Test using TamaAgent as context manager."""
        from rikai.tama.agent import TamaAgent

        with patch("letta_client.Letta", return_value=mock_letta_client):
            config = TamaConfig(letta_api_key="test-key")
            agent = TamaAgent(config)

            # Mock the UmiClient
            with patch("rikai.umi.UmiClient") as mock_umi:
                mock_umi_instance = AsyncMock()
                mock_umi.return_value = mock_umi_instance

                async with agent as tama:
                    assert tama._client is not None


class TestTamaAgentSelfHosted:
    """Test TamaAgent with self-hosted Letta server."""

    @pytest.mark.asyncio
    async def test_agent_connect_self_hosted_no_key(self, mock_letta_client):
        """Test that self-hosted server doesn't require API key."""
        from rikai.tama.agent import TamaAgent, TamaConfig

        config = TamaConfig(
            letta_api_key=None,
            letta_base_url="http://localhost:8283",
        )
        agent = TamaAgent(config)

        with patch("letta_client.Letta", return_value=mock_letta_client):
            with patch("rikai.umi.UmiClient") as mock_umi:
                mock_umi_instance = AsyncMock()
                mock_umi.return_value = mock_umi_instance

                # Should not raise - self-hosted doesn't require API key
                await agent.connect()
                assert agent._client is not None

    @pytest.mark.asyncio
    async def test_agent_connect_cloud_requires_key(self):
        """Test that Letta Cloud requires API key."""
        from rikai.tama.agent import TamaAgent, TamaConfig

        config = TamaConfig(letta_api_key=None)  # No key, no base URL = cloud
        agent = TamaAgent(config)

        with pytest.raises(RuntimeError, match="LETTA_API_KEY"):
            await agent.connect()


class TestUmiTools:
    """Test Umi tools for Tama."""

    def test_tool_definitions_structure(self):
        """Test that tool definitions have correct structure."""
        from rikai.tama.tools import get_tool_definitions

        tools = get_tool_definitions()
        assert len(tools) == 5  # 5 Umi tools

        # Check each tool has required fields
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool
            assert tool["parameters"]["type"] == "object"

    def test_tool_names(self):
        """Test getting tool names."""
        from rikai.tama.tools import get_tool_names

        names = get_tool_names()
        assert "umi_search" in names
        assert "umi_get_entity" in names
        assert "umi_list_entities" in names
        assert "umi_store_memory" in names
        assert "umi_get_context" in names

    @pytest.mark.asyncio
    async def test_tool_handler_search(self):
        """Test umi_search tool handler."""
        from rikai.tama.tools import UmiToolHandler
        from rikai.core.models import SearchResult

        # Create mock UmiClient
        mock_umi = AsyncMock()
        mock_umi.search = AsyncMock(return_value=[
            MagicMock(
                content="Test result content",
                source_type="note",
                source_id="test-id",
                score=0.95,
            )
        ])

        handler = UmiToolHandler(mock_umi)
        result = await handler.execute("umi_search", {"query": "test query"})

        assert result["success"] is True
        assert result["count"] == 1
        assert len(result["results"]) == 1
        mock_umi.search.assert_called_once_with("test query", limit=5)

    @pytest.mark.asyncio
    async def test_tool_handler_store_memory(self):
        """Test umi_store_memory tool handler."""
        from rikai.tama.tools import UmiToolHandler

        # Create mock UmiClient
        mock_umi = AsyncMock()
        mock_entity = MagicMock()
        mock_entity.id = "new-entity-id"
        mock_umi.entities = MagicMock()
        mock_umi.entities.create = AsyncMock(return_value=mock_entity)

        handler = UmiToolHandler(mock_umi)
        result = await handler.execute("umi_store_memory", {
            "content": "Important fact to remember",
            "name": "Test Memory",
        })

        assert result["success"] is True
        assert result["entity_id"] == "new-entity-id"
        mock_umi.entities.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_handler_unknown_tool(self):
        """Test handler returns error for unknown tool."""
        from rikai.tama.tools import UmiToolHandler

        mock_umi = AsyncMock()
        handler = UmiToolHandler(mock_umi)

        result = await handler.execute("unknown_tool", {})

        assert result["success"] is False
        assert "Unknown tool" in result["error"]

    def test_agent_tool_definitions_includes_umi(self):
        """Test that TamaAgent includes Umi tools."""
        from rikai.tama.agent import TamaAgent, TamaConfig

        config = TamaConfig(letta_api_key="test-key")
        agent = TamaAgent(config)

        tools = agent._get_tool_definitions()

        # Should include built-in Letta tools
        assert "memory" in tools
        assert "conversation_search" in tools

        # Should include Umi tools
        assert "umi_search" in tools
        assert "umi_store_memory" in tools
