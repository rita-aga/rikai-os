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
    uvicorn rikaios.servers.api:app --reload

Or via CLI:
    rikai serve
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rikaios import __version__
from rikaios.core.config import get_config
from rikaios.core.models import EntityType, DocumentSource
from rikaios.umi import UmiClient


# =============================================================================
# Request/Response Models
# =============================================================================


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = __version__
    timestamp: datetime = Field(default_factory=datetime.utcnow)


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
    local: bool = Field(False, description="Use local agent mode")


class TamaChatResponse(BaseModel):
    """Tama chat response."""
    message: str
    context_used: list[str] = Field(default_factory=list)


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
    entities = await umi.entities.list(type=entity_type, limit=limit, offset=offset)

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
    """Chat with Tama (your personal agent)."""
    import os

    try:
        if request.local or not os.getenv("LETTA_API_KEY"):
            if not os.getenv("ANTHROPIC_API_KEY"):
                raise HTTPException(
                    status_code=503,
                    detail="No API keys configured. Set LETTA_API_KEY or ANTHROPIC_API_KEY.",
                )

            from rikaios.tama.agent import LocalTamaAgent

            async with LocalTamaAgent() as tama:
                response = await tama.chat(request.message)
        else:
            from rikaios.tama.agent import TamaAgent

            async with TamaAgent() as tama:
                response = await tama.chat(request.message)

        return TamaChatResponse(
            message=response.message,
            context_used=response.context_used,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Connector Endpoints
# =============================================================================


@app.get("/connectors", response_model=list[ConnectorStatus], tags=["Connectors"])
async def list_connectors():
    """List available connectors and their status."""
    from rikaios.connectors import (
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
        "files": "rikaios.connectors.FilesConnector",
        "git": "rikaios.connectors.GitConnector",
        "chat": "rikaios.connectors.ChatConnector",
        "google": "rikaios.connectors.GoogleConnector",
    }

    if request.connector not in connector_map:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown connector: {request.connector}. Available: {list(connector_map.keys())}",
        )

    try:
        # Import and instantiate the connector
        if request.connector == "files":
            from rikaios.connectors import FilesConnector
            connector = FilesConnector()
        elif request.connector == "git":
            from rikaios.connectors import GitConnector
            connector = GitConnector()
        elif request.connector == "chat":
            from rikaios.connectors import ChatConnector
            connector = ChatConnector()
        elif request.connector == "google":
            from rikaios.connectors import GoogleConnector
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
