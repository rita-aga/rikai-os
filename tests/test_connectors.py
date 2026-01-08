"""
Tests for data connectors.

Tests connector base classes and implementations.
"""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rikai.connectors.base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorMode,
    ConnectorStatus,
    IngestResult,
    ConnectorState,
)


class TestConnectorModels:
    """Test connector data models."""

    def test_connector_mode_enum(self):
        """Test ConnectorMode enum."""
        assert ConnectorMode.PULL == "pull"
        assert ConnectorMode.PUSH == "push"
        assert ConnectorMode.HYBRID == "hybrid"

    def test_connector_status_enum(self):
        """Test ConnectorStatus enum."""
        assert ConnectorStatus.IDLE == "idle"
        assert ConnectorStatus.RUNNING == "running"
        assert ConnectorStatus.ERROR == "error"
        assert ConnectorStatus.DISABLED == "disabled"

    def test_connector_config(self):
        """Test ConnectorConfig model."""
        config = ConnectorConfig(
            enabled=True,
            poll_interval_seconds=600,
            metadata={"api_key": "test"},
        )

        assert config.enabled is True
        assert config.poll_interval_seconds == 600
        assert config.metadata == {"api_key": "test"}

    def test_connector_config_defaults(self):
        """Test ConnectorConfig default values."""
        config = ConnectorConfig()

        assert config.enabled is True
        assert config.poll_interval_seconds == 300
        assert config.metadata == {}

    def test_ingest_result(self):
        """Test IngestResult model."""
        result = IngestResult(
            success=True,
            documents_created=5,
            entities_created=3,
            errors=[],
            metadata={"source": "test"},
        )

        assert result.success is True
        assert result.documents_created == 5
        assert result.entities_created == 3
        assert len(result.errors) == 0

    def test_ingest_result_with_errors(self):
        """Test IngestResult with errors."""
        result = IngestResult(
            success=False,
            errors=["Failed to connect", "Timeout"],
        )

        assert result.success is False
        assert len(result.errors) == 2

    def test_connector_state(self):
        """Test ConnectorState model."""
        now = datetime.now(UTC)
        state = ConnectorState(
            last_sync=now,
            cursor="page-2",
            metadata={"total_processed": 100},
        )

        assert state.last_sync == now
        assert state.cursor == "page-2"
        assert state.metadata == {"total_processed": 100}


class MockConnector(BaseConnector):
    """Mock connector for testing."""

    name = "mock"
    description = "Mock connector for testing"

    async def setup(self) -> None:
        """Setup mock connector."""
        pass

    async def sync(self) -> IngestResult:
        """Perform mock sync."""
        return IngestResult(success=True, documents_created=1)


class TestBaseConnector:
    """Test BaseConnector base class."""

    def test_connector_initialization(self):
        """Test connector initialization."""
        connector = MockConnector()

        assert connector.name == "mock"
        assert connector.mode == ConnectorMode.PULL
        assert connector.status == ConnectorStatus.IDLE
        assert connector.config.enabled is True

    def test_connector_with_config(self):
        """Test connector with custom config."""
        config = ConnectorConfig(
            enabled=False,
            poll_interval_seconds=600,
        )
        connector = MockConnector(config)

        assert connector.config.enabled is False
        assert connector.config.poll_interval_seconds == 600

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test connector initialization with UmiClient."""
        connector = MockConnector()
        mock_umi = MagicMock()

        await connector.initialize(mock_umi)

        assert connector._umi is mock_umi

    @pytest.mark.asyncio
    async def test_sync(self):
        """Test sync operation."""
        connector = MockConnector()

        result = await connector.sync()

        assert result.success is True
        assert result.documents_created == 1

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check."""
        connector = MockConnector()

        is_healthy = await connector.health_check()
        assert is_healthy is True

        connector._status = ConnectorStatus.ERROR
        is_healthy = await connector.health_check()
        assert is_healthy is False

    def test_update_state(self):
        """Test updating connector state."""
        connector = MockConnector()

        connector.update_state(cursor="page-3", custom_field="value")

        assert connector.state.cursor == "page-3"
        assert connector.state.metadata.get("custom_field") == "value"


class TestFileConnector:
    """Test FileConnector base class."""

    @pytest.mark.asyncio
    async def test_files_connector_import(self):
        """Test importing LocalFilesConnector."""
        from rikai.connectors.files import LocalFilesConnector

        config = ConnectorConfig()
        connector = LocalFilesConnector(watch_path="/tmp/test", config=config)

        assert connector.name == "local_files"
        assert connector.watch_path == "/tmp/test"


class TestGitConnector:
    """Test GitConnector."""

    @pytest.mark.asyncio
    async def test_git_connector_import(self):
        """Test importing GitConnector."""
        from rikai.connectors.git import GitConnector

        config = ConnectorConfig()
        connector = GitConnector(repo_path="/tmp/repo", config=config)

        assert connector.name == "git"


class TestChatConnector:
    """Test ChatConnector."""

    @pytest.mark.asyncio
    async def test_chat_connector_import(self):
        """Test importing ChatConnector."""
        from rikai.connectors.chat import ClaudeChatConnector

        connector = ClaudeChatConnector(api_key="test-key")

        assert connector.name == "claude_chat"


class TestGoogleConnector:
    """Test GoogleConnector."""

    @pytest.mark.asyncio
    async def test_google_connector_import(self):
        """Test importing GoogleConnector."""
        from rikai.connectors.google import GoogleDocsConnector

        connector = GoogleDocsConnector(credentials_path="/tmp/creds.json")

        assert connector.name == "google_docs"
