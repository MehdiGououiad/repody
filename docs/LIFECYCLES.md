# Lifecycles

Every status in Repody is a small state machine with one owner. This page lists them, their
transitions, and the code allowed to change each one. Decision: [ADR 010](./adr/010-explicit-lifecycles.md).

**Rule of thumb:** a status changes only through the code named under "Owner". The backend owns
the persisted states, enforces them with a transition table and Postgres CHECK constraints, and
publishes them as enums in the OpenAPI schema (`lib/api/generated/schema.d.ts`). The frontend
holds each async flow as one discriminated union, so a contradictory state cannot be built.

| State machine | States | Owner | Enforced by |
|---|---|---|---|
| [Run](#run) | queued · running · done · failed | `backend/src/repody/app/lifecycle.py` (`move_run`) | `RUN_TRANSITIONS`, `ck_runs_status`, `ck_runs_outcome` |
| [Workflow](#workflow) | draft · active · archived | `backend/src/repody/app/workflows.py` (`deploy_workflow`, `archive_workflows`) | `ck_workflows_status`; not writable by clients |
| [Rule result](#rule-result) | passed · failed · skipped | `backend/src/repody/rules/evaluate.py` | `ck_rule_results_status` |
| [Run progress step](#run-progress-step) | pending · active · done | `backend/src/repody/app/progress.py` (`Tracker`) | `ProgressStep.status` enum |
| [Builder test run](#builder-test-run) | idle · running · done · failed | `components/workflow/builder/test-run-session.ts` (`TestRun`) | TypeScript union |
| [Builder sync](#builder-sync) | idle · saving · deploying | `components/workflow/builder/use-builder-workflow.ts` (`BuilderSync`) | TypeScript union |

## Run

```mermaid
stateDiagram-v2
  [*] --> queued: POST /v1/workflows/{id}/runs
  queued --> running: worker claims the task
  queued --> failed: waited over 1 h (maintenance)
  running --> done: rules checked, report saved
  running --> failed: error, AUDIT_RUN_TIMEOUT_MINUTES, or worker lost (maintenance)
  done --> [*]
  failed --> [*]
```

- `done` and `failed` are final. `outcome` (passed · warning · failed) exists only on a done run;
  an **audit** is a done run, so the audit list filters by outcome, never by run status.
- Each transition is one conditional `UPDATE … WHERE status IN (<allowed sources>)`. When two
  processes race on a run (a duplicate task delivery, maintenance and a slow worker), the loser's
  update matches no row and it backs off: a final state is never overwritten.
- `dispatched_at IS NULL` while queued means the task was never sent; maintenance resends it.
- Clients see it as `RunState.status` (`GET /v1/runs/{id}`) and as SSE events ending with
  `{"terminal": true, "status": "done" | "failed"}` (`lib/api/run.ts` `watchRun`).

## Workflow

```mermaid
stateDiagram-v2
  [*] --> draft: POST /v1/workflows, or first PUT
  draft --> active: POST /deploy (issues an API key)
  active --> active: POST /deploy again (new key, old one stops working)
  draft --> archived: DELETE
  active --> archived: DELETE
  archived --> [*]
```

- The server owns the status. `PUT /v1/workflows/{id}` saves the definition and never changes the
  status (a `status` field in the body is ignored); saving an archived workflow is a 404.
- **Active means deployed**: `status = 'active'` exactly when `deployed_at` is set (CHECK
  constraint). Production API runs need it (`409 Workflow is not deployed` otherwise).
- Archived workflows are hidden from every read (`404`); their runs and audits stay.

## Rule result

Set once per rule when a run finishes (`rules/evaluate.py` `evaluate_rule`):
`failed` when a condition does not hold, `skipped` when a value it needs was not extracted or a
field is unknown, `passed` otherwise. A run's `outcome` follows: any failed `reject` rule → failed,
any other failed rule → warning, else passed.

## Run progress step

The step plan stored on a run (`runs.progress`) and pushed over SSE: queued → extract each
document → check the rules → save the report. `Tracker.start(step)` marks earlier steps done and
that step active; `Tracker.finish()` marks all done. It is display only: the run's status is the
source of truth.

## Builder test run

```mermaid
stateDiagram-v2
  [*] --> idle
  idle --> running: Run test
  running --> done: report received
  running --> failed: start or run error (shows the run id)
  done --> running: Run test
  failed --> running: Run test
```

`TestRun` carries only the data of its phase (`progress` while running, `result` when done,
`error` and `runId` when failed). Progress events reach only a running test (`withProgress`), so a
late event never reopens a finished one. The chosen test files live beside it and survive runs.

## Builder sync

```mermaid
stateDiagram-v2
  [*] --> idle
  idle --> saving: Save draft, or autosave 2.5 s after an edit
  idle --> deploying: Deploy / Redeploy
  saving --> idle
  deploying --> idle
```

One request to the server at a time: Save, Deploy and Redeploy are disabled outside `idle`, and
autosave waits for `idle`. A double click therefore never issues two API keys, and a deploy never
races a save.

## Adding or changing a state

1. Backend: add it to the `Literal` in `schemas/` and, for runs, to `RUN_TRANSITIONS`; change
   it only through the owner above.
2. Write an Alembic migration that moves existing rows and updates the CHECK constraint (and the
   matching `CheckConstraint` in `infra/models.py`).
3. `pnpm codegen:api`, then let `pnpm typecheck` show every `Record<Status, …>` and union that
   needs the new case.
4. Update this page and the tests in `backend/tests/integration/test_lifecycle.py`.
