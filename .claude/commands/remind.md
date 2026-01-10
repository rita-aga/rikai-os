# TigerStyle Reminder

**STOP. Read this before continuing.**

---

## Are You Following the Process?

### Before Writing Code

- [ ] Did you check if `.vision/` exists? Read NORTHSTAR.md, CONSTRAINTS.md, ARCHITECTURE.md
- [ ] Did you create a plan in `.progress/NNN_YYYYMMDD_HHMMSS_task-name.md`?
- [ ] Did you document the options you considered?
- [ ] Did you note the trade-offs of your chosen approach?

### Required Plan Sections (DO NOT SKIP)

⚠️ **These sections are MANDATORY:**

#### 1. Options & Decisions
- [ ] Listed 2-3 options for each significant choice
- [ ] Documented pros/cons of each option
- [ ] Stated decision with REASONING (why this option?)
- [ ] Listed trade-offs accepted (what are we giving up?)

#### 2. Quick Decision Log
- [ ] Logging ALL decisions, even small ones
- [ ] Each entry has: Time, Decision, Rationale, Trade-off

#### 3. What to Try (UPDATE AFTER EVERY PHASE)
- [ ] **Works Now**: What can user test? Exact steps? Expected result?
- [ ] **Doesn't Work Yet**: What's missing? Why? When expected?
- [ ] **Known Limitations**: Caveats? Edge cases?

### During Implementation

- [ ] Updating Quick Decision Log as you make choices?
- [ ] Updating "What to Try" after each phase?
- [ ] Updating the plan as you complete phases?
- [ ] If you hit a blocker, did you document it?

### Before Completion

- [ ] **Options & Decisions section is filled in** (not placeholders)?
- [ ] **Quick Decision Log has entries** (not empty)?
- [ ] **What to Try section is current** (not template text)?
- [ ] Did you write tests (if applicable for this project)?
- [ ] Did you run `/no-cap` to verify no placeholders/hacks?
- [ ] Does the result align with documented constraints?
- [ ] Did you update the plan state to COMPLETE?

---

## Quick Reference

```
State Machine: GROUNDING → PLANNING → IMPLEMENTING → VERIFYING → COMPLETE

GROUNDING:   Check .vision/, understand context
PLANNING:    Create plan with OPTIONS, DECISIONS, TRADE-OFFS
IMPLEMENTING: Do the work, LOG DECISIONS, UPDATE "WHAT TO TRY"
VERIFYING:   Tests, /no-cap, alignment check
COMPLETE:    Commit, push
```

---

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `.vision/` | Project vision docs (NORTHSTAR, CONSTRAINTS, ARCHITECTURE, etc.) |
| `.progress/` | Task plans (create before coding) |
| `.progress/templates/` | Plan template |

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Skipped Options & Decisions | Stop. Fill in options, pros/cons, reasoning, trade-offs |
| Empty Quick Decision Log | Log decisions NOW, even retroactively |
| "What to Try" has template text | Fill in actual features, steps, expected results |
| Started coding without plan | Stop. Create plan first |
| Made decision without documenting | Add to Options & Decisions or Quick Decision Log |

---

## If You're Lost

1. Check `.vision/` for any guidance
2. Check current plan in `.progress/`
3. Ask user for clarification if needed

**Goal: Disciplined, traceable development with complete decision documentation.**
