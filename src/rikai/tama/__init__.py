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
"""

from rikai.tama.agent import TamaAgent, TamaConfig, TamaResponse

__all__ = ["TamaAgent", "TamaConfig", "TamaResponse"]
