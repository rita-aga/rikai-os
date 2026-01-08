"""
Tests for Hiroba (広場) - Federation and collaborative rooms.

Tests permission management and room coordination.
"""

from uuid import uuid4

import pytest

from rikaios.core.models import AccessLevel


class TestPermissions:
    """Test permission management."""

    @pytest.mark.asyncio
    async def test_store_permission(self, postgres_adapter):
        """Test storing a federation permission."""
        perm_id = str(uuid4())

        result = await postgres_adapter.store_permission(
            id=perm_id,
            path="projects/ai/*",
            agent_id="agent-123",
            access="read",
            granted_by="self",
        )

        assert result["id"] == perm_id
        assert result["path"] == "projects/ai/*"
        assert result["agent_id"] == "agent-123"
        assert result["access"] == "read"

    @pytest.mark.asyncio
    async def test_list_permissions(self, postgres_adapter):
        """Test listing permissions."""
        # Store multiple permissions
        await postgres_adapter.store_permission(
            id=str(uuid4()),
            path="public/*",
            agent_id="agent-1",
            access="read",
            granted_by="self",
        )
        await postgres_adapter.store_permission(
            id=str(uuid4()),
            path="private/*",
            agent_id="agent-2",
            access="write",
            granted_by="self",
        )

        perms = await postgres_adapter.list_permissions()
        assert len(perms) >= 2

    @pytest.mark.asyncio
    async def test_list_permissions_by_agent(self, postgres_adapter):
        """Test listing permissions filtered by agent."""
        agent_id = "agent-test"

        await postgres_adapter.store_permission(
            id=str(uuid4()),
            path="data/*",
            agent_id=agent_id,
            access="read",
            granted_by="self",
        )

        perms = await postgres_adapter.list_permissions(agent_id=agent_id)
        assert all(p["agent_id"] == agent_id for p in perms)

    @pytest.mark.asyncio
    async def test_delete_permission(self, postgres_adapter):
        """Test deleting a permission."""
        perm_id = str(uuid4())

        await postgres_adapter.store_permission(
            id=perm_id,
            path="temp/*",
            agent_id="agent-temp",
            access="read",
            granted_by="self",
        )

        deleted = await postgres_adapter.delete_permission(perm_id)
        assert deleted is True


class TestAccessRequests:
    """Test access request management."""

    @pytest.mark.asyncio
    async def test_store_access_request(self, postgres_adapter):
        """Test storing an access request."""
        req_id = str(uuid4())

        result = await postgres_adapter.store_access_request(
            id=req_id,
            requester_id="agent-requester",
            path="projects/secret",
            access="read",
            reason="Need to collaborate",
        )

        assert result["id"] == req_id
        assert result["requester_id"] == "agent-requester"
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_access_request(self, postgres_adapter):
        """Test retrieving an access request."""
        req_id = str(uuid4())

        await postgres_adapter.store_access_request(
            id=req_id,
            requester_id="agent-req",
            path="data/sensitive",
            access="read",
        )

        result = await postgres_adapter.get_access_request(req_id)
        assert result is not None
        assert result["id"] == req_id

    @pytest.mark.asyncio
    async def test_update_access_request(self, postgres_adapter):
        """Test updating access request status."""
        req_id = str(uuid4())

        await postgres_adapter.store_access_request(
            id=req_id,
            requester_id="agent-update",
            path="test/*",
            access="read",
        )

        updated = await postgres_adapter.update_access_request(
            req_id,
            status="approved",
        )

        assert updated is True

        result = await postgres_adapter.get_access_request(req_id)
        assert result["status"] == "approved"


class TestAgentConnections:
    """Test agent connection management."""

    @pytest.mark.asyncio
    async def test_store_agent_connection(self, postgres_adapter):
        """Test storing a remote agent connection."""
        result = await postgres_adapter.store_agent_connection(
            agent_id="agent-remote",
            endpoint="https://agent.example.com",
            name="Remote Agent",
            metadata={"version": "1.0"},
        )

        assert result["agent_id"] == "agent-remote"
        assert result["endpoint"] == "https://agent.example.com"
        assert result["name"] == "Remote Agent"

    @pytest.mark.asyncio
    async def test_list_agent_connections(self, postgres_adapter):
        """Test listing all agent connections."""
        await postgres_adapter.store_agent_connection(
            agent_id="agent-1",
            endpoint="https://agent1.example.com",
        )
        await postgres_adapter.store_agent_connection(
            agent_id="agent-2",
            endpoint="https://agent2.example.com",
        )

        connections = await postgres_adapter.list_agent_connections()
        assert len(connections) >= 2

    @pytest.mark.asyncio
    async def test_delete_agent_connection(self, postgres_adapter):
        """Test deleting an agent connection."""
        await postgres_adapter.store_agent_connection(
            agent_id="agent-delete",
            endpoint="https://delete.example.com",
        )

        deleted = await postgres_adapter.delete_agent_connection("agent-delete")
        assert deleted is True


class TestHirobaRooms:
    """Test Hiroba room management."""

    @pytest.mark.asyncio
    async def test_store_hiroba(self, postgres_adapter):
        """Test creating a Hiroba room."""
        room_id = f"room-{uuid4().hex[:8]}"

        result = await postgres_adapter.store_hiroba(
            id=room_id,
            name="Test Room",
            description="A test collaboration room",
            owner_id="self",
        )

        assert result["id"] == room_id
        assert result["name"] == "Test Room"
        assert result["owner_id"] == "self"

    @pytest.mark.asyncio
    async def test_get_hiroba_by_id(self, postgres_adapter):
        """Test retrieving a Hiroba room by ID."""
        room_id = f"room-{uuid4().hex[:8]}"

        await postgres_adapter.store_hiroba(
            id=room_id,
            name="Retrieve Room",
            owner_id="self",
        )

        result = await postgres_adapter.get_hiroba_by_id(room_id)
        assert result is not None
        assert result["id"] == room_id

    @pytest.mark.asyncio
    async def test_list_hirobas(self, postgres_adapter):
        """Test listing all Hiroba rooms."""
        await postgres_adapter.store_hiroba(
            id=f"room-{uuid4().hex[:8]}",
            name="Room A",
            owner_id="self",
        )
        await postgres_adapter.store_hiroba(
            id=f"room-{uuid4().hex[:8]}",
            name="Room B",
            owner_id="self",
        )

        rooms = await postgres_adapter.list_hirobas()
        assert len(rooms) >= 2

    @pytest.mark.asyncio
    async def test_delete_hiroba(self, postgres_adapter):
        """Test deleting a Hiroba room."""
        room_id = f"room-{uuid4().hex[:8]}"

        await postgres_adapter.store_hiroba(
            id=room_id,
            name="Delete Room",
            owner_id="self",
        )

        deleted = await postgres_adapter.delete_hiroba(room_id)
        assert deleted is True


class TestHirobaMembers:
    """Test Hiroba membership management."""

    @pytest.mark.asyncio
    async def test_add_member(self, postgres_adapter):
        """Test adding a member to a Hiroba."""
        room_id = f"room-{uuid4().hex[:8]}"

        await postgres_adapter.store_hiroba(
            id=room_id,
            name="Member Test Room",
            owner_id="self",
        )

        result = await postgres_adapter.add_hiroba_member(
            room_id=room_id,
            agent_id="member-1",
            role="participant",
        )

        assert result["room_id"] == room_id
        assert result["agent_id"] == "member-1"
        assert result["role"] == "participant"

    @pytest.mark.asyncio
    async def test_list_members(self, postgres_adapter):
        """Test listing members of a Hiroba."""
        room_id = f"room-{uuid4().hex[:8]}"

        await postgres_adapter.store_hiroba(
            id=room_id,
            name="List Members Room",
            owner_id="self",
        )

        await postgres_adapter.add_hiroba_member(room_id, "member-1", "participant")
        await postgres_adapter.add_hiroba_member(room_id, "member-2", "observer")

        members = await postgres_adapter.list_hiroba_members(room_id)
        assert len(members) >= 2

    @pytest.mark.asyncio
    async def test_remove_member(self, postgres_adapter):
        """Test removing a member from a Hiroba."""
        room_id = f"room-{uuid4().hex[:8]}"

        await postgres_adapter.store_hiroba(
            id=room_id,
            name="Remove Member Room",
            owner_id="self",
        )

        await postgres_adapter.add_hiroba_member(room_id, "member-remove", "participant")

        removed = await postgres_adapter.remove_hiroba_member(room_id, "member-remove")
        assert removed is True


class TestHirobaContent:
    """Test Hiroba content management."""

    @pytest.mark.asyncio
    async def test_store_content(self, postgres_adapter):
        """Test storing content in a Hiroba."""
        room_id = f"room-{uuid4().hex[:8]}"

        await postgres_adapter.store_hiroba(
            id=room_id,
            name="Content Room",
            owner_id="self",
        )

        content_id = str(uuid4())
        result = await postgres_adapter.store_hiroba_content(
            id=content_id,
            room_id=room_id,
            author_id="author-1",
            content="Hello from the room!",
            content_type="note",
        )

        assert result["id"] == content_id
        assert result["room_id"] == room_id
        assert result["content"] == "Hello from the room!"

    @pytest.mark.asyncio
    async def test_list_content(self, postgres_adapter):
        """Test listing content in a Hiroba."""
        room_id = f"room-{uuid4().hex[:8]}"

        await postgres_adapter.store_hiroba(
            id=room_id,
            name="List Content Room",
            owner_id="self",
        )

        await postgres_adapter.store_hiroba_content(
            id=str(uuid4()),
            room_id=room_id,
            author_id="author-1",
            content="First message",
        )
        await postgres_adapter.store_hiroba_content(
            id=str(uuid4()),
            room_id=room_id,
            author_id="author-2",
            content="Second message",
        )

        content = await postgres_adapter.list_hiroba_content(room_id)
        assert len(content) >= 2
