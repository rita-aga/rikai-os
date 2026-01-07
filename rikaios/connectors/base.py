"""
Base Connector Interface

All connectors inherit from this base class.
Connectors ingest data from various sources into Umi.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator

from rikaios.core.models import Document, Entity


class ConnectorMode(str, Enum):
    """How the connector operates."""
    PULL = "pull"      # Connector polls for new data
    PUSH = "push"      # Connector receives data via webhooks/events
    HYBRID = "hybrid"  # Both pull and push


class ConnectorStatus(str, Enum):
    """Current status of a connector."""
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class ConnectorConfig:
    """Base configuration for connectors."""
    enabled: bool = True
    poll_interval_seconds: int = 300  # 5 minutes default
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestResult:
    """Result of an ingestion operation."""
    success: bool
    documents_created: int = 0
    entities_created: int = 0
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectorState:
    """Persistent state for a connector."""
    last_sync: datetime | None = None
    cursor: str | None = None  # For pagination/incremental sync
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseConnector(ABC):
    """
    Base class for all data connectors.

    Connectors are responsible for:
    1. Connecting to a data source
    2. Fetching new/updated data
    3. Converting data to Umi format (Documents/Entities)
    4. Storing in Umi via UmiClient
    """

    name: str = "base"
    mode: ConnectorMode = ConnectorMode.PULL
    description: str = "Base connector"

    def __init__(self, config: ConnectorConfig | None = None) -> None:
        self._config = config or ConnectorConfig()
        self._status = ConnectorStatus.IDLE
        self._state = ConnectorState()
        self._umi = None

    @property
    def status(self) -> ConnectorStatus:
        """Get current connector status."""
        return self._status

    @property
    def config(self) -> ConnectorConfig:
        """Get connector configuration."""
        return self._config

    @property
    def state(self) -> ConnectorState:
        """Get connector state."""
        return self._state

    async def initialize(self, umi_client) -> None:
        """
        Initialize the connector with a UmiClient.

        Args:
            umi_client: Connected UmiClient instance
        """
        self._umi = umi_client
        await self.setup()

    @abstractmethod
    async def setup(self) -> None:
        """
        Set up the connector (authenticate, validate config, etc).

        Override this in subclasses.
        """
        pass

    @abstractmethod
    async def sync(self) -> IngestResult:
        """
        Perform a sync operation - fetch and ingest new data.

        Override this in subclasses.

        Returns:
            IngestResult with counts and any errors
        """
        pass

    async def teardown(self) -> None:
        """
        Clean up resources when connector is stopped.

        Override in subclasses if needed.
        """
        pass

    def update_state(self, **kwargs) -> None:
        """Update connector state."""
        for key, value in kwargs.items():
            if hasattr(self._state, key):
                setattr(self._state, key, value)
            else:
                self._state.metadata[key] = value

    async def health_check(self) -> bool:
        """
        Check if the connector is healthy.

        Override in subclasses for source-specific checks.
        """
        return self._status != ConnectorStatus.ERROR


class FileConnector(BaseConnector):
    """Base class for file-based connectors."""

    @abstractmethod
    async def watch(self) -> AsyncIterator[str]:
        """
        Watch for file changes.

        Yields file paths that have changed.
        """
        pass

    @abstractmethod
    async def process_file(self, path: str) -> IngestResult:
        """
        Process a single file.

        Args:
            path: Path to the file

        Returns:
            IngestResult
        """
        pass


class APIConnector(BaseConnector):
    """Base class for API-based connectors."""

    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the API.

        Returns:
            True if authentication successful
        """
        pass

    @abstractmethod
    async def fetch_items(
        self,
        cursor: str | None = None,
        limit: int = 100,
    ) -> tuple[list[Any], str | None]:
        """
        Fetch items from the API.

        Args:
            cursor: Pagination cursor
            limit: Max items to fetch

        Returns:
            Tuple of (items, next_cursor)
        """
        pass


class WebhookConnector(BaseConnector):
    """Base class for webhook-based connectors."""

    mode = ConnectorMode.PUSH

    @abstractmethod
    async def handle_webhook(self, payload: dict[str, Any]) -> IngestResult:
        """
        Handle an incoming webhook.

        Args:
            payload: Webhook payload

        Returns:
            IngestResult
        """
        pass

    @abstractmethod
    def get_webhook_path(self) -> str:
        """
        Get the webhook endpoint path.

        Returns:
            Path like "/webhooks/my-connector"
        """
        pass
