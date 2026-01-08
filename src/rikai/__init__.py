"""
RikaiOS (理解OS) - Personal Context Operating System

A unified personal context layer that:
- Aggregates your entire digital life into one coherent, queryable space
- Is managed by a persistent AI agent (Tama) that organizes, summarizes, and acts on your behalf
- Stores context in Umi (海), the external context lake
- Exposes APIs (MCP + REST) for any agent/tool to query and update
- Federates with other users' RikaiOS instances via MCP-based sharing

Components:
- Umi (海) - Context Lake: External storage for all your context data
- Tama (魂) - Agent: Your personal AI soul that manages your context
- Hiroba (広場) - Plaza: Collaborative rooms for sharing with others
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
