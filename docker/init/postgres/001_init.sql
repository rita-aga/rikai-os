-- RikaiOS - Initial Database Schema
-- Umi (海) - Context Lake

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- Core Entities
-- =============================================================================

-- Entity types for the context lake
CREATE TYPE entity_type AS ENUM (
    'self',      -- User persona
    'project',   -- Project metadata
    'person',    -- People the user knows
    'topic',     -- Topics/interests
    'note',      -- Notes and thoughts
    'task'       -- Tasks and todos
);

-- Main entities table
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type entity_type NOT NULL,
    name TEXT NOT NULL,
    content TEXT,
    metadata JSONB DEFAULT '{}',
    embedding_id TEXT,  -- Reference to vector in Qdrant
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Entity relationships (simple graph)
CREATE TABLE entity_relations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    target_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_id, target_id, relation_type)
);

-- =============================================================================
-- Documents
-- =============================================================================

-- Document sources
CREATE TYPE document_source AS ENUM (
    'chat',      -- LLM conversations
    'docs',      -- Google Docs, notes
    'social',    -- X bookmarks, Instagram saves
    'voice',     -- PlauD transcripts
    'file',      -- Local files
    'git'        -- Git repositories
);

-- Documents stored in object storage (MinIO)
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source document_source NOT NULL,
    title TEXT NOT NULL,
    object_key TEXT NOT NULL,  -- Key in MinIO
    content_type TEXT,
    size_bytes BIGINT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Document chunks for vector search
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding_id TEXT,  -- Reference to vector in Qdrant
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- Federation
-- =============================================================================

-- Permission scopes for sharing
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    path_pattern TEXT NOT NULL,  -- e.g., 'projects/*', 'public/*'
    allowed_users TEXT[] DEFAULT '{}',  -- User identifiers
    access_level TEXT NOT NULL DEFAULT 'read',  -- read, write
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Hiroba (広場) - Collaborative rooms
CREATE TABLE hiroba (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    members TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Hiroba sync state
CREATE TABLE hiroba_sync (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hiroba_id UUID REFERENCES hiroba(id) ON DELETE CASCADE,
    member_id TEXT NOT NULL,
    last_sync_at TIMESTAMPTZ,
    sync_version BIGINT DEFAULT 0,
    UNIQUE(hiroba_id, member_id)
);

-- =============================================================================
-- Indexes
-- =============================================================================

CREATE INDEX idx_entities_type ON entities(type);
CREATE INDEX idx_entities_name ON entities(name);
CREATE INDEX idx_entities_metadata ON entities USING GIN(metadata);

CREATE INDEX idx_documents_source ON documents(source);
CREATE INDEX idx_documents_created ON documents(created_at DESC);

CREATE INDEX idx_document_chunks_document ON document_chunks(document_id);
CREATE INDEX idx_document_chunks_embedding ON document_chunks(embedding_id);

CREATE INDEX idx_entity_relations_source ON entity_relations(source_id);
CREATE INDEX idx_entity_relations_target ON entity_relations(target_id);

-- =============================================================================
-- Functions
-- =============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables with updated_at
CREATE TRIGGER entities_updated_at
    BEFORE UPDATE ON entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER permissions_updated_at
    BEFORE UPDATE ON permissions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER hiroba_updated_at
    BEFORE UPDATE ON hiroba
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
