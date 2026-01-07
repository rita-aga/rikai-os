"""
RikaiOS Connectors

Data ingestion connectors for various sources.

Usage:
    from rikaios.connectors import (
        FilesConnector,
        GitConnector,
        ChatConnector,
        GoogleConnector,
    )

    # Local files
    files = FilesConnector(FilesConnectorConfig(
        watch_paths=["~/Documents"],
    ))

    # Git repositories
    git = GitConnector(GitConnectorConfig(
        repo_paths=["~/projects/myrepo"],
    ))

    # LLM chat imports
    chat = ChatConnector(ChatConnectorConfig(
        import_paths=["~/Downloads/claude_export"],
    ))

    # Google Docs
    google = GoogleConnector(GoogleConnectorConfig(
        folder_ids=["folder_id"],
    ))
"""

from rikaios.connectors.base import (
    BaseConnector,
    FileConnector,
    APIConnector,
    WebhookConnector,
    ConnectorConfig,
    ConnectorMode,
    ConnectorStatus,
    ConnectorState,
    IngestResult,
)
from rikaios.connectors.files import FilesConnector, FilesConnectorConfig
from rikaios.connectors.git import GitConnector, GitConnectorConfig
from rikaios.connectors.chat import ChatConnector, ChatConnectorConfig
from rikaios.connectors.google import (
    GoogleConnector,
    GoogleConnectorConfig,
    start_oauth_flow,
    complete_oauth_flow,
)

__all__ = [
    # Base classes
    "BaseConnector",
    "FileConnector",
    "APIConnector",
    "WebhookConnector",
    "ConnectorConfig",
    "ConnectorMode",
    "ConnectorStatus",
    "ConnectorState",
    "IngestResult",
    # Files connector
    "FilesConnector",
    "FilesConnectorConfig",
    # Git connector
    "GitConnector",
    "GitConnectorConfig",
    # Chat connector
    "ChatConnector",
    "ChatConnectorConfig",
    # Google connector
    "GoogleConnector",
    "GoogleConnectorConfig",
    "start_oauth_flow",
    "complete_oauth_flow",
]
