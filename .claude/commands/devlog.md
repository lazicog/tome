Create a new development log entry for this session.

Steps:
1. Read `docs/devlog/` to see existing entries and confirm the naming format (`YYYY-MM-DD-short-title.md`)
2. Read one recent devlog entry to understand the template structure
3. Determine today's date and a short slug for this session (e.g. `position-aware-retrieval`, `notes-bugfix`, `claude-config`)
4. Create a new file at `docs/devlog/YYYY-MM-DD-<slug>.md` with:

```markdown
# <Title of what was built/fixed>

**Date:** YYYY-MM-DD
**Session focus:** <one sentence>

## What was done

<bullet points of everything implemented or fixed this session>

## Key decisions made

<bullet points of significant technical or design decisions and why>

## Issues / Gotchas

<any problems encountered, workarounds used, or things to watch out for>

## Next steps

<what logically follows from this session's work>
```

5. Fill in all sections from the current conversation context — be specific, include file names, function names, and the reasoning behind decisions.
6. Show the draft and ask for confirmation before writing.
