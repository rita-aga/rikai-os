// ============================================
// IKAI OS Type Definitions
// Mirrors rikaios/core/models.py
// ============================================

// Entity Types
export type EntityType = 'self' | 'project' | 'person' | 'topic' | 'note' | 'task';

export interface Entity {
  id: string;
  type: EntityType;
  name: string;
  content?: string;
  metadata: Record<string, unknown>;
  embedding_id?: string;
  created_at: string;
  updated_at: string;
}

export interface EntityRelation {
  id: string;
  source_id: string;
  target_id: string;
  relation_type: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

// Document Types
export type DocumentSource = 'chat' | 'docs' | 'social' | 'voice' | 'file' | 'git';

export interface Document {
  id: string;
  source: DocumentSource;
  title: string;
  object_key: string;
  content_type: string;
  size_bytes: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  embedding_id?: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

// Search Types
export interface SearchQuery {
  query: string;
  limit?: number;
  filters?: Record<string, string>;
}

export interface SearchResult {
  id: string;
  content: string;
  score: number;
  source_type: 'entity' | 'document_chunk';
  metadata: Record<string, unknown>;
}

// Hiroba (Collaboration) Types
export interface HirobaRoom {
  id: string;
  name: string;
  description?: string;
  owner_id: string;
  settings: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface HirobaMember {
  room_id: string;
  agent_id: string;
  role: string;
  joined_at: string;
  last_sync?: string;
}

export interface HirobaContent {
  id: string;
  room_id: string;
  author_id: string;
  content: string;
  content_type: string;
  sync_status: 'pending' | 'synced' | 'failed';
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

// Federation Types
export interface AgentConnection {
  agent_id: string;
  endpoint: string;
  name: string;
  metadata: Record<string, unknown>;
  connected_at: string;
}

export interface Permission {
  id: string;
  path: string;
  agent_id: string;
  access: 'read' | 'write';
  granted_by: string;
  expires_at?: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

// Context Types
export interface Context {
  self?: Entity;
  focus?: string;
  projects: Entity[];
  recent_notes: Entity[];
}

// Activity Types
export interface ActivityItem {
  id: string;
  type: 'entity_created' | 'entity_updated' | 'document_synced' | 'task_completed';
  entity_type?: EntityType;
  entity_id?: string;
  entity_name?: string;
  description: string;
  timestamp: string;
}

// UI Types
export interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  badge?: number;
}

// Entity color mapping helper
export const entityColors: Record<EntityType, string> = {
  self: 'entity-self',
  project: 'entity-project',
  person: 'entity-person',
  topic: 'entity-topic',
  note: 'entity-note',
  task: 'entity-task',
};

// Document source color mapping helper
export const sourceColors: Record<DocumentSource, string> = {
  chat: 'source-chat',
  docs: 'source-docs',
  social: 'source-social',
  voice: 'source-voice',
  file: 'source-file',
  git: 'source-git',
};

// Entity type labels
export const entityLabels: Record<EntityType, string> = {
  self: 'Self',
  project: 'Project',
  person: 'Person',
  topic: 'Topic',
  note: 'Note',
  task: 'Task',
};

// Document source labels
export const sourceLabels: Record<DocumentSource, string> = {
  chat: 'Chat',
  docs: 'Docs',
  social: 'Social',
  voice: 'Voice',
  file: 'File',
  git: 'Git',
};
