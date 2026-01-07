"""
Tama (魂) - Your Digital Soul

The persistent AI agent that manages your context in RikaiOS.
Powered by Letta for self-editing memory and persistent state.

Usage:
    from rikaios.tama import TamaAgent, LocalTamaAgent

    # With Letta (requires LETTA_API_KEY)
    async with TamaAgent() as tama:
        response = await tama.chat("What am I working on?")
        print(response.message)

    # Local mode (requires ANTHROPIC_API_KEY)
    async with LocalTamaAgent() as tama:
        response = await tama.chat("What am I working on?")
        print(response.message)
"""

from rikaios.tama.agent import TamaAgent, LocalTamaAgent, TamaConfig, TamaResponse

__all__ = ["TamaAgent", "LocalTamaAgent", "TamaConfig", "TamaResponse"]
