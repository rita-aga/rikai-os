"""
Agent-to-Agent Federation

MCP-based communication between RikaiOS instances.

Usage:
    federation = AgentFederation(umi)

    # Connect to another agent
    await federation.connect("alice@rikai.example.com")

    # Query their context (with permission)
    result = await federation.query("alice@rikai", "What is Alice working on?")

    # List connected agents
    agents = await federation.list_connected()
"""

import logging
import httpx

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any
from urllib.parse import urlparse


@dataclass
class RemoteAgent:
    """A connected remote agent."""
    id: str  # e.g., "alice@rikai.example.com"
    name: str
    endpoint: str  # MCP endpoint URL
    public_key: str | None = None
    connected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_seen: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryResult:
    """Result from a remote query."""
    success: bool
    content: str | None = None
    source_agent: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentFederation:
    """
    Manages federation with other RikaiOS agents.

    Federation uses MCP (Model Context Protocol) for communication.
    Each agent exposes an MCP server that other agents can connect to.
    """

    def __init__(self, umi_client, self_id: str | None = None) -> None:
        self._umi = umi_client
        self._self_id = self_id or "local"
        self._connected: dict[str, RemoteAgent] = {}
        self._client: httpx.AsyncClient | None = None

    async def setup(self) -> None:
        """Initialize the federation manager."""
        self._client = httpx.AsyncClient(timeout=30.0)

    async def teardown(self) -> None:
        """Clean up resources."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def connect(
        self,
        agent_id: str,
        endpoint: str | None = None,
        token: str | None = None,
    ) -> RemoteAgent | None:
        """
        Connect to a remote agent.

        Args:
            agent_id: Agent identifier (e.g., "alice@rikai.example.com")
            endpoint: MCP endpoint URL (optional, can be derived from agent_id)
            token: Authentication token (optional)

        Returns:
            Connected agent info, or None if connection failed
        """
        # Derive endpoint from agent_id if not provided
        if not endpoint:
            endpoint = self._derive_endpoint(agent_id)

        if not endpoint:
            return None

        try:
            # Verify connection by calling health endpoint
            if not self._client:
                await self.setup()

            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"

            response = await self._client.get(
                f"{endpoint}/health",
                headers=headers,
            )

            if response.status_code != 200:
                return None

            # Get agent info
            info_response = await self._client.get(
                f"{endpoint}/",
                headers=headers,
            )
            agent_info = info_response.json() if info_response.status_code == 200 else {}

            agent = RemoteAgent(
                id=agent_id,
                name=agent_info.get("name", agent_id.split("@")[0]),
                endpoint=endpoint,
                metadata={
                    "token": token,
                    "version": agent_info.get("version"),
                },
            )

            self._connected[agent_id] = agent

            # Store connection in Umi for persistence
            if self._umi and hasattr(self._umi, 'storage'):
                await self._umi.storage.store_agent_connection(
                    agent_id=agent_id,
                    endpoint=endpoint,
                    name=agent.name,
                    metadata=agent.metadata,
                )

            return agent

        except Exception as e:
            logger.warning(f"Failed to connect to agent {agent_id}: {e}")
            return None

    async def disconnect(self, agent_id: str) -> bool:
        """
        Disconnect from a remote agent.

        Args:
            agent_id: Agent to disconnect from

        Returns:
            True if disconnected
        """
        if agent_id in self._connected:
            del self._connected[agent_id]

        if self._umi and hasattr(self._umi, 'storage'):
            await self._umi.storage.delete_agent_connection(agent_id)

        return True

    async def query(
        self,
        agent_id: str,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> QueryResult:
        """
        Query a remote agent's context.

        Args:
            agent_id: Agent to query
            query: Query string
            context: Optional context to include

        Returns:
            Query result
        """
        agent = self._connected.get(agent_id)
        if not agent:
            return QueryResult(
                success=False,
                error=f"Not connected to {agent_id}",
            )

        try:
            headers = {}
            if "token" in agent.metadata:
                headers["Authorization"] = f"Bearer {agent.metadata['token']}"

            response = await self._client.post(
                f"{agent.endpoint}/search",
                json={"query": query, "limit": 5},
                headers=headers,
            )

            if response.status_code != 200:
                return QueryResult(
                    success=False,
                    error=f"Query failed: {response.status_code}",
                )

            data = response.json()

            # Format results as content
            results = data.get("results", [])
            if results:
                content_parts = []
                for r in results:
                    content_parts.append(f"- {r.get('content', '')[:200]}")
                content = "\n".join(content_parts)
            else:
                content = "No results found."

            # Update last seen
            agent.last_seen = datetime.now(UTC)

            return QueryResult(
                success=True,
                content=content,
                source_agent=agent_id,
                metadata={"result_count": len(results)},
            )

        except Exception as e:
            return QueryResult(
                success=False,
                error=str(e),
            )

    async def share(
        self,
        agent_id: str,
        content: str,
        content_type: str = "note",
    ) -> bool:
        """
        Share content with a remote agent.

        Args:
            agent_id: Agent to share with
            content: Content to share
            content_type: Type of content (note, document, etc.)

        Returns:
            True if shared successfully
        """
        agent = self._connected.get(agent_id)
        if not agent:
            return False

        try:
            headers = {}
            if "token" in agent.metadata:
                headers["Authorization"] = f"Bearer {agent.metadata['token']}"

            response = await self._client.post(
                f"{agent.endpoint}/entities",
                json={
                    "type": content_type,
                    "name": f"Shared from {self._self_id}",
                    "content": content,
                    "metadata": {
                        "shared_by": self._self_id,
                        "shared_at": datetime.now(UTC).isoformat(),
                    },
                },
                headers=headers,
            )

            return response.status_code == 201

        except Exception as e:
            logger.warning(f"Failed to share content with {agent_id}: {e}")
            return False

    async def list_connected(self) -> list[RemoteAgent]:
        """List all connected agents."""
        # Load from storage if empty
        if not self._connected and self._umi and hasattr(self._umi, 'storage'):
            rows = await self._umi.storage.list_agent_connections()
            for row in rows:
                agent = RemoteAgent(
                    id=row["agent_id"],
                    name=row.get("name", ""),
                    endpoint=row["endpoint"],
                    connected_at=row.get("connected_at"),
                    metadata=row.get("metadata", {}),
                )
                self._connected[row["agent_id"]] = agent

        return list(self._connected.values())

    async def discover(self, query: str | None = None) -> list[dict[str, Any]]:
        """
        Discover other RikaiOS agents.

        NOTE: Agent discovery is not yet implemented. Future mechanisms may include:
        - DNS-based discovery (SRV records)
        - Registry lookup (central directory)
        - DHT-based discovery (distributed)
        - mDNS/Bonjour for local network

        Currently, agents must be connected manually using their agent_id.

        Args:
            query: Optional search query (unused - reserved for future)

        Returns:
            Empty list (discovery not implemented)
        """
        logger.info("Agent discovery not yet implemented - use manual connect with agent_id")
        return []

    def _derive_endpoint(self, agent_id: str) -> str | None:
        """Derive MCP endpoint from agent ID."""
        # Format: username@hostname -> https://hostname/mcp/username
        if "@" not in agent_id:
            return None

        username, hostname = agent_id.rsplit("@", 1)

        # Check if hostname already has protocol
        if hostname.startswith("http://") or hostname.startswith("https://"):
            parsed = urlparse(hostname)
            return f"{parsed.scheme}://{parsed.netloc}/api"

        # Default to HTTPS
        return f"https://{hostname}/api"


class FederatedSearch:
    """
    Search across federated agents.

    Aggregates results from multiple connected agents.
    """

    def __init__(self, federation: AgentFederation, umi_client) -> None:
        self._federation = federation
        self._umi = umi_client

    async def search(
        self,
        query: str,
        include_local: bool = True,
        include_remote: list[str] | None = None,
        limit: int = 10,
    ) -> list[QueryResult]:
        """
        Search across local and remote contexts.

        Args:
            query: Search query
            include_local: Include local Umi results
            include_remote: List of remote agents to include (None = all)
            limit: Max results per source

        Returns:
            Aggregated results
        """
        results = []

        # Local search
        if include_local and self._umi:
            local_results = await self._umi.search(query, limit=limit)
            for r in local_results:
                results.append(QueryResult(
                    success=True,
                    content=r.content,
                    source_agent="local",
                    metadata={
                        "score": r.score,
                        "source_type": r.source_type,
                    },
                ))

        # Remote search
        agents = await self._federation.list_connected()
        for agent in agents:
            if include_remote is not None and agent.id not in include_remote:
                continue

            result = await self._federation.query(agent.id, query)
            if result.success:
                results.append(result)

        return results
