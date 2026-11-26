# Repody - architecture context

Single-page map for tech leads and new contributors. How-tos: [docs/README.md](./docs/README.md). Decisions: [docs/adr/](./docs/adr/).

## Names (read once)

| Name               | Where                                             | Meaning                                         |
| ------------------ | ------------------------------------------------- | ----------------------------------------------- |
| **Repody**         | Product, repo, npm package, Helm release          | Public name everywhere                          |
| **repody**         | Python package (`backend/src/repody/`, dist name) | Import path + `pip install -e backend`          |
| **`AUDIT_*`**      | Env vars                                          | Settings prefix (kept for stable ops config)    |
| **Next.js `app/`** | Repo root `app/`                                  | App Router routes (thin pages) - not Python     |
| **`repody.app`**   | `backend/src/repody/app/`                         | Python application use cases (Workflow, Run, …) |

Document extraction: NuExtract3 on an OpenAI-compatible server: vLLM on Modal for the hosted demo,
llama-server on a laptop ([docs/EXTRACTION.md](./docs/EXTRACTION.md)).

## Domain glossary

| Term               | Meaning                                                                                                                        |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| **Workflow**       | Configured audit template: documents, field schema, validation rules                                                           |
| **Run**            | One execution of a workflow against uploaded files (test or production)                                                        |
| **Document model** | NuExtract3 on an OpenAI-compatible server: vLLM on Modal, or a local llama-server ([docs/EXTRACTION.md](./docs/EXTRACTION.md)) |
| **Logic rule**     | Typed conditions on extracted fields (`rules/`); passed, failed or skipped                                                     |
| **Audit**          | A done run: its report, with an outcome of passed, warning or failed                                                           |
| **Lifecycle**      | The states of a run, workflow or builder flow, and their one owner: [docs/LIFECYCLES.md](./docs/LIFECYCLES.md)                 |

## Request lifecycle

```mermaid
sequenceDiagram
  participant UI as Next.js UI
  participant API as FastAPI /v1
  participant Store as S3 storage
  participant Q as Hatchet
  participant W as Worker
  participant Inf as External VLM
  participant DB as Postgres

  UI->>API: POST /workflows/{id}/runs (multipart files)
  API->>Store: put files
  API->>Q: trigger process-run (run id)
  Q->>W: assign the task (rate limit, round robin per client)
  W->>Store: fetch PDF/image
  W->>Inf: document-model chat completion
  Inf-->>W: structured JSON fields
  W->>W: check rules
  W->>DB: save the report (Run, RuleResults)
  UI->>API: GET /runs/{id} (poll until done)
```

## Backend layers

```
backend/src/repody/
├── main.py · worker.py  FastAPI app; Hatchet worker (process-run workflow, maintenance cron)
├── api/               HTTP routes (workflows, runs, platform, credits, admin, access requests)
│                      and caller dependencies (deps.py)
├── app/               Use cases: workflows, runs, execute (worker), progress, lifecycle (the only
│                      code that changes a run's status), credits, admin, access, dashboard,
│                      operations, scope (who sees what), maintenance, seed
├── extraction/        NuExtract requests, page rendering, model client, field values
├── rules/             Typed conditions and their evaluation (no database, no settings)
├── schemas/           Pydantic models: the API, and the stored workflow definition
├── infra/             auth (Keycloak JWT, roles, API keys), queue (Hatchet client), models, db,
│                      storage (S3), keycloak_admin, turnstile, observability (logs, errors)
└── settings.py        Every AUDIT_* setting, in one place
```

Dependencies point one way: entry points → `api` → `app` → `extraction` / `rules` → `infra` →
`schemas` → `settings`.
`app`, `extraction`, `rules`, `schemas` and `infra` never import FastAPI. import-linter checks both
(`backend/pyproject.toml`, `bun run architecture:check`). The API and the worker are the same image
with two commands, so they already deploy and scale apart; the model is an HTTP endpoint and
storage is S3.

**Hot path:** `app/execute.py` `process_run`: claim (conditional UPDATE) -> extract each document -> check rules -> save the report ([ADR 009](./docs/adr/009-simple-backend.md)).

### Bounded contexts

| Context                    | Responsibility                                       | Key modules                                                    |
| -------------------------- | ---------------------------------------------------- | -------------------------------------------------------------- |
| **Workflow configuration** | Definition (documents + rules), deployment, API keys | `app/workflows.py`, `schemas/workflow.py`                      |
| **Run execution**          | Start, queue, process, progress, upkeep              | `app/runs.py`, `app/execute.py`, `app/progress.py`, `queue.py` |
| **Rules**                  | Typed conditions and their evaluation                | `rules/`                                                       |
| **Clients and credits**    | Client companies, users, credits, access requests    | `app/admin.py`, `app/credits.py`, `app/access.py`              |

### Run pipeline

One Hatchet workflow, `process-run`, with one task (`process_run`). The API triggers it after the commit and keeps the Hatchet run id (`runs.task_run_id`, to cancel it); when Hatchet cannot take it, the run fails at once and the API answers 503. Hatchet enforces the timeouts (an hour to reach a worker, `AUDIT_RUN_TIMEOUT_MINUTES` to finish), the per-client rate limit and round robin, and calls the workflow's failure task when it gives up (a timeout, a lost worker), which fails the run. A Hatchet cron runs maintenance every minute: it fails the runs the queue lost, and deletes runs past their retention and declined access requests past theirs. [ADR 011](./docs/adr/011-hatchet.md). Every status change is a conditional UPDATE through `app/lifecycle.py`, so a duplicate delivery does nothing and a final run is never overwritten ([LIFECYCLES.md](./docs/LIFECYCLES.md)). Each run keeps its own copy of the workflow definition. Decision: [ADR 009](./docs/adr/009-simple-backend.md).

## Extraction

`extraction/pipeline.py` `extract` is the one entry point: it renders the pages
(`extraction/render.py`, at least 3 MP each), sends one request per document to the model
(`extraction/client.py`, the openai SDK) and turns the answer into one value per field
(`extraction/fields.py`). With `AUDIT_SECOND_READ` (default `all`), a document with fields is
read a second time at half the pixels; a field the two reads disagree on is flagged and the run
needs review. Details: [docs/EXTRACTION.md](./docs/EXTRACTION.md).

| Concern             | Configuration                                                                  |
| ------------------- | ------------------------------------------------------------------------------ |
| Document extraction | `AUDIT_INFERENCE_BASE_URL`, `AUDIT_INFERENCE_MODEL`, `AUDIT_INFERENCE_API_KEY` |
| Second read         | `AUDIT_SECOND_READ` (`all`, `images` or `off`)                                 |

## Frontend layout

Next.js 16 App Router at repo root:

- `app/` - thin pages
- `components/` - domain UI
- `lib/api/` - typed clients; RSC `serverFetch`, client islands via `/api/*` -> backend `/v1/*`

## Deploy modules

| Module     | Kubernetes shape                  | Purpose                                                                      |
| ---------- | --------------------------------- | ---------------------------------------------------------------------------- |
| control    | `repody-api`                      | Workflows, runs, uploads                                                     |
| worker     | `repody-worker`                   | Hatchet worker: runs and the maintenance cron (scale by replicas)            |
| edge       | `repody-web`                      | Next.js UI                                                                   |
| data plane | Postgres, Hatchet, object storage | Durable state; Hatchet queues the runs (Hatchet Lite on Postgres in Compose) |
| auth       | External OIDC                     | Authentication                                                               |
| inference  | External OpenAI-compatible        | Not in the Repody chart                                                      |

Daily local: Compose ([docs/LOCAL.md](./docs/LOCAL.md)). The hosted demo (app.repody.com) and its staging: one VPS with Compose, the model on Modal ([deploy/vps/README.md](./deploy/vps/README.md), [ADR 012](./docs/adr/012-hosted-demo-on-a-vps.md)). Client installations: Helm ([docs/CLUSTER.md](./docs/CLUSTER.md)). Packaging: [ADR 004](./docs/adr/004-cloud-kubernetes-packaging.md) · [ADR 005](./docs/adr/005-kubernetes-only-external-inference.md).

| Lane                           | Command                                                                                           |
| ------------------------------ | ------------------------------------------------------------------------------------------------- |
| Run the product locally        | `bun run platform`                                                                                |
| Develop from source            | `bun run platform dev`                                                                            |
| Release the hosted demo        | Merge (staging), then `git tag v1.2.3` ([deploy/vps/README.md](./deploy/vps/README.md#releasing)) |
| Client Kubernetes installation | [docs/CLUSTER.md](./docs/CLUSTER.md)                                                              |
| Release to client              | `bun run images:release`                                                                          |

## Authorization

Keycloak realm roles -> `infra/auth.py` (`ROLE_PERMISSIONS`). Routes declare `require("workflow:write")` and similar. When `AUDIT_OIDC_ENABLED=false`, API uses a `platform_admin` dev principal. A platform admin manages client companies and their users in the app's Admin area; the Keycloak admin console is for everything else.

| Role             | Typical access                                                      |
| ---------------- | ------------------------------------------------------------------- |
| `viewer`         | Read workflows, runs and audits                                     |
| `operator`       | Viewer + write workflows, start runs, dashboard and platform config |
| `admin`          | Operator + delete workflows                                         |
| `platform_admin` | Admin + grant credits; sees every client                            |

Roles say what a user may do; their **account** says on what (`app/scope.py`). A Keycloak group `client-<name>` makes the user's client company their account: they see and change only its workflows and runs, and shared workflows (no account) read-only. Users outside any client group see everything. **Credits** (`app/credits.py`, `credit_entries`): every run is metered by pages sent to the model and, with `AUDIT_CREDITS_ENFORCED`, refused (402) when its account cannot pay. Setup and sizing: [deploy/ENV.md](deploy/ENV.md#credits). **Admin area** (`app/admin.py`, `/admin`): platform admins manage clients, users and credits in Keycloak through the `repody-admin` service account (`infra/keycloak_admin.py`); every change goes to the `admin_events` audit log. Setup: [deploy/ENV.md](deploy/ENV.md#admin-area).

## Tests

| Layer                                  | Command                           |
| -------------------------------------- | --------------------------------- |
| Backend unit/integration               | `bun run test:api`                |
| Live stack                             | `bun run test:live` (needs stack) |
| Playwright smoke (sign-in, navigation) | `bun run test:e2e:smoke`          |

Full command list: [docs/COMMANDS.md](./docs/COMMANDS.md). Engineering notes: [docs/DEVELOPMENT.md](./docs/DEVELOPMENT.md).

## Further reading

- [docs/README.md](./docs/README.md) - docs hub
- [docs/EXTRACTION.md](./docs/EXTRACTION.md) - document models
- [docs/LIFECYCLES.md](./docs/LIFECYCLES.md) - every state machine and its owner
- [docs/adr/](./docs/adr/README.md) - ADRs
