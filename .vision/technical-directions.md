# RikaiOS Technical Directions

**Last Updated:** January 2026
**Purpose:** Critically assess research directions, who's solving them, and whether RikaiOS should pursue each.

---

## Direction 1: Hierarchical Memory Architecture

**The Problem:** Current AI agents have "amnesia" — context windows are bigger buffers, not true memory. The field is fragmented with no unified approach.

### What Exists in 2026

| Solution | Approach | Open Source | Production Ready |
|----------|----------|-------------|------------------|
| [Letta](https://www.letta.com/blog/letta-code) | Token-space learning, skill extraction | Yes | Yes |
| [Mem0](https://arxiv.org/abs/2504.19413) | Memory extraction + graph (Mem0g) | Partial | Yes |
| [MIRIX](https://arxiv.org/html/2507.07957v1) | 6-type memory system | Unknown | Research |
| [Supermemory](https://supermemory.ai/) | Brain-inspired with decay | Partial | Yes (proprietary core) |
| [Zep](https://medium.com/asymptotic-spaghetti-integration/from-beta-to-battle-tested-picking-between-letta-mem0-zep-for-ai-memory-6850ca8703d1) | Knowledge graphs for temporal reasoning | Partial | Yes |

### Current Landscape Assessment

[MemoryBench (2025)](https://arxiv.org/html/2510.17281v4) findings are damning: **None of the advanced memory systems (A-Mem, Mem0, MemoryOS) consistently outperform simple RAG baselines.**

Letta outperforms Mem0 on LoCoMo benchmark (74.0% vs 68.5%). The reason? Agents with filesystem access beat specialized memory tools because they can iteratively query.

MIRIX introduces a promising 6-type taxonomy: Core, Episodic, Semantic, Procedural, Resource, Knowledge Vault. Achieves 35% higher accuracy than RAG on ScreenshotVQA while reducing storage 99.9%.

### RikaiOS Opportunity

**The Forms/Functions/Dynamics taxonomy you proposed is sound:**

```
FORMS (storage medium)
├── Token-level (Letta blocks - explicit)
├── Parametric (fine-tuned weights - implicit)
└── Latent (hidden states - working context)

FUNCTIONS (what it stores)
├── Factual (Umi entities - knowledge)
├── Experiential (patterns, habits, preferences)
└── Working (active task context)

DYNAMICS (lifecycle)
├── Formation (extract from conversations)
├── Evolution (consolidate, compress, forget)
└── Retrieval (hybrid search + retrieval)
```

**What's missing that RikaiOS could provide:**
- Hot→cold consolidation (Letta→Umi boundary is primitive)
- Episodic memory (conversation trajectories, not just facts)
- Sleep-time consolidation (exists in Letta, not connected to external storage)

### Verdict: PURSUE (HIGH IMPACT)

**Why:** The foundation exists (Letta + Umi), but the integration is basic. No one has an open-source hybrid that does consolidation properly. RikaiOS is positioned to fill this gap.

**Risk:** MIRIX or Letta may ship this before RikaiOS. Monitor closely.

---

## Direction 2: Context Federation (Hiroba)

**The Problem:** A2A and MCP handle tool calling, not personal context sharing across owners.

### What Exists in 2026

| Protocol | Purpose | Who |
|----------|---------|-----|
| [MCP](https://auth0.com/blog/mcp-vs-a2a/) | Context flow to agents | Anthropic |
| [A2A](https://a2a-protocol.org/latest/topics/a2a-and-mcp/) | Agent-to-agent task coordination | Google + 50 partners |
| [SAMEP](https://arxiv.org/html/2507.10562) | **Secure Agent Memory Exchange Protocol** | Academic |
| [ACP](https://onereach.ai/blog/power-of-multi-agent-ai-open-protocols/) | Agent Communication Protocol | IBM |
| [ANP](https://onereach.ai/blog/power-of-multi-agent-ai-open-protocols/) | Agent Network Protocol | Community |

### SAMEP Is Directly Relevant

[SAMEP (Secure Agent Memory Exchange Protocol)](https://arxiv.org/html/2507.10562) addresses exactly what Hiroba needs:
- Persistent context preservation across agent sessions
- Secure multi-agent collaboration with fine-grained access control
- Semantic discovery of relevant historical context
- Implements distributed memory repository with vector search
- Cryptographic access controls (AES-256-GCM)
- **Compatible with MCP and A2A**

This is new research (2026). SAMEP is academic, not production.

### Market Context

[Gartner forecasts](https://onereach.ai/blog/guide-choosing-mcp-vs-a2a-protocols/) 40% of business apps will have task-specific agents by 2027 (up from 5% in 2025). Multi-agent coordination is urgent.

But: Enterprise agents use A2A. **Consumer personal AI federation doesn't exist.** This is genuinely unoccupied territory.

### Verdict: PURSUE (VERY HIGH IMPACT)

**Why:** SAMEP validates the direction but is academic/incomplete. Hiroba could be the production implementation of personal context federation. No one else is doing this for consumers.

**Action:** Study SAMEP deeply. Consider contributing to or building on their protocol spec rather than inventing new.

---

## Direction 3: Trajectory Verification & Skill Learning

**The Problem:** How do agents learn from their own experience?

### What Exists in 2026

[Letta has already solved this](https://www.letta.com/blog/skill-learning):
- Given a trajectory, generate a reflection (did it work? logical? edge cases?)
- Feed reflection to learning agent → generate reusable skill
- **36.8% relative improvement** over baseline
- Skills capture successful patterns; feedback-informed skills encode failure modes

Related work:
- [MUSE Framework](https://arxiv.org/html/2510.08002v1): Hierarchical Memory Module extracts reusable knowledge from trajectories
- [LEGOMem (AAMAS 2026)](https://arxiv.org/html/2510.04851): Modular procedural memory for workflow automation
- ExpeL, Agent Workflow Memory, Memp: Various approaches to procedural learning

### Verdict: LEVERAGE, DON'T REINVENT (MEDIUM IMPACT)

**Why:** Letta's skill learning is mature. RikaiOS already uses Letta. The opportunity is connecting Letta's skill learning to Umi's knowledge graph, not building skill learning from scratch.

**Action:** Ensure TamaMemory bridges skills from Letta into Umi entities. Focus on the integration, not the mechanism.

---

## Direction 4: Personality Learning from Passive Data

**The Problem:** Stanford gets 85% accuracy from 2-hour interviews. Can we bootstrap this from passive data (chat histories, decisions, patterns)?

### What Exists in 2026

| Approach | Source | Status |
|----------|--------|--------|
| [ML-based personality from text](https://www.researchgate.net/publication/366867571_How_Well_Can_an_AI_Chatbot_Infer_Personality_Examining_Psychometric_Properties_of_Machine-Inferred_Personality_Scores) | APA/Academic | Research |
| [Digital Fingerprint of Learner Behavior](https://www.sciencedirect.com/science/article/pii/S2666920X24001255) | Academic | Research |
| [Behavioral Biometrics](https://www.ibm.com/think/topics/behavioral-biometrics) | IBM/Industry | Security-focused |
| [Social media personality prediction](https://www.nature.com/articles/s41598-024-56080-8) | Nature/Academic | Research |

Key insight from research: ML extracts linguistic cues capturing behavioral nuances **beyond what self-reported questionnaires capture**. This is promising.

The "Digital Fingerprint of Learner Behavior" research shows: given enough fine-grained behavioral data, you can discriminate individuals across contexts.

### Current State

- Academic research validates feasibility
- No production system does this for personal AI assistants
- Behavioral biometrics is used for security, not personality modeling
- Social media analysis works but raises privacy concerns

### Verdict: PURSUE AS RESEARCH (HIGH IMPACT, HIGH RISK)

**Why:** Genuine gap. If RikaiOS can auto-generate Tama's `human_description` from passive data instead of interviews, that's a significant differentiator.

**Approach:**
```python
class PersonalityLearner:
    async def analyze_chat_history(self, documents: list[Document]):
        # Extract: communication style, topics, sentiment patterns

    async def analyze_decisions(self, entities: list[Entity]):
        # Extract: decision patterns, priorities, values

    async def synthesize_persona(self) -> str:
        # Generate Tama's "human" memory block automatically
```

**Risk:** Privacy implications. Must be explicitly opt-in with clear consent.

---

## Direction 5: What to Remember vs Forget

**The Problem:** "None of these systems solve the fundamental challenge: deciding what to remember and what to forget." — [Dan Giannone](https://www.emergentmind.com/papers/2512.13564)

### What Exists in 2026

| Solution | Approach | Open? |
|----------|----------|-------|
| [Supermemory](https://blog.supermemory.ai/memory-engine/) | "Intelligent decay" — older/less relevant fades | Proprietary |
| [Google Titans](https://research.google/blog/titans-miras-helping-ai-have-long-term-memory/) | Adaptive weight decay + "surprise metric" | No |
| Academic | Various forgetting mechanisms | Fragmented |

Supermemory's approach is brain-inspired:
- Smart forgetting (gradual decay)
- Recency bias
- Context rewriting
- Scales to 50M tokens/user

Google's Titans uses "surprise" — humans forget routine events but remember surprises. This is compelling neuroscience.

### The Open Research Question

From [Memory in the Age of AI Agents survey](https://arxiv.org/abs/2512.13564):
> "Limited treatment of non-iid streaming and concept drift necessitates developing adaptive memory policies (aging, reweighting, forgetting) and drift detection mechanisms."

No open-source solution exists.

### Verdict: MERGE INTO DIRECTION 1 (CRITICAL GAP)

**Why:** This is core to hierarchical memory, not a separate direction. The "what to forget" algorithm is the missing piece in the Letta→Umi consolidation pipeline.

**Approach:**
1. Implement surprise-based importance scoring (inspired by Titans)
2. Decay based on access patterns + relevance + age
3. Allow "Core Memories" that never decay (user-tagged)
4. Make the decay algorithm transparent and configurable

---

## Direction 6: Hybrid Continual Learning Architecture

**The Problem:** No one combines token-space learning (Letta) + sparse parametric memory (Meta) + cold storage (Umi) in open source.

### What Exists in 2026

From the [Memory in AI Agents survey](https://github.com/Shichun-Liu/Agent-Memory-Paper-List):

| Approach | Who | Open Source | Production Ready |
|----------|-----|-------------|------------------|
| Nested Learning | Google | No | Research |
| Sparse Memory Layers | Meta FAIR | Yes | Reference impl |
| Token Space Learning | Letta | Yes | Yes |
| MESU (Bayesian) | Academic | Unknown | Research |

### The Gap

RikaiOS could fill:
- **Open-source hybrid** — Combine token space + sparse memory + cold storage
- **Sleep-time consolidation** — Letta has it, not integrated with external storage
- **Declarative + Procedural together** — MemoryBench shows no one handles both

### Verdict: MERGE INTO DIRECTION 1 (ARCHITECTURAL)

**Why:** This isn't a separate direction — it's the implementation strategy for Direction 1.

The proposed architecture is sound:
```python
class HybridContinualLearning:
    def __init__(self):
        self.letta = LettaAgent()       # Hot memory (token space)
        self.umi = UmiClient()           # Cold storage (vectors + graph)
        # Sparse memory is optional/future

    async def sleep_consolidate(self):
        """Run during idle time."""
        patterns = await self.extract_patterns()
        await self.umi.consolidate_memories()
        await self.apply_decay()
        skills = await self.extract_skills()
        await self.letta.update_persona(skills)
```

---

## Direction 7: Declarative + Procedural Memory Together

**The Problem:** [MemoryBench](https://arxiv.org/html/2510.17281v4) shows ALL existing systems fail at combining declarative (facts) and procedural (how-to) memory.

### What Exists in 2026

- **Mem0, MemoryOS**: Treat all inputs as declarative memory
- **LEGOMem**: Focuses on procedural (workflow automation)
- **MIRIX**: Claims to handle both (6-type system)
- **Letta**: Has skill learning (procedural) but separate from archival (declarative)

### The Gap

> "The feedback logs in MemoryBench are non-factual information describing how the system performed in historical tasks (i.e., procedural memory). Existing memory-based LLM systems such as Mem0 and MemoryOS simply treat all inputs as declarative memory and develop memory mechanisms accordingly."

RikaiOS architecture already separates:
- **Umi** = Declarative (entities, documents, facts)
- **Letta skills** = Procedural (how to do things)

### Verdict: NATURAL FIT (HIGH IMPACT)

**Why:** RikaiOS is architected for this. Umi stores facts, Letta stores skills. The gap is **unified retrieval** — when should the agent use a skill vs. a fact?

**Action:** Build a unified retrieval layer that considers both Umi entities and Letta skills based on query intent classification.

---

## Direction 8: Session Continuity

**The Problem:** `claude-progress.txt` files, flat logs. No semantic understanding of prior work.

### What Exists in 2026

This is becoming commoditized:

| Solution | Approach |
|----------|----------|
| [LangGraph + cognee](https://www.cognee.ai/blog/integrations/langgraph-cognee-integration-build-langgraph-agents-with-persistent-cognee-memory) | Graph-backed persistent semantic memory |
| [OpenAI Agents SDK](https://cookbook.openai.com/examples/agents_sdk/session_memory) | `session.run()` with automatic context management |
| [Letta](https://www.letta.com/blog/letta-code) | Built-in stateful agents |
| Vector DBs (Pinecone, Weaviate) | Long-term context retention |

[LangGraph-cognee](https://www.cognee.ai/blog/integrations/langgraph-cognee-integration-build-langgraph-agents-with-persistent-cognee-memory): "Agents store data in graph-backed systems and retrieve it via natural language, enabling seamless continuity without manual state management."

### Verdict: TABLE (LOW DIFFERENTIATION)

**Why:** Session continuity is being solved by multiple players. Letta already provides this for Tama. RikaiOS doesn't need to innovate here — just use what exists.

**Risk of over-investment:** Building custom session continuity when Letta handles it.

---

## Direction 9: Multi-Agent Memory Protocol (Hiroba)

**See Direction 2: Context Federation**

This is the same direction with a different name. Hiroba IS the multi-agent memory protocol for RikaiOS.

**Key insight:** [SAMEP](https://arxiv.org/html/2507.10562) is the academic foundation. Hiroba could be the production implementation.

---

## Direction 10: Context Drift Detection & Correction

**The Problem:** Agents degrade over extended interactions. Context gets diluted, not lost.

### What Exists in 2026 (BREAKING RESEARCH)

[Agent Drift paper (January 2026)](https://arxiv.org/html/2601.04170) — just published:

Defines three drift types:
1. **Semantic drift**: Progressive deviation from original intent
2. **Coordination drift**: Breakdown in multi-agent consensus
3. **Behavioral drift**: Emergence of unintended strategies

Proposes **Agent Stability Index (ASI)** — 12 dimensions including response consistency, tool usage patterns, reasoning pathway stability.

**Mitigation strategies:**
- **EMC (Episodic Memory Consolidation)**: Periodic compression, distilling learnings while pruning redundant context
- **DAR (Drift-Aware Routing)**: Router prefers stable agents, triggers resets for drifting ones
- **ABA (Adaptive Behavioral Anchoring)**: Few-shot prompt augmentation from baseline period

[Contextual Memory Intelligence paper](https://arxiv.org/html/2506.05370v1) introduces:
- **Insight drift**: Gradual loss of meaning behind decisions
- **Resonance Intelligence**: Detect misalignment and restore coherence

### Key Finding

> "The real source of drift is often tool output noise — as agents call APIs, parse PDFs, or process logs, they accumulate enormous amounts of irrelevant text that bury earlier instructions. The context doesn't run out, it gets diluted."

[Research shows](https://medium.com/aimonks/the-brains-behind-the-bots-a-comprehensive-guide-to-ai-agent-memory-in-2026-58934cc588b6) multi-agent coordination can consume **15x more tokens** than single-agent work. Without shared memory, multi-agent systems fail **77.5% of the time**.

### Verdict: PURSUE (HIGH IMPACT, RESEARCH-ADJACENT)

**Why:** This is cutting-edge. The Agent Drift paper is 2 days old. No production implementations exist. RikaiOS could implement EMC/DAR/ABA for Tama.

**Action:**
1. Implement drift detection (ASI metrics for Tama)
2. Add periodic consolidation (EMC) to TamaMemory
3. Consider drift-aware routing for multi-Tama scenarios (Hiroba)

---

## Direction 11: Proactive Context Surfacing

**The Problem:** Current agents are reactive — they wait for prompts. The vision describes Tama that says: "You mentioned X last week and Y today — these seem related." This requires anticipating user needs without being asked.

### What Exists in 2026

| Solution | Approach | Status |
|----------|----------|--------|
| [Google Jules](https://blog.google/technology/developers/jules-proactive-updates/) | Suggested Tasks — scans code, proposes improvements | Production |
| [Lenovo Qira / Motorola Project Maxwell](https://news.lenovo.com/pressroom/press-releases/hybrid-ai-personalized-perceptive-proactive-ai-portfolio-tech-world-ces-2026/) | Personal Ambient Intelligence — context-aware across devices | CES 2026 |
| [Gemini 3 in Gmail](https://markets.financialcontent.com/wral/article/tokenring-2026-1-9-google-redefines-the-inbox-gemini-3-integration-turns-gmail-into-a-proactive-personal-assistant) | Proactive inbox assistant | Production |
| [CHI 2025 Research](https://dl.acm.org/doi/10.1145/3706598.3714002) | UX patterns for proactive programming assistants | Research |

### Key Insight: It's Happening in 2026

[Google's bet](https://blog.google/technology/developers/jules-proactive-updates/) on Jules: "We're betting on proactive agents, ones that can carry that load for you. They surface meaningful tasks, prepare fixes you didn't explicitly ask for and keep the system healthy in the background."

[Lenovo at CES 2026](https://news.lenovo.com/pressroom/press-releases/hybrid-ai-personalized-perceptive-proactive-ai-portfolio-tech-world-ces-2026/): AI is now "personal, perceptive, proactive, and everywhere" — Project Maxwell "continuously collects scenario data—seeing what you see, hearing what you hear—and provides real-time insights."

[AI Assistants becoming OS features](http://www.techtimes.com/articles/313714/20260103/how-ai-assistants-are-becoming-default-operating-systems-features-2026.htm): "Context-aware intelligence means AI analyzes usage patterns, location, environmental factors, and user preferences to anticipate actions."

### The Gap

Big players (Google, Lenovo, Apple) are doing this for their ecosystems. But:
- **Closed ecosystems** — Qira works on Lenovo devices, Gemini on Google products
- **No personal ownership** — Your patterns are learned by the platform, not you
- **No federation** — Your proactive agent can't collaborate with others

### How Proactive Surfacing Works

[From Lyzr's definition](https://www.lyzr.ai/glossaries/proactive-ai-agents/):
1. **Event Monitoring** — Continuously ingest data (calendars, emails, sensors, APIs)
2. **Predictive Models** — ML on user behavior/preferences to anticipate needs
3. **Decision Frameworks** — Reasoning engine determines if intervention is valuable vs. intrusive

### Challenges

From [CHI 2025 research](https://dl.acm.org/doi/10.1145/3706598.3714002):
- **Interruption fatigue** — Too frequent = frustrating. Knowing when to stay silent is critical.
- **Misinterpretation** — Wrong context leads to disruptive suggestions
- **Privacy** — Requires access to vast personal data

### RikaiOS Opportunity

Tama already has the primitives:
- **Umi** = Event monitoring (connectors ingest from everywhere)
- **Letta** = Reasoning engine with self-modifying memory
- **Human block** = Learned preferences

What's missing:
- **Proactive trigger system** — When should Tama speak up?
- **Relevance scoring** — Is this connection worth surfacing?
- **Timing/channel** — Mobile push? Dashboard highlight? Wait for next conversation?

### Proposed Architecture

```python
class ProactiveContextEngine:
    """Surface relevant connections without being asked."""

    async def detect_connections(self):
        """Run periodically or on new data ingestion."""
        recent = await self.umi.get_recent_entities(hours=24)
        for entity in recent:
            # Find unexpected connections to older context
            connections = await self.umi.semantic_search(
                entity.summary,
                min_age_days=7,  # Don't surface obvious recent stuff
                min_relevance=0.8
            )
            for conn in connections:
                if await self.is_worth_surfacing(entity, conn):
                    await self.queue_insight(entity, conn)

    async def is_worth_surfacing(self, new: Entity, old: Entity) -> bool:
        """Avoid interruption fatigue."""
        # Not surfaced recently
        # User hasn't dismissed similar before
        # High surprise value (unexpected connection)
        # Actionable (not just trivia)
        pass

    async def deliver_insight(self, insight: Insight):
        """Choose channel based on urgency and user preferences."""
        if insight.urgency == "high":
            await self.push_notification(insight)
        else:
            await self.add_to_dashboard(insight)
            # Or wait for next conversation: "By the way..."
```

### Verdict: PURSUE (HIGH IMPACT)

**Why:** This is core to the Tama vision — a proactive assistant, not a reactive chatbot. Big players are doing it for their ecosystems; RikaiOS can do it for the open/self-hosted world.

**Differentiation:**
- Open source — see exactly how it decides to surface
- Federated — your proactive agent can consider shared Hiroba context
- User-owned — your patterns stay in your Umi, not Google's servers

**Risk:** Getting the UX right is hard. Start conservative (dashboard only), graduate to notifications.

---

## Summary: Prioritized Directions

| Direction | Priority | Rationale |
|-----------|----------|-----------|
| **2. Context Federation (Hiroba)** | VERY HIGH | Unoccupied territory. SAMEP validates approach. |
| **1. Hierarchical Memory** | HIGH | Foundation exists, integration is primitive. Includes decay/forget. |
| **11. Proactive Context Surfacing** | HIGH | Core to Tama vision. Big players doing it closed; RikaiOS can do it open. |
| **7. Declarative + Procedural** | HIGH | Natural fit for Umi + Letta. Unified retrieval needed. |
| **10. Context Drift** | HIGH | Cutting-edge research. First-mover opportunity. |
| **4. Personality from Passive Data** | MEDIUM-HIGH | Differentiator, but research-heavy. |
| **3. Trajectory/Skill Learning** | MEDIUM | Leverage Letta, don't reinvent. |
| **8. Session Continuity** | LOW | Commoditized. Use existing solutions. |

### Directions Merged

- **Direction 5 (Remember/Forget)** → Merged into Direction 1
- **Direction 6 (Hybrid Architecture)** → Merged into Direction 1
- **Direction 9 (Multi-Agent Protocol)** → Same as Direction 2

---

## Competitive Landscape Summary

| Player | Strength | Weakness | RikaiOS Opportunity |
|--------|----------|----------|---------------------|
| Letta | Token-space learning, skills | No external cold storage integration | Bridge to Umi |
| Mem0 | Graph memory (Mem0g) | Doesn't beat RAG per MemoryBench | Beat their benchmarks |
| Supermemory | Intelligent decay, scale | Proprietary core | Open-source alternative |
| SAMEP | Academic rigor on federation | Not production | Implement for real |
| OpenAI/Google/Anthropic | Resources, users | Lock-in, no federation | Ownership + federation |

---

## Sources

- [Letta Benchmarking AI Agent Memory](https://www.letta.com/blog/benchmarking-ai-agent-memory)
- [Mem0 arXiv Paper](https://arxiv.org/abs/2504.19413)
- [MemoryBench](https://arxiv.org/html/2510.17281v4)
- [SAMEP: Secure Agent Memory Exchange Protocol](https://arxiv.org/html/2507.10562)
- [Agent Drift Paper](https://arxiv.org/html/2601.04170)
- [Memory in the Age of AI Agents Survey](https://arxiv.org/abs/2512.13564)
- [MIRIX Multi-Agent Memory](https://arxiv.org/html/2507.07957v1)
- [LEGOMem (AAMAS 2026)](https://arxiv.org/html/2510.04851)
- [Letta Skill Learning](https://www.letta.com/blog/skill-learning)
- [Supermemory Memory Engine](https://blog.supermemory.ai/memory-engine/)
- [Google Titans + MIRAS](https://research.google/blog/titans-miras-helping-ai-have-long-term-memory/)
- [MCP vs A2A Guide](https://auth0.com/blog/mcp-vs-a2a/)
- [A2A Protocol](https://a2a-protocol.org/latest/topics/a2a-and-mcp/)
- [Google Jules Proactive Updates](https://blog.google/technology/developers/jules-proactive-updates/)
- [Lenovo CES 2026 - Proactive AI](https://news.lenovo.com/pressroom/press-releases/hybrid-ai-personalized-perceptive-proactive-ai-portfolio-tech-world-ces-2026/)
- [Proactive AI Agents Definition](https://www.lyzr.ai/glossaries/proactive-ai-agents/)
- [CHI 2025 - Proactive AI Assistants for Programming](https://dl.acm.org/doi/10.1145/3706598.3714002)
