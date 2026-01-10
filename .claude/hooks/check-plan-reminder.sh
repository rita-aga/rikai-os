#!/bin/bash
# Reminder hook - checks if plan exists and reminds agent of process
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
    echo "3. Document options considered and trade-offs"
    echo ""
    echo "Use /remind to see full checklist."
    echo "=================================================="
    echo ""
    # Don't block, just remind
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

exit 0
