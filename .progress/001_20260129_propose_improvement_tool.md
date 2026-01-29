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
| `rikaios/src/telegram.rs` | Enhance system prompt with detailed instructions | DONE |
| `rikaios/src/tools/proposal.rs` | Add parameters_schema support | DONE |

## Verification Plan

1. Build rikaios with `cargo build`
2. Start Telegram bot
3. Ask "What tools do you have access to?"
4. Ask "Create a tool to fetch weather"
5. Verify proposal is created
6. Use `/approve` and verify tool is registered

## Quick Decision Log

| Time | Decision | Rationale |
|------|----------|-----------|
| 2026-01-29 | Found propose_improvement already registered | Read main.rs:201 |
| 2026-01-29 | Found apply_proposal already works | Read telegram.rs:953-1052 |
| 2026-01-29 | Need to add to MemgptAgent allowed_tools | Capabilities control tool access |
