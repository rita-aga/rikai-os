# ADR-007: SimLLMProvider - Deterministic LLM Simulation

## Status

Accepted

## Context

Phase 2 of the hybrid architecture (ADR-006) requires a Python layer for LLM integration. To maintain DST (Deterministic Simulation Testing) coverage at the Python layer, we need a way to simulate LLM responses deterministically.

### The Problem

LLM calls are inherently non-deterministic:
- Same prompt can produce different responses
- Network latency varies
- API failures are unpredictable
- Rate limits and timeouts are real

This makes testing LLM-dependent features (entity extraction, query rewriting, evolution detection) difficult:
- Tests are flaky
- Can't reproduce bugs
- Can't test error handling systematically
- Expensive to run (API costs)

### Requirements

1. **Deterministic**: Same seed + prompt = same response
2. **Fault injection**: Simulate timeouts, errors, malformed responses
3. **Domain-aware**: Generate plausible responses for memory operations
4. **Drop-in replacement**: Same interface as real providers

## Decision

Implement `SimLLMProvider` as a deterministic LLM simulator using:

1. **Seeded RNG** for reproducible behavior
2. **Prompt-based routing** to domain-specific response generators
3. **FaultConfig** for systematic error injection
4. **LLMProvider Protocol** for interface consistency

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    LLMProvider Protocol                          │
│                                                                  │
│  async def complete(prompt: str) -> str                         │
│  async def complete_json(prompt: str, schema: type) -> dict     │
└─────────────────────────────────────────────────────────────────┘
         ↑                    ↑                    ↑
         │                    │                    │
┌────────┴────────┐  ┌───────┴────────┐  ┌───────┴────────┐
│ SimLLMProvider  │  │AnthropicProvider│  │ OpenAIProvider │
│   (testing)     │  │  (production)   │  │  (production)  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SimLLMProvider Internals                      │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │PromptRouter │  │ResponseBank │  │FaultInjector│              │
│  │ (classify)  │  │ (templates) │  │  (errors)   │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

### Response Generation Strategy

SimLLMProvider routes prompts to domain-specific generators:

| Prompt Pattern | Generator | Example Output |
|---------------|-----------|----------------|
| "extract entities" | `_sim_entity_extraction()` | `{"entities": [...]}` |
| "rewrite query" | `_sim_query_rewrite()` | `["query1", "query2"]` |
| "detect evolution" | `_sim_evolution_detection()` | `{"type": "update", ...}` |
| "categorize" | `_sim_categorization()` | `["preferences"]` |
| (default) | `_sim_generic()` | `"SimResponse[hash]"` |

Each generator uses:
1. **Prompt hash** for deterministic variation
2. **Seeded RNG** for random choices
3. **Domain knowledge** for plausible outputs

### Fault Injection

FaultConfig enables systematic testing of error paths:

```python
@dataclass
class FaultConfig:
    # LLM faults
    llm_timeout: float = 0.0      # Probability of timeout
    llm_error: float = 0.0        # Probability of API error
    llm_malformed: float = 0.0    # Probability of unparseable response
    llm_rate_limit: float = 0.0   # Probability of rate limit

    # Storage faults (passed to Rust layer)
    storage_read_error: float = 0.0
    storage_write_error: float = 0.0
```

### Determinism Guarantees

1. **Seed-based RNG**: `random.Random(seed)` for all random choices
2. **Prompt hashing**: `sha256(prompt)[:8]` for prompt-specific variation
3. **Ordered iteration**: No dict/set iteration in response generation
4. **No external state**: No timestamps, no network, no file I/O

### Test Example

```python
@pytest.mark.asyncio
async def test_entity_extraction_deterministic():
    """Same seed + prompt = same entities."""
    provider1 = SimLLMProvider(seed=42)
    provider2 = SimLLMProvider(seed=42)

    prompt = "Extract entities from: I met Alice at Acme Corp"

    response1 = await provider1.complete(prompt)
    response2 = await provider2.complete(prompt)

    assert response1 == response2  # Deterministic!

@pytest.mark.asyncio
async def test_handles_timeout_gracefully():
    """Memory system recovers from LLM timeouts."""
    faults = FaultConfig(llm_timeout=1.0)  # 100% timeout
    provider = SimLLMProvider(seed=42, faults=faults)

    with pytest.raises(TimeoutError):
        await provider.complete("any prompt")
```

## Consequences

### Positive

- **Reproducible tests**: Same seed = same behavior across runs
- **Systematic fault testing**: Test all error paths reliably
- **Fast tests**: No network, no API costs
- **CI-friendly**: No API keys needed for basic tests
- **Debug-friendly**: Can replay exact sequences

### Negative

- **Response fidelity**: Simulated responses are simpler than real LLM
- **Maintenance**: Must update generators when adding new prompt types
- **False confidence**: Passing sim tests doesn't guarantee production works

### Mitigations

1. **Integration tests**: Run subset of tests against real LLMs in CI
2. **Response validation**: Validate real responses match expected schema
3. **Prompt regression**: Log prompts in production, replay in sim

## Implementation

### Files to Create

```
umi/
├── __init__.py
├── providers/
│   ├── __init__.py
│   ├── base.py          # LLMProvider Protocol
│   ├── sim.py           # SimLLMProvider
│   ├── anthropic.py     # AnthropicProvider
│   └── openai.py        # OpenAIProvider
├── faults.py            # FaultConfig
└── tests/
    ├── __init__.py
    └── test_providers.py
```

### SimLLMProvider Implementation Sketch

```python
class SimLLMProvider:
    def __init__(self, seed: int, faults: FaultConfig | None = None):
        self.rng = random.Random(seed)
        self.faults = faults or FaultConfig()

    async def complete(self, prompt: str) -> str:
        # 1. Check faults
        self._maybe_inject_fault()

        # 2. Route to generator
        return self._route_prompt(prompt)

    def _route_prompt(self, prompt: str) -> str:
        prompt_lower = prompt.lower()

        if "extract entities" in prompt_lower:
            return self._sim_entity_extraction(prompt)
        elif "rewrite query" in prompt_lower:
            return self._sim_query_rewrite(prompt)
        elif "detect evolution" in prompt_lower:
            return self._sim_evolution_detection(prompt)
        else:
            return self._sim_generic(prompt)
```

## References

- ADR-006: Hybrid Architecture
- TigerStyle: Simulation-First Testing
- FoundationDB Testing: https://apple.github.io/foundationdb/testing.html
