---
name: worktree-feature-builder
description: Implements one scoped feature inside a dedicated git worktree and branch with strict scope control, local verification, and clean handoff notes. Use when building a feature in parallel with other agents.
---

# Worktree Feature Builder

Build exactly one feature in one branch/worktree, then hand off cleanly.

## Workflow

1. Confirm assigned scope:
   - ticket/spec subsection
   - acceptance criteria
   - out-of-scope items
2. Work only in assigned branch/worktree.
3. Make minimal, focused changes for the feature.
4. Run targeted tests for changed areas.
5. Update significant docs (`CHANGELOG`, devlog, session handoff).
6. Prepare a concise handoff summary for reviewer/integration.

## Rules

- Do not mix unrelated refactors in the same branch.
- Preserve existing contracts unless explicitly assigned to change them.
- If shared contracts are changed (API/SSE/schema), call it out explicitly in handoff.
- Never commit secrets, runtime data, or local artifacts.

## Required Handoff Format

```markdown
## Feature Handoff
- Branch:
- Scope completed:
- Files changed:
- Tests run:
- Contract impact: (None | API | SSE | Schema)
- Risks / follow-ups:
```
