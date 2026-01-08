"""
RikaiOS Servers

Server implementations for accessing RikaiOS:
- MCP Server: Model Context Protocol for AI agents
- REST API: HTTP API for applications and web clients
"""

from rikai.servers.mcp import server as mcp_server, main as mcp_main
from rikai.servers.api import app as api_app, main as api_main

__all__ = [
    "mcp_server",
    "mcp_main",
    "api_app",
    "api_main",
]
