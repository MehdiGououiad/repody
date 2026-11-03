# ADR 008: Flat run pipeline (supersedes 006 and 007)

**Status:** Accepted
**Date:** 2026-11-03
**Context:** [CONTEXT.md](../../CONTEXT.md)

## Context

One audit run passed through about six layers: `processor` → `agents/idp/run` → ports →
`compose_idp` → `adapters/*` → mappers, with a domain `RunEntity`, in-process domain events,
`Result[T]` return values, a transactional dispatch outbox with replay and purge, and Postgres
advisory locks on top of Taskiq's own delivery guarantees. The same concepts were modelled four
or five times (ORM row → snapshot dataclass → IDP contract → extraction type → API schema).

The indirection hid real bugs: an extractor called through `Callable[..., Awaitable]` received
a removed keyword argument, the `TypeError` was swallowed as a "soft" document failure, and runs
completed as `passed` with every rule skipped.

## Decision

- **State transitions are single conditional UPDATEs** in `app/run/state.py`:
  `claim_run` (queued → running), `complete_run` (running → done), `fail_run`
  (non-terminal → failed). The database enforces the state machine; no advisory locks.
- **One worker module**, `app/run/worker.py`: claim → extract each document through
  `extraction.pipeline.extract_document` (typed, direct call) → evaluate rules → persist →
  complete, with progress published over SSE. A per-document extraction error is logged and
  that document is skipped; any other error fails the run.
- **No outbox table.** The API commits the run, then sends the Taskiq task and stamps
  `runs.dispatched_at`. Maintenance re-sends queued runs whose `dispatched_at` is still NULL.
  After a successful send, delivery is Taskiq's job (RedisStreamBroker acks and redelivery);
  duplicates are harmless because the claim is conditional.
- **Exceptions, not `Result[T]`.** Services raise `AppError` (an `Exception`); one FastAPI
  exception handler maps it to the HTTP status, `detail` and `Retry-After`.

## Consequences

- `agents/idp/`, `app/run/{processor,commands,lifecycle,persistence,dispatch_outbox}.py`
  and the `run_dispatch_outbox` table are gone (migration `h2i3j4k5l6m7`).
- Tests target behaviour (claim once, fail rules, re-dispatch, an end-to-end worker run
  through mocked NuExtract) instead of ports and entities.
- The HTTP contract (`/v1/workflows/{id}/runs`, `/v1/runs/{id}`, `/status`, `/events`) is
  unchanged.
