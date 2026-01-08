"""
Permission Scoping System

Controls what parts of your context can be shared with other agents.

Usage:
    permissions = PermissionManager(umi)

    # Grant access to a path
    await permissions.grant("projects/rikaios/*", agent_id="alice@rikai", access="read")

    # Check access
    can_read = await permissions.check("projects/rikaios/readme", "alice@rikai", "read")

    # List permissions
    grants = await permissions.list_grants(agent_id="alice@rikai")
"""

import fnmatch
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any
from uuid import uuid4


class AccessLevel(str, Enum):
    """Access level for permissions."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


@dataclass
class Permission:
    """A permission grant."""
    id: str
    path: str  # Path pattern (supports wildcards)
    agent_id: str  # Grantee agent ID (or "*" for public)
    access: AccessLevel
    granted_by: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessRequest:
    """A request for access from another agent."""
    id: str
    requester_id: str
    path: str
    access: AccessLevel
    reason: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: str = "pending"  # pending, approved, denied


class PermissionManager:
    """
    Manages permission grants for federated access.

    Permissions use path patterns that support wildcards:
    - "projects/*" - All projects
    - "projects/rikaios/*" - Everything under rikaios project
    - "public/*" - Public content
    - "*" - Everything (full access)
    """

    def __init__(self, umi_client) -> None:
        self._umi = umi_client
        self._cache: dict[str, list[Permission]] = {}

    async def grant(
        self,
        path: str,
        agent_id: str,
        access: AccessLevel | str = AccessLevel.READ,
        granted_by: str = "self",
        expires_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Permission:
        """
        Grant access to a path for an agent.

        Args:
            path: Path pattern (supports wildcards like "projects/*")
            agent_id: Agent to grant access to ("*" for public)
            access: Access level (read, write, admin)
            granted_by: ID of granter
            expires_at: Optional expiration time
            metadata: Optional metadata

        Returns:
            Created permission
        """
        if isinstance(access, str):
            access = AccessLevel(access)

        permission = Permission(
            id=str(uuid4()),
            path=path,
            agent_id=agent_id,
            access=access,
            granted_by=granted_by,
            expires_at=expires_at,
            metadata=metadata or {},
        )

        # Store in Umi (via postgres adapter)
        if self._umi and hasattr(self._umi, 'storage'):
            await self._umi.storage.store_permission(
                id=permission.id,
                path=permission.path,
                agent_id=permission.agent_id,
                access=permission.access.value,
                granted_by=permission.granted_by,
                expires_at=permission.expires_at,
                metadata=permission.metadata,
            )

        # Invalidate cache
        self._cache.pop(agent_id, None)

        return permission

    async def revoke(self, permission_id: str) -> bool:
        """
        Revoke a permission.

        Args:
            permission_id: ID of permission to revoke

        Returns:
            True if revoked, False if not found
        """
        if self._umi and hasattr(self._umi, 'storage'):
            await self._umi.storage.delete_permission(permission_id)

        # Invalidate entire cache
        self._cache.clear()

        return True

    async def check(
        self,
        path: str,
        agent_id: str,
        access: AccessLevel | str = AccessLevel.READ,
    ) -> bool:
        """
        Check if an agent has access to a path.

        Args:
            path: Path to check
            agent_id: Agent requesting access
            access: Required access level

        Returns:
            True if access is allowed
        """
        if isinstance(access, str):
            access = AccessLevel(access)

        # Get agent's permissions
        permissions = await self.list_grants(agent_id=agent_id)

        # Also check public permissions
        if agent_id != "*":
            public_permissions = await self.list_grants(agent_id="*")
            permissions = permissions + public_permissions

        for perm in permissions:
            # Check if path matches
            if self._path_matches(path, perm.path):
                # Check if access level is sufficient
                if self._access_sufficient(perm.access, access):
                    # Check expiration
                    if perm.expires_at is None or perm.expires_at > datetime.now(UTC):
                        return True

        return False

    async def list_grants(
        self,
        agent_id: str | None = None,
        path: str | None = None,
    ) -> list[Permission]:
        """
        List permission grants.

        Args:
            agent_id: Filter by agent
            path: Filter by path pattern

        Returns:
            List of matching permissions
        """
        # Check cache first
        if agent_id and agent_id in self._cache:
            permissions = self._cache[agent_id]
        else:
            # Load from storage
            if self._umi and hasattr(self._umi, 'storage'):
                rows = await self._umi.storage.list_permissions(agent_id=agent_id)
                permissions = [
                    Permission(
                        id=row["id"],
                        path=row["path"],
                        agent_id=row["agent_id"],
                        access=AccessLevel(row["access"]),
                        granted_by=row["granted_by"],
                        created_at=row.get("created_at"),
                        expires_at=row.get("expires_at"),
                        metadata=row.get("metadata", {}),
                    )
                    for row in rows
                ]
            else:
                permissions = []

            # Cache if filtering by agent
            if agent_id:
                self._cache[agent_id] = permissions

        # Filter by path if specified
        if path:
            permissions = [p for p in permissions if self._path_matches(path, p.path)]

        return permissions

    async def request_access(
        self,
        requester_id: str,
        path: str,
        access: AccessLevel | str = AccessLevel.READ,
        reason: str | None = None,
    ) -> AccessRequest:
        """
        Request access to a path.

        Args:
            requester_id: Agent requesting access
            path: Path requesting access to
            access: Requested access level
            reason: Reason for request

        Returns:
            Access request
        """
        if isinstance(access, str):
            access = AccessLevel(access)

        request = AccessRequest(
            id=str(uuid4()),
            requester_id=requester_id,
            path=path,
            access=access,
            reason=reason,
        )

        # Store request for review
        if self._umi and hasattr(self._umi, 'storage'):
            await self._umi.storage.store_access_request(
                id=request.id,
                requester_id=request.requester_id,
                path=request.path,
                access=request.access.value,
                reason=request.reason,
            )

        return request

    async def approve_request(
        self,
        request_id: str,
        granted_by: str = "self",
        expires_at: datetime | None = None,
    ) -> Permission | None:
        """
        Approve an access request.

        Args:
            request_id: Request to approve
            granted_by: ID of approver
            expires_at: Optional expiration

        Returns:
            Created permission if approved
        """
        # Get request
        if self._umi and hasattr(self._umi, 'storage'):
            request_data = await self._umi.storage.get_access_request(request_id)
            if not request_data or request_data.get("status") != "pending":
                return None

            # Create permission
            permission = await self.grant(
                path=request_data["path"],
                agent_id=request_data["requester_id"],
                access=AccessLevel(request_data["access"]),
                granted_by=granted_by,
                expires_at=expires_at,
            )

            # Update request status
            await self._umi.storage.update_access_request(
                request_id,
                status="approved",
            )

            return permission

        return None

    async def deny_request(self, request_id: str, reason: str | None = None) -> bool:
        """
        Deny an access request.

        Args:
            request_id: Request to deny
            reason: Reason for denial

        Returns:
            True if denied
        """
        if self._umi and hasattr(self._umi, 'storage'):
            await self._umi.storage.update_access_request(
                request_id,
                status="denied",
                denial_reason=reason,
            )
            return True

        return False

    def _path_matches(self, path: str, pattern: str) -> bool:
        """Check if a path matches a pattern (supports wildcards)."""
        # Normalize paths
        path = path.strip("/")
        pattern = pattern.strip("/")

        # Use fnmatch for glob-style matching
        return fnmatch.fnmatch(path, pattern)

    def _access_sufficient(self, granted: AccessLevel, required: AccessLevel) -> bool:
        """Check if granted access level is sufficient."""
        # Access hierarchy: admin > write > read
        hierarchy = {
            AccessLevel.READ: 1,
            AccessLevel.WRITE: 2,
            AccessLevel.ADMIN: 3,
        }

        return hierarchy[granted] >= hierarchy[required]


def parse_permissions_yaml(yaml_content: str) -> list[dict[str, Any]]:
    """
    Parse a permissions YAML file.

    Format:
        sharing:
          - path: "projects/rikaios/*"
            with: ["alice@rikai", "bob@rikai"]
            access: read

          - path: "public/*"
            with: "*"
            access: read
    """
    import yaml

    data = yaml.safe_load(yaml_content)
    if not data or "sharing" not in data:
        return []

    permissions = []
    for item in data.get("sharing", []):
        path = item.get("path", "")
        agents = item.get("with", [])
        access = item.get("access", "read")

        # Normalize agents list
        if isinstance(agents, str):
            agents = [agents]

        for agent in agents:
            permissions.append({
                "path": path,
                "agent_id": agent,
                "access": access,
            })

    return permissions


async def load_permissions_from_file(
    permission_manager: PermissionManager,
    file_path: str,
) -> int:
    """
    Load permissions from a YAML file.

    Args:
        permission_manager: Permission manager instance
        file_path: Path to permissions YAML file

    Returns:
        Number of permissions loaded
    """
    from pathlib import Path

    path = Path(file_path).expanduser()
    if not path.exists():
        return 0

    content = path.read_text()
    permissions = parse_permissions_yaml(content)

    count = 0
    for perm in permissions:
        await permission_manager.grant(
            path=perm["path"],
            agent_id=perm["agent_id"],
            access=perm["access"],
        )
        count += 1

    return count
