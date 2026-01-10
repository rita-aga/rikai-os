# RikaiOS Architecture

> System design, components, and technical decisions.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              INPUTS                                      │
│                                                                          │
│  Apps: Google Docs, GitHub, Slack, Telegram, Email, Calendar, Notion    │
│  Chat histories: Claude, ChatGPT, Perplexity (via share/export)         │
│  Files: Local folders, cloud storage, documents                         │
│  Real-time: Browser activity, voice, wearables                          │
│  Manual: Share buttons, quick capture, voice notes                      │
│                                                                          │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                         UMI (海) - Context Lake                          │
│                                                                          │
│  STORAGE                                                                 │
│  ├─ Structured data (Postgres)                                          │
│  ├─ Semantic vectors (Qdrant)                                           │
│  ├─ Files and attachments (MinIO/S3)                                    │
│  └─ Knowledge graph (entities, relationships, patterns)                 │
│                                                                          │
│  ENTITIES: SELF, PROJECT, PERSON, TOPIC, NOTE, TASK                     │
│  SOURCES: CHAT, DOCS, SOCIAL, VOICE, FILE, GIT                          │
│                                                                          │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                         TAMA (魂) - Agent Runtime                        │
│                                                                          │
│  ├─ Reasons over Umi (hybrid memory: Letta hot + Umi cold)              │
│  ├─ Learns patterns, preferences, decision-making style                 │
│  ├─ Proactive suggestions and actions                                   │
│  ├─ Represents user in federation scenarios                             │
│  └─ Model-agnostic: Claude, GPT, local models                           │
│                                                                          │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                        HIROBA (広場) - Federation                        │
│                                                                          │
│  ├─ Permission-scoped shared rooms                                      │
│  ├─ Agent-to-agent collaboration on tasks                               │
│  ├─ Negotiation and conflict resolution                                 │
│  └─ Outcomes presented to humans for final decision                     │
│                                                                          │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                              OUTPUTS                                     │
│                                                                          │
│  Dashboard: Mind map, insights, connections                             │
│  CLI: rikaictl (Python), rikai (TypeScript)                             │
│  MCP Server: Context for Claude Desktop and other clients               │
│  REST API: Programmatic access                                          │
│  Mobile/Voice: On-the-go access (planned)                               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Key Modules

| Module | Purpose |
|--------|---------|
| `src/rikai/core/models.py` | Pydantic data models (Entity, Document, Permission) |
| `src/rikai/core/config.py` | Settings via Pydantic Settings (env prefix: `RIKAI_`) |
| `src/rikai/umi/client.py` | UmiClient with EntityManager and DocumentManager |
| `src/rikai/umi/storage/` | Storage adapters: `postgres.py`, `vectors.py`, `objects.py` |
| `src/rikai/tama/agent.py` | TamaAgent (Letta-based) |
| `src/rikai/tama/memory.py` | TamaMemory bridge between Letta and Umi |
| `src/rikai/connectors/` | Data ingestion connectors |
| `src/rikai/servers/mcp.py` | MCP server for external clients |

---

## Data Flow

1. **Connectors** ingest data from sources (files, APIs, webhooks)
2. **Umi** stores across three tiers: Postgres (structured), Qdrant (vectors), MinIO (files)
3. **Tama** queries Umi for context, maintains self-editing memory via Letta
4. **Hiroba** syncs context with other users' agents (permission-scoped)
5. **MCP Server** exposes context to any MCP-compatible client

---

## Memory Architecture

```
HOT MEMORY (Letta)          COLD MEMORY (Umi)
├─ Active conversation      ├─ All entities
├─ Recent context           ├─ All documents
├─ Working memory blocks    ├─ Semantic vectors
└─ Skills                   └─ Knowledge graph

         TamaMemory Bridge
         ├─ consolidate()  →  Hot → Cold
         ├─ retrieve()     ←  Cold → Hot
         └─ forget()       →  Decay old data
```

---

## Technical Decisions

### Why Letta?
- Self-editing memory already built
- Skill learning via Reflexion
- Don't rebuild agent infrastructure

### Why Qdrant over pgvector?
- Better performance at scale
- Native graph capabilities
- Can switch back if needed

### Why separate storage tiers?
- Postgres: ACID transactions, relational queries
- Qdrant: Semantic search, nearest neighbor
- MinIO: Large files, S3-compatible

---

## Open Technical Questions

See [technical-directions.md](./technical-directions.md) for prioritized research directions.

Key areas:
- Hot→cold memory consolidation
- Context drift detection
- Hiroba sync protocol
- Personality learning from passive data

---

*See also: [summary.md](./summary.md) for the complete vision document.*
