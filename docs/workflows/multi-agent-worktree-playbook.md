# Multi-Agent Worktree Playbook

Use this when running multiple Cursor agents in parallel, each on a separate feature branch/worktree.

## Goals

- Keep each agent isolated to one feature.
- Prevent merge conflicts and contract drift.
- Add a dedicated reviewer gate before merge.

## Standard Roles

- Feature Builder A: backend-heavy feature.
- Feature Builder B: frontend-heavy feature.
- Feature Builder C: tests/docs hardening.
- PR Reviewer: bug/risk/test review only.
- Integration Manager: rebases, smoke tests, merge order.

## Branch and Worktree Convention

- Branch names:
  - `feat/<area>-<short-topic>`
  - `fix/<area>-<short-topic>`
  - `test/<area>-<short-topic>`
- Worktree folder names:
  - `.worktrees/<branch-name>`
- One active ticket/spec item per branch.

## Startup Checklist (Per Feature Agent)

1. Confirm target spec section and acceptance criteria.
2. Create/switch to assigned branch/worktree.
3. Implement only files needed for that feature.
4. Run local tests relevant to changed area.
5. Update docs (`CHANGELOG`, `docs/devlog`, handoff) if change is significant.
6. Open a PR with summary + test evidence.

## Reviewer Checklist (PR Reviewer Agent)

- Correctness first:
  - behavioral regressions
  - routing/API contract changes
  - edge cases and error handling
- Test quality:
  - covers happy path and at least one failure path
  - no brittle assertions tied to incidental output
- Scope control:
  - no unrelated refactors
  - no secrets or local data committed
- Return findings ordered by severity:
  - `Critical`, `Medium`, `Low`

## Integration Manager Checklist

1. Pull latest `master`.
2. Rebase feature branches in dependency order.
3. Run full backend + frontend verification.
4. Merge smallest-risk PRs first.
5. Re-run smoke tests after each merge.
6. Update `docs/SESSION-HANDOFF.md` with current state.

## PR Template (Recommended)

```markdown
## Summary
- What changed and why (2-4 bullets)

## Scope
- In scope:
- Out of scope:

## Test Plan
- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual verification steps

## Risks
- Key risks and mitigations
```

## Merge Policy

- Merge only when reviewer reports no unresolved critical findings.
- Keep PRs under ~400 changed lines when possible.
- Prefer sequential merges for features touching shared contracts (SSE/API schemas).
