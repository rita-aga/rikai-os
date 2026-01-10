#!/bin/bash
# Northstar Pre-Commit Hook
# Language-agnostic quality gates before commits

set -e

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
PROGRESS_DIR="$REPO_ROOT/.progress"

echo "[GATE] Running pre-commit verification..."

# 1. Check for active plan in correct state
PLAN=$(ls -t "$PROGRESS_DIR"/*.md 2>/dev/null | grep -v archive | grep -v templates | head -1)
if [ -n "$PLAN" ]; then
    STATE=$(grep -oP '^\*\*State:\*\*\s*\K\w+' "$PLAN" 2>/dev/null || grep -oE 'State:\s*\w+' "$PLAN" 2>/dev/null | head -1 | sed 's/State:\s*//')
    if [ -n "$STATE" ] && [ "$STATE" != "IMPLEMENTING" ] && [ "$STATE" != "VERIFYING" ] && [ "$STATE" != "COMPLETE" ]; then
        echo "[GATE] WARNING: Plan state is '$STATE'"
        echo "[GATE] Consider completing planning before committing"
    fi
fi

# 2. Auto-detect and run tests
echo "[GATE] Checking for tests..."
if [ -f "$REPO_ROOT/package.json" ]; then
    # Node.js project - try bun, npm, yarn
    if command -v bun &> /dev/null && [ -f "$REPO_ROOT/bun.lockb" ]; then
        echo "[GATE] Running: bun test"
        (cd "$REPO_ROOT" && bun test) || echo "[GATE] WARNING: Tests failed"
    elif [ -f "$REPO_ROOT/yarn.lock" ]; then
        echo "[GATE] Running: yarn test"
        (cd "$REPO_ROOT" && yarn test) || echo "[GATE] WARNING: Tests failed"
    else
        echo "[GATE] Running: npm test"
        (cd "$REPO_ROOT" && npm test) || echo "[GATE] WARNING: Tests failed"
    fi
elif [ -f "$REPO_ROOT/pyproject.toml" ] || [ -f "$REPO_ROOT/setup.py" ] || [ -f "$REPO_ROOT/requirements.txt" ]; then
    # Python project
    if [ -d "$REPO_ROOT/tests" ] || [ -d "$REPO_ROOT/test" ]; then
        echo "[GATE] Running: pytest"
        (cd "$REPO_ROOT" && pytest) || echo "[GATE] WARNING: Tests failed"
    fi
elif [ -f "$REPO_ROOT/go.mod" ]; then
    # Go project
    echo "[GATE] Running: go test ./..."
    (cd "$REPO_ROOT" && go test ./...) || echo "[GATE] WARNING: Tests failed"
elif [ -f "$REPO_ROOT/Cargo.toml" ]; then
    # Rust project
    echo "[GATE] Running: cargo test"
    (cd "$REPO_ROOT" && cargo test) || echo "[GATE] WARNING: Tests failed"
fi

# 3. Check for debug statements in staged files
echo "[GATE] Checking for debug statements..."
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

DEBUG_PATTERNS="console\.log|console\.debug|debugger|print\(|println!|fmt\.Print|log\.Print"
DEBUG_FOUND=""

for file in $STAGED_FILES; do
    if [ -f "$file" ]; then
        case "$file" in
            *.test.*|*.spec.*|*_test.*|*_spec.*|*/test/*|*/tests/*|*/spec/*)
                # Skip test files
                continue
                ;;
        esac

        MATCHES=$(grep -nE "$DEBUG_PATTERNS" "$file" 2>/dev/null || true)
        if [ -n "$MATCHES" ]; then
            DEBUG_FOUND="$DEBUG_FOUND\n$file:\n$MATCHES"
        fi
    fi
done

if [ -n "$DEBUG_FOUND" ]; then
    echo "[GATE] WARNING: Debug statements found in staged files:"
    echo -e "$DEBUG_FOUND"
fi

# 4. Check for placeholders
echo "[GATE] Checking for placeholders..."
PLACEHOLDER_PATTERNS="TODO|FIXME|HACK|XXX|PLACEHOLDER"
PLACEHOLDERS_FOUND=""

for file in $STAGED_FILES; do
    if [ -f "$file" ]; then
        MATCHES=$(grep -nE "$PLACEHOLDER_PATTERNS" "$file" 2>/dev/null || true)
        if [ -n "$MATCHES" ]; then
            PLACEHOLDERS_FOUND="$PLACEHOLDERS_FOUND\n$file:\n$MATCHES"
        fi
    fi
done

if [ -n "$PLACEHOLDERS_FOUND" ]; then
    echo "[GATE] WARNING: Placeholders found in staged files:"
    echo -e "$PLACEHOLDERS_FOUND"
fi

# 5. Warn about vision file modifications
if echo "$STAGED_FILES" | grep -q '\.vision/'; then
    echo "[GATE] WARNING: .vision/ files modified - verify this is intentional"
fi

# 6. Check for test files (warning only)
echo "[GATE] Checking test coverage..."
for file in $STAGED_FILES; do
    if [ -f "$file" ]; then
        case "$file" in
            *.test.*|*.spec.*|*_test.*|*_spec.*|*/test/*|*/tests/*|*/spec/*)
                # This is a test file, skip
                continue
                ;;
            *.ts|*.tsx|*.js|*.jsx)
                # JavaScript/TypeScript - check for .test.ts or .spec.ts
                base="${file%.*}"
                if [ ! -f "${base}.test.ts" ] && [ ! -f "${base}.test.tsx" ] && [ ! -f "${base}.spec.ts" ] && [ ! -f "${base}.spec.tsx" ]; then
                    echo "[GATE] NOTE: No test file found for $file"
                fi
                ;;
            *.py)
                # Python - check for test_*.py or *_test.py
                dir=$(dirname "$file")
                base=$(basename "$file" .py)
                if [ ! -f "$dir/test_${base}.py" ] && [ ! -f "$dir/${base}_test.py" ] && [ ! -f "$dir/tests/test_${base}.py" ]; then
                    echo "[GATE] NOTE: No test file found for $file"
                fi
                ;;
            *.go)
                # Go - check for *_test.go
                base="${file%.go}"
                if [ ! -f "${base}_test.go" ]; then
                    echo "[GATE] NOTE: No test file found for $file"
                fi
                ;;
            *.rs)
                # Rust - tests are usually in the same file or tests/ directory
                # Just note, don't warn specifically
                ;;
        esac
    fi
done

echo "[GATE] Pre-commit checks complete"
