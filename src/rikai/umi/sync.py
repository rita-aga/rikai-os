"""
Local Sync for Umi

Syncs context data between Umi (cloud) and local ~/.rikai/ directory.

The local directory provides:
- Human-readable markdown view of your context
- Ability to edit certain files (like now.md) and sync back
- Offline access to your context
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, UTC
from pathlib import Path
from typing import TYPE_CHECKING

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from rikai.core.config import get_local_path
from rikai.core.models import EntityType
from rikai.umi.export import MarkdownExporter

if TYPE_CHECKING:
    from rikai.umi.client import UmiClient

logger = logging.getLogger(__name__)


class SyncState:
    """Tracks sync state between local and cloud."""

    def __init__(self, local_path: Path) -> None:
        self._path = local_path / ".rikai-sync.json"
        self._state: dict = {}
        self._load()

    def _load(self) -> None:
        """Load sync state from file."""
        if self._path.exists():
            try:
                self._state = json.loads(self._path.read_text())
            except json.JSONDecodeError:
                self._state = {}

    def save(self) -> None:
        """Save sync state to file."""
        self._path.write_text(json.dumps(self._state, indent=2))

    @property
    def last_sync(self) -> datetime | None:
        """Get last sync time."""
        if "last_sync" in self._state:
            return datetime.fromisoformat(self._state["last_sync"])
        return None

    def update_last_sync(self) -> None:
        """Update last sync time to now."""
        self._state["last_sync"] = datetime.now(UTC).isoformat()
        self.save()

    def get_file_hash(self, path: str) -> str | None:
        """Get stored hash for a file."""
        return self._state.get("file_hashes", {}).get(path)

    def set_file_hash(self, path: str, hash: str) -> None:
        """Set hash for a file."""
        if "file_hashes" not in self._state:
            self._state["file_hashes"] = {}
        self._state["file_hashes"][path] = hash


class LocalSyncHandler(FileSystemEventHandler):
    """Handles local file changes for sync back to Umi."""

    # Files that can be edited locally and synced back
    EDITABLE_FILES = {
        "now.md": EntityType.TASK,
        "self.md": EntityType.SELF,
    }

    def __init__(self, umi: "UmiClient", local_path: Path, loop: asyncio.AbstractEventLoop | None = None) -> None:
        self._umi = umi
        self._local_path = local_path
        self._sync_state = SyncState(local_path)
        self._loop = loop
        self._pending_syncs: set[str] = set()
        self._debounce_delay = 1.0  # seconds

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification."""
        if event.is_directory:
            return

        path = Path(event.src_path)
        try:
            relative_path = path.relative_to(self._local_path)
        except ValueError:
            return

        filename = relative_path.name

        # Only sync editable files
        if filename in self.EDITABLE_FILES:
            entity_type = self.EDITABLE_FILES[filename]
            logger.info(f"Detected change in {filename}, syncing to Umi")

            # Debounce: avoid multiple syncs for rapid changes
            if filename in self._pending_syncs:
                return
            self._pending_syncs.add(filename)

            # Schedule async sync
            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._sync_file(path, entity_type, filename),
                    self._loop,
                )
            else:
                # Fallback: create new event loop for sync
                try:
                    asyncio.run(self._sync_file(path, entity_type, filename))
                except RuntimeError:
                    logger.warning(f"Could not sync {filename}: no event loop available")

    async def _sync_file(self, path: Path, entity_type: EntityType, filename: str) -> None:
        """Sync a single file back to Umi."""
        try:
            # Debounce delay
            await asyncio.sleep(self._debounce_delay)

            content = path.read_text()
            parsed_content = self._parse_markdown_content(content)

            # Calculate hash to check if content actually changed
            current_hash = hashlib.md5(content.encode()).hexdigest()
            stored_hash = self._sync_state.get_file_hash(filename)

            if current_hash == stored_hash:
                logger.debug(f"No actual change in {filename}, skipping sync")
                return

            # Find or create entity
            entities = await self._umi.entities.list(type=entity_type, limit=1)
            if entities:
                await self._umi.entities.update(
                    id=str(entities[0].id),
                    content=parsed_content,
                )
                logger.info(f"Updated {entity_type.value} entity from {filename}")
            else:
                name = entity_type.value.title()
                await self._umi.entities.create(
                    type=entity_type,
                    name=name,
                    content=parsed_content,
                )
                logger.info(f"Created {entity_type.value} entity from {filename}")

            # Update stored hash
            self._sync_state.set_file_hash(filename, current_hash)
            self._sync_state.save()

        except Exception as e:
            logger.error(f"Failed to sync {filename}: {e}")
        finally:
            self._pending_syncs.discard(filename)

    def _parse_markdown_content(self, content: str) -> str:
        """Parse markdown content, stripping metadata."""
        lines = content.split("\n")
        result_lines = []
        in_content = False
        skip_header = True

        for line in lines:
            # Skip title line
            if skip_header and line.startswith("# "):
                skip_header = False
                continue

            # Skip blockquotes at the start (description)
            if line.startswith(">") and not in_content:
                continue

            # Skip empty lines at the start
            if not line.strip() and not in_content:
                continue

            # Skip footer
            if line.startswith("---") or line.startswith("*Last updated:") or line.startswith("*Updated:"):
                break

            in_content = True
            result_lines.append(line)

        return "\n".join(result_lines).strip()


class UmiSync:
    """
    Manages bidirectional sync between Umi and local ~/.rikai/.

    Pull: Downloads context from Umi to local markdown files
    Push: Uploads changes from editable local files back to Umi
    Watch: Monitors local files for changes
    """

    def __init__(
        self,
        umi: "UmiClient",
        local_path: Path | None = None,
    ) -> None:
        self._umi = umi
        self._local_path = local_path or get_local_path()
        self._exporter = MarkdownExporter(self._local_path)
        self._sync_state = SyncState(self._local_path)
        self._observer: Observer | None = None

    async def pull(self) -> dict[str, int]:
        """
        Pull all data from Umi to local markdown files.

        Returns:
            Dict with counts of synced items
        """
        logger.info(f"Pulling from Umi to {self._local_path}")

        counts = await self._exporter.export_all(self._umi)

        self._sync_state.update_last_sync()
        logger.info(f"Pulled {counts['entities']} entities, {counts['documents']} documents")

        return counts

    async def push(self) -> dict[str, int]:
        """
        Push local changes back to Umi.

        Only pushes changes to editable files (now.md, self.md).

        Returns:
            Dict with counts of pushed items
        """
        counts = {"entities": 0}

        # Check now.md
        now_path = self._local_path / "now.md"
        if now_path.exists():
            content = now_path.read_text()
            # Parse and update task entity
            await self._push_editable_file(now_path, EntityType.TASK, content)
            counts["entities"] += 1

        # Check self.md
        self_path = self._local_path / "self.md"
        if self_path.exists():
            content = self_path.read_text()
            await self._push_editable_file(self_path, EntityType.SELF, content)
            counts["entities"] += 1

        self._sync_state.update_last_sync()
        return counts

    async def _push_editable_file(
        self,
        path: Path,
        entity_type: EntityType,
        content: str,
    ) -> None:
        """Push an editable file back to Umi."""
        import hashlib

        # Check if file changed
        current_hash = hashlib.md5(content.encode()).hexdigest()
        stored_hash = self._sync_state.get_file_hash(str(path.name))

        if current_hash == stored_hash:
            return  # No change

        # Parse content (strip frontmatter and metadata)
        parsed_content = self._parse_markdown_content(content)

        # Find or create entity
        entities = await self._umi.entities.list(type=entity_type, limit=1)
        if entities:
            # Update existing
            await self._umi.entities.update(
                id=str(entities[0].id),
                content=parsed_content,
            )
        else:
            # Create new
            name = entity_type.value.title()
            await self._umi.entities.create(
                type=entity_type,
                name=name,
                content=parsed_content,
            )

        # Update hash
        self._sync_state.set_file_hash(str(path.name), current_hash)
        self._sync_state.save()

    def _parse_markdown_content(self, content: str) -> str:
        """Parse markdown content, stripping metadata."""
        lines = content.split("\n")
        result_lines = []
        in_content = False
        skip_header = True

        for line in lines:
            # Skip title line
            if skip_header and line.startswith("# "):
                skip_header = False
                continue

            # Skip blockquotes at the start (description)
            if line.startswith(">") and not in_content:
                continue

            # Skip empty lines at the start
            if not line.strip() and not in_content:
                continue

            # Skip footer
            if line.startswith("---") or line.startswith("*Last updated:") or line.startswith("*Updated:"):
                break

            in_content = True
            result_lines.append(line)

        return "\n".join(result_lines).strip()

    def start_watch(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Start watching local files for changes."""
        if self._observer:
            return  # Already watching

        # Get current event loop if not provided
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

        handler = LocalSyncHandler(self._umi, self._local_path, loop=loop)
        self._observer = Observer()
        self._observer.schedule(handler, str(self._local_path), recursive=True)
        self._observer.start()
        logger.info(f"Watching {self._local_path} for changes")

    def stop_watch(self) -> None:
        """Stop watching local files."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("Stopped watching local files")

    @property
    def last_sync(self) -> datetime | None:
        """Get last sync time."""
        return self._sync_state.last_sync
