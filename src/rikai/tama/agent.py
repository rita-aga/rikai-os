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
        Get tool definitions for the agent.

        NOTE: Custom tool definitions are not yet implemented.
        Letta agents use their built-in tools by default.
        Future versions may add custom Umi-specific tools for:
        - Direct entity creation/updates
        - Relationship management
        - Memory consolidation triggers

        Returns:
            Empty list (using Letta built-in tools only)
        """
        return []

    async def chat(self, message: str) -> TamaResponse:
        """
        Send a message to Tama and get a response.

        This is the main interface for interacting with Tama.
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

        # Extract response content
        response_text = ""
        tool_calls = []

        for msg in response.messages:
            if hasattr(msg, "content") and msg.content:
                response_text += msg.content
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                tool_calls.extend(msg.tool_calls)

        return TamaResponse(
            message=response_text,
            tool_calls=tool_calls,
            context_used=context_results,
            metadata={"agent_id": self._agent_id},
        )

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
