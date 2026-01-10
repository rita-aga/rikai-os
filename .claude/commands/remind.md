# TigerStyle Reminder

**STOP. Read this before continuing.**

---

## Are You Following the Process?

### Before Writing Code

- [ ] Did you check if `.vision/` exists? Read whatever's there.
- [ ] Did you create a plan in `.progress/NNN_YYYYMMDD_HHMMSS_task-name.md`?
- [ ] Did you document the options you considered?
- [ ] Did you note the trade-offs of your chosen approach?

### During Implementation

- [ ] Are you logging significant decisions in the plan file?
- [ ] Are you updating the plan as you complete phases?
- [ ] If you hit a blocker, did you document it?

### Before Completion

- [ ] Did you write tests (if applicable for this project)?
- [ ] Did you run `/no-cap` to verify no placeholders/hacks?
- [ ] Does the result align with documented constraints (if any)?
- [ ] Did you update the plan state to COMPLETE?

---

## Quick Reference

```
State Machine: GROUNDING → PLANNING → IMPLEMENTING → VERIFYING → COMPLETE

GROUNDING:   Check .vision/ (read what exists), understand context
PLANNING:    Create .progress/ plan with options/decisions/trade-offs
IMPLEMENTING: Do the work, log decisions
VERIFYING:   Tests (if applicable), /no-cap, alignment check
COMPLETE:    Commit, push
```

---

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `.vision/` | Project vision docs (optional - read if exists) |
| `.progress/` | Task plans (create before coding) |
| `.progress/templates/` | Plan template |

---

## If No Vision Docs Exist

That's fine! Either:
1. Proceed without them (for small tasks)
2. Offer to interview user and create relevant ones:
   - CONSTRAINTS.md - Non-negotiable rules
   - ARCHITECTURE.md - System design
   - PHILOSOPHY.md - Design principles
   - [Custom] - Domain-specific guidance

**Don't assume all files are needed.** Ask what would help.

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Started coding without plan | Stop. Create plan first. |
| Made decision without documenting | Add to Options & Decisions section |
| Skipped tests (when project has them) | Write tests before marking complete |
| Left TODOs in code | Fix or document as intentional |
| Forgot to update plan state | Update now |

---

## If You're Lost

1. Check `.vision/` for any guidance
2. Check current plan in `.progress/`
3. Ask user for clarification if needed

**Goal: Disciplined, traceable development - proportional to task size.**
