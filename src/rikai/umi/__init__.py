"""
Umi (海) - The Context Lake

Umi is the "sea" of your knowledge - the external storage layer for RikaiOS.
It stores all your context data:
- Entities (self, projects, people, topics)
- Documents (chats, docs, voice transcripts)
- Vectors (embeddings for semantic search)

Usage:
    from rikai.umi import UmiClient, get_umi

    # As context manager
    async with UmiClient() as umi:
        entity = await umi.entities.create(
            type=EntityType.PROJECT,
            name="RikaiOS",
            content="Personal context OS"
        )
        results = await umi.search("What projects am I working on?")

    # Or with get_umi helper
    async with get_umi() as umi:
        ...
"""

from rikai.umi.client import UmiClient, get_umi

__all__ = ["UmiClient", "get_umi"]
