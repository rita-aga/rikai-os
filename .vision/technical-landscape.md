# Technical Landscape (January 2026)

This document captures the state of the art in agent memory, harnesses, and context engineering as of January 2026, along with RikaiOS's strategic opportunities.

---

## Table of Contents

1. [Agent Harness Landscape](#agent-harness-landscape)
2. [Memory Systems](#memory-systems)
3. [Context Engineering](#context-engineering)
4. [Session State Management](#session-state-management)
5. [Continual Learning](#continual-learning)
6. [Skill Learning](#skill-learning)
7. [Federation & Multi-Agent](#federation--multi-agent)
8. [RikaiOS Opportunities](#rikaios-opportunities)
9. [What NOT to Build](#what-not-to-build)
10. [References](#references)

---

## Agent Harness Landscape

### Definition

An **Agent Harness** is the infrastructure that wraps around an AI model to manage long-running tasks. It handles:
- Human-in-the-loop tool calls
- Sub-agent management
- Filesystem access
- Prompt presets
- Lifecycle hooks
- State persistence across sessions

Key examples: Claude Code, Claude Agent SDK, LangGraph, Manus

### Core Problems (2026)

| Problem | Description | Current Solutions |
|---------|-------------|-------------------|
| **Context Rot** | Performance degrades at ~256k tokens, well before 1M limit | Pre-rot thresholds, compaction, summarization |
| **Session Continuity** | Each new session starts with no memory | `claude-progress.txt`, git history, checkpointers |
| **Model Drift** | Model stops following instructions after 100+ tool calls | Manual observation, no automated detection |
| **Context Pollution** | Too much irrelevant info distracts the model | Context isolation, sub-agents |
| **Context Confusion** | Can't distinguish instructions vs data | Structured formats, clear delimiters |
| **Multi-Agent State** | State management across agent boundaries | Emerging protocols, mostly unsolved |

### Key Insight from Anthropic

> "The key insight was finding a way for agents to quickly understand the state of work when starting with a fresh context window, which is accomplished with the `claude-progress.txt` file alongside the git history."

The two-fold agent architecture:
1. **Initializer agent**: Sets up environment, creates progress file, initial git commit
2. **Coding agent**: Makes incremental progress session-by-session

### Manus Evolution

Manus rebuilt their agent framework **five times** since March 2025. Key learnings:

- **V1**: `todo.md` file rewritten every turn
  - Purpose: Push global plan into recent attention span (avoid "lost in the middle")
  - Problem: ~30% of tokens wasted on todo updates

- **V2**: Dedicated Planner sub-agent
  - Returns structured Plan object
  - Injected into context only when needed
  - Sub-agents use constrained decoding for output schema

### Context Management Strategies

| Strategy | Description | Reversibility |
|----------|-------------|---------------|
| **Compaction** | Strip info that exists in environment (files, git) | Reversible |
| **Summarization** | LLM summarizes history at threshold (~128k tokens) | Lossy |
| **Offloading** | Move info to external system for later retrieval | Reversible |
| **Isolation** | Separate context per sub-agent | N/A |

Best practice from Manus: Keep most recent tool calls in full detail when summarizing to maintain "rhythm" and formatting style.

---

## Memory Systems

### Taxonomy

Memory systems in 2026 fall into three categories by storage medium:

1. **Token-level**: Explicit, discrete (conversation history, RAG)
2. **Parametric**: Implicit in weights (fine-tuning, LoRA)
3. **Latent**: Hidden states (KV cache manipulation)

### Leading Open-Source Systems

#### Zep / Graphiti

**Repository**: https://github.com/getzep/graphiti

**Architecture**: Temporal Knowledge Graph with three layers:
```
Episodic Memory (raw events, conversations)
         ↓
Semantic Memory (extracted entities, concepts)
         ↓
Community Memory (high-level domain summaries)
```

**Key Innovation**: Bi-temporal data model
- **Event Time (T)**: When a fact actually occurred
- **Ingestion Time (T')**: When information was added to memory

**Performance**:
- 94.8% on Deep Memory Retrieval benchmark (vs MemGPT 93.4%)
- P95 latency: 300ms
- Up to 18.5% accuracy improvement over baselines
- 90% latency reduction vs baseline implementations

**Search Methods**: Cosine similarity, BM25 full-text, breadth-first graph traversal

**Stack**: Neo4j, BGE-m3 embeddings, GPT-4o-mini for graph construction

---

#### MAGMA (Multi-Graph Agentic Memory Architecture)

**Repository**: https://github.com/FredJiang0324/MAMGA

**Paper**: arXiv:2601.03236 (January 2026)

**Architecture**: Four orthogonal relational graphs:
```
Query → Intent Classification
              ↓
    Route to relevant graph(s):
    ┌─────────────────────────────────────┐
    │ Semantic Graph  │ What relates to what │
    │ Temporal Graph  │ What happened when   │
    │ Causal Graph    │ What caused what     │
    │ Entity Graph    │ Who/what involved    │
    └─────────────────────────────────────┘
              ↓
    Fuse subgraphs → Compact, type-aligned context
```

**Key Innovations**:
- **Adaptive Traversal Policy**: Routes retrieval based on query intent
- **Dual-stream memory evolution**: Decouples latency-sensitive ingestion from async structural consolidation

**Performance**: Beats Zep, Mem0, MemOS, LightMem on LoCoMo, HotpotQA, RULER, LongMemEval

---

#### MemOS (Memory Operating System)

**Repository**: https://github.com/MemTensor/MemOS

**Paper**: arXiv (May 2025, first to propose "Memory OS" concept)

**Architecture**: Graph structure organized by task→concept→fact paths

**Key Concepts**:
- **MemCube**: Fundamental encapsulation unit unifying parametric knowledge, KV-caches, and external content
- **MemOperator**: Manages memory via tagging, graph structures, multi-layer partitions

**Features** (v2.0 "Stardust", Dec 2025):
- Knowledge Base system with auto document/URL parsing
- Memory feedback mechanism
- Multi-modal memory (images, charts)
- Tool Memory for agent planning
- Millisecond-level async memory add
- BM25, graph recall, mixture search

---

#### GAM (General Agentic Memory)

**Repository**: https://github.com/VectorSpaceLab/general-agentic-memory

**Paper**: arXiv:2511.18423 (November 2025)

**Architecture**: Dual-agent "Just-In-Time compilation" approach
```
┌─────────────────────────────────────────────┐
│ Memorizer                                    │
│ - Highlights key historical info             │
│ - Maintains lightweight memory index         │
│ - Stores complete history in page-store      │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ Researcher                                   │
│ - Analyzes query, plans search strategy      │
│ - Uses tools: vector search, BM25, page IDs  │
│ - Conducts "deep research" into page-store   │
└─────────────────────────────────────────────┘
```

**Performance**:
- RULER Multi-Hop Tracing: >90% accuracy (competitors <60%)
- HotpotQA F1: >55% even at 448K tokens
- State-of-the-art on LoCoMo, HotpotQA, RULER, NarrativeQA

---

#### Mem0

**Repository**: https://github.com/mem0ai/mem0

**Architecture**: Scalable memory-centric with graph variant

**Key Features**:
- Dynamic extraction, consolidation, retrieval from conversations
- Graph-based variant captures relational structures
- ~90% token cost reduction vs full history
- ~91% latency reduction

---

### Comparison Matrix

| System | Graph Type | Temporal | Causal | Open Source | Production Ready |
|--------|-----------|----------|--------|-------------|------------------|
| Zep/Graphiti | Hierarchical KG | Yes (bi-temporal) | No | Yes | Yes |
| MAGMA | Multi-graph (4 types) | Yes | Yes | Yes | New (Jan 2026) |
| MemOS | Task→concept→fact | Partial | No | Yes | Yes |
| GAM | Dual-agent | Partial | No | Yes | Yes |
| Mem0 | Vector + Graph hybrid | Partial | No | Yes | Yes |

---

## Context Engineering

### Definition

> "Context Engineering is the discipline of designing and building dynamic systems that provide the right information and tools, in the right format, at the right time, to give an LLM everything it needs to accomplish a task."

Unlike prompt engineering (the "how"), context engineering is about the "what".

### Three Core Data Sources

1. **Domain Documents** (RAG): Enterprise/private unstructured data
2. **Conversation History** (Memory): State from agent interactions
3. **Tool Descriptions** (Tool Retrieval): Usage guides for available tools

### The Evolution from RAG

RAG is evolving from "Retrieval-Augmented Generation" into a **Context Engine** with intelligent retrieval as its core capability. This coincides with the broader shift from prompt engineering to context engineering.

### Context Failure Modes

| Failure | Description |
|---------|-------------|
| **Context Rot** | Performance degrades as window fills, even below limit |
| **Context Pollution** | Irrelevant/redundant/conflicting info distracts model |
| **Context Confusion** | Can't distinguish instructions vs data vs structure |
| **Lost in the Middle** | Model ignores information in middle of long context |

### Key Metrics

Manus reports **100:1 input-to-output token ratio** - vast majority of cost is processing context, not generating responses. This makes cache efficiency critical.

---

## Session State Management

### Current Approaches

| Approach | Used By | Pros | Cons |
|----------|---------|------|------|
| **Flat files** (`claude-progress.txt`) | Anthropic | Simple, model reads easily | No semantic structure |
| **Git history** | Most harnesses | Natural checkpoints, diff-able | Not queryable semantically |
| **`todo.md` recitation** | Manus (early) | Keeps goals in attention | 30% token waste |
| **Structured Planner agent** | Manus (current) | Token efficient | More complex |
| **Checkpointer** | LangGraph | Thread-scoped persistence | Linear history only |
| **Knowledge graph** | Zep, MAGMA | Semantic, queryable | Overhead for simple tasks |

### The Gap: Harness-Specific Semantic State

Current memory systems solve "what do I know?" but not "what was I doing across sessions?"

**What's NOT modeled semantically**:
- Task progress state (which step am I on?)
- Tool call history with WHY annotations
- Multi-agent handoff state
- Decision points and reasoning
- Blockers and their resolutions

### Anthropic's State Tracking Findings

| Approach | Improvement |
|----------|-------------|
| Memory + Context Editing | 39% over baseline |
| Context Editing Alone | 29% over baseline |
| Token Reduction | 84% in 100-turn evaluation |

---

## Continual Learning

### Two Paradigms

#### 1. Weight Updates (Parametric)

**Meta FAIR's Sparse Memory Finetuning** (2025):
- 1M memory slots in model weights
- Only ~10K activate per forward pass
- Reduces catastrophic forgetting from 89% → 11%
- Published in "Memory in the Age of AI Agents" survey (arXiv:2512.13564)

**Pros**: Knowledge becomes intrinsic, no retrieval latency
**Cons**: Requires training infrastructure, risk of forgetting

#### 2. Token Space Learning (Non-Parametric)

**Letta's Approach**:
- Self-editing memory via tools (`core_memory_replace`, `core_memory_append`)
- Skill learning based on Reflexion framework (NeurIPS 2023)
- Sleep-time compute for memory consolidation

**Pros**: No training needed, interpretable, can be federated
**Cons**: Context limits, retrieval latency

### Current Benchmark Results (MemoryBench, October 2025)

All current memory systems fail at **declarative + procedural memory together**. They handle facts OR procedures, not both simultaneously.

### Emerging Research

- **Google's Nested Learning**: Hierarchical memory consolidation
- **MESU Bayesian Metaplasticity**: Principled approach to what to remember/forget
- **DeepSeek**: Storing memory as images (experimental)
- **Anthropic**: Curated, evolving context states

---

## Skill Learning

### Letta's Implementation

**Framework**: Based on Reflexion (NeurIPS 2023)

**Two Phases**:
1. **Reflection**: After task completion, analyze trajectory
2. **Creation**: Abstract patterns into reusable skills

**Self-Editing Tools**:
- `core_memory_replace`: Overwrite memory block
- `core_memory_append`: Add to memory block
- `memory_insert`: Add to archival memory
- `memory_replace`: Update archival memory

### What's Open Source vs Proprietary (Letta)

| Feature | Status |
|---------|--------|
| Self-editing memory tools | Open source |
| `/skill` command (LLM-guided creation) | Open source |
| SKILL.md format and loading | Open source |
| Automatic trajectory→reflection→skill pipeline | **NOT in open source** |
| Terminal Bench evaluation | Internal/proprietary |

### Anthropic's Skills Specification

`.skills/` directory format:
```
.skills/
  my-skill/
    SKILL.md      # Instructions and context
    files/        # Supporting files
```

Skills are loaded on-demand, injected into context when invoked.

---

## Federation & Multi-Agent

### Existing Protocols

| Protocol | Focus | Status |
|----------|-------|--------|
| **MCP** (Anthropic) | Tool/resource sharing | Production |
| **A2A** (Google) | Agent-to-agent enterprise | Production |
| **Collaborative Memory** (Accenture) | Two-tier private/shared | Research (May 2025) |

### What's Missing: Consumer Personal Context Federation

A2A and MCP handle tool calling but NOT:
- Shared personal context across owners
- Permission-scoped memory access
- Conflict resolution for concurrent edits
- Trust verification between personal agents

### Multi-Agent State Challenges

From industry research:
- Inter-agent communication protocols
- State management across agent boundaries
- Conflict resolution mechanisms
- Orchestration logic

These are "core challenges that didn't exist in single-agent systems."

---

## RikaiOS Opportunities

### Unique Position

RikaiOS has:
- **Umi**: Context lake (Postgres + pgvector + MinIO)
- **Tama**: Letta-powered agent with self-editing memory
- **Hiroba**: Federation layer (unique differentiator)
- **TamaMemory**: Bridge between Letta and Umi with `consolidate()`, `forget()`

### Strategic Opportunities

#### 1. Harness-Aware Semantic Session State (High Impact)

**Gap**: Memory systems solve "what do I know" not "what was I doing"

**Opportunity**: Build session-specific entities in Umi:
```python
class SessionEntity(Entity):
    type = "SESSION"
    task_description: str
    current_step: int
    tool_calls: list[ToolCallRecord]  # with WHY annotations
    blockers: list[str]
    decisions_made: list[Decision]  # with reasoning
```

**Integration**: Use Graphiti as graph engine, add session schema layer

#### 2. Context Durability / Drift Detection (High Impact)

**Gap**: No automated detection of model drift after 100+ tool calls

**Opportunity**: Build drift detection in Tama:
```python
class DriftDetector:
    async def check_instruction_adherence(self,
        original_instructions: str,
        recent_actions: list[str]
    ) -> DriftReport:
        # Evaluate if actions still align with instructions
```

**Bonus**: Drift data becomes training signal for local models

#### 3. Hiroba as Multi-Agent Memory Protocol (Very High Impact)

**Gap**: No consumer protocol for personal AI federation

**Opportunity**: Define protocol where:
- Two Tamas share permission-scoped view of Umi
- Session state synchronizes across agents
- Explicit conflict resolution (not "last write wins")

This is genuinely unoccupied territory.

#### 4. GAM-Style Deep Retrieval in TamaMemory (Medium Impact)

**Current**: `TamaMemory.get_context_for_query()` does simple vector search

**Upgrade**: Implement Memorizer + Researcher pattern:
- Strategic query planning
- Multi-method retrieval (vector, BM25, graph traversal)
- Reflection on results before returning

#### 5. Pre-Rot Compaction to Umi (Medium Impact)

**Opportunity**: Umi becomes compaction target:
```python
async def compact_to_umi(context: list[Message]) -> CompactionResult:
    # Strip tool call bodies (exist in Umi/git)
    # Keep semantic summaries
    # Store full detail in Umi for retrieval
    # Return lightweight context with Umi references
```

Reversible compaction - information moves to Umi, not deleted.

### 10x Ambitious Version (With Model Training)

Since local models are a goal:

1. **Collect drift data**: Log every trajectory where Tama deviates from instructions
2. **Finetune on recoveries**: Train local model on "how to get back on track"
3. **Personality layer**: Sparse memory finetuning to encode user patterns in weights
4. **Harness-native model**: Local model designed for long-horizon personal tasks with native Umi integration

**Endgame**: Local model that doesn't suffer context rot because user-specific knowledge lives in weights, not just tokens.

### Implementation Roadmap

| Phase | Build | Differentiation |
|-------|-------|-----------------|
| 1 | Upgrade TamaMemory to GAM-style retrieval | Strategic vs dumb vector search |
| 2 | Add session state entities to Umi schema | Semantic session continuity |
| 3 | Build drift detection in Tama | Instruction adherence monitoring |
| 4 | Implement Hiroba sync protocol | First consumer personal AI federation |
| 5 | Create long-horizon personal task benchmark | First benchmark beyond 100 tool calls |
| 6 | Local model with sparse memory layers | User patterns in weights |

---

## What NOT to Build

These are solved or being actively solved elsewhere:

| Area | Don't Rebuild | Use Instead |
|------|---------------|-------------|
| Basic memory retrieval | Vector search, embedding | Mem0, Zep, or existing Umi |
| Enterprise agent protocols | A2A implementation | Google's A2A |
| Skill file format | Custom skill spec | Anthropic's `.skills/` |
| Context summarization | Custom summarizer | Claude Agent SDK compact |
| Knowledge graph engine | Custom graph DB | Graphiti (Neo4j-based) |
| Reflexion prompts | Custom reflection | Letta's patterns |
| General memory benchmarks | Custom benchmark | LoCoMo, MemoryBench, DMR |

---

## References

### Papers

- [Memory in the Age of AI Agents: A Survey](https://arxiv.org/abs/2512.13564) - Comprehensive taxonomy
- [Zep: A Temporal Knowledge Graph Architecture](https://arxiv.org/abs/2501.13956) - Bi-temporal memory
- [MAGMA: Multi-Graph Agentic Memory](https://arxiv.org/abs/2601.03236) - Four-graph architecture
- [GAM: General Agentic Memory](https://arxiv.org/abs/2511.18423) - Dual-agent deep research
- [MemOS: A Memory OS for AI Systems](https://arxiv.org/abs/2505.22101) - Memory operating system
- [Mem0: Production-Ready AI Agents with Long-Term Memory](https://arxiv.org/abs/2504.19413)
- [Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366) - NeurIPS 2023

### Industry Resources

- [Anthropic: Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Anthropic: Building Agents with Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Phil Schmid: Agent Harness 2026](https://www.philschmid.de/agent-harness-2026)
- [Phil Schmid: Context Engineering Part 2](https://www.philschmid.de/context-engineering-part-2)
- [LangChain: Context Engineering for Agents](https://blog.langchain.com/context-engineering-for-agents)
- [Manus: Context Engineering Lessons](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)
- [Letta: Skill Learning Blog](https://www.letta.com/blog/skill-learning)

### Open Source Repositories

- [Graphiti](https://github.com/getzep/graphiti) - Temporal knowledge graphs
- [MAGMA](https://github.com/FredJiang0324/MAMGA) - Multi-graph memory
- [MemOS](https://github.com/MemTensor/MemOS) - Memory operating system
- [GAM](https://github.com/VectorSpaceLab/general-agentic-memory) - Dual-agent memory
- [Mem0](https://github.com/mem0ai/mem0) - Production memory layer
- [Letta](https://github.com/letta-ai/letta) - Stateful agents with self-editing memory
- [Agent Memory Paper List](https://github.com/Shichun-Liu/Agent-Memory-Paper-List) - Curated research

### Benchmarks

- **LoCoMo**: Long-context memory benchmark
- **LongMemEval**: Extended memory evaluation
- **MemoryBench**: Declarative + procedural memory (October 2025)
- **DMR (Deep Memory Retrieval)**: MemGPT's primary benchmark
- **RULER Multi-Hop Tracing**: Complex reasoning chains
- **HotpotQA**: Multi-hop question answering
- **NarrativeQA**: Story comprehension

---

*Last updated: January 2026*
*Document location: `.vision/technical-landscape.md`*
