"""
Hiroba (広場) - Collaborative Rooms

Named shared spaces where multiple agents collaborate.
Content is replicated to all participants.

Usage:
    hiroba = HirobaManager(umi, federation)

    # Create a room
    room = await hiroba.create("project-x", description="Our project")

    # Invite members
    await hiroba.invite("project-x", "alice@rikai")

    # Share content to room
    await hiroba.share("project-x", content="Today's notes...")

    # Get room content
    content = await hiroba.get_content("project-x")
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class RoomRole(str, Enum):
    """Role within a room."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class SyncStatus(str, Enum):
    """Sync status for room content."""
    PENDING = "pending"
    SYNCED = "synced"
    CONFLICT = "conflict"
    ERROR = "error"


@dataclass
class RoomMember:
    """A member of a room."""
    agent_id: str
    role: RoomRole
    joined_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_sync: datetime | None = None


@dataclass
class RoomContent:
    """Content item in a room."""
    id: str
    room_id: str
    author_id: str
    content: str
    content_type: str = "note"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = None
    sync_status: SyncStatus = SyncStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Hiroba:
    """A collaborative room (広場)."""
    id: str
    name: str
    description: str = ""
    owner_id: str = "self"
    members: list[RoomMember] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = None
    settings: dict[str, Any] = field(default_factory=dict)


class HirobaManager:
    """
    Manages collaborative rooms (Hiroba).

    Rooms are named spaces where multiple agents can share content.
    Content is replicated to all members.
    """

    def __init__(self, umi_client, federation=None) -> None:
        self._umi = umi_client
        self._federation = federation
        self._rooms: dict[str, Hiroba] = {}

    async def create(
        self,
        name: str,
        description: str = "",
        settings: dict[str, Any] | None = None,
    ) -> Hiroba:
        """
        Create a new collaborative room.

        Args:
            name: Room name (used as identifier)
            description: Room description
            settings: Optional room settings

        Returns:
            Created room
        """
        room_id = name.lower().replace(" ", "-")

        # Check if room exists
        if room_id in self._rooms:
            raise ValueError(f"Room {name} already exists")

        room = Hiroba(
            id=room_id,
            name=name,
            description=description,
            owner_id="self",
            members=[
                RoomMember(agent_id="self", role=RoomRole.OWNER),
            ],
            settings=settings or {},
        )

        self._rooms[room_id] = room

        # Store in Umi
        if self._umi and hasattr(self._umi, 'storage'):
            await self._umi.storage.store_hiroba(
                id=room.id,
                name=room.name,
                description=room.description,
                owner_id=room.owner_id,
                settings=room.settings,
            )

        return room

    async def get(self, room_id: str) -> Hiroba | None:
        """Get a room by ID."""
        if room_id in self._rooms:
            return self._rooms[room_id]

        # Load from storage
        if self._umi and hasattr(self._umi, 'storage'):
            data = await self._umi.storage.get_hiroba(room_id)
            if data:
                room = Hiroba(
                    id=data["id"],
                    name=data["name"],
                    description=data.get("description", ""),
                    owner_id=data.get("owner_id", "self"),
                    created_at=data.get("created_at"),
                    settings=data.get("settings", {}),
                )

                # Load members
                members_data = await self._umi.storage.list_hiroba_members(room_id)
                room.members = [
                    RoomMember(
                        agent_id=m["agent_id"],
                        role=RoomRole(m["role"]),
                        joined_at=m.get("joined_at"),
                        last_sync=m.get("last_sync"),
                    )
                    for m in members_data
                ]

                self._rooms[room_id] = room
                return room

        return None

    async def list(self) -> list[Hiroba]:
        """List all rooms the user is a member of."""
        # Load from storage
        if self._umi and hasattr(self._umi, 'storage'):
            rooms_data = await self._umi.storage.list_hirobas()
            for data in rooms_data:
                if data["id"] not in self._rooms:
                    room = Hiroba(
                        id=data["id"],
                        name=data["name"],
                        description=data.get("description", ""),
                        owner_id=data.get("owner_id", "self"),
                        created_at=data.get("created_at"),
                        settings=data.get("settings", {}),
                    )
                    self._rooms[data["id"]] = room

        return list(self._rooms.values())

    async def delete(self, room_id: str) -> bool:
        """
        Delete a room (owner only).

        Args:
            room_id: Room to delete

        Returns:
            True if deleted
        """
        room = await self.get(room_id)
        if not room:
            return False

        # Only owner can delete
        if room.owner_id != "self":
            return False

        # Remove from memory
        self._rooms.pop(room_id, None)

        # Remove from storage
        if self._umi and hasattr(self._umi, 'storage'):
            await self._umi.storage.delete_hiroba(room_id)

        return True

    async def invite(
        self,
        room_id: str,
        agent_id: str,
        role: RoomRole = RoomRole.MEMBER,
    ) -> bool:
        """
        Invite an agent to a room.

        Args:
            room_id: Room to invite to
            agent_id: Agent to invite
            role: Role to assign

        Returns:
            True if invited
        """
        room = await self.get(room_id)
        if not room:
            return False

        # Check if already a member
        if any(m.agent_id == agent_id for m in room.members):
            return False

        member = RoomMember(agent_id=agent_id, role=role)
        room.members.append(member)

        # Store membership
        if self._umi and hasattr(self._umi, 'storage'):
            await self._umi.storage.add_hiroba_member(
                room_id=room_id,
                agent_id=agent_id,
                role=role.value,
            )

        # Notify the invited agent (via federation)
        if self._federation:
            await self._notify_invitation(agent_id, room)

        return True

    async def leave(self, room_id: str, agent_id: str = "self") -> bool:
        """
        Leave a room.

        Args:
            room_id: Room to leave
            agent_id: Agent leaving (default: self)

        Returns:
            True if left
        """
        room = await self.get(room_id)
        if not room:
            return False

        # Owner cannot leave, must delete or transfer
        if room.owner_id == agent_id:
            return False

        # Remove from members
        room.members = [m for m in room.members if m.agent_id != agent_id]

        # Update storage
        if self._umi and hasattr(self._umi, 'storage'):
            await self._umi.storage.remove_hiroba_member(room_id, agent_id)

        return True

    async def share(
        self,
        room_id: str,
        content: str,
        content_type: str = "note",
        metadata: dict[str, Any] | None = None,
    ) -> RoomContent | None:
        """
        Share content to a room.

        Args:
            room_id: Room to share to
            content: Content to share
            content_type: Type of content
            metadata: Optional metadata

        Returns:
            Created content item
        """
        room = await self.get(room_id)
        if not room:
            return None

        # Check if user is a member
        if not any(m.agent_id == "self" for m in room.members):
            return None

        item = RoomContent(
            id=str(uuid4()),
            room_id=room_id,
            author_id="self",
            content=content,
            content_type=content_type,
            metadata=metadata or {},
        )

        # Store content
        if self._umi and hasattr(self._umi, 'storage'):
            await self._umi.storage.store_hiroba_content(
                id=item.id,
                room_id=item.room_id,
                author_id=item.author_id,
                content=item.content,
                content_type=item.content_type,
                metadata=item.metadata,
            )

        # Sync to other members
        await self._sync_to_members(room, item)

        return item

    async def get_content(
        self,
        room_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RoomContent]:
        """
        Get content from a room.

        Args:
            room_id: Room to get content from
            limit: Max items to return
            offset: Offset for pagination

        Returns:
            List of content items
        """
        room = await self.get(room_id)
        if not room:
            return []

        # Check if user is a member
        if not any(m.agent_id == "self" for m in room.members):
            return []

        # Load from storage
        if self._umi and hasattr(self._umi, 'storage'):
            items_data = await self._umi.storage.list_hiroba_content(
                room_id=room_id,
                limit=limit,
                offset=offset,
            )

            return [
                RoomContent(
                    id=item["id"],
                    room_id=item["room_id"],
                    author_id=item["author_id"],
                    content=item["content"],
                    content_type=item.get("content_type", "note"),
                    created_at=item.get("created_at"),
                    updated_at=item.get("updated_at"),
                    sync_status=SyncStatus(item.get("sync_status", "synced")),
                    metadata=item.get("metadata", {}),
                )
                for item in items_data
            ]

        return []

    async def sync(self, room_id: str) -> dict[str, int]:
        """
        Synchronize room content with all members.

        Args:
            room_id: Room to sync

        Returns:
            Sync statistics
        """
        room = await self.get(room_id)
        if not room:
            return {"error": 1}

        stats = {"pulled": 0, "pushed": 0, "conflicts": 0}

        for member in room.members:
            if member.agent_id == "self":
                continue

            # Pull from member
            pulled = await self._pull_from_member(room, member)
            stats["pulled"] += pulled

            # Push to member
            pushed = await self._push_to_member(room, member)
            stats["pushed"] += pushed

        return stats

    async def _sync_to_members(self, room: Hiroba, content: RoomContent) -> None:
        """Sync a content item to all room members."""
        if not self._federation:
            return

        for member in room.members:
            if member.agent_id == "self":
                continue

            try:
                success = await self._federation.share(
                    member.agent_id,
                    content=content.content,
                    content_type=content.content_type,
                )

                if success:
                    content.sync_status = SyncStatus.SYNCED
                else:
                    content.sync_status = SyncStatus.ERROR

            except Exception as e:
                logger.warning(f"Failed to sync content to {member.agent_id}: {e}")
                content.sync_status = SyncStatus.ERROR

    async def _pull_from_member(
        self,
        room: Hiroba,
        member: RoomMember,
    ) -> int:
        """Pull content from a member."""
        if not self._federation:
            return 0

        # Query member for room content
        result = await self._federation.query(
            member.agent_id,
            f"hiroba:{room.id}",
        )

        if not result.success:
            return 0

        # Parse and store new content
        # (Implementation depends on content format)
        return 0

    async def _push_to_member(
        self,
        room: Hiroba,
        member: RoomMember,
    ) -> int:
        """Push pending content to a member."""
        if not self._federation:
            return 0

        # Get pending content
        content_items = await self.get_content(room.id)
        pushed = 0

        for item in content_items:
            if item.sync_status == SyncStatus.PENDING:
                try:
                    success = await self._federation.share(
                        member.agent_id,
                        content=item.content,
                        content_type=item.content_type,
                    )

                    if success:
                        item.sync_status = SyncStatus.SYNCED
                        pushed += 1

                except Exception as e:
                    logger.warning(f"Failed to push content to {member.agent_id}: {e}")

        return pushed

    async def _notify_invitation(self, agent_id: str, room: Hiroba) -> None:
        """Notify an agent of a room invitation."""
        if not self._federation:
            return

        await self._federation.share(
            agent_id,
            content=f"You have been invited to room: {room.name}\n"
                    f"Description: {room.description}",
            content_type="notification",
        )
