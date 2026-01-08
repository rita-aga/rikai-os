"""
Tama (魂) - Your Digital Soul

The persistent AI agent that manages your context in RikaiOS.
Powered by Letta for self-editing memory and persistent state.

Tama capabilities:
1. Passive   - Ingests, organizes, answers queries
2. Proactive - Notices patterns, surfaces insights
3. Active    - Takes actions on your behalf (with consent)
4. Orchestrates - Delegates to specialized sub-agents
"""

import asyncio
import logging
import os
from typing import Any, AsyncIterator
from dataclasses import dataclass, field

from rikai.core.config import get_config, RikaiConfig
from rikai.core.models import Entity, EntityType, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class TamaConfig:
    """Configuration for Tama agent."""

    # Letta configuration
    # Supports both Letta Cloud and self-hosted servers
    # Set LETTA_BASE_URL env var to use self-hosted (e.g., http://localhost:8283)
    letta_api_key: str | None = None
    letta_base_url: str | None = None  # None = use LETTA_BASE_URL env or default to cloud

    # Model configuration
    model: str = "anthropic/claude-sonnet-4-5-20250929"
    embedding_model: str = "openai/text-embedding-3-small"

    # Agent identity
    agent_name: str = "tama"

    # Memory configuration
    persona: str = """I am Tama (魂), your digital soul and personal context assistant.

I help you understand and navigate your knowledge, projects, and life.
I remember our conversations and learn about you over time.
I can search your context lake (Umi) to find relevant information.

I speak naturally and helpfully, like a knowledgeable friend who knows you well.
I respect your privacy and only share what you've allowed."""

    human_description: str = """The user of RikaiOS - I'm learning about them through our conversations.
I'll update this as I learn more about their preferences, projects, and goals."""

    def get_letta_base_url(self) -> str:
        """Get Letta base URL, preferring env var over config."""
        if self.letta_base_url:
            return self.letta_base_url
        return os.getenv("LETTA_BASE_URL", "https://api.letta.com")


@dataclass
class TamaMessage:
    """A message in a Tama conversation."""

    role: str  # "user", "assistant", "system", "tool"
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TamaResponse:
    """Response from Tama."""

    message: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    context_used: list[SearchResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class TamaAgent:
    """
    Tama - The persistent AI agent for RikaiOS.

    Uses Letta for agent runtime with self-editing memory.
    Connects to Umi for archival/long-term memory storage.
    """

    def __init__(
        self,
        config: TamaConfig | None = None,
        rikai_config: RikaiConfig | None = None,
    ) -> None:
        self._config = config or TamaConfig(
            letta_api_key=os.getenv("LETTA_API_KEY"),
        )
        self._rikai_config = rikai_config or get_config()
        self._client = None
        self._agent_id: str | None = None
        self._umi = None

    async def connect(self) -> None:
        """Connect to Letta and initialize/load the agent."""
        # Import here to avoid import errors if letta not installed
        try:
            from letta_client import Letta
        except ImportError:
            raise RuntimeError(
                "Letta client not installed. Install with: pip install letta-client"
            )

        base_url = self._config.get_letta_base_url()
        is_self_hosted = "api.letta.com" not in base_url

        # Self-hosted servers may not require API key
        if not self._config.letta_api_key and not is_self_hosted:
            raise RuntimeError(
                "LETTA_API_KEY not set. Get one at https://app.letta.com\n"
                "Or set LETTA_BASE_URL for self-hosted server."
            )

        # Initialize Letta client
        client_kwargs = {"base_url": base_url}
        if self._config.letta_api_key:
            client_kwargs["api_key"] = self._config.letta_api_key

        self._client = Letta(**client_kwargs)
        logger.info(f"Connected to Letta at {base_url}")

        # Try to find existing agent or create new one
        self._agent_id = await self._get_or_create_agent()

        # Connect to Umi for context retrieval
        from rikai.umi import UmiClient
        self._umi = UmiClient(self._rikai_config)
        await self._umi.connect()

    async def disconnect(self) -> None:
        """Disconnect from Letta and Umi."""
        if self._umi:
            await self._umi.disconnect()
        # Letta client doesn't need explicit disconnect

    async def __aenter__(self) -> "TamaAgent":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()

    async def _get_or_create_agent(self) -> str:
        """Get existing agent or create a new one."""
        if not self._client:
            raise RuntimeError("Not connected to Letta")

        # List existing agents to find ours (wrap sync call)
        agents = await asyncio.to_thread(self._client.agents.list)
        for agent in agents:
            if agent.name == self._config.agent_name:
                logger.info(f"Found existing Tama agent: {agent.id}")
                return agent.id

        # Create new agent (wrap sync call)
        logger.info("Creating new Tama agent")
        agent_state = await asyncio.to_thread(
            self._client.agents.create,
            name=self._config.agent_name,
            model=self._config.model,
            embedding=self._config.embedding_model,
            memory_blocks=[
                {
                    "label": "persona",
                    "value": self._config.persona,
                },
                {
                    "label": "human",
                    "value": self._config.human_description,
                },
            ],
            tools=self._get_tool_definitions(),
        )

        logger.info(f"Created Tama agent: {agent_state.id}")
        return agent_state.id

    def _get_tool_definitions(self) -> list[str]:
        """
        Get tool names for the agent.

        Returns Letta built-in tools plus Umi tool names.
        Umi tools are executed locally by TamaAgent when called.

        Returns:
            List of tool names
        """
        from rikai.tama.tools import get_tool_names

        # Letta built-in tools
        builtin_tools = ["memory", "conversation_search"]

        # Umi tools (will be handled locally)
        umi_tools = get_tool_names()

        return builtin_tools + umi_tools

    def _get_tool_handler(self):
        """Get the Umi tool handler (lazy initialization)."""
        if not hasattr(self, "_tool_handler") or self._tool_handler is None:
            from rikai.tama.tools import UmiToolHandler
            if self._umi:
                self._tool_handler = UmiToolHandler(self._umi)
            else:
                self._tool_handler = None
        return self._tool_handler

    async def chat(self, message: str) -> TamaResponse:
        """
        Send a message to Tama and get a response.

        This is the main interface for interacting with Tama.
        Handles Umi tool calls locally when requested by the agent.
        """
        if not self._client or not self._agent_id:
            raise RuntimeError("Not connected. Use 'async with TamaAgent()' or call connect().")

        # Search Umi for relevant context
        context_results = []
        if self._umi:
            try:
                context_results = await self._umi.search(message, limit=5)
            except Exception as e:
                logger.warning(f"Context search failed: {e}")
                # Continue without context

        # Build context string for the message
        context_str = ""
        if context_results:
            context_str = "\n\n[Relevant context from your knowledge base:]\n"
            for result in context_results:
                context_str += f"- {result.content[:200]}...\n"

        # Send message to Letta agent
        full_message = message
        if context_str:
            full_message = f"{message}\n{context_str}"

        # Wrap sync Letta call
        response = await asyncio.to_thread(
            self._client.agents.messages.create,
            agent_id=self._agent_id,
            messages=[{"role": "user", "content": full_message}],
        )

        # Extract response content and handle tool calls
        response_text = ""
        tool_calls = []
        tool_results = []

        for msg in response.messages:
            if hasattr(msg, "content") and msg.content:
                response_text += msg.content
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                tool_calls.extend(msg.tool_calls)

        # Execute Umi tools locally if called
        if tool_calls:
            tool_handler = self._get_tool_handler()
            if tool_handler:
                tool_results = await self._execute_umi_tools(tool_calls, tool_handler)

                # If we executed tools, include results in response
                if tool_results:
                    tool_summary = self._format_tool_results(tool_results)
                    if tool_summary:
                        response_text += f"\n\n{tool_summary}"

        return TamaResponse(
            message=response_text,
            tool_calls=tool_calls,
            context_used=context_results,
            metadata={
                "agent_id": self._agent_id,
                "tool_results": tool_results,
            },
        )

    async def _execute_umi_tools(
        self, tool_calls: list, tool_handler
    ) -> list[dict]:
        """Execute Umi tools locally and return results."""
        from rikai.tama.tools import get_tool_names

        umi_tool_names = set(get_tool_names())
        results = []

        for call in tool_calls:
            tool_name = getattr(call, "name", None) or call.get("name")
            if not tool_name:
                continue

            # Only handle Umi tools locally
            if tool_name not in umi_tool_names:
                continue

            # Get arguments
            args = getattr(call, "arguments", None) or call.get("arguments", {})
            if isinstance(args, str):
                import json
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}

            # Execute the tool
            logger.info(f"Executing Umi tool: {tool_name}")
            result = await tool_handler.execute(tool_name, args)
            results.append({
                "tool": tool_name,
                "result": result,
            })

        return results

    def _format_tool_results(self, tool_results: list[dict]) -> str:
        """Format tool results for inclusion in response."""
        if not tool_results:
            return ""

        parts = ["[Tool Results]"]
        for tr in tool_results:
            tool_name = tr["tool"]
            result = tr["result"]

            if result.get("success"):
                if "results" in result:
                    # Search results
                    count = result.get("count", 0)
                    parts.append(f"- {tool_name}: Found {count} results")
                elif "entity" in result:
                    # Entity details
                    entity = result["entity"]
                    parts.append(f"- {tool_name}: {entity.get('name', 'Unknown')}")
                elif "entities" in result:
                    # Entity list
                    count = result.get("count", 0)
                    parts.append(f"- {tool_name}: Listed {count} entities")
                elif "message" in result:
                    # Store result
                    parts.append(f"- {tool_name}: {result['message']}")
                elif "context" in result:
                    # Context result
                    parts.append(f"- {tool_name}: Retrieved user context")
                else:
                    parts.append(f"- {tool_name}: Success")
            else:
                error = result.get("error", "Unknown error")
                parts.append(f"- {tool_name}: Error - {error}")

        return "\n".join(parts)

    async def chat_with_image(
        self,
        image_bytes: bytes,
        text: str | None = None,
        image_media_type: str = "image/png",
        platform: str = "direct",
        sender: str = "user",
    ) -> TamaResponse:
        """
        Send a message with an image to Tama.

        Images are processed through Claude Vision (Tama's "eyes")
        and converted to descriptions before being sent to Letta.

        Args:
            image_bytes: Raw image data
            text: Optional accompanying text
            image_media_type: MIME type (image/png, image/jpeg, etc.)
            platform: Source platform (telegram, slack, direct)
            sender: Who sent the message

        Returns:
            TamaResponse with Tama's understanding and response
        """
        from rikai.connectors.messaging import prepare_message_for_tama

        # Prepare the message (describe image)
        processed = await prepare_message_for_tama(
            text=text,
            image_bytes=image_bytes,
            image_media_type=image_media_type,
            platform=platform,
            sender=sender,
        )

        logger.info(f"Processed image from {platform}: {processed.metadata.get('image_description', '')[:100]}...")

        # Send to Tama
        response = await self.chat(processed.text)

        # Add image metadata to response
        response.metadata["image_processed"] = True
        response.metadata["image_description"] = processed.metadata.get("image_description")
        response.metadata["platform"] = platform

        return response

    async def stream_chat(self, message: str) -> AsyncIterator[str]:
        """
        Stream a response from Tama.

        Yields chunks of the response as they arrive.

        Note: True streaming depends on Letta's streaming support.
        Currently simulates streaming by yielding the response in chunks.
        """
        if not self._client or not self._agent_id:
            raise RuntimeError("Not connected.")

        # Get full response first
        response = await self.chat(message)

        # Simulate streaming by yielding in chunks
        # This provides a streaming-like interface while we wait for
        # Letta to support true streaming
        chunk_size = 50  # characters per chunk
        text = response.message
        for i in range(0, len(text), chunk_size):
            yield text[i:i + chunk_size]
            # Small delay to simulate streaming
            await asyncio.sleep(0.01)

    async def update_memory(self, key: str, value: str) -> None:
        """
        Update a memory block in Tama's core memory.

        Args:
            key: Memory block label (e.g., "persona", "human")
            value: New value for the memory block
        """
        if not self._client or not self._agent_id:
            raise RuntimeError("Not connected.")

        # Get current agent state (wrap sync call)
        agent = await asyncio.to_thread(
            self._client.agents.retrieve,
            self._agent_id,
        )

        # Find and update the memory block
        for block in agent.memory_blocks:
            if block.label == key:
                await asyncio.to_thread(
                    self._client.agents.memory.update_block,
                    agent_id=self._agent_id,
                    block_id=block.id,
                    value=value,
                )
                logger.info(f"Updated memory block '{key}'")
                return

        raise ValueError(f"Memory block '{key}' not found")

    async def get_memory(self) -> dict[str, str]:
        """Get all memory blocks from Tama."""
        if not self._client or not self._agent_id:
            raise RuntimeError("Not connected.")

        # Wrap sync call
        agent = await asyncio.to_thread(
            self._client.agents.retrieve,
            self._agent_id,
        )

        return {
            block.label: block.value
            for block in agent.memory_blocks
        }

    async def learn(self, content: str, source: str = "user") -> None:
        """
        Add new information to Tama's knowledge.

        This stores the content in Umi and optionally updates
        Tama's memory if it's important.
        """
        if not self._umi:
            raise RuntimeError("Not connected to Umi.")

        # Store in Umi as a note entity
        await self._umi.entities.create(
            type=EntityType.NOTE,
            name=f"Learning from {source}",
            content=content,
            metadata={"source": source},
        )
        logger.info(f"Stored learning from {source}")

    @property
    def agent_id(self) -> str | None:
        """Get the Letta agent ID."""
        return self._agent_id
