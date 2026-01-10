---
description: Verify no hacks, placeholders, silent failures, or code that looks like it works but doesn't
argument-hint: [file-path]
allowed-tools: Bash(grep:*), Bash(rg:*), Read, Glob, Grep
---

# No Cap - Rigorous Code Quality Check

Perform a thorough verification to ensure code is production-ready with NO shortcuts, hacks, or misrepresentations.

## What to Check

Search for and report ALL instances of:

1. **Placeholders & Incomplete Code**
   - TODO, FIXME, HACK, XXX comments
   - Placeholder strings like "TODO:", "Not implemented", "Coming soon"
   - Empty function bodies or stub implementations
   - Commented-out code blocks

2. **Silent Failures & Poor Error Handling**
   - Catch-all exception handlers that swallow errors (bare `except:`, `catch (e) {}`)
   - Empty error handlers
   - Silent returns without proper error propagation
   - Missing null/undefined checks
   - Unchecked return values from functions that can fail

3. **Debugging Code Left Behind**
   - print(), console.log(), debugger statements
   - Debug logging at inappropriate levels
   - Temporary test code

4. **Logical Issues**
   - Edge cases not handled (empty arrays, null values, boundary conditions)
   - Off-by-one errors in loops
   - Race conditions or async issues
   - Type safety violations

5. **Misrepresentations**
   - Functions claiming to do X but only partially implementing it
   - Comments that don't match actual behavior
   - Code marked "complete" but containing TODOs
   - Overly-simplified implementations hiding complexity

## Instructions

1. If `$ARGUMENTS` provided, scan those specific files/directories
2. Otherwise, check recently modified files from git status/diff
3. Search for the patterns listed above using grep/rg/read
4. For each issue found, report:
   - File path and line number
   - Severity: CRITICAL, HIGH, MEDIUM, LOW
   - Specific issue description
   - Recommendation for fix

5. Provide final verdict:
   - ✅ **PASS**: No issues found, code is ship-ready
   - ⚠️  **WARNING**: Minor issues found, review recommended
   - ❌ **FAIL**: Critical issues found, DO NOT SHIP

## Usage Examples

```
/no-cap                          # Check recent changes
/no-cap rikaios/core/           # Check specific directory
/no-cap src/utils/helpers.ts    # Check specific file
```

## What Passes

- Proper error handling with explicit propagation
- All edge cases handled explicitly
- No TODOs/FIXMEs in code (tracked in issues instead)
- Logic handles null, empty, and error states
- Comments match implementation
- No debug code left behind
- Type safety and validation throughout
