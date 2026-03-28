# Frontend Chat Regression Checklist

Use this checklist after changes to chat streaming, routing labels, or source rendering.

## Preconditions

- Backend running at `http://127.0.0.1:8000`
- Frontend running at `http://127.0.0.1:3000`
- At least one `ready` book exists

## Core Stream Checks

- [ ] Send a normal prompt and confirm incremental token rendering.
- [ ] Confirm assistant label matches routed intent (`Tutor`, `Example Agent`, `Context Enricher`).
- [ ] Confirm a `Sources` section appears after response completion.
- [ ] Confirm loading button returns from `Thinking...` to `Send`.

## Source Interaction Checks

- [ ] Click `Page N` filter and confirm only matching source cards remain.
- [ ] Pick a page with no matches and confirm no-results helper message is shown.
- [ ] Click `All pages` and confirm full source list returns.
- [ ] Click `Copy citation` and confirm copy feedback text appears.

## Failure-Path Checks

- [ ] Stop backend and send a message; confirm friendly error and no stuck loading state.
- [ ] Restart backend and confirm chat recovers without page reload.

## Notes Template

```markdown
## Frontend Chat QA Run
- Date:
- Branch/commit:
- Book used:
- Passed checks:
- Failed checks:
- Follow-ups:
```
