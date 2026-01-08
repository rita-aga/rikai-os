"""
Umi tools for Tama agent.

These tools allow Tama to interact with the Umi context lake.
Tools are defined with JSON schemas for Letta and implemented
as async handlers that execute with access to UmiClient.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Tool Definitions (Letta JSON Schema format)
# =============================================================================

UMI_TOOL_DEFINITIONS = [
    {
        "name": "umi_search",
        "description": (
            "Search the user's context lake (Umi) for relevant information using semantic search. "
            "Use this to find documents, notes, projects, or any stored knowledge."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query - what to look for",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 5)",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "umi_get_entity",
        "description": (
            "Retrieve a specific entity from Umi by its ID. "
            "Use this to get full details of a known entity."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {
                    "type": "string",
                    "description": "The UUID of the entity to retrieve",
                },
            },
            "required": ["entity_id"],
        },
    },
    {
        "name": "umi_list_entities",
        "description": (
            "List entities in Umi, optionally filtered by type. "
            "Entity types: self, project, person, topic, note, task."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "description": "Filter by entity type",
                    "enum": ["self", "project", "person", "topic", "note", "task"],
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results (default: 10)",
                    "default": 10,
                },
            },
        },
    },
    {
        "name": "umi_store_memory",
        "description": (
            "Store new information in Umi as a memory or note. "
            "Use this to remember important facts, decisions, or learnings."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The content to remember",
                },
                "name": {
                    "type": "string",
                    "description": "A short name/title for this memory",
                },
                "importance": {
                    "type": "number",
                    "description": "Importance level 0-1 (default: 0.5)",
                    "default": 0.5,
                    "minimum": 0,
                    "maximum": 1,
                },
            },
            "required": ["content", "name"],
        },
    },
    {
        "name": "umi_get_context",
        "description": (
            "Get comprehensive context about the user including their self description, "
            "current focus, and active projects."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
]


def get_tool_names() -> list[str]:
    """Get list of Umi tool names."""
    return [tool["name"] for tool in UMI_TOOL_DEFINITIONS]


def get_tool_definitions() -> list[dict]:
    """Get Letta-compatible tool definitions."""
    return UMI_TOOL_DEFINITIONS


# =============================================================================
# Tool Handlers (execute with UmiClient)
# =============================================================================


class UmiToolHandler:
    """
    Handles execution of Umi tools.

    Tools are executed locally with access to the UmiClient,
    allowing Tama to interact with the context lake.
    """

    def __init__(self, umi_client) -> None:
        """Initialize with a connected UmiClient."""
        self._umi = umi_client

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a tool and return the result.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Dictionary with success status and result data
        """
        handlers = {
            "umi_search": self._handle_search,
            "umi_get_entity": self._handle_get_entity,
            "umi_list_entities": self._handle_list_entities,
            "umi_store_memory": self._handle_store_memory,
            "umi_get_context": self._handle_get_context,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

        try:
            return await handler(arguments)
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_search(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle umi_search tool."""
        query = args["query"]
        limit = args.get("limit", 5)

        results = await self._umi.search(query, limit=limit)

        return {
            "success": True,
            "count": len(results),
            "results": [
                {
                    "content": r.content[:300] if r.content else "",
                    "source_type": r.source_type,
                    "source_id": r.source_id,
                    "score": round(r.score, 3),
                }
                for r in results
            ],
        }

    async def _handle_get_entity(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle umi_get_entity tool."""
        entity_id = args["entity_id"]

        entity = await self._umi.entities.get(entity_id)
        if not entity:
            return {"success": False, "error": f"Entity {entity_id} not found"}

        return {
            "success": True,
            "entity": {
                "id": str(entity.id),
                "type": entity.type.value,
                "name": entity.name,
                "content": entity.content,
                "metadata": entity.metadata,
            },
        }

    async def _handle_list_entities(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle umi_list_entities tool."""
        from rikai.core.models import EntityType

        entity_type_str = args.get("entity_type")
        limit = args.get("limit", 10)

        entity_type = EntityType(entity_type_str) if entity_type_str else None
        entities = await self._umi.entities.list(type=entity_type, limit=limit)

        return {
            "success": True,
            "count": len(entities),
            "entities": [
                {
                    "id": str(e.id),
                    "type": e.type.value,
                    "name": e.name,
                    "content_preview": e.content[:100] if e.content else None,
                }
                for e in entities
            ],
        }

    async def _handle_store_memory(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle umi_store_memory tool."""
        from rikai.core.models import EntityType

        content = args["content"]
        name = args["name"]
        importance = args.get("importance", 0.5)

        entity = await self._umi.entities.create(
            type=EntityType.NOTE,
            name=name,
            content=content,
            metadata={
                "source": "tama",
                "importance": importance,
            },
        )

        return {
            "success": True,
            "entity_id": str(entity.id),
            "message": f"Stored: {name}",
        }

    async def _handle_get_context(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle umi_get_context tool."""
        from rikai.core.models import EntityType

        context = {}

        # Get self description
        self_entities = await self._umi.entities.list(type=EntityType.SELF, limit=1)
        if self_entities:
            context["self"] = {
                "name": self_entities[0].name,
                "content": self_entities[0].content,
            }

        # Get current focus/tasks
        tasks = await self._umi.entities.list(type=EntityType.TASK, limit=3)
        if tasks:
            context["current_focus"] = [
                {"name": t.name, "content": t.content[:200] if t.content else None}
                for t in tasks
            ]

        # Get active projects
        projects = await self._umi.entities.list(type=EntityType.PROJECT, limit=5)
        if projects:
            context["projects"] = [
                {"name": p.name, "content": p.content[:100] if p.content else None}
                for p in projects
            ]

        return {
            "success": True,
            "context": context,
        }
