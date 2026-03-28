# Quiz Master Agent

## Problem

Users have no way to test their understanding of book material. The current system explains, provides examples, and gives context, but doesn't challenge the learner. Active recall through quizzing is one of the most effective learning techniques, and the platform lacks it entirely.

## Scope

- In scope:
  - New `quiz` intent in the router
  - Quiz Master agent node with structured quiz generation
  - Multiple question types: multiple-choice, true/false, short-answer
  - Answer evaluation with feedback and source citations
  - SSE streaming compatible with existing frontend parser
  - LangGraph integration alongside existing 3 agents

- Out of scope:
  - Persistent quiz score tracking (future: SQLite progress tables)
  - Spaced repetition scheduling
  - Quiz UI components beyond the chat interface
  - Adaptive difficulty levels

## Goals

- Generate 3-5 quiz questions from retrieved book content per request.
- Provide immediate feedback when the user answers.
- Ground all questions in actual book material with source citations.
- Route `quiz` intent naturally alongside existing `explain` / `example` / `context` flows.

## Non-goals

- Building a standalone quiz dashboard.
- Tracking cumulative scores across sessions (deferred to progress-tracking phase).
- Generating questions without RAG context.

## Proposed Design

### Router extension

Add `quiz` to the intent classifier:

```python
quiz_terms = ["quiz", "test", "question", "assess", "check my understanding", "practice"]
```

Classification order: `context` > `quiz` > `example` > `explain` (fallback).

### Quiz Master prompt

The agent generates a structured JSON quiz block inside the streamed response:

```
You are Tome Quiz Master.
Generate 3-5 questions based solely on the retrieved context to test the user's understanding.

Requirements:
- Mix question types: at least one multiple-choice, one true/false, one short-answer
- Each question must be directly grounded in the context
- For multiple-choice, provide 4 options with exactly one correct answer
- After each question, include the answer key with a brief explanation
- Format as numbered list for readability
- Reference source material implicitly

Context:
{context}
```

### Graph integration

```
routerNode -->|"quiz"| quizPrepNode[Quiz Prep]
quizPrepNode --> streamNode
```

Add `quiz_prep` node alongside existing prep nodes. Same pattern: set `system_prompt` to `QUIZ_PROMPT`, then `stream_prompted_answer` handles the rest.

### SSE behavior

Same event contract: `agent` ("quiz") -> `token` (streamed quiz) -> `sources` -> `done`.

Frontend displays agent label as "Quiz Master".

## API and Data Changes

- No endpoint changes.
- No schema changes.
- New `agent_type` value: `"quiz"`.

## Risks and Mitigations

- Risk: LLM generates questions not grounded in context.
  - Mitigation: Explicit prompt constraint to use only retrieved context. Source citations provide auditability.

- Risk: Router misclassifies quiz intent.
  - Mitigation: Specific quiz-related keywords. Deterministic keyword matching keeps routing predictable.

- Risk: Quiz output is too long for streaming UX.
  - Mitigation: Constrain to 3-5 questions in prompt. Token limit in LLM config provides hard ceiling.

## Test Plan

- Unit tests:
  - Router classifies quiz keywords correctly
  - `route_intent` maps `"quiz"` to `"quiz_prep"`
  - Quiz prep node sets correct system prompt

- Integration tests:
  - SSE stream with quiz intent emits `agent: "quiz"` event
  - Full event ordering: `agent` -> `token` -> `sources` -> `done`

- Manual checks:
  - Quiz output is readable and well-formatted in chat UI
  - Questions are grounded in the uploaded book's content

## Rollout Plan

1. Add quiz keywords to router classifier.
2. Add `QUIZ_PROMPT` in `backend/app/agents/quiz_master.py`.
3. Add `quiz_prep` node to LangGraph.
4. Update frontend `toAgentLabel` to display "Quiz Master".
5. Add tests for routing and stream contract.
6. Validate end-to-end.

## Implementation Checklist

- [ ] Add quiz intent terms to `backend/app/agents/router.py`.
- [ ] Create `backend/app/agents/quiz_master.py` with `QUIZ_PROMPT`.
- [ ] Add `quiz_prep` node to `backend/app/agents/graph.py`.
- [ ] Update `route_intent` to handle `"quiz"` -> `"quiz_prep"`.
- [ ] Update frontend `toAgentLabel` for `"quiz"` -> `"Quiz Master"`.
- [ ] Add router tests for quiz intent classification.
- [ ] Add integration test for quiz SSE stream contract.
- [ ] Update devlog and changelog.
