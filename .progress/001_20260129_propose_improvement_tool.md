# Plan: Enable Agent to Propose & Learn New Tools

**Created**: 2026-01-29
**Status**: COMPLETED

## Goal
Allow the Tama agent to propose new tools when asked to do something it can't do.

## Current State Analysis

### What EXISTS ✅
- Proposal data model: `rikaios/src/proposals.rs` - ProposalType::NewTool exists
- Proposal store: In-memory store works
- `propose_improvement` tool: `rikaios/src/tools/proposal.rs` - Tool code exists and IS registered
- `/approve` command: `rikaios/src/telegram.rs` - User can approve proposals
- `apply_proposal()`: `rikaios/src/telegram.rs` - ALREADY properly implemented!
- Tool registry: `kelpie-server/src/tools/registry.rs` - Can register custom tools

### What's Actually Working
After reading the code, I found that:
1. `propose_improvement` tool IS already registered in `main.rs:201`
2. `apply_proposal()` IS already implemented properly - registers tools with the registry
3. The system prompt mentions the tool but may need enhancement

### What Might Still Need Work
1. Add `propose_improvement` to MemgptAgent's allowed_tools in kelpie-server/src/models.rs
2. Potentially enhance the system prompt for better tool proposals
3. Add parameter schema support for proposed tools

## Implementation Phases

### Phase 1: Add propose_improvement to MemgptAgent capabilities
**Status**: PENDING
**File**: `kelpie/crates/kelpie-server/src/models.rs`

The MemgptAgent needs to include `propose_improvement` in its allowed_tools.

### Phase 2: Verify tool registration flow
**Status**: COMPLETED (already works)

The tool is already:
- Registered in `main.rs` line 201
- Has proper handler in `tools/proposal.rs`
- `apply_proposal()` properly registers custom tools

### Phase 3: Enhance system prompt
**Status**: PENDING
**File**: `rikaios/src/telegram.rs`

Update system prompt to be more explicit about using propose_improvement.

## Files Modified

| File | Changes | Status |
|------|---------|--------|
| `kelpie/crates/kelpie-server/src/models.rs` | Add `propose_improvement` to MemgptAgent capabilities | DONE |
| `rikaios/src/telegram.rs` | System prompt, persistence init, security warnings in /view & /proposals, namespaced tools, real MemoryAddition & ConfigChange | DONE |
| `rikaios/src/tools/proposal.rs` | Add `init_proposal_store_with_persistence()`, parameters_schema support | DONE |
| `rikaios/src/proposals.rs` | Full rewrite: file persistence, security analysis, validation, cleanup, namespacing | DONE |

## Verification Plan

1. Build rikaios with `cargo build`
2. Start Telegram bot
3. Ask "What tools do you have access to?"
4. Ask "Create a tool to fetch weather"
5. Verify proposal is created
6. Use `/approve` and verify tool is registered

## Issues Fixed (from Code Review)

### CRITICAL #1: Custom tools couldn't be used by agent
**Fixed**: `apply_proposal()` now updates the agent's `tool_ids` after registering the tool.
The agent filter at `agent_actor.rs:313` only allows tools in `allowed_tools` OR `tool_ids`.

### CRITICAL #3: No code review before approval
**Fixed**: Added `/view <id>` command to show full proposal details including source code.
Users are now warned to review code before approving.

### MAJOR #5: Agent didn't know user_id/agent_id
**Fixed**: System prompt now includes both `user_id` and `agent_id`. The agent is created with
a placeholder prompt, then updated after creation to include the generated `agent_id`.

## Quick Decision Log

| Time | Decision | Rationale |
|------|----------|-----------|
| 2026-01-29 | Found propose_improvement already registered | Read main.rs:201 |
| 2026-01-29 | Found apply_proposal already works | Read telegram.rs:953-1052 |
| 2026-01-29 | Need to add to MemgptAgent allowed_tools | Capabilities control tool access |
| 2026-01-29 | Fix: Update agent tool_ids after approval | Agent filter only allows tools in tool_ids |
| 2026-01-29 | Fix: Add /view command for code review | Security: users should see code before approving |
| 2026-01-29 | Fix: Inject user_id/agent_id into system prompt | Agent needs context for propose_improvement |
| 2026-01-29 | Add file-based persistence for proposals | JSON file at {data_dir}/proposals.json |
| 2026-01-29 | Add security pattern detection | Warn users of dangerous code patterns before approval |
| 2026-01-29 | Add namespaced tool names (user_id prefix) | Prevent tool collisions between users |
| 2026-01-29 | Implement actual MemoryAddition | Updates agent.blocks instead of just logging |
| 2026-01-29 | Implement actual ConfigChange | Stores config in agent.metadata["config"] |

## Issues Fixed (Final Code Review)

### CRITICAL #2: Proposal Persistence
**Fixed**: `proposals.rs` now has file-based persistence with `ProposalStore::with_persistence(data_dir)`.
Proposals are saved to `{data_dir}/proposals.json` and loaded on startup.

### Tool Name Collision Prevention
**Fixed**: `Proposal::namespaced_tool_name()` generates `user{user_id}_{tool_name}` to prevent collisions.
`apply_proposal()` now uses namespaced names when registering tools.

### Schema Validation
**Fixed**: `validate_parameters_schema()` validates that parameters_schema is a proper JSON Schema object
with correct `type`, `properties`, and `required` fields.

### Tool Name Validation
**Fixed**: `validate_tool_name()` ensures tool names are lowercase, start with a letter, and contain
only letters, underscores, and digits.

### Security Code Analysis
**Fixed**: `analyze_code_security()` detects dangerous patterns in shell/Python code including:
- Fork bombs, destructive rm commands, disk wiping
- Pipe-to-shell attacks (curl|sh, wget|sh)
- Reverse shell patterns (nc -e, bash -i)
- Python dangerous functions (eval, exec, os.system)

Security warnings are shown in `/proposals` and `/view` commands.

### MemoryAddition Implementation
**Fixed**: Now actually updates agent's `blocks` (memory) instead of just logging.
Appends content to existing block or creates new block for the category.

### ConfigChange Implementation
**Fixed**: Now stores config changes in agent's metadata under a "config" key.

### Proposal Cleanup
**Added**: `cleanup_old_proposals()` removes non-pending proposals older than 30 days.

## Remaining Issues (Deferred)

### Custom Tool Persistence
Custom tools registered via `register_custom_tool()` are still in-memory only.
The Kelpie tool registry doesn't have file-based persistence yet.
**Workaround**: Proposals are persisted, so re-approval after restart would recreate tools.
