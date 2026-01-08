"""
Local Files Connector

Watches local directories for file changes and ingests them into Umi.
Supports markdown, text, and other common file types.
"""

import asyncio
import hashlib
import logging
import mimetypes
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import AsyncIterator

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from rikai.core.models import DocumentSource, EntityType
from rikai.connectors.base import (
    FileConnector,
    ConnectorConfig,
    ConnectorMode,
    ConnectorStatus,
    IngestResult,
)

logger = logging.getLogger(__name__)


@dataclass
class FilesConnectorConfig(ConnectorConfig):
    """Configuration for the files connector."""
    watch_paths: list[str] = field(default_factory=lambda: ["~/.rikai/sources"])
    include_patterns: list[str] = field(default_factory=lambda: ["*.md", "*.txt", "*.json"])
    exclude_patterns: list[str] = field(default_factory=lambda: [".*", "__pycache__", "node_modules"])
    max_file_size_mb: int = 10
    process_existing: bool = True  # Process existing files on first sync


class FileChangeHandler(FileSystemEventHandler):
    """Handles file system events."""

    def __init__(self, queue: asyncio.Queue) -> None:
        self._queue = queue
        self._loop = asyncio.get_event_loop()

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._loop.call_soon_threadsafe(
                self._queue.put_nowait, ("created", event.src_path)
            )

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._loop.call_soon_threadsafe(
                self._queue.put_nowait, ("modified", event.src_path)
            )

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._loop.call_soon_threadsafe(
                self._queue.put_nowait, ("deleted", event.src_path)
            )


class FilesConnector(FileConnector):
    """
    Connector for local files.

    Watches directories for changes and ingests files into Umi.
    """

    name = "files"
    mode = ConnectorMode.PUSH
    description = "Local file watcher"

    def __init__(self, config: FilesConnectorConfig | None = None) -> None:
        super().__init__(config or FilesConnectorConfig())
        self._config: FilesConnectorConfig
        self._observer: Observer | None = None
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._file_hashes: dict[str, str] = {}

    async def setup(self) -> None:
        """Set up the file watcher."""
        self._status = ConnectorStatus.IDLE

    async def sync(self) -> IngestResult:
        """
        Sync all files in watched directories.

        This does a full scan and ingests any new/changed files.
        """
        if not self._umi:
            return IngestResult(success=False, errors=["Not initialized"])

        self._status = ConnectorStatus.RUNNING
        result = IngestResult(success=True)

        try:
            for watch_path in self._config.watch_paths:
                path = Path(watch_path).expanduser()
                if not path.exists():
                    continue

                # Find all matching files
                for pattern in self._config.include_patterns:
                    for file_path in path.rglob(pattern):
                        if self._should_process(file_path):
                            file_result = await self.process_file(str(file_path))
                            result.documents_created += file_result.documents_created
                            result.entities_created += file_result.entities_created
                            result.errors.extend(file_result.errors)

            self._state.last_sync = datetime.now(UTC)
            self._status = ConnectorStatus.IDLE

        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            self._status = ConnectorStatus.ERROR

        return result

    async def watch(self) -> AsyncIterator[str]:
        """Watch for file changes."""
        if self._observer is not None:
            return

        self._observer = Observer()
        handler = FileChangeHandler(self._event_queue)

        for watch_path in self._config.watch_paths:
            path = Path(watch_path).expanduser()
            if path.exists():
                self._observer.schedule(handler, str(path), recursive=True)

        self._observer.start()
        self._status = ConnectorStatus.RUNNING

        try:
            while True:
                event_type, file_path = await self._event_queue.get()
                if self._should_process(Path(file_path)):
                    yield file_path
        finally:
            self._observer.stop()
            self._observer.join()
            self._observer = None

    async def process_file(self, path: str) -> IngestResult:
        """Process a single file."""
        if not self._umi:
            return IngestResult(success=False, errors=["Not initialized"])

        result = IngestResult(success=True)
        file_path = Path(path)

        try:
            # Check if file exists
            if not file_path.exists():
                return result  # File was deleted, nothing to do

            # Check file size
            size_mb = file_path.stat().st_size / (1024 * 1024)
            if size_mb > self._config.max_file_size_mb:
                result.errors.append(f"File too large: {path}")
                return result

            # Check if file changed (by hash)
            content = file_path.read_bytes()
            file_hash = hashlib.md5(content).hexdigest()

            if self._file_hashes.get(path) == file_hash:
                return result  # No change

            self._file_hashes[path] = file_hash

            # Determine content type
            content_type = mimetypes.guess_type(path)[0] or "text/plain"

            # Determine source type from path
            source = self._determine_source(file_path)

            # Store in Umi
            if content_type.startswith("text/"):
                text_content = content.decode("utf-8", errors="replace")

                # For markdown files, also create an entity
                if file_path.suffix == ".md":
                    await self._process_markdown(file_path, text_content, result)
                else:
                    await self._umi.documents.store(
                        source=source,
                        title=file_path.name,
                        content=text_content,
                        content_type=content_type,
                        metadata={
                            "path": str(file_path),
                            "size": len(content),
                        },
                    )
                    result.documents_created += 1
            else:
                # Binary file
                await self._umi.documents.store(
                    source=source,
                    title=file_path.name,
                    content=content,
                    content_type=content_type,
                    metadata={
                        "path": str(file_path),
                        "size": len(content),
                    },
                )
                result.documents_created += 1

        except Exception as e:
            result.success = False
            result.errors.append(f"Error processing {path}: {e}")

        return result

    async def _process_markdown(
        self,
        path: Path,
        content: str,
        result: IngestResult,
    ) -> None:
        """Process a markdown file - extract metadata and create entity."""
        # Parse frontmatter if present
        metadata = {}
        body = content

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml
                try:
                    metadata = yaml.safe_load(parts[1]) or {}
                    body = parts[2].strip()
                except yaml.YAMLError as e:
                    logger.warning(f"Failed to parse YAML frontmatter in {path}: {e}")

        # Extract title from first heading or filename
        title = path.stem
        lines = body.split("\n")
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break

        # Determine entity type from path or metadata
        entity_type = self._determine_entity_type(path, metadata)

        if entity_type:
            # Create as entity
            await self._umi.entities.create(
                type=entity_type,
                name=title,
                content=body,
                metadata={
                    "path": str(path),
                    "source": "files",
                    **metadata,
                },
            )
            result.entities_created += 1
        else:
            # Store as document
            await self._umi.documents.store(
                source=DocumentSource.FILE,
                title=title,
                content=content,
                content_type="text/markdown",
                metadata={
                    "path": str(path),
                    **metadata,
                },
            )
            result.documents_created += 1

    def _determine_source(self, path: Path) -> DocumentSource:
        """Determine document source from path."""
        path_str = str(path).lower()

        if "chat" in path_str:
            return DocumentSource.CHAT
        elif "voice" in path_str or "transcript" in path_str:
            return DocumentSource.VOICE
        elif "doc" in path_str:
            return DocumentSource.DOCS
        else:
            return DocumentSource.FILE

    def _determine_entity_type(
        self,
        path: Path,
        metadata: dict,
    ) -> EntityType | None:
        """Determine if file should be an entity and what type."""
        path_str = str(path).lower()
        filename = path.name.lower()

        # Check metadata first
        if "type" in metadata:
            type_str = metadata["type"].lower()
            type_map = {
                "project": EntityType.PROJECT,
                "person": EntityType.PERSON,
                "topic": EntityType.TOPIC,
                "note": EntityType.NOTE,
                "task": EntityType.TASK,
            }
            if type_str in type_map:
                return type_map[type_str]

        # Check filename/path
        if filename == "self.md":
            return EntityType.SELF
        elif filename == "now.md":
            return EntityType.TASK
        elif filename == "memory.md":
            return EntityType.NOTE
        elif "project" in path_str:
            return EntityType.PROJECT
        elif "people" in path_str or "person" in path_str:
            return EntityType.PERSON
        elif "topic" in path_str:
            return EntityType.TOPIC

        return None

    def _should_process(self, path: Path) -> bool:
        """Check if a file should be processed."""
        # Check exclude patterns
        for pattern in self._config.exclude_patterns:
            if path.match(pattern):
                return False
            # Check parent directories
            for parent in path.parents:
                if parent.name.startswith("."):
                    return False

        # Check include patterns
        for pattern in self._config.include_patterns:
            if path.match(pattern):
                return True

        return False

    async def teardown(self) -> None:
        """Stop the file watcher."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
        self._status = ConnectorStatus.IDLE
