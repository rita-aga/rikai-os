# RikaiOS (理解OS)

> **Rikai** (理解) - Japanese for "understanding, comprehension" (理 = reason + 解 = unravel)

A Personal Context Operating System that aggregates your entire digital life into one coherent, queryable space.

## Vision

RikaiOS is an **Agent Harness** - infrastructure that wraps around AI models to manage long-running tasks:

| Concept | Computer | RikaiOS |
|---------|----------|---------|
| **CPU** | Processor | LLM (Claude, GPT, local models) |
| **RAM** | Volatile memory | Context window |
| **OS** | Operating system | **RikaiOS itself** |
| **SSD/Cloud** | Persistent storage | **Umi** (海) - Context Lake |
| **App** | User application | **Tama** (魂) - Your personal agent |

## Components

### Umi (海) - The Sea
Your context lake - a separate, external service that stores all your data:
- **Object Storage** (S3/R2/MinIO) - Raw files, documents, attachments
- **Vector Database** (Qdrant/Pinecone) - Semantic search
- **Relational DB** (Postgres) - Structured metadata
- **Markdown Export** - Human-readable view at `~/.rikai/`

### Tama (魂) - The Soul
Your persistent AI agent powered by [Letta](https://letta.com):
- Connects to Umi but does NOT contain it
- Self-editing memory across conversations
- Model-agnostic (Claude, GPT, local models)

### Hiroba (広場) - The Plaza
Collaborative rooms for sharing context with others:
- Permission-scoped sharing
- Replicated state across participants
- MCP-based federation

## Installation

```bash
# Using uv (recommended)
uv pip install rikai

# Or using pip
pip install rikai
```

## Quick Start

```bash
# Initialize RikaiOS
rikai init

# Start local infrastructure
docker-compose up -d

# Check status
rikai status

# Ask your Tama
rikai ask "What am I working on?"
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR RIKAIOS DEPLOYMENT                   │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                 UMI - Context Lake                      │ │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────────────┐   │ │
│  │  │ Postgres │  │  Qdrant  │  │ MinIO/S3           │   │ │
│  │  └──────────┘  └──────────┘  └────────────────────┘   │ │
│  └────────────────────────────────────────────────────────┘ │
│                              ↑                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │               TAMA - Agent Runtime                      │ │
│  │  ┌────────────────┐    ┌─────────────────────────────┐ │ │
│  │  │ Letta Server   │───→│ MCP Server + REST API       │ │ │
│  │  └────────────────┘    └─────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Development

```bash
# Clone the repository
git clone https://github.com/rita-aga/rikai-os.git
cd rikai-os

# Install with dev dependencies
uv pip install -e ".[dev]"

# Start infrastructure
docker-compose -f docker/docker-compose.yml up -d

# Run tests
pytest
```

## Design Philosophy

Inspired by Japanese aesthetics:

| Principle | Japanese | Application |
|-----------|----------|-------------|
| **Kanso** (簡素) | Simplicity | Umi stores, Tama thinks. Clear separation. |
| **Ma** (間) | Negative space | What we don't build matters. |
| **Shizen** (自然) | Naturalness | Work with existing tools (MCP, Letta). |
| **Fukinsei** (不均整) | Imperfection | Don't solve everything. Be excellent at one thing. |

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

## Acknowledgments

- [Letta](https://letta.com) - Agent runtime with persistent memory
- [MCP](https://modelcontextprotocol.io) - Model Context Protocol by Anthropic
- [Phil Schmid's Agent Harness](https://www.philschmid.de/agent-harness-2026) - Architecture inspiration
