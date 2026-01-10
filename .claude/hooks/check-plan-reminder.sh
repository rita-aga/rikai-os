#!/bin/bash
# Reminder hook - checks if plan exists and required sections are filled
# Used as PreToolUse hook for Edit/Write operations

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
PROGRESS_DIR="$REPO_ROOT/.progress"

# Find active plan
PLAN=$(ls -t "$PROGRESS_DIR"/*.md 2>/dev/null | grep -v archive | grep -v templates | head -1)

if [ -z "$PLAN" ]; then
    echo ""
    echo "=================================================="
    echo "  REMINDER: No plan file found!"
    echo "=================================================="
    echo ""
    echo "Before making changes, you should:"
    echo "1. Read .vision/*.md files"
    echo "2. Create a plan: .progress/$(date +%Y%m%d_%H%M%S)_task-name.md"
    echo "3. Document OPTIONS, DECISIONS, TRADE-OFFS"
    echo ""
    echo "Use /remind to see full checklist."
    echo "=================================================="
    echo ""
    exit 0
fi

# Check plan state
STATE=$(grep -oP '^\*\*State:\*\*\s*\K\w+' "$PLAN" 2>/dev/null || echo "UNKNOWN")

if [ "$STATE" = "GROUNDING" ] || [ "$STATE" = "PLANNING" ]; then
    echo ""
    echo "=================================================="
    echo "  REMINDER: Plan is in $STATE state"
    echo "=================================================="
    echo ""
    echo "Current plan: $(basename "$PLAN")"
    echo ""
    echo "Complete planning before implementing:"
    echo "- Fill in Options & Decisions section"
    echo "- Document trade-offs"
    echo "- Update state to IMPLEMENTING when ready"
    echo "=================================================="
    echo ""
fi

# Check for empty required sections
WARNINGS=""

# Check Options & Decisions - look for unfilled template
if grep -q '\[Title\]' "$PLAN" 2>/dev/null && grep -q '\[Which option and why\]' "$PLAN" 2>/dev/null; then
    WARNINGS="$WARNINGS\n- Options & Decisions: Still has template placeholders"
fi

# Check Quick Decision Log - look for empty table
DECISION_LOG_LINES=$(grep -A 3 "Quick Decision Log" "$PLAN" 2>/dev/null | grep -c '| |' || echo "0")
if [ "$DECISION_LOG_LINES" -gt 0 ]; then
    WARNINGS="$WARNINGS\n- Quick Decision Log: Appears empty (no entries)"
fi

# Check What to Try - look for template text
if grep -q '\[Feature/capability\]' "$PLAN" 2>/dev/null && grep -q '\[Exact command or steps\]' "$PLAN" 2>/dev/null; then
    WARNINGS="$WARNINGS\n- What to Try: Still has template placeholders"
fi

if [ -n "$WARNINGS" ]; then
    echo ""
    echo "=================================================="
    echo "  WARNING: Required sections need attention"
    echo "=================================================="
    echo ""
    echo "Current plan: $(basename "$PLAN")"
    echo ""
    echo "Issues found:"
    echo -e "$WARNINGS"
    echo ""
    echo "These sections are REQUIRED - do not skip them."
    echo "Use /remind to see what's needed."
    echo "=================================================="
    echo ""
fi

exit 0
