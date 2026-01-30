# Plan: Remove All HashMaps - Single Source of Truth (Actor System)

**Goal**: Eliminate all in-memory HashMaps that create dual data sources. All data flows through the Actor system only.

**Status**: In Progress

---

## Phase 1: Add Missing Actor Operations (In Progress)

### 1.1 Update AgentActorState (state.rs in actor/)

- [x] Add `archival: Vec<ArchivalEntry>` field
- [x] Add `add_archival_entry()` method
- [x] Add `search_archival()` method (text search)
- [x] Add `get_archival_entry()` method
- [x] Add `delete_archival_entry()` method
- [x] Add `search_messages()` method (for conversation_search)

### 1.2 Add Actor Operations (agent_actor.rs)

Add handlers and match arms for:

- [x] `"archival_insert"` - insert archival entry, return entry ID
- [x] `"archival_search"` - search archival by query, return matches
- [x] `"archival_delete"` - delete archival entry by ID
- [x] `"conversation_search"` - search messages by query
- [x] `"conversation_search_date"` - search messages with date filter
- [x] `"core_memory_replace"` - replace content in a block
- [x] `"get_block"` - get a block by label
- [x] `"list_messages"` - list messages with pagination

---

## Phase 2: Add AgentService Methods (Pending)

### 2.1 Update AgentService (service/mod.rs)

Add async methods that invoke actor operations:

- [ ] `archival_insert(&self, agent_id: &str, content: &str, metadata: Option<Value>) -> Result<String>`
- [ ] `archival_search(&self, agent_id: &str, query: &str, limit: usize) -> Result<Vec<ArchivalEntry>>`
- [ ] `archival_delete(&self, agent_id: &str, entry_id: &str) -> Result<()>`
- [ ] `conversation_search(&self, agent_id: &str, query: &str, limit: usize) -> Result<Vec<Message>>`
- [ ] `conversation_search_date(&self, agent_id: &str, query: &str, start: Option<&str>, end: Option<&str>, limit: usize) -> Result<Vec<Message>>`
- [ ] `core_memory_replace(&self, agent_id: &str, label: &str, old: &str, new: &str) -> Result<()>`
- [ ] `get_block_by_label(&self, agent_id: &str, label: &str) -> Result<Option<Block>>`
- [ ] `list_messages(&self, agent_id: &str, limit: usize, cursor: Option<&str>) -> Result<Vec<Message>>`

---

## Phase 3: Update Memory Tools (Pending)

### 3.1 Update tools/memory.rs

Change each tool to use AgentService:

- [ ] `core_memory_append` - Already fixed (uses `append_or_create_block_by_label_async`)
- [ ] `core_memory_replace` - Change to use `service.core_memory_replace()`
- [ ] `archival_memory_insert` - Change to use `service.archival_insert()`
- [ ] `archival_memory_search` - Change to use `service.archival_search()`
- [ ] `conversation_search` - Change to use `service.conversation_search()`
- [ ] `conversation_search_date` - Change to use `service.conversation_search_date()`

---

## Phase 4: Remove HashMaps from AppState (Pending)

### 4.1 Remove HashMap fields (state.rs in kelpie-server/src/)

Remove from `AppStateInner`:
- [ ] `agents: RwLock<HashMap<String, AgentState>>`
- [ ] `messages: RwLock<HashMap<String, Vec<Message>>>`
- [ ] `archival: RwLock<HashMap<String, Vec<ArchivalEntry>>>`

---

## Phase 5: Fix Compilation Errors (Pending)

---

## Phase 6: Verification (Pending)

---

## Decision Log

| Time | Decision | Rationale |
|------|----------|-----------|
| 2026-01-29 | Add archival to AgentActorState | Need archival storage in actor for single source of truth |

