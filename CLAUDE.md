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
mypy src/rikai
```

## Development Workflow (Northstar)

### Vision-Aligned Planning (MANDATORY)

**STOP. Before starting ANY non-trivial task (3+ steps, multi-file, or research required), you MUST:**

#### Before Starting - DO THIS FIRST

1. **Check for `.vision/`** - READ `NORTHSTAR.md`, `CONSTRAINTS.md`, `ARCHITECTURE.md`
2. **Check for `.progress/`** - Read existing plans to understand current state
3. **Create numbered plan** - ALWAYS save to `.progress/NNN_YYYYMMDD_HHMMSS_task-name.md` BEFORE writing code
4. **If task is trivial** - Small fixes don't need full plans, but document decisions

**DO NOT skip planning. DO NOT start coding without a plan file.**

#### Required Plan Sections (DO NOT SKIP)

These sections are **MANDATORY** and must be filled in:

1. **Options & Decisions** - Document every significant choice
   - List 2-3 options considered
   - Explain pros/cons of each
   - State which option chosen and WHY (reasoning)
   - List trade-offs accepted

2. **Quick Decision Log** - Log ALL decisions, even small ones
   - Time, decision, rationale, trade-off
   - This is your audit trail

3. **What to Try** - Update AFTER EVERY PHASE
   - Works Now: What user can test, exact steps, expected result
   - Doesn't Work Yet: What's missing, why, when expected
   - Known Limitations: Caveats, edge cases

**If you skip these sections, the plan is incomplete.**

#### During Execution

1. **Update plan after each phase** - Mark phases complete, log findings
2. **Log decisions in Quick Decision Log** - Every choice, with rationale
3. **Update "What to Try"** - After EVERY phase, not just at the end
4. **Re-read plan before major decisions** - Keeps goals in attention window
5. **Document deviations** - If implementation differs from plan, note why

#### Before Completion

1. **Verify required sections are filled** - Options, Decision Log, What to Try
2. **Run `/no-cap`** - Verify no hacks, placeholders, or incomplete code
3. **Check vision alignment** - Does result match RikaiOS architecture?
4. **Update plan status** - Mark as complete with verification status
5. **Commit and push**

### Testing

- **Write tests for new code** - Any new feature or bug fix should have tests
- **Run tests before pushing** - `pytest` for Python, `bun test` for TypeScript
- **If tests fail, fix before pushing** - Don't rely on CI to catch issues

### Multi-Instance Coordination

When multiple Claude instances work on shared tasks:
- Read `.progress/` plans before starting work
- Claim phases in the Instance Log section
- Update status frequently to avoid conflicts
- Use findings section for shared discoveries

### Commands

- `/remind` - Show workflow checklist
- `/no-cap` - Verify implementation quality

## Git Workflow

After implementing a feature or fix, always commit and push the changes:
- Use conventional commit format: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`
- Push to the current branch after committing

## CLI Entry Points

- `rikaictl` - Infrastructure management CLI (Typer-based)
- `rikai` - Interactive chat CLI (TypeScript, in `rikai-apps/rikai-code/`)
- `rikai-mcp` - MCP server for Model Context Protocol clients
- `rikai-api` - REST API server

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
| `src/rikai/core/models.py` | Pydantic data models (Entity, Document, Permission, etc.) |
| `src/rikai/core/config.py` | Settings via Pydantic Settings (env prefix: `RIKAI_`) |
| `src/rikai/umi/client.py` | UmiClient with EntityManager and DocumentManager |
| `src/rikai/umi/storage/` | Three storage adapters: `postgres.py`, `vectors.py`, `objects.py` |
| `src/rikai/tama/agent.py` | TamaAgent (Letta-based) - requires Letta server |
| `src/rikai/tama/memory.py` | TamaMemory bridge between Letta and Umi |
| `src/rikai/connectors/base.py` | Abstract base classes for data ingestion connectors |
| `src/rikai/cli/main.py` | Typer CLI with subcommands (umi, tama) |
| `src/rikai/servers/mcp.py` | MCP server exposing search, entities, and context |

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

Letta configuration:
- `LETTA_BASE_URL` - Self-hosted Letta server URL (e.g., http://localhost:8283)
- `LETTA_API_KEY` - Required for Letta Cloud, optional for self-hosted

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
