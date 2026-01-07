"""
RikaiOS MCP Server

Exposes RikaiOS context through the Model Context Protocol (MCP).
This allows any MCP client (Claude, other agents) to access your context lake.

Tools provided:
- search: Semantic search across your context
- get_entity: Get a specific entity by ID
- list_entities: List entities by type
- store_memory: Store new information in Umi
- get_context: Get context about the user

Resources provided:
- self: User's self description
- now: Current focus and tasks
- projects: Active projects
"""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    ResourceContents,
    ListResourcesResult,
    ListToolsResult,
    CallToolResult,
    ReadResourceResult,
)

from rikaios.core.config import get_config
from rikaios.core.models import EntityType
from rikaios.umi import UmiClient


# Create MCP server
server = Server("rikaios")

# Global Umi client (initialized on startup)
_umi: UmiClient | None = None


async def get_umi() -> UmiClient:
    """Get or create Umi client."""
    global _umi
    if _umi is None:
        _umi = UmiClient(get_config())
        await _umi.connect()
    return _umi


# =============================================================================
# Tools
# =============================================================================


@server.list_tools()
async def list_tools() -> ListToolsResult:
    """List available tools."""
    return ListToolsResult(
        tools=[
            Tool(
                name="search",
                description="Semantic search across the user's context lake (Umi). "
                "Use this to find relevant information about projects, people, notes, etc.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "What to search for",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results (default 5)",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="get_entity",
                description="Get a specific entity by ID from the context lake.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Entity ID",
                        },
                    },
                    "required": ["id"],
                },
            ),
            Tool(
                name="list_entities",
                description="List entities in the context lake, optionally filtered by type.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "Entity type: self, project, person, topic, note, task",
                            "enum": ["self", "project", "person", "topic", "note", "task"],
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results (default 10)",
                            "default": 10,
                        },
                    },
                },
            ),
            Tool(
                name="store_memory",
                description="Store new information in the user's context lake. "
                "Use this to remember important facts, decisions, or learnings.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "What to remember",
                        },
                        "name": {
                            "type": "string",
                            "description": "Short name/title for this memory",
                        },
                        "type": {
                            "type": "string",
                            "description": "Entity type (default: note)",
                            "enum": ["note", "topic", "task"],
                            "default": "note",
                        },
                    },
                    "required": ["content", "name"],
                },
            ),
            Tool(
                name="get_context",
                description="Get comprehensive context about the user including "
                "their self description, current focus, and active projects.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]
    )


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Handle tool calls."""
    umi = await get_umi()

    if name == "search":
        query = arguments["query"]
        limit = arguments.get("limit", 5)

        results = await umi.search(query, limit=limit)

        if not results:
            return CallToolResult(
                content=[TextContent(type="text", text="No results found.")]
            )

        text_parts = [f"Found {len(results)} results:\n"]
        for i, result in enumerate(results, 1):
            text_parts.append(
                f"{i}. [{result.source_type}] (score: {result.score:.3f})\n"
                f"   {result.content[:200]}...\n"
            )

        return CallToolResult(
            content=[TextContent(type="text", text="\n".join(text_parts))]
        )

    elif name == "get_entity":
        entity_id = arguments["id"]
        entity = await umi.entities.get(entity_id)

        if not entity:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Entity {entity_id} not found.")]
            )

        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"**{entity.name}** ({entity.type.value})\n\n{entity.content or 'No content'}"
            )]
        )

    elif name == "list_entities":
        entity_type = arguments.get("type")
        limit = arguments.get("limit", 10)

        type_enum = EntityType(entity_type) if entity_type else None
        entities = await umi.entities.list(type=type_enum, limit=limit)

        if not entities:
            return CallToolResult(
                content=[TextContent(type="text", text="No entities found.")]
            )

        text_parts = [f"Found {len(entities)} entities:\n"]
        for entity in entities:
            text_parts.append(
                f"- **{entity.name}** ({entity.type.value}) - ID: {entity.id}"
            )

        return CallToolResult(
            content=[TextContent(type="text", text="\n".join(text_parts))]
        )

    elif name == "store_memory":
        content = arguments["content"]
        name_arg = arguments["name"]
        entity_type = EntityType(arguments.get("type", "note"))

        entity = await umi.entities.create(
            type=entity_type,
            name=name_arg,
            content=content,
        )

        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"Stored memory: {name_arg} (ID: {entity.id})"
            )]
        )

    elif name == "get_context":
        context_parts = []

        # Get self
        self_entities = await umi.entities.list(type=EntityType.SELF, limit=1)
        if self_entities and self_entities[0].content:
            context_parts.append(f"**About the user:**\n{self_entities[0].content}")

        # Get current focus
        task_entities = await umi.entities.list(type=EntityType.TASK, limit=1)
        if task_entities and task_entities[0].content:
            context_parts.append(f"**Current focus:**\n{task_entities[0].content}")

        # Get projects
        projects = await umi.entities.list(type=EntityType.PROJECT, limit=5)
        if projects:
            project_list = "\n".join(
                f"- {p.name}: {p.content[:100] if p.content else 'No description'}"
                for p in projects
            )
            context_parts.append(f"**Active projects:**\n{project_list}")

        if not context_parts:
            return CallToolResult(
                content=[TextContent(type="text", text="No context available yet.")]
            )

        return CallToolResult(
            content=[TextContent(type="text", text="\n\n".join(context_parts))]
        )

    else:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Unknown tool: {name}")]
        )


# =============================================================================
# Resources
# =============================================================================


@server.list_resources()
async def list_resources() -> ListResourcesResult:
    """List available resources."""
    return ListResourcesResult(
        resources=[
            Resource(
                uri="rikaios://self",
                name="Self",
                description="User's self description and persona",
                mimeType="text/markdown",
            ),
            Resource(
                uri="rikaios://now",
                name="Now",
                description="User's current focus and tasks",
                mimeType="text/markdown",
            ),
            Resource(
                uri="rikaios://projects",
                name="Projects",
                description="User's active projects",
                mimeType="text/markdown",
            ),
        ]
    )


@server.read_resource()
async def read_resource(uri: str) -> ReadResourceResult:
    """Read a resource."""
    umi = await get_umi()

    if uri == "rikaios://self":
        entities = await umi.entities.list(type=EntityType.SELF, limit=1)
        if entities and entities[0].content:
            content = f"# Self\n\n{entities[0].content}"
        else:
            content = "# Self\n\nNo self description yet."

        return ReadResourceResult(
            contents=[ResourceContents(uri=uri, text=content, mimeType="text/markdown")]
        )

    elif uri == "rikaios://now":
        entities = await umi.entities.list(type=EntityType.TASK, limit=1)
        if entities and entities[0].content:
            content = f"# Now\n\n{entities[0].content}"
        else:
            content = "# Now\n\nNo current focus defined."

        return ReadResourceResult(
            contents=[ResourceContents(uri=uri, text=content, mimeType="text/markdown")]
        )

    elif uri == "rikaios://projects":
        projects = await umi.entities.list(type=EntityType.PROJECT, limit=10)
        if projects:
            project_parts = ["# Projects\n"]
            for p in projects:
                project_parts.append(f"## {p.name}\n\n{p.content or 'No description'}\n")
            content = "\n".join(project_parts)
        else:
            content = "# Projects\n\nNo projects yet."

        return ReadResourceResult(
            contents=[ResourceContents(uri=uri, text=content, mimeType="text/markdown")]
        )

    else:
        return ReadResourceResult(
            contents=[ResourceContents(uri=uri, text=f"Unknown resource: {uri}", mimeType="text/plain")]
        )


# =============================================================================
# Server Entry Point
# =============================================================================


async def run_server():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    """Main entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
