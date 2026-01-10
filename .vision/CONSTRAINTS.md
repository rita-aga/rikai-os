# RikaiOS Constraints

> Non-negotiable rules. If a decision violates these, it's wrong.

---

## Privacy Constraints

### MUST
- [ ] Self-hosted option must always exist
- [ ] User data must never be used for training without explicit consent
- [ ] Zero-knowledge encryption for any cloud storage
- [ ] User holds encryption keys, not the service
- [ ] Local model support (Ollama, etc.) for complete privacy

### MUST NOT
- [ ] Never send user context to third parties without explicit permission
- [ ] Never make cloud-only features that can't be self-hosted
- [ ] Never require account creation for core functionality
- [ ] Never collect telemetry without opt-in

---

## Architecture Constraints

### Three-Layer Architecture
Every feature must fit into:
- **Umi** — Storage and retrieval
- **Tama** — Agent reasoning and action
- **Hiroba** — Federation and sharing

If it doesn't fit, reconsider the feature.

### Technology Choices
- **Letta** for agent runtime (don't rebuild this)
- **Postgres + Qdrant + MinIO** for storage tiers
- **MCP** for external tool integration
- **Python 3.11+** with async/await throughout
- **TypeScript** for CLI (rikai-code)

### Integration Over Invention
- Use existing protocols (MCP, A2A) before creating new ones
- Integrate with Supermemory for quick wins, custom connectors for differentiation
- Don't rebuild what Letta already does well

---

## Open Source Constraints

### MUST be open source
- Umi (context lake)
- Tama (agent runtime)
- Hiroba (federation protocol)
- All connectors
- Self-hosted deployment

### MAY be proprietary
- Cloud hosting infrastructure
- Enterprise features (SSO, audit logs, compliance)
- Managed federation network

---

## Code Quality Constraints

- Ruff for linting (line-length 100)
- MyPy strict mode enabled
- Pydantic v2 for data validation
- Tests for new features
- No TODOs in production code (track in issues)

---

## Federation Constraints

- Permission-scoped always — no "share everything" option
- Humans review agent negotiations before final decisions
- No silent data sharing — user must explicitly grant access
- Revocable permissions — can always take back access

---

*When in doubt, choose the option that gives users more control.*
