"""
RikaiOS Federation

Agent-to-agent communication and collaborative spaces.

Components:
- Permissions: Access control for sharing context
- Agent Federation: MCP-based communication between agents
- Hiroba (広場): Collaborative rooms for shared context

Usage:
    from rikai.federation import (
        PermissionManager,
        AgentFederation,
        HirobaManager,
    )

    # Set up permissions
    permissions = PermissionManager(umi)
    await permissions.grant("projects/*", "alice@rikai", "read")

    # Connect to another agent
    federation = AgentFederation(umi)
    await federation.connect("alice@rikai.example.com")

    # Create a collaborative room
    hiroba = HirobaManager(umi, federation)
    room = await hiroba.create("our-project", "Shared workspace")
    await hiroba.invite("our-project", "alice@rikai")
"""

from rikai.federation.permissions import (
    Permission,
    AccessLevel,
    AccessRequest,
    PermissionManager,
    parse_permissions_yaml,
    load_permissions_from_file,
)
from rikai.federation.agent import (
    RemoteAgent,
    QueryResult,
    AgentFederation,
    FederatedSearch,
)
from rikai.federation.hiroba import (
    Hiroba,
    RoomRole,
    RoomMember,
    RoomContent,
    SyncStatus,
    HirobaManager,
)

__all__ = [
    # Permissions
    "Permission",
    "AccessLevel",
    "AccessRequest",
    "PermissionManager",
    "parse_permissions_yaml",
    "load_permissions_from_file",
    # Agent Federation
    "RemoteAgent",
    "QueryResult",
    "AgentFederation",
    "FederatedSearch",
    # Hiroba
    "Hiroba",
    "RoomRole",
    "RoomMember",
    "RoomContent",
    "SyncStatus",
    "HirobaManager",
]
