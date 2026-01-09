# RikaiOS Vision

## The Problem

You save things in different places. You interact with different apps. Every time you open a new app, there's no shared context. Your life is fragmented across tools that don't talk to each other.

You have a lot of data — messages, calendars, documents, code, conversations — but no coherent view of your own life.

The data exists. The understanding doesn't.

And when you need to share context with someone else — dump what's in your head into their head — there's no way to do it. You resort to long emails, repeated explanations, context that gets lost in translation.

---

## What RikaiOS Is

RikaiOS is a Personal Context Operating System.

Three components:

**Umi (海)** — The Sea. Your context lake. Everything you've seen, done, saved, written — aggregated into one place. Structured data, vectors for semantic search, files. The memory layer.

**Tama (魂)** — The Soul. Your agent. Built on Letta. It reasons over Umi, organizes your context, surfaces insights, acts on your behalf. A proactive assistant that learns your patterns and represents you.

**Hiroba (広場)** — The Plaza. Federation layer. Permission-scoped rooms where your agent can share context with other people's agents. Collaboration without giving up ownership.

---

## How It Works

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
│  ├─ Semantic vectors (pgvector / Qdrant)                                │
│  ├─ Files and attachments (S3 / MinIO)                                  │
│  └─ Knowledge graph (entities, relationships, patterns)                 │
│                                                                          │
│  ENTITIES: SELF, PROJECT, PERSON, TOPIC, NOTE, TASK                     │
│  SOURCES: CHAT, DOCS, SOCIAL, VOICE, FILE, GIT                          │
│                                                                          │
│  OPEN PROBLEMS TO SOLVE                                                  │
│  ├─ Multi-modal memory (declarative + procedural together)              │
│  ├─ Intelligent curation (what to keep vs. let fade)                    │
│  └─ Continual learning without catastrophic forgetting                  │
│                                                                          │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                         TAMA (魂) - Your Agent                           │
│                                                                          │
│  CAPABILITIES                                                            │
│  ├─ Reasons over Umi (hybrid memory: Letta hot + Umi cold)              │
│  ├─ Learns your patterns, preferences, decision-making style            │
│  ├─ Proactive suggestions and actions                                   │
│  ├─ Represents you in federation scenarios                              │
│  └─ Model-agnostic: Claude, GPT, local models (Ollama, etc.)            │
│                                                                          │
│  OPEN PROBLEMS TO SOLVE                                                  │
│  ├─ Personality replication from passive data (not interviews)          │
│  ├─ Belief system and value learning                                    │
│  └─ Autonomous goal-setting and long-horizon planning                   │
│                                                                          │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                        HIROBA (広場) - Federation                        │
│                                                                          │
│  CAPABILITIES                                                            │
│  ├─ Permission-scoped shared rooms                                      │
│  ├─ Agent-to-agent collaboration on tasks                               │
│  ├─ Negotiation and conflict resolution between agents                  │
│  └─ Outcomes presented to humans for final decision                     │
│                                                                          │
│  OPEN PROBLEMS TO SOLVE                                                  │
│  ├─ Personal context federation (MCP, A2A exist but not for this)       │
│  ├─ Trust and verification between agents                               │
│  └─ Selective context sharing without leaking private data              │
│                                                                          │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                              OUTPUTS                                     │
│                                                                          │
│  Dashboard: Mind map, insights, connections you missed                  │
│  CLI: Quick queries and commands                                        │
│  Mobile: On-the-go access, share button ingestion                       │
│  Voice: Hands-free interaction                                          │
│  Any device: The agent is always available                              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         PRIVACY LAYER                                    │
│                                                                          │
│  Self-hosted: Full control, data never leaves your infrastructure       │
│  Cloud: Zero-knowledge encryption, you hold the keys                    │
│  Hybrid: Sensitive local, convenience cloud                             │
│  Local models: Complete privacy with Ollama, etc.                       │
│                                                                          │
│  OPEN PROBLEMS TO SOLVE                                                  │
│  ├─ Zero-knowledge cloud deployment at scale                            │
│  ├─ Encrypted inference (compute on encrypted data)                     │
│  └─ What happens when local models match cloud quality?                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Data flows in** from everywhere you work. Connectors pull from your apps. Share buttons push from mobile. Umi stores, indexes, and builds a knowledge graph of your context.

**Tama reasons over Umi.** Hot context lives in Letta's memory blocks. Cold context is queryable via tools. Over time, Tama learns your patterns — how you work, what you care about, how you make decisions. Eventually, it can represent you.

**Hiroba connects you to others.** Your agent and their agent share a room. They collaborate on tasks, negotiate disagreements, reach resolutions. Humans review and decide.

**You access it from anywhere.** Dashboard shows your context as a mind map, surfaces insights and connections. CLI for power users. Mobile and voice for convenience.

**Privacy is yours to configure.** Self-host for full control. Cloud with zero-knowledge encryption for accessibility. Local models for complete privacy. You decide the tradeoffs.

---

## The Agent

Tama is a proactive assistant that:

**Organizes** — Processes incoming context, creates structure, surfaces connections you missed.

**Suggests** — "You mentioned X last week and Y today — these seem related." "You have a meeting with Sarah tomorrow. Here's what you discussed last time." "Based on your patterns, you usually take a break now."

**Acts** — With your permission, takes actions. Books things. Sends messages. Manages tasks. "Your son usually does soccer on Tuesdays — should I book that for him?"

**Represents** — In federation scenarios, Tama can argue on your behalf. Two agents can negotiate, debate, reach resolution — then present the outcome to the humans for final decision.

It handles the busywork so you don't have to.

---

## Federation

Most personal AI systems don't solve this: sharing context with others.

Current state: Your AI and my AI can't talk to each other. If you and I collaborate, context gets copied back and forth manually. Information degrades.

Hiroba solves this:
- Create a shared room with specific permissions
- Both agents see the shared subgraph
- Agents can collaborate on tasks, share updates, even negotiate
- Humans review outcomes, make final calls

Use cases:
- Work: Project context shared across team members' agents
- Personal: Family members coordinating schedules, shared household knowledge
- Hybrid: Spouses who also work together

Federation is near-term, after MVP. MCP and A2A provide foundations, but personal context federation needs more work. RikaiOS can contribute here.

---

## Philosophy

The name comes from Japanese:

**Rikai (理解)** — Understanding, comprehension. Easy for English speakers to pronounce. I also considered **Kioku (記憶)** — memory — but Rikai felt more active. The agent understands and acts, not just remembers.

The aesthetic is intentional. Japanese design principles:
- **Kanso (簡素)** — Simplicity. Clean separation of concerns.
- **Ma (間)** — Negative space. Don't build everything. Be intentional.
- **Shizen (自然)** — Naturalness. Work with existing tools (MCP, Letta), not against them.

The vibe is **stillness and clarity**. Marie Kondo for your digital life.

Free and independent. Your context, your control, your pace.

---

## Privacy

Privacy matters, but it's nuanced.

**Self-hosted**: Full control. Data never leaves your infrastructure. Use local models (Ollama, etc.) for complete privacy.

**Cloud-hosted**: For accessibility — your agent available anywhere. But with zero-knowledge encryption. You hold the keys. The server sees encrypted data only.

**Hybrid**: Sensitive stuff local. Convenience stuff cloud. You decide the boundary.

You own your context. Not Google. Not OpenAI. Not Anthropic. You.

If you use cloud models (Claude, GPT), yes, those queries go to their APIs. That's a tradeoff you choose. But the context lake — Umi — stays yours.

---

## Market Reality

OpenAI, Google, and Anthropic will go heavily into the personal assistant space. They have more resources, more users, more data.

RikaiOS focuses on a different thing:
- **Ownership**: Your context lake, yours to keep
- **Federation**: Share with others directly
- **Model agnostic**: Switch providers without losing context
- **Open source**: Inspect, modify, self-host
- **Philosophy**: Stillness and clarity

RikaiOS is for people who want to own their context.

---

## Open Source Strategy

**Core is open source:**
- Umi (context lake)
- Tama (agent runtime)
- Hiroba (federation)
- Self-hosted deployment
- Connectors

**Paid offerings:**
- Cloud-hosted version (convenience, managed infrastructure)
- Enterprise features (SSO, audit logs, compliance)
- Managed federation network

Open-core plus commercial service. Revenue comes from hosting and enterprise needs.

---

## What Exists Today

The repository is a working prototype.

**Done:**
- Umi storage layer (Postgres + pgvector + MinIO)
- Entity and document management
- Semantic search with Voyage AI embeddings
- Tama agent on Letta with custom Umi tools
- Connectors: Git, Google, Files, Chat, Telegram, Slack
- MCP server exposing context to Claude Desktop
- CLI (rikaictl) for infrastructure management
- REST API

**In progress:**
- Hiroba federation (structure exists, sync protocol is placeholder)
- Dashboard with mind map visualization
- Proactive agent behaviors

**Not started:**
- Zero-knowledge cloud deployment
- Personality learning from passive data
- Agent-to-agent negotiation protocol

---

## Technical Open Questions

These are research areas, not solved problems:

**Multi-modal memory**: Current systems handle declarative OR procedural memory, not both well. MemoryBench (2025) shows this gap.

**Federation protocol**: MCP and A2A exist for agent communication, but personal context sharing across owners is still undefined. RikaiOS can help define this.

**Personality replication**: Stanford's research gets 85% accuracy from 2-hour interviews. Can this be bootstrapped from passive data (chat histories, decisions, patterns) without explicit interviews?

**Intelligent curation**: What to remember vs. forget? Supermemory uses "intelligent decay" — less relevant info fades. Is this right, or should the philosophy be "remember everything, let humans decide"? Open question.

**Memory coexistence**: How should Umi and Letta's internal memory coexist? Current answer: hybrid. Letta for hot context, Umi for cold. The boundary needs refinement.

**Integration strategy**: Build custom connectors (control, more work) or integrate with Supermemory as a layer (faster, but dependency)? Answer: both. Supermemory for quick wins, custom for differentiation.

---

## What If

**What if local models get really good?**

In 2-3 years, local models might match cloud quality. Does RikaiOS become more valuable (full privacy possible) or less (everyone can run this)? Hard to predict. Stay flexible. This needs ongoing research with potential pivots.

**What if big labs ship persistent memory?**

They will. The difference isn't features — it's ownership, federation, and philosophy. Different approach for different users.

**What if the landscape shifts dramatically?**

It will. This is a 2025 prototype in a fast-moving space. The assumption: people want unified context they own. Implementation will evolve.

---

## Naming

**Rikai (理解)** — Understanding. Chosen for pronunciation (accessible to English speakers) and meaning.

The kanji 理 (ri) means logic/reason. "Understanding" as a whole captures the goal.

**Kioku (記憶)** — Memory. Was considered. More accurate to storage, but felt passive. Also harder for non-Japanese speakers to pronounce.

The Japanese naming signals the philosophy: simplicity, intentionality, naturalness.
