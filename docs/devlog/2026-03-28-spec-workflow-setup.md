# 2026-03-28: Spec Workflow Setup

## What was done

- Added an always-on spec rule: `.cursor/rules/specs.mdc`
- Added a dedicated spec-writing skill: `.cursor/skills/spec-authoring/SKILL.md`
- Created `docs/specs/README.md` with naming convention and template guidance
- Wired this into the existing docs workflow so specs can be linked with ADR/devlog/changelog entries

## Key decisions made

- Use a **rule + skill** combo:
  - Rule enforces when specs are required
  - Skill improves the quality and consistency of spec content
- Keep specs lightweight and implementation-oriented instead of long-form design docs

## Issues / Gotchas

- None during setup

## Next steps

- Write the first feature spec in `docs/specs/` before starting Phase 2 router/specialized agents work
