---
name: worktree-integration-manager
description: Integrates multiple feature branches from separate worktrees by ordering merges safely, running verification gates, and keeping docs/handoff current. Use when coordinating multi-branch integration.
---

# Worktree Integration Manager

Merge safely across parallel feature branches.

## Integration Steps

1. Build merge queue:
   - low-risk, isolated branches first
   - shared-contract branches later with extra checks
2. For each branch:
   - ensure reviewer verdict is clear
   - rebase/sync with latest `master`
   - run verification gates
   - merge
3. After each merge:
   - run smoke checks for backend and frontend
   - confirm no contract regressions

## Verification Gates

- Backend tests for changed area (plus contract tests for API/SSE changes)
- Frontend type/build checks when UI is touched
- Any feature-specific checks defined in spec or PR

## Required Integration Log

```markdown
## Integration Log
- Merge order:
- Gate results per branch:
- Conflicts resolved:
- Post-merge smoke status:
- Follow-up actions:
```
