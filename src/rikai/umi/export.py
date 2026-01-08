"""
Markdown Export Layer for Umi

Exports context data to human-readable markdown files.
This creates the local ~/.rikai/ view of your context lake.
"""

from datetime import datetime, UTC
from pathlib import Path
from typing import TYPE_CHECKING

from rikai.core.models import Entity, EntityType, Document, DocumentSource

if TYPE_CHECKING:
    from rikai.umi.client import UmiClient


class MarkdownExporter:
    """Exports Umi data to markdown files."""

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure output directories exist."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        (self._output_dir / "projects").mkdir(exist_ok=True)
        (self._output_dir / "people").mkdir(exist_ok=True)
        (self._output_dir / "sources" / "chats").mkdir(parents=True, exist_ok=True)
        (self._output_dir / "sources" / "docs").mkdir(parents=True, exist_ok=True)
        (self._output_dir / "sources" / "voice").mkdir(parents=True, exist_ok=True)
        (self._output_dir / "sources" / "social").mkdir(parents=True, exist_ok=True)

    async def export_all(self, umi: "UmiClient") -> dict[str, int]:
        """
        Export all data from Umi to markdown.

        Returns:
            Dict with counts of exported items by type
        """
        counts = {
            "entities": 0,
            "documents": 0,
        }

        # Export entities
        entities = await umi.entities.list(limit=10000)
        for entity in entities:
            self.export_entity(entity)
            counts["entities"] += 1

        # Export documents
        documents = await umi.documents.list(limit=10000)
        for doc in documents:
            content = await umi.documents.get_content(str(doc.id))
            if content and doc.content_type and doc.content_type.startswith("text/"):
                self.export_document(doc, content.decode("utf-8"))
                counts["documents"] += 1

        # Write sync metadata
        self._write_sync_metadata()

        return counts

    def export_entity(self, entity: Entity) -> Path:
        """Export a single entity to markdown."""
        if entity.type == EntityType.SELF:
            path = self._output_dir / "self.md"
            content = self._format_self_entity(entity)
        elif entity.type == EntityType.PROJECT:
            path = self._output_dir / "projects" / f"{self._slugify(entity.name)}.md"
            content = self._format_project_entity(entity)
        elif entity.type == EntityType.PERSON:
            path = self._output_dir / "people" / f"{self._slugify(entity.name)}.md"
            content = self._format_person_entity(entity)
        elif entity.type == EntityType.NOTE:
            path = self._output_dir / "memory.md"
            content = self._format_note_entity(entity)
        elif entity.type == EntityType.TOPIC:
            path = self._output_dir / f"topics/{self._slugify(entity.name)}.md"
            (self._output_dir / "topics").mkdir(exist_ok=True)
            content = self._format_topic_entity(entity)
        elif entity.type == EntityType.TASK:
            path = self._output_dir / "now.md"
            content = self._format_task_entity(entity)
        else:
            path = self._output_dir / f"entities/{entity.id}.md"
            (self._output_dir / "entities").mkdir(exist_ok=True)
            content = self._format_generic_entity(entity)

        path.write_text(content)
        return path

    def export_document(self, doc: Document, content: str) -> Path:
        """Export a document to markdown."""
        source_dir = self._get_source_dir(doc.source)
        filename = f"{self._slugify(doc.title)}.md"
        path = source_dir / filename

        md_content = self._format_document(doc, content)
        path.write_text(md_content)
        return path

    def _get_source_dir(self, source: DocumentSource) -> Path:
        """Get the directory for a document source."""
        source_map = {
            DocumentSource.CHAT: "chats",
            DocumentSource.DOCS: "docs",
            DocumentSource.VOICE: "voice",
            DocumentSource.SOCIAL: "social",
            DocumentSource.FILE: "files",
            DocumentSource.GIT: "git",
        }
        subdir = source_map.get(source, "other")
        dir_path = self._output_dir / "sources" / subdir
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def _format_self_entity(self, entity: Entity) -> str:
        """Format self entity as markdown."""
        lines = [
            "# Self",
            "",
            "> Your persona, preferences, and who you are.",
            "> This file is synced from your Umi context lake.",
            "",
        ]

        if entity.content:
            lines.extend([entity.content, ""])

        if entity.metadata:
            lines.extend(["## Metadata", "", "```yaml"])
            for key, value in entity.metadata.items():
                lines.append(f"{key}: {value}")
            lines.extend(["```", ""])

        lines.extend([
            "---",
            f"*Last updated: {entity.updated_at.isoformat()}*",
        ])

        return "\n".join(lines)

    def _format_project_entity(self, entity: Entity) -> str:
        """Format project entity as markdown."""
        lines = [
            f"# {entity.name}",
            "",
        ]

        if entity.content:
            lines.extend([entity.content, ""])

        if entity.metadata:
            if "status" in entity.metadata:
                lines.extend([f"**Status:** {entity.metadata['status']}", ""])
            if "tags" in entity.metadata:
                tags = entity.metadata["tags"]
                if isinstance(tags, list):
                    lines.extend([f"**Tags:** {', '.join(tags)}", ""])

        lines.extend([
            "---",
            f"*Created: {entity.created_at.isoformat()}*",
            f"*Updated: {entity.updated_at.isoformat()}*",
        ])

        return "\n".join(lines)

    def _format_person_entity(self, entity: Entity) -> str:
        """Format person entity as markdown."""
        lines = [
            f"# {entity.name}",
            "",
        ]

        if entity.content:
            lines.extend([entity.content, ""])

        if entity.metadata:
            lines.extend(["## Details", ""])
            for key, value in entity.metadata.items():
                lines.append(f"- **{key.title()}:** {value}")
            lines.append("")

        lines.extend([
            "---",
            f"*Updated: {entity.updated_at.isoformat()}*",
        ])

        return "\n".join(lines)

    def _format_note_entity(self, entity: Entity) -> str:
        """Format note entity as markdown."""
        lines = [
            "# Memory",
            "",
            "> Accumulated learnings and decisions made.",
            "",
        ]

        if entity.content:
            lines.extend(["## Notes", "", entity.content, ""])

        lines.extend([
            "---",
            f"*Updated: {entity.updated_at.isoformat()}*",
        ])

        return "\n".join(lines)

    def _format_topic_entity(self, entity: Entity) -> str:
        """Format topic entity as markdown."""
        lines = [
            f"# {entity.name}",
            "",
        ]

        if entity.content:
            lines.extend([entity.content, ""])

        lines.extend([
            "---",
            f"*Updated: {entity.updated_at.isoformat()}*",
        ])

        return "\n".join(lines)

    def _format_task_entity(self, entity: Entity) -> str:
        """Format task entity as markdown."""
        lines = [
            "# Now",
            "",
            "> Current focus and priorities.",
            "",
        ]

        if entity.content:
            lines.extend(["## Current Tasks", "", entity.content, ""])

        lines.extend([
            "---",
            f"*Updated: {entity.updated_at.isoformat()}*",
        ])

        return "\n".join(lines)

    def _format_generic_entity(self, entity: Entity) -> str:
        """Format generic entity as markdown."""
        lines = [
            f"# {entity.name}",
            "",
            f"**Type:** {entity.type.value}",
            "",
        ]

        if entity.content:
            lines.extend([entity.content, ""])

        lines.extend([
            "---",
            f"*Updated: {entity.updated_at.isoformat()}*",
        ])

        return "\n".join(lines)

    def _format_document(self, doc: Document, content: str) -> str:
        """Format document as markdown."""
        lines = [
            f"# {doc.title}",
            "",
            f"> Source: {doc.source.value}",
            f"> Imported: {doc.created_at.isoformat()}",
            "",
            "---",
            "",
            content,
        ]

        return "\n".join(lines)

    def _write_sync_metadata(self) -> None:
        """Write sync metadata file."""
        import json

        metadata = {
            "last_sync": datetime.now(UTC).isoformat(),
            "version": "0.1.0",
        }

        path = self._output_dir / ".rikai-sync.json"
        path.write_text(json.dumps(metadata, indent=2))

    def _slugify(self, text: str) -> str:
        """Convert text to a safe filename slug."""
        import re

        # Convert to lowercase
        slug = text.lower()
        # Replace spaces and special chars with hyphens
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        # Remove leading/trailing hyphens
        slug = slug.strip("-")
        # Limit length
        return slug[:50] or "unnamed"
