---
name: multi-agent-coordinator
description: Plans and coordinates parallel Cursor agents across isolated git worktrees, including role assignment, branch naming, dependency order, and handoff protocol. Use when running multiple agents on different features.
---

# Multi-Agent Coordinator

Create a safe parallel execution plan before coding begins.

## Coordination Plan

1. Split work into parallel-safe slices.
2. Assign one branch/worktree per slice.
3. Identify dependencies and merge order.
4. Assign reviewer and integration roles.
5. Define handoff artifacts required from each agent.

## Recommended Role Map

- `feature-builder-*`: implement scoped feature
- `pr-review-guardian`: review findings by severity
- `worktree-integration-manager`: merge and verify

## Plan Template

```markdown
## Parallel Plan
- Feature slices:
- Branch/worktree map:
- Dependencies:
- Reviewer assignment:
- Integration order:
- Acceptance gates:
```

## Safety Rules

- No shared file ownership without explicit coordination.
- Shared contract changes require explicit callout and dedicated tests.
- Keep each branch small enough for fast review and rollback.
