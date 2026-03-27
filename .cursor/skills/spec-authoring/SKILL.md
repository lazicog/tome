---
name: spec-authoring
description: Write high-quality implementation specs for Tome using a consistent template and decision-oriented workflow. Use when planning features, refactors, API/data changes, or any non-trivial implementation before coding.
---

# Spec Authoring

Create specs in `docs/specs/` before non-trivial implementation.

## Output Path

- `docs/specs/YYYY-MM-DD-short-title.md`

## Workflow

1. Clarify problem and desired outcome.
2. Define scope boundaries and non-goals.
3. Design solution at the right depth (interfaces, data flow, key modules).
4. Identify risks/trade-offs and mitigations.
5. Define a concrete test plan and rollout sequence.
6. Add implementation checklist.

## Spec Template

```markdown
# <Title>

## Problem
<What is broken/missing and why it matters>

## Scope
- In scope:
- Out of scope:

## Goals
- <measurable objective>

## Non-goals
- <explicitly excluded work>

## Proposed Design
<High-level approach, key modules, and request/data flow>

## API and Data Changes
- Endpoints:
- Request/response changes:
- Storage/model changes:

## Risks and Mitigations
- Risk:
  - Mitigation:

## Test Plan
- Unit:
- Integration:
- Manual checks:

## Rollout Plan
1. <step>
2. <step>

## Implementation Checklist
- [ ] <task>
- [ ] <task>
```

## Quality Checklist

- Problem and scope are unambiguous.
- Non-goals prevent scope creep.
- API/data impacts are explicitly listed.
- Test plan can actually validate success.
- Checklist items are concrete and implementable.

## Notes For Tome

- Prefer practical, incremental specs over heavy design docs.
- If architecture decisions change, create/update ADRs in `docs/adr/`.
- After completion, reflect outcome in `docs/devlog/` and `CHANGELOG.md` when user-facing.
