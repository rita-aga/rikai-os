"""
LLM Chat Import Connector

Imports chat exports from Claude and ChatGPT into Umi:
- Claude: conversations.json export
- ChatGPT: conversations.json export
- Generic: markdown chat logs
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from rikai.core.models import DocumentSource, EntityType
from rikai.connectors.base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorMode,
    ConnectorStatus,
    IngestResult,
)

logger = logging.getLogger(__name__)


@dataclass
class ChatConnectorConfig(ConnectorConfig):
    """Configuration for the chat connector."""
    import_paths: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=lambda: ["claude", "chatgpt", "markdown"])
    extract_entities: bool = True  # Extract people, topics from chats


@dataclass
class ChatMessage:
    """A single chat message."""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """A conversation containing messages."""
    id: str
    title: str
    messages: list[ChatMessage]
    source: str  # claude, chatgpt, markdown
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ChatConnector(BaseConnector):
    """
    Connector for importing LLM chat exports.

    Supports:
    - Claude conversations.json export
    - ChatGPT conversations.json export
    - Generic markdown chat logs
    """

    name = "chat"
    mode = ConnectorMode.PULL
    description = "LLM chat import connector"

    def __init__(self, config: ChatConnectorConfig | None = None) -> None:
        super().__init__(config or ChatConnectorConfig())
        self._config: ChatConnectorConfig
        self._processed_ids: set[str] = set()

    async def setup(self) -> None:
        """Initialize the connector."""
        self._status = ConnectorStatus.IDLE

    async def sync(self) -> IngestResult:
        """Sync all configured import paths."""
        if not self._umi:
            return IngestResult(success=False, errors=["Not initialized"])

        self._status = ConnectorStatus.RUNNING
        result = IngestResult(success=True)

        try:
            for import_path in self._config.import_paths:
                path = Path(import_path).expanduser()
                if not path.exists():
                    result.errors.append(f"Path not found: {import_path}")
                    continue

                if path.is_file():
                    file_result = await self._process_file(path)
                else:
                    file_result = await self._process_directory(path)

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

    async def import_file(self, path: str) -> IngestResult:
        """Import a single chat export file."""
        file_path = Path(path).expanduser()
        if not file_path.exists():
            return IngestResult(success=False, errors=[f"File not found: {path}"])

        return await self._process_file(file_path)

    async def _process_directory(self, path: Path) -> IngestResult:
        """Process all chat files in a directory."""
        result = IngestResult(success=True)

        # Look for conversations.json (Claude/ChatGPT exports)
        for json_file in path.glob("*.json"):
            file_result = await self._process_file(json_file)
            result.documents_created += file_result.documents_created
            result.entities_created += file_result.entities_created
            result.errors.extend(file_result.errors)

        # Look for markdown chat logs
        for md_file in path.glob("*.md"):
            if self._is_chat_log(md_file):
                file_result = await self._process_file(md_file)
                result.documents_created += file_result.documents_created
                result.entities_created += file_result.entities_created
                result.errors.extend(file_result.errors)

        return result

    async def _process_file(self, path: Path) -> IngestResult:
        """Process a single chat export file."""
        result = IngestResult(success=True)

        try:
            if path.suffix == ".json":
                conversations = self._parse_json_export(path)
            elif path.suffix == ".md":
                conversations = self._parse_markdown_chat(path)
            else:
                return result  # Skip unsupported files

            for conversation in conversations:
                if conversation.id in self._processed_ids:
                    continue  # Skip already processed

                conv_result = await self._store_conversation(conversation)
                result.documents_created += conv_result.documents_created
                result.entities_created += conv_result.entities_created
                result.errors.extend(conv_result.errors)

                self._processed_ids.add(conversation.id)

        except Exception as e:
            result.errors.append(f"Error processing {path}: {e}")

        return result

    def _parse_json_export(self, path: Path) -> list[Conversation]:
        """Parse a JSON export file (Claude or ChatGPT format)."""
        conversations = []

        try:
            with open(path) as f:
                data = json.load(f)

            # Handle both list and object formats
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict) and "conversations" in data:
                items = data["conversations"]
            elif isinstance(data, dict):
                items = [data]
            else:
                return []

            for item in items:
                conv = self._parse_conversation(item, path)
                if conv:
                    conversations.append(conv)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from {path}: {e}")

        return conversations

    def _parse_conversation(self, data: dict, source_path: Path) -> Conversation | None:
        """Parse a single conversation from JSON."""
        # Try to detect format
        if "mapping" in data:
            # ChatGPT format
            return self._parse_chatgpt_conversation(data, source_path)
        elif "messages" in data or "chat_messages" in data:
            # Claude or generic format
            return self._parse_claude_conversation(data, source_path)
        elif "uuid" in data and "name" in data:
            # Claude format (newer)
            return self._parse_claude_conversation(data, source_path)

        return None

    def _parse_claude_conversation(self, data: dict, source_path: Path) -> Conversation:
        """Parse Claude conversation format."""
        messages = []

        # Handle different message key names
        raw_messages = data.get("messages") or data.get("chat_messages") or []

        for msg in raw_messages:
            # Handle different role formats
            role = msg.get("role") or msg.get("sender") or "unknown"
            if role == "human":
                role = "user"

            # Handle different content formats
            content = msg.get("content") or msg.get("text") or ""
            if isinstance(content, list):
                # Content blocks format
                content = "\n".join(
                    block.get("text", "")
                    for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                )

            # Parse timestamp if available
            timestamp = None
            if "created_at" in msg:
                try:
                    timestamp = datetime.fromisoformat(msg["created_at"].replace("Z", "+00:00"))
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Could not parse message timestamp: {e}")

            messages.append(ChatMessage(
                role=role,
                content=content,
                timestamp=timestamp,
            ))

        # Get conversation metadata
        conv_id = data.get("uuid") or data.get("id") or str(hash(str(data)))
        title = data.get("name") or data.get("title") or f"Conversation {conv_id[:8]}"

        created_at = None
        if "created_at" in data:
            try:
                created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
            except (ValueError, AttributeError) as e:
                logger.debug(f"Could not parse conversation created_at: {e}")

        return Conversation(
            id=conv_id,
            title=title,
            messages=messages,
            source="claude",
            created_at=created_at,
            metadata={
                "source_file": str(source_path),
                "model": data.get("model"),
            },
        )

    def _parse_chatgpt_conversation(self, data: dict, source_path: Path) -> Conversation:
        """Parse ChatGPT conversation format (with mapping)."""
        messages = []

        # ChatGPT uses a tree structure with mapping
        mapping = data.get("mapping", {})

        # Find the root and traverse
        for node_id, node in mapping.items():
            message = node.get("message")
            if not message:
                continue

            role = message.get("author", {}).get("role", "unknown")
            if role == "system":
                continue  # Skip system messages

            content_parts = message.get("content", {}).get("parts", [])
            content = "\n".join(str(p) for p in content_parts if p)

            if not content.strip():
                continue

            # Parse timestamp
            timestamp = None
            create_time = message.get("create_time")
            if create_time:
                try:
                    timestamp = datetime.fromtimestamp(create_time)
                except (ValueError, TypeError) as e:
                    logger.debug(f"Could not parse ChatGPT message timestamp: {e}")

            messages.append(ChatMessage(
                role=role,
                content=content,
                timestamp=timestamp,
                metadata={"model": message.get("metadata", {}).get("model_slug")},
            ))

        # Sort by timestamp if available
        messages.sort(key=lambda m: m.timestamp or datetime.min)

        conv_id = data.get("id") or data.get("conversation_id") or str(hash(str(data)))
        title = data.get("title") or f"ChatGPT {conv_id[:8]}"

        created_at = None
        if "create_time" in data:
            try:
                created_at = datetime.fromtimestamp(data["create_time"])
            except (ValueError, TypeError) as e:
                logger.debug(f"Could not parse ChatGPT conversation created_at: {e}")

        return Conversation(
            id=conv_id,
            title=title,
            messages=messages,
            source="chatgpt",
            created_at=created_at,
            metadata={
                "source_file": str(source_path),
            },
        )

    def _parse_markdown_chat(self, path: Path) -> list[Conversation]:
        """Parse a markdown chat log."""
        conversations = []

        try:
            content = path.read_text()
            messages = []
            current_role = None
            current_content = []

            for line in content.split("\n"):
                # Detect role markers
                line_lower = line.lower().strip()
                if line_lower.startswith("## user") or line_lower.startswith("**user**"):
                    if current_role and current_content:
                        messages.append(ChatMessage(
                            role=current_role,
                            content="\n".join(current_content).strip(),
                        ))
                    current_role = "user"
                    current_content = []
                elif line_lower.startswith("## assistant") or line_lower.startswith("**assistant**"):
                    if current_role and current_content:
                        messages.append(ChatMessage(
                            role=current_role,
                            content="\n".join(current_content).strip(),
                        ))
                    current_role = "assistant"
                    current_content = []
                elif line_lower.startswith("## claude") or line_lower.startswith("**claude**"):
                    if current_role and current_content:
                        messages.append(ChatMessage(
                            role=current_role,
                            content="\n".join(current_content).strip(),
                        ))
                    current_role = "assistant"
                    current_content = []
                elif current_role:
                    current_content.append(line)

            # Add final message
            if current_role and current_content:
                messages.append(ChatMessage(
                    role=current_role,
                    content="\n".join(current_content).strip(),
                ))

            if messages:
                # Extract title from first heading or filename
                title = path.stem
                for line in content.split("\n"):
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break

                conversations.append(Conversation(
                    id=f"md-{hash(str(path))}",
                    title=title,
                    messages=messages,
                    source="markdown",
                    metadata={"source_file": str(path)},
                ))

        except Exception as e:
            logger.warning(f"Failed to parse markdown chat from {path}: {e}")

        return conversations

    def _is_chat_log(self, path: Path) -> bool:
        """Check if a markdown file looks like a chat log."""
        try:
            content = path.read_text()[:2000]  # Check first 2KB
            markers = ["## user", "## assistant", "**user**", "**assistant**", "## claude"]
            return any(marker in content.lower() for marker in markers)
        except Exception as e:
            logger.debug(f"Failed to check if {path} is a chat log: {e}")
            return False

    async def _store_conversation(self, conversation: Conversation) -> IngestResult:
        """Store a conversation in Umi."""
        result = IngestResult(success=True)

        if not self._umi:
            return result

        try:
            # Format conversation as markdown
            content_parts = [f"# {conversation.title}", ""]

            if conversation.created_at:
                content_parts.append(f"*{conversation.created_at.strftime('%Y-%m-%d %H:%M')}*")
                content_parts.append("")

            for msg in conversation.messages:
                role_label = msg.role.capitalize()
                content_parts.append(f"## {role_label}")
                content_parts.append("")
                content_parts.append(msg.content)
                content_parts.append("")

            content = "\n".join(content_parts)

            # Store as document
            await self._umi.documents.store(
                source=DocumentSource.CHAT,
                title=conversation.title,
                content=content,
                content_type="text/markdown",
                metadata={
                    "conversation_id": conversation.id,
                    "source": conversation.source,
                    "message_count": len(conversation.messages),
                    "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
                    **conversation.metadata,
                },
            )
            result.documents_created += 1

            # Extract entities if configured
            if self._config.extract_entities:
                entities_result = await self._extract_entities(conversation)
                result.entities_created += entities_result.entities_created

        except Exception as e:
            result.errors.append(f"Error storing conversation {conversation.id}: {e}")

        return result

    async def _extract_entities(self, conversation: Conversation) -> IngestResult:
        """Extract entities (topics, projects) from conversation."""
        result = IngestResult(success=True)

        if not self._umi:
            return result

        # Simple extraction: look for project references in title
        title_lower = conversation.title.lower()

        # Check if this looks like a project discussion
        project_keywords = ["building", "creating", "implementing", "working on", "developing"]
        if any(kw in title_lower for kw in project_keywords):
            # Try to extract project name
            for msg in conversation.messages[:3]:  # Check first few messages
                if msg.role == "user" and len(msg.content) < 500:
                    # This might contain the project context
                    await self._umi.entities.create(
                        type=EntityType.TOPIC,
                        name=conversation.title,
                        content=f"Topic from conversation: {conversation.title}",
                        metadata={
                            "source": "chat",
                            "conversation_id": conversation.id,
                        },
                    )
                    result.entities_created += 1
                    break

        return result
