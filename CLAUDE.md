# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Engineering Philosophy

**Priority Order: Safety > Performance > Developer Experience**

Inspired by [TigerStyle](https://github.com/tigerbeetle/tigerbeetle/blob/main/docs/TIGER_STYLE.md) and FoundationDB's simulation-first approach.

### Core Principles

1. **Simulation-First**: Test infrastructure comes before implementation. If you can't test it deterministically, reconsider the design.

2. **Explicit Limits**: Everything has bounds. No unbounded queues, no unlimited retries, no implicit defaults.

3. **Honest Documentation**: Document what works AND what doesn't. Never claim something is tested if it isn't.

4. **No Silent Failures**: All errors must be handled explicitly. No swallowed exceptions, no ignored return values.

5. **Determinism Where Possible**: Same inputs should produce same outputs. Use sorted iteration, seeded RNG in tests.

## Build & Development Commands

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Start infrastructure (Postgres+pgvector, MinIO)
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

### Commit Policy: Only Working Software

**Never commit broken code.** Every commit must represent working software.

### Pre-Commit Checklist

Before EVERY commit, verify:

```bash
# Required - ALL must pass
pytest                    # All tests pass
ruff check .              # No lint errors
mypy src/rikai            # No type errors (if applicable)
```

### If Tests Fail

Do NOT commit. Instead:
1. Fix the failing tests
2. If fix is complex, use `git stash` to save work
3. Never use `--no-verify` to skip checks
4. Never commit with `# TODO: fix this` comments

### Commit Format

Use conventional commits:
- `feat:` - New feature
- `fix:` - Bug fix
- `refactor:` - Code refactoring (no behavior change)
- `docs:` - Documentation only
- `chore:` - Build/tooling changes
- `test:` - Adding/updating tests

Push to the current branch after committing.

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
│  │  Postgres+pgvector (metadata+vectors) + MinIO (files)   │ │
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
| `src/rikai/umi/storage/` | Storage adapters: `postgres.py` (metadata+vectors via pgvector), `objects.py` (MinIO) |
| `src/rikai/tama/agent.py` | TamaAgent (Letta-based) - requires Letta server |
| `src/rikai/tama/memory.py` | TamaMemory bridge between Letta and Umi |
| `src/rikai/connectors/base.py` | Abstract base classes for data ingestion connectors |
| `src/rikai/cli/main.py` | Typer CLI with subcommands (umi, tama) |
| `src/rikai/servers/mcp.py` | MCP server exposing search, entities, and context |

### Data Flow

1. **Connectors** ingest data from sources (files, APIs, webhooks)
2. **Umi** stores data across two tiers: Postgres+pgvector (structured + vectors), MinIO (files)
3. **Tama** queries Umi for context and maintains self-editing memory via Letta
4. **MCP Server** exposes context to any MCP-compatible client

### Entity Types (from `core/models.py`)

`SELF`, `PROJECT`, `PERSON`, `TOPIC`, `NOTE`, `TASK`

### Document Sources

`CHAT`, `DOCS`, `SOCIAL`, `VOICE`, `FILE`, `GIT`

## Environment Variables

Key configuration (prefix with `RIKAI_`):
- `RIKAI_POSTGRES_URL` - Postgres connection string (includes pgvector for embeddings)
- `RIKAI_MINIO_*` - MinIO/S3 connection settings
- `RIKAI_OPENAI_API_KEY` - OpenAI API key for embeddings
- `RIKAI_EMBEDDING_MODEL` - Embedding model (default: text-embedding-3-small)

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

### Language & Tooling

- Python 3.11+ with async/await throughout
- Ruff for linting (line-length 100)
- MyPy strict mode enabled
- Pydantic v2 for data validation

### TigerStyle Naming Conventions

**Constants with Units (big-endian, most significant first):**
```python
# Good - unit in name, explicit limit, big-endian
ENTITY_CONTENT_BYTES_MAX = 1_000_000
QUERY_RESULTS_COUNT_MAX = 100
EMBEDDING_DIMENSIONS_SIZE = 1536
CONSOLIDATION_WINDOW_DAYS_MAX = 30

# Bad - unclear units, small-endian
MAX_CONTENT = 1000000
maxQueryResults = 100
EMBEDDING_DIM = 1536
```

**Variable and Function Names:**
```python
# Good - big-endian (general to specific)
entity_content_bytes_max
search_results_limit_default
memory_consolidation_threshold

# Bad - small-endian or unclear
max_entity_content
defaultSearchLimit
threshold
```

### Assertions (2+ per non-trivial function)

Every function that modifies state or has preconditions should have assertions:

```python
async def store_entity(self, entity: Entity) -> str:
    # Preconditions
    assert entity.id, "entity must have id"
    assert entity.type in EntityType.__members__, f"invalid type: {entity.type}"
    assert len(entity.content) <= ENTITY_CONTENT_BYTES_MAX, "content too large"

    result = await self._postgres.insert(entity)

    # Postconditions
    assert result.id == entity.id, "stored id must match"
    return result.id
```

### Typed Errors (no string errors)

```python
# Good - typed error with context
class UmiError(Exception):
    pass

class EntityNotFound(UmiError):
    def __init__(self, entity_type: str, entity_id: str):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} not found: {entity_id}")

class LimitExceeded(UmiError):
    def __init__(self, resource: str, current: int, maximum: int):
        super().__init__(f"{resource}: {current} exceeds max {maximum}")

# Bad - string errors
raise Exception("Entity not found")
raise ValueError(f"Too many results")
```

### Function Length

- Target: under 50 lines per function
- If exceeding 70 lines, decompose into helper functions
- Parent functions handle control flow, helpers are pure
