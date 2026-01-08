# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Start infrastructure (Postgres, Qdrant, MinIO)
docker-compose -f docker/docker-compose.yml up -d

# Run all tests
pytest

# Run single test file
pytest tests/test_file.py

# Run specific test
pytest tests/test_file.py::test_function_name

# Linting
ruff check .
ruff check --fix .

# Type checking
mypy rikaios
```

## Git Workflow

After implementing a feature or fix, always commit and push the changes:
- Use conventional commit format: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`
- Push to the current branch after committing

## CLI Entry Points

- `rikai` - Main CLI (Typer-based)
- `rikai-mcp` - MCP server for Model Context Protocol clients

## Architecture Overview

RikaiOS is a Personal Context Operating System with three core components:

```
┌─────────────────────────────────────────────────────────────┐
│                      RIKAIOS                                 │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              UMI (海) - Context Lake                    │ │
│  │  Postgres (metadata) + Qdrant (vectors) + MinIO (files) │ │
│  └────────────────────────────────────────────────────────┘ │
│                              ↑                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              TAMA (魂) - Agent Runtime                  │ │
│  │           Letta-powered agent with self-editing memory  │ │
│  └────────────────────────────────────────────────────────┘ │
│                              ↑                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              HIROBA (広場) - Collaboration              │ │
│  │         Permission-scoped rooms for sharing context     │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Key Modules

| Module | Purpose |
|--------|---------|
| `rikaios/core/models.py` | Pydantic data models (Entity, Document, Permission, etc.) |
| `rikaios/core/config.py` | Settings via Pydantic Settings (env prefix: `RIKAI_`) |
| `rikaios/umi/client.py` | UmiClient with EntityManager and DocumentManager |
| `rikaios/umi/storage/` | Three storage adapters: `postgres.py`, `vectors.py`, `objects.py` |
| `rikaios/tama/agent.py` | TamaAgent (Letta-based) and LocalTamaAgent classes |
| `rikaios/tama/memory.py` | TamaMemory bridge between Letta and Umi |
| `rikaios/connectors/base.py` | Abstract base classes for data ingestion connectors |
| `rikaios/cli/main.py` | Typer CLI with subcommands (umi, tama) |
| `rikaios/servers/mcp.py` | MCP server exposing search, entities, and context |

### Data Flow

1. **Connectors** ingest data from sources (files, APIs, webhooks)
2. **Umi** stores data across three tiers: Postgres (structured), Qdrant (vectors), MinIO (files)
3. **Tama** queries Umi for context and maintains self-editing memory via Letta
4. **MCP Server** exposes context to any MCP-compatible client

### Entity Types (from `core/models.py`)

`SELF`, `PROJECT`, `PERSON`, `TOPIC`, `NOTE`, `TASK`

### Document Sources

`CHAT`, `DOCS`, `SOCIAL`, `VOICE`, `FILE`, `GIT`

## Environment Variables

Key configuration (prefix with `RIKAI_`):
- `RIKAI_POSTGRES_URL` - Postgres connection string
- `RIKAI_QDRANT_URL` - Qdrant connection URL
- `RIKAI_MINIO_*` - MinIO/S3 connection settings
- `RIKAI_VOYAGE_API_KEY` - Voyage AI API key for semantic embeddings
- `RIKAI_VOYAGE_MODEL` - Voyage model (default: voyage-3)
- `ANTHROPIC_API_KEY` - For LocalTamaAgent (Claude-based)
- `LETTA_API_KEY` - For TamaAgent (Letta-based)

## Local Data Directory

`~/.rikai/` contains human-readable markdown exports:
- `self.md` - User persona
- `now.md` - Current focus
- `memory.md` - Learnings
- `projects/` - Project files
- `sources/` - Document sources

## Code Style

- Python 3.11+ with async/await throughout
- Ruff for linting (line-length 100)
- MyPy strict mode enabled
- Pydantic v2 for data validation
