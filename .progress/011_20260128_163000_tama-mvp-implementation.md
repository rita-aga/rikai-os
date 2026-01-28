# Plan: Tama MVP Implementation

**Goal**: Build a minimal, security-first AI assistant using Kelpie that can bootstrap its own development.

**Status**: Complete

---

## Phase 0: Archive & Setup

### 0.1 Archive Old Code
- [x] Create .archive/ directory
- [x] Move src/, rikai-apps/, infrastructure/, tests/, docker/ to .archive/
- [x] Keep: .vision/, .progress/, CLAUDE.md, README.md

### 0.2 Initialize New Rust Project
- [x] Create Cargo.toml with kelpie dependencies
- [x] Create src/ directory structure

---

## Phase 1: Kelpie Infrastructure

### 1.1 API Authentication Middleware
- File: kelpie/crates/kelpie-server/src/security/auth.rs
- [x] Create ApiKeyAuth struct
- [x] Add middleware for /v1/* endpoints
- [x] Constant-time comparison (subtle crate)
- [x] Public paths: /health, /metrics, /v1/health, /v1/capabilities

### 1.2 Audit Logging
- File: kelpie/crates/kelpie-server/src/security/audit.rs
- [x] Log all tool executions with input/output
- [x] Agent lifecycle events
- [x] Authentication events
- [x] Proposal events
- [x] Stats and export functionality

---

## Phase 2: Tama Assistant

### 2.1 Proposal System
- File: rikai-os/src/proposals.rs
- [x] ProposalType enum (NewTool, MemoryAddition, ConfigChange)
- [x] ProposalTrigger enum (UserRequested, AgentSuggested)
- [x] Proposal struct with status tracking
- [x] ProposalStore with per-user limits
- [x] Tests passing

### 2.2 Trajectory Capture
- File: rikai-os/src/trajectory.rs
- [x] TaskTrajectory struct
- [x] Hot→cold storage pattern
- [x] TrajectoryStore with archival
- [x] Training data export
- [x] Tests passing

### 2.3 User Key Storage
- File: rikai-os/src/user_keys.rs
- [x] AES-GCM encryption at rest
- [x] Per-user key storage
- [x] Master key generation
- [x] Tests passing

### 2.4 Tools
- File: rikai-os/src/tools/proposal.rs
- [x] propose_improvement tool
- File: rikai-os/src/tools/trajectory.rs
- [x] start_trajectory tool
- [x] trajectory_step tool
- [x] complete_trajectory tool

### 2.5 Main Application
- File: rikai-os/src/main.rs
- [x] Wire Kelpie agent service
- [x] Register proposal tools
- [x] Register trajectory tools
- [x] HTTP mode for debugging
- [x] Telegram mode for production

---

## Phase 3: Telegram UX

### 3.1 API Key Collection
- [x] /setup command for entering API keys
- [x] /keys command to show configured integrations
- [x] /clear command to remove keys
- [x] Secure storage with AES-GCM

### 3.2 Proposal Flow
- [x] /proposals command to list pending
- [x] /approve <id> command
- [x] /reject <id> [reason] command

### 3.3 Commands
- [x] /start - Welcome message
- [x] /help - Command help
- [x] /reset - Reset conversation
- [x] /cancel - Cancel setup

---

## Quick Decision Log

| Time | Decision | Rationale |
|------|----------|-----------|
| 16:30 | Use existing rikaios repo | It already has .vision/ files |
| 16:30 | Archive to .archive/ | Preserve old code for reference |
| 16:45 | Use UnifiedToolRegistry | Match kelpie's actual API |
| 16:50 | Get AgentService from AppState | AppState creates it internally |
| 17:00 | Add security module to kelpie | Reusable auth/audit infrastructure |

---

## Findings

- Kelpie already has Telegram interface (kelpie-server/src/interface/telegram.rs)
- Kelpie has both VM backends: Apple VZ and Firecracker
- rikaios repo exists at /Users/seshendranalla/Development/rikaios/
- AppState creates AgentService internally when LLM keys are set
- All 6 rikai tests passing
- All 205 kelpie-server tests passing

---

## Verification

```bash
# rikai-os tests
cd /Users/seshendranalla/Development/rikaios && cargo test
# Result: 6 passed

# kelpie-server tests
cd /Users/seshendranalla/Development/kelpie && cargo test -p kelpie-server --lib
# Result: 205 passed

# Build verification
cd /Users/seshendranalla/Development/rikaios && cargo build
```

---

## Files Created/Modified

### rikai-os (New Rust Assistant)
- `Cargo.toml` - NEW
- `src/main.rs` - NEW
- `src/proposals.rs` - NEW
- `src/trajectory.rs` - NEW
- `src/telegram.rs` - NEW
- `src/user_keys.rs` - NEW
- `src/tools/mod.rs` - NEW
- `src/tools/proposal.rs` - NEW
- `src/tools/trajectory.rs` - NEW
- `.gitignore` - MODIFIED (added .archive/, target/)

### kelpie (Infrastructure)
- `crates/kelpie-server/src/lib.rs` - MODIFIED (added security module)
- `crates/kelpie-server/Cargo.toml` - MODIFIED (added subtle crate)
- `crates/kelpie-server/src/security/mod.rs` - NEW
- `crates/kelpie-server/src/security/auth.rs` - NEW
- `crates/kelpie-server/src/security/audit.rs` - NEW
