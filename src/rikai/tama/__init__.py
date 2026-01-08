"""
Tama (魂) - Your Digital Soul

The persistent AI agent that manages your context in RikaiOS.
Powered by Letta for self-editing memory and persistent state.

Usage:
    from rikai.tama import TamaAgent

    # Requires Letta server (self-hosted or cloud)
    # Set LETTA_BASE_URL for self-hosted, or LETTA_API_KEY for cloud
    async with TamaAgent() as tama:
        response = await tama.chat("What am I working on?")
        print(response.message)

Umi Tools:
    Tama can use these tools to interact with Umi:
    - umi_search: Semantic search across context lake
    - umi_get_entity: Get entity by ID
    - umi_list_entities: List entities by type
    - umi_store_memory: Store new information
    - umi_get_context: Get user context
"""

from rikai.tama.agent import TamaAgent, TamaConfig, TamaResponse
from rikai.tama.tools import UmiToolHandler, get_tool_definitions, get_tool_names

__all__ = [
    "TamaAgent",
    "TamaConfig",
    "TamaResponse",
    "UmiToolHandler",
    "get_tool_definitions",
    "get_tool_names",
]
