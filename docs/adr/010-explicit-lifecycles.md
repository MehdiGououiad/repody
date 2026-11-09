# ADR 010: Explicit lifecycles

**Status:** accepted

## Context

Statuses were implicit state machines spread over the code:

- A run's status was changed by three hand-written UPDATEs (claim, fail, finish); the finish was
  unconditional, so a worker finishing late could overwrite a run maintenance had failed.
- A workflow's status was whatever the client sent on save. The builder derived `active` from a
  local flag, the API accepted `paused` though nothing produced it, and a client could mark a
  workflow active without deploying it (no API key) or revive an archived one by saving it.
- In the UI, a builder test run was five independent fields (`phase`, `progress`, `result`,
  `error`, `errorRunId`). A failure was stored as `idle` beside the previous result, so after a
  failed retest the results panel was blank while the step nav still said "has results". Deploy
  had no in-flight state: a double click issued two API keys. Status helpers accepted any string
  and handled states that never occur (`error` rules, `running` audits, `paused` workflows).

## Decision

- **One owner per lifecycle.** Run transitions go through `app/lifecycle.py` `move_run`, checked
  against `RUN_TRANSITIONS`, each one a conditional UPDATE: a final state is never overwritten.
  Workflow status is server-owned: deploy activates, delete archives, save never changes it.
- **The database enforces the invariants** with CHECK constraints (migration 0003): valid
  statuses, outcome only on done runs, active exactly when deployed.
- **Statuses are enums end to end**: `Literal` types in the schemas and ORM columns, OpenAPI
  enums, generated TypeScript unions, `Record<Status, …>` maps in the UI so a new state is a
  type error until every view handles it.
- **Async UI flows are discriminated unions** holding only their phase's data (`TestRun`), or a
  single in-flight state (`BuilderSync`). States nothing produces are removed.
- **One page documents them all**: [LIFECYCLES.md](../LIFECYCLES.md), linked from CONTEXT.md and
  CLAUDE.md for people and coding agents.

## Consequences

- A status bug becomes a type error, a failed CHECK, or a no-op conditional UPDATE instead of a
  silent inconsistent row.
- `PUT /v1/workflows/{id}` ignores a `status` field; workflows saved as `paused` became active
  (deployed) or draft.
- Adding a state means a migration, a codegen and a type-check pass: the checklist is in
  LIFECYCLES.md.
