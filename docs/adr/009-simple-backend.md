# ADR 009: One definition, one queue, one upload path

**Status:** accepted (supersedes the pools of ADR 007 and the module layout of ADR 008)

## Context

The backend had grown to ~10k lines: a workflow split over four tables with diff-and-upsert
code, rules passed around as camel/snake dictionaries and compiled to Python text before being
parsed back, two worker pools, presigned uploads with confirmation records, a progress model
updated by four paths, three throttling layers and about 70 settings.

## Decision

- **A workflow is one JSON definition** (`schemas.workflow.WorkflowDefinition`: documents,
  NuExtract schemas, rules), stored on `workflows.definition`. Each run stores its own copy,
  so editing a workflow never changes a queued or finished run.
- **Rules are typed conditions** (`schemas.rule.Condition`) evaluated directly. A rule passes
  when every condition holds; the readable form of each condition is shown in the builder
  and stored on the result. No expression language, no `simpleeval`.
- **Values keep the type the schema declares.** NuExtract returns each field in its
  template type, so extracted values are stored as JSON (NULL when missing) and rules read
  them by that type: no amount or date guessing (`price-parser` removed), no money-specific
  rounding. Saving a workflow rejects operators that do not fit a field's type.
- **One queue and task**, `process_run(run_id)`, on Hatchet ([ADR 011](./011-hatchet.md)):
  triggered after the commit, bounded by Hatchet's timeouts, claimed with a conditional update.
- **One upload path**: the run request is multipart (files, and for each file its workflow
  document); the API checks the bytes' type and stores the files in S3.
- **Progress** is a Pydantic model stored on the run, which clients poll (runs take minutes;
  a 1 s poll is enough and works through every proxy).
- **Limits**: one queue cap, and Hatchet's per-client rate limit, round robin and run timeout.
- **One Alembic migration** for the new schema (local databases are recreated).

## Consequences

- The backend is ~3k lines; the API has 14 routes. The frontend types come from the OpenAPI
  schema instead of hand-written copies.
- Large files travel through the API instead of straight to S3; the upload cap
  (`AUDIT_MAX_UPLOAD_BYTES`, default 25 MiB) bounds this.
- A rule that needs "any of" must be written as separate rules.
- A total compared as a number must be declared `number`; a `verbatim-string` field compares as text.
- Rule templates, the dry-run endpoint and serverless GPU hints were removed.
