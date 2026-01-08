# RikaiOS Implementation Plan

## Current State Assessment

### What Works
- **Umi (Context Lake)**: PostgresAdapter, PgVectorAdapter, ObjectAdapter, VoyageEmbeddings - all functional
- **Data Models**: Entity types, Document sources, Pydantic validation
- **Connectors**: Git, Google, Chat, File - implemented with sync operations
- **MCP Server**: 5 tools + 3 resources for exposing context to MCP clients
- **REST API**: FastAPI with CRUD endpoints
- **CLI (Python)**: Infrastructure management commands
- **Docker**: Compose file for local dev (Postgres, MinIO)
- **Terraform**: AWS deployment configs ready

### What Doesn't Work / Needs Attention
1. **LocalTamaAgent** - Should be removed (unnecessary fallback)
2. **TamaAgent Letta Tools** - Returns empty `[]`, no Umi integration
3. **Hiroba/Federation** - Data structures exist, sync is placeholder
4. **Naming Conflict** - Both Python and TypeScript packages install binary called `rikai`
5. **rikai-code Umi Integration** - No connection to Umi context lake

### Deployment Status
- **Local Docker**: Ready but not verified recently
- **AWS**: Terraform exists, unclear if deployed
- **Production**: Unknown

---

## Phase 1: Cleanup & Foundation (Priority: HIGH)

### 1.1 Remove LocalTamaAgent
- [ ] Delete `LocalTamaAgent` class from `src/rikai/tama/agent.py`
- [ ] Remove all references in CLI (`--local` flag)
- [ ] Update tests to remove LocalTamaAgent tests
- [ ] Document that Letta is required (no fallback)

### 1.2 Resolve Naming Conflict
**Decision needed:** What should each CLI be called?

Options:
| Option | Python CLI | TypeScript CLI | Notes |
|--------|-----------|----------------|-------|
| A | `rikai` | `rikai-chat` | Keep Python as main, rename TS |
| B | `rikai-infra` | `rikai` | TS is user-facing, Python is ops |
| C | `rikaictl` | `rikai` | Following kubectl pattern |
| D | Keep both `rikai` | Rely on PATH priority | Confusing, not recommended |

**Recommendation**: Option C - `rikaictl` for infrastructure, `rikai` for chat

- [ ] Rename Python CLI entry point to chosen name
- [ ] Update all documentation
- [ ] Update pyproject.toml entry points

### 1.3 Verify Infrastructure Works
- [ ] `docker-compose up -d` and test all services
- [ ] Run `pytest` - ensure all tests pass
- [ ] Verify Umi client can connect to all storage layers
- [ ] Document any missing environment variables

---

## Phase 2: Tama Agent Completion (Priority: HIGH)

### 2.1 Implement Letta Tools for Umi
The TamaAgent needs custom tools so Letta can interact with Umi.

Tools to implement:
- [ ] `umi_search` - Semantic search across context lake
- [ ] `umi_get_entity` - Get entity by ID
- [ ] `umi_list_entities` - List entities by type
- [ ] `umi_create_entity` - Create new entity
- [ ] `umi_store_document` - Store document with chunking
- [ ] `umi_get_context` - Get user context (self, now, projects)

Implementation approach:
- [ ] Research Letta custom tool registration
- [ ] Define tool schemas in Letta format
- [ ] Implement tool handlers that call UmiClient
- [ ] Test tools work through Letta agent

### 2.2 Verify Letta Cloud Integration
- [ ] Confirm TamaAgent creates agent on Letta Cloud
- [ ] Verify memory persistence across sessions
- [ ] Test chat + context retrieval flow
- [ ] Document required environment variables (LETTA_API_KEY)

---

## Phase 3: rikai-code Umi Integration (Priority: HIGH)

### 3.1 Connect rikai-code to Umi
The TypeScript chat interface needs to access Umi context.

Options:
1. **MCP Integration** - rikai-code connects to rikai MCP server
2. **Direct API** - rikai-code calls REST API
3. **Embedded** - rikai-code starts Umi client directly

**Recommendation**: MCP Integration (cleanest separation)

- [ ] Configure rikai-code to use rikai MCP server
- [ ] Add MCP server config to rikai-code settings
- [ ] Test context retrieval through MCP
- [ ] Verify search works from chat interface

### 3.2 Implement Umi-specific Tools in rikai-code
Add tools to the TypeScript toolset for Umi operations:
- [ ] `UmiSearch` - Search context lake
- [ ] `UmiRemember` - Store new information
- [ ] `UmiContext` - Get user context

---

## Phase 4: End-to-End Testing (Priority: HIGH)

### 4.1 Local Development Flow
- [ ] Document full setup steps
- [ ] Script to start all services
- [ ] Verify: init -> ingest data -> search -> chat -> remember

### 4.2 Integration Tests
- [ ] Test connector -> Umi -> Tama flow
- [ ] Test MCP server with Claude Desktop
- [ ] Test rikai-code with Umi context

---

## Phase 5: Deployment (Priority: MEDIUM)

### 5.1 Docker Deployment
- [ ] Build production Docker image
- [ ] Test docker-compose in production mode
- [ ] Document deployment steps

### 5.2 AWS Deployment
- [ ] Review Terraform configuration
- [ ] Deploy to AWS (dev environment)
- [ ] Verify all services running
- [ ] Document costs and scaling

---

## Phase 6: Hiroba/Federation (Priority: LOW)

### 6.1 Complete Hiroba Sync
- [ ] Implement `_pull_from_member()` properly
- [ ] Implement content format for sync
- [ ] Test room sync between two local instances

### 6.2 Federation Protocol
- [ ] Design agent discovery mechanism
- [ ] Implement discover() function
- [ ] Document federation protocol
- [ ] Security review for cross-agent communication

---

## Decisions Made (2025-01-08)

1. **Naming**: Python CLI renamed to `rikaictl`, TypeScript CLI stays `rikai`
2. **Letta**: Support self-hosted Letta server via `LETTA_BASE_URL` env var
3. **rikai-code Integration**: MCP integration (via rikai-mcp server)
4. **LocalTamaAgent**: Removed - Letta is required

## Remaining Open Questions

1. **Deployment Target**: Which AWS region? What scale?

---

## Completed (Phase 1 Cleanup)

- [x] Removed LocalTamaAgent from `src/rikai/tama/agent.py`
- [x] Removed `--local` flag from CLI commands
- [x] Updated tests to remove LocalTamaAgent tests, added self-hosted tests
- [x] Renamed Python CLI from `rikai` to `rikaictl` in pyproject.toml
- [x] Updated TamaConfig to support self-hosted via `LETTA_BASE_URL`
- [x] Updated CLAUDE.md with new CLI names and env vars

## Completed (Phase 2 - Tama Agent Tools)

- [x] Implemented 5 Umi tools with JSON schema definitions:
  - `umi_search`: Semantic search across context lake
  - `umi_get_entity`: Get entity by ID
  - `umi_list_entities`: List entities by type
  - `umi_store_memory`: Store new information
  - `umi_get_context`: Get user context (self, focus, projects)
- [x] Created `UmiToolHandler` class for local tool execution
- [x] Updated `TamaAgent` to include Umi tools in agent creation
- [x] Added tool call handling in `chat()` method
- [x] Fixed `mock_letta_client` fixture to match actual Letta API
- [x] Added 6 new tests for Umi tools (20 total Tama tests passing)

---

## Next Actions

1. Start Phase 3 - Connect rikai-code to Umi via MCP
2. Verify end-to-end flow with real Letta server
3. Update PLAN.md Phase 2 checkboxes
