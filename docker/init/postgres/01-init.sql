-- RikaiOS Postgres Initialization
-- This script runs on first container startup

-- Enable pgvector extension (for vector storage and Letta agent memory)
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Vector Embeddings Table (pgvector)
-- Replaces the external Qdrant vector database
-- =============================================================================

CREATE TABLE IF NOT EXISTS embeddings (
    id TEXT PRIMARY KEY,
    embedding vector(1024),  -- Voyage AI voyage-3 produces 1024-dim vectors
    text TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- IVFFlat index for approximate nearest neighbor search
-- Note: Index creation deferred until table has data (IVFFlat requires existing data)
-- The application will create the index after initial data load

-- Index on metadata for filtering
CREATE INDEX IF NOT EXISTS idx_embeddings_metadata ON embeddings USING GIN(metadata);

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE rikai TO rikai;
