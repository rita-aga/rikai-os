"""
RikaiOS REST API

FastAPI-based REST API for accessing RikaiOS context and services.

Endpoints:
- /health - Health check
- /entities - Entity CRUD operations
- /documents - Document operations
- /search - Semantic search
- /connectors - Connector management
- /tama - Agent interaction

Usage:
    uvicorn rikai.servers.api:app --reload

Or via CLI:
    rikai serve
"""

from contextlib import asynccontextmanager
from datetime import datetime, UTC
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rikai import __version__
from rikai.core.config import get_config
from rikai.core.models import EntityType, DocumentSource
from rikai.umi import UmiClient


# =============================================================================
# Request/Response Models
# =============================================================================


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = __version__
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EntityCreate(BaseModel):
    """Create entity request."""
    type: str = Field(..., description="Entity type: self, project, person, topic, note, task")
    name: str = Field(..., description="Entity name")
    content: str | None = Field(None, description="Entity content")
    metadata: dict[str, Any] = Field(default_factory=dict)


class EntityUpdate(BaseModel):
    """Update entity request."""
    name: str | None = None
    content: str | None = None
    metadata: dict[str, Any] | None = None


class EntityResponse(BaseModel):
    """Entity response."""
    id: str
    type: str
    name: str
    content: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DocumentCreate(BaseModel):
    """Create document request."""
    source: str = Field(..., description="Document source: chat, docs, social, voice, file, git")
    title: str
    content: str
    content_type: str = "text/plain"
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentResponse(BaseModel):
    """Document response."""
    id: str
    source: str
    title: str
    content_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class RelationCreate(BaseModel):
    """Create entity relation request."""
    source_id: str = Field(..., description="Source entity ID")
    target_id: str = Field(..., description="Target entity ID")
    relation_type: str = Field(..., description="Type of relationship (e.g., 'related_to', 'part_of', 'depends_on')")
    metadata: dict[str, Any] = Field(default_factory=dict)


class RelationResponse(BaseModel):
    """Entity relation response."""
    id: str
    source_id: str
    target_id: str
    relation_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class SearchRequest(BaseModel):
    """Search request."""
    query: str = Field(..., description="Search query")
    limit: int = Field(10, ge=1, le=100)
    entity_type: str | None = None


class SearchResult(BaseModel):
    """Single search result."""
    content: str
    source_type: str
    source_id: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Search response."""
    query: str
    results: list[SearchResult]
    count: int


class TamaChatRequest(BaseModel):
    """Tama chat request."""
    message: str = Field(..., description="Message to send to Tama")


class TamaChatResponse(BaseModel):
    """Tama chat response."""
    message: str
    context_used: list[dict[str, Any]] = Field(default_factory=list, description="Context items used in generating the response")


class ConnectorStatus(BaseModel):
    """Connector status response."""
    name: str
    status: str
    mode: str
    last_sync: datetime | None = None


class ConnectorSyncRequest(BaseModel):
    """Connector sync request."""
    connector: str = Field(..., description="Connector name: files, git, chat, google")


class ConnectorSyncResponse(BaseModel):
    """Connector sync response."""
    success: bool
    documents_created: int = 0
    entities_created: int = 0
    errors: list[str] = Field(default_factory=list)


# =============================================================================
# App Lifecycle
# =============================================================================


_umi: UmiClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global _umi
    _umi = UmiClient(get_config())
    await _umi.connect()
    yield
    if _umi:
        await _umi.disconnect()


# =============================================================================
# FastAPI App
# =============================================================================


app = FastAPI(
    title="RikaiOS API",
    description="REST API for RikaiOS - Personal Context Operating System",
    version=__version__,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_umi() -> UmiClient:
    """Get Umi client."""
    if _umi is None:
        raise HTTPException(status_code=503, detail="Umi not initialized")
    return _umi


# =============================================================================
# Health Endpoint
# =============================================================================


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API info."""
    return {
        "name": "RikaiOS API",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }


# =============================================================================
# Entity Endpoints
# =============================================================================


@app.get("/entities", response_model=list[EntityResponse], tags=["Entities"])
async def list_entities(
    type: str | None = Query(None, description="Filter by entity type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List entities with optional type filter."""
    umi = get_umi()

    entity_type = EntityType(type) if type else None
    # TODO: Add offset support to EntityManager.list()
    entities = await umi.entities.list(type=entity_type, limit=limit)

    return [
        EntityResponse(
            id=str(e.id),
            type=e.type.value,
            name=e.name,
            content=e.content,
            metadata=e.metadata or {},
            created_at=e.created_at,
            updated_at=e.updated_at,
        )
        for e in entities
    ]


@app.post("/entities", response_model=EntityResponse, status_code=201, tags=["Entities"])
async def create_entity(entity: EntityCreate):
    """Create a new entity."""
    umi = get_umi()

    try:
        entity_type = EntityType(entity.type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity type: {entity.type}. Valid types: {[t.value for t in EntityType]}",
        )

    created = await umi.entities.create(
        type=entity_type,
        name=entity.name,
        content=entity.content,
        metadata=entity.metadata,
    )

    return EntityResponse(
        id=str(created.id),
        type=created.type.value,
        name=created.name,
        content=created.content,
        metadata=created.metadata or {},
        created_at=created.created_at,
        updated_at=created.updated_at,
    )


@app.get("/entities/{entity_id}", response_model=EntityResponse, tags=["Entities"])
async def get_entity(entity_id: str):
    """Get a specific entity by ID."""
    umi = get_umi()

    entity = await umi.entities.get(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    return EntityResponse(
        id=str(entity.id),
        type=entity.type.value,
        name=entity.name,
        content=entity.content,
        metadata=entity.metadata or {},
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


@app.patch("/entities/{entity_id}", response_model=EntityResponse, tags=["Entities"])
async def update_entity(entity_id: str, update: EntityUpdate):
    """Update an entity."""
    umi = get_umi()

    entity = await umi.entities.get(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    updated = await umi.entities.update(
        entity_id,
        name=update.name,
        content=update.content,
        metadata=update.metadata,
    )

    return EntityResponse(
        id=str(updated.id),
        type=updated.type.value,
        name=updated.name,
        content=updated.content,
        metadata=updated.metadata or {},
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@app.delete("/entities/{entity_id}", status_code=204, tags=["Entities"])
async def delete_entity(entity_id: str):
    """Delete an entity."""
    umi = get_umi()

    entity = await umi.entities.get(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    await umi.entities.delete(entity_id)


# =============================================================================
# Entity Relation Endpoints
# =============================================================================


@app.get("/entities/{entity_id}/relations", response_model=list[RelationResponse], tags=["Relations"])
async def get_entity_relations(
    entity_id: str,
    direction: str = Query("both", description="Direction: 'outgoing', 'incoming', or 'both'"),
    relation_type: str | None = Query(None, description="Filter by relation type"),
):
    """Get relations for an entity."""
    umi = get_umi()

    entity = await umi.entities.get(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    relations = await umi.storage.get_entity_relations(
        entity_id,
        direction=direction,
        relation_type=relation_type,
    )

    return [
        RelationResponse(
            id=str(r.id),
            source_id=str(r.source_id),
            target_id=str(r.target_id),
            relation_type=r.relation_type,
            metadata=r.metadata or {},
            created_at=r.created_at,
        )
        for r in relations
    ]


@app.get("/entities/{entity_id}/related", response_model=list[EntityResponse], tags=["Relations"])
async def get_related_entities(
    entity_id: str,
    relation_type: str | None = Query(None, description="Filter by relation type"),
    limit: int = Query(50, ge=1, le=100),
):
    """Get entities related to the given entity."""
    umi = get_umi()

    entity = await umi.entities.get(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    related = await umi.storage.get_related_entities(
        entity_id,
        relation_type=relation_type,
        limit=limit,
    )

    return [
        EntityResponse(
            id=str(e.id),
            type=e.type.value,
            name=e.name,
            content=e.content,
            metadata=e.metadata or {},
            created_at=e.created_at,
            updated_at=e.updated_at,
        )
        for e in related
    ]


@app.post("/relations", response_model=RelationResponse, status_code=201, tags=["Relations"])
async def create_relation(relation: RelationCreate):
    """Create a relationship between two entities."""
    umi = get_umi()

    # Verify both entities exist
    source = await umi.entities.get(relation.source_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Source entity {relation.source_id} not found")

    target = await umi.entities.get(relation.target_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Target entity {relation.target_id} not found")

    try:
        created = await umi.storage.create_entity_relation(
            source_id=relation.source_id,
            target_id=relation.target_id,
            relation_type=relation.relation_type,
            metadata=relation.metadata,
        )
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail="This relation already exists",
            )
        raise HTTPException(status_code=500, detail=str(e))

    return RelationResponse(
        id=str(created.id),
        source_id=str(created.source_id),
        target_id=str(created.target_id),
        relation_type=created.relation_type,
        metadata=created.metadata or {},
        created_at=created.created_at,
    )


@app.delete("/relations/{relation_id}", status_code=204, tags=["Relations"])
async def delete_relation(relation_id: str):
    """Delete a relation by ID."""
    umi = get_umi()
    await umi.storage.delete_entity_relation(relation_id)


# =============================================================================
# Document Endpoints
# =============================================================================


@app.get("/documents", response_model=list[DocumentResponse], tags=["Documents"])
async def list_documents(
    source: str | None = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List documents with optional source filter."""
    umi = get_umi()

    doc_source = DocumentSource(source) if source else None
    documents = await umi.documents.list(source=doc_source, limit=limit, offset=offset)

    return [
        DocumentResponse(
            id=str(d.id),
            source=d.source.value,
            title=d.title,
            content_type=d.content_type or "text/plain",
            metadata=d.metadata or {},
            created_at=d.created_at,
        )
        for d in documents
    ]


@app.post("/documents", response_model=DocumentResponse, status_code=201, tags=["Documents"])
async def create_document(doc: DocumentCreate):
    """Store a new document."""
    umi = get_umi()

    try:
        doc_source = DocumentSource(doc.source)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source: {doc.source}. Valid sources: {[s.value for s in DocumentSource]}",
        )

    created = await umi.documents.store(
        source=doc_source,
        title=doc.title,
        content=doc.content,
        content_type=doc.content_type,
        metadata=doc.metadata,
    )

    return DocumentResponse(
        id=str(created.id),
        source=created.source.value,
        title=created.title,
        content_type=created.content_type or "text/plain",
        metadata=created.metadata or {},
        created_at=created.created_at,
    )


@app.get("/documents/{document_id}", response_model=DocumentResponse, tags=["Documents"])
async def get_document(document_id: str):
    """Get a specific document by ID."""
    umi = get_umi()

    doc = await umi.documents.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=str(doc.id),
        source=doc.source.value,
        title=doc.title,
        content_type=doc.content_type or "text/plain",
        metadata=doc.metadata or {},
        created_at=doc.created_at,
    )


@app.delete("/documents/{document_id}", status_code=204, tags=["Documents"])
async def delete_document(document_id: str):
    """Delete a document."""
    umi = get_umi()

    doc = await umi.documents.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    await umi.documents.delete(document_id)


# =============================================================================
# Search Endpoint
# =============================================================================


@app.post("/search", response_model=SearchResponse, tags=["Search"])
async def search(request: SearchRequest):
    """Semantic search across the context lake."""
    umi = get_umi()

    results = await umi.search(request.query, limit=request.limit)

    return SearchResponse(
        query=request.query,
        results=[
            SearchResult(
                content=r.content,
                source_type=r.source_type,
                source_id=r.source_id,
                score=r.score,
                metadata=r.metadata or {},
            )
            for r in results
        ],
        count=len(results),
    )


@app.get("/search", response_model=SearchResponse, tags=["Search"])
async def search_get(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100),
):
    """Semantic search (GET endpoint)."""
    return await search(SearchRequest(query=q, limit=limit))


# =============================================================================
# Tama (Agent) Endpoints
# =============================================================================


@app.post("/tama/chat", response_model=TamaChatResponse, tags=["Tama"])
async def tama_chat(request: TamaChatRequest):
    """Chat with Tama (your personal agent).

    Requires Letta server (self-hosted or cloud).
    Set LETTA_BASE_URL for self-hosted or LETTA_API_KEY for cloud.
    """
    try:
        from rikai.tama.agent import TamaAgent

        async with TamaAgent() as tama:
            response = await tama.chat(request.message)

        # Convert SearchResult objects to dicts for JSON serialization
        context_items = [
            {
                "content": r.content[:200] if r.content else "",
                "source_type": r.source_type,
                "score": r.score,
            }
            for r in response.context_used
        ] if response.context_used else []

        return TamaChatResponse(
            message=response.message,
            context_used=context_items,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Connector Endpoints
# =============================================================================


@app.get("/connectors", response_model=list[ConnectorStatus], tags=["Connectors"])
async def list_connectors():
    """List available connectors and their status."""
    from rikai.connectors import (
        FilesConnector,
        GitConnector,
        ChatConnector,
        GoogleConnector,
    )

    connectors = [
        ("files", FilesConnector()),
        ("git", GitConnector()),
        ("chat", ChatConnector()),
        ("google", GoogleConnector()),
    ]

    return [
        ConnectorStatus(
            name=name,
            status=connector.status.value,
            mode=connector.mode.value,
            last_sync=connector.state.last_sync,
        )
        for name, connector in connectors
    ]


@app.post("/connectors/sync", response_model=ConnectorSyncResponse, tags=["Connectors"])
async def sync_connector(request: ConnectorSyncRequest):
    """Trigger a sync for a specific connector."""
    umi = get_umi()

    connector_map = {
        "files": "rikai.connectors.FilesConnector",
        "git": "rikai.connectors.GitConnector",
        "chat": "rikai.connectors.ChatConnector",
        "google": "rikai.connectors.GoogleConnector",
    }

    if request.connector not in connector_map:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown connector: {request.connector}. Available: {list(connector_map.keys())}",
        )

    try:
        # Import and instantiate the connector
        if request.connector == "files":
            from rikai.connectors import FilesConnector
            connector = FilesConnector()
        elif request.connector == "git":
            from rikai.connectors import GitConnector
            connector = GitConnector()
        elif request.connector == "chat":
            from rikai.connectors import ChatConnector
            connector = ChatConnector()
        elif request.connector == "google":
            from rikai.connectors import GoogleConnector
            connector = GoogleConnector()
        else:
            raise HTTPException(status_code=400, detail=f"Unknown connector: {request.connector}")

        # Initialize and sync
        await connector.initialize(umi)
        result = await connector.sync()

        return ConnectorSyncResponse(
            success=result.success,
            documents_created=result.documents_created,
            entities_created=result.entities_created,
            errors=result.errors,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Webhook Endpoints (Telegram, Slack)
# =============================================================================


# Global Tama agent for webhooks (initialized lazily)
_tama = None


async def get_tama():
    """Get or create Tama agent for webhook processing."""
    global _tama
    if _tama is None:
        from rikai.tama.agent import TamaAgent
        _tama = TamaAgent()
        await _tama.connect()
    return _tama


@app.post("/webhooks/telegram", tags=["Webhooks"])
async def telegram_webhook(payload: dict):
    """
    Telegram webhook endpoint.

    Receives Telegram updates and sends them to Tama.
    Set up webhook with:
        curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<YOUR_URL>/webhooks/telegram"
    """
    from rikai.connectors.telegram import TelegramConnector, TelegramConnectorConfig

    try:
        tama = await get_tama()
        config = TelegramConnectorConfig()
        connector = TelegramConnector(config=config, tama_agent=tama)
        await connector.setup()

        result = await connector.handle_webhook(payload)

        return {"ok": True, "result": result.metadata}

    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/webhooks/slack", tags=["Webhooks"])
async def slack_webhook(payload: dict):
    """
    Slack Events API webhook endpoint.

    Receives Slack events and sends them to Tama.
    Configure Event Subscriptions URL in your Slack App settings.
    """
    from rikai.connectors.slack import SlackConnector, SlackConnectorConfig

    # Handle URL verification challenge
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    try:
        tama = await get_tama()
        config = SlackConnectorConfig()
        connector = SlackConnector(config=config, tama_agent=tama)
        await connector.setup()

        result = await connector.handle_webhook(payload)

        # If result is a dict (URL verification), return it directly
        if isinstance(result, dict):
            return result

        return {"ok": True}

    except Exception as e:
        return {"ok": False, "error": str(e)}


# =============================================================================
# Context Endpoint
# =============================================================================


@app.get("/context", tags=["Context"])
async def get_context():
    """Get comprehensive user context (self, current focus, projects)."""
    umi = get_umi()

    context = {}

    # Get self
    self_entities = await umi.entities.list(type=EntityType.SELF, limit=1)
    if self_entities:
        context["self"] = {
            "name": self_entities[0].name,
            "content": self_entities[0].content,
        }

    # Get current focus
    task_entities = await umi.entities.list(type=EntityType.TASK, limit=1)
    if task_entities:
        context["now"] = {
            "name": task_entities[0].name,
            "content": task_entities[0].content,
        }

    # Get projects
    projects = await umi.entities.list(type=EntityType.PROJECT, limit=5)
    if projects:
        context["projects"] = [
            {"name": p.name, "content": p.content[:200] if p.content else None}
            for p in projects
        ]

    # Get recent notes
    notes = await umi.entities.list(type=EntityType.NOTE, limit=5)
    if notes:
        context["recent_notes"] = [
            {"name": n.name, "content": n.content[:200] if n.content else None}
            for n in notes
        ]

    return context


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    """Run the API server."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
