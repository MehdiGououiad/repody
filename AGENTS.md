<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

## Docs

**Hub:** [docs/README.md](./docs/README.md) · **Commands:** [docs/COMMANDS.md](./docs/COMMANDS.md)

Bun is the package manager (`package.json` pins `bun@1.4.4`). Daily: `bun run platform` · once: `bun run platform setup` · stop: `bun run platform stop` · contributors (API and UI reloading on the host): `bun run platform dev` · before pushing: `bun run verify`

Guides: [docs/LOCAL.md](./docs/LOCAL.md) · [docs/CLUSTER.md](./docs/CLUSTER.md) · architecture: [CONTEXT.md](./CONTEXT.md)

## Logs

Do **not** write logs to workspace files.

Production and staging run on one VPS with Docker Compose ([deploy/vps/README.md](./deploy/vps/README.md)): production in `/opt/repody`, staging in `/home/deploy/repody-staging`. Read their logs over Tailscale, never their `.env` (do not run `docker compose config` there, it prints it):

```powershell
tailscale ssh deploy@repody-vps "docker logs --since 30m repody-api-1"
tailscale ssh deploy@repody-vps "docker logs --since 30m repody-staging-worker-1"
```

Grafana (Loki) and Bugsink on the server hold older logs and the errors ([deploy/vps/README.md](./deploy/vps/README.md#logs)).

A client's Kubernetes installation (Helm, a reference, [docs/CLUSTER.md](./docs/CLUSTER.md)):

```powershell
kubectl -n repody logs -f deploy/repody-api
```

## Hard rules

These hold for every agent working on Repody (Claude, Antigravity, others). When one of them
blocks the task, stop and ask the owner.

**Secrets**

- Never print a secret. They live in `.env` files on the server (mode 600) and in GitHub and Modal
  secrets. Do not `cat` an `.env`, and do not run `docker compose config` on the server: it prints
  every variable. To pass one to a command, read it into the environment
  (`export X=$(grep '^X=' .env | cut -d= -f2-)`) and never echo it.
- Never put a token or password in the repository, a commit, a PR, a doc or a log line.

**Production and staging**

- Server access: `tailscale ssh deploy@repody-vps`. Production is in `/opt/repody`, staging in
  `/home/deploy/repody-staging`.
- Production: never sign in with a password. Read it only through logs (`docker logs`), the health
  check (`https://app.repody.com/api/v1/healthz`) and the release checks (the smoke test).
- Staging (staging.repody.com) may be used with the UI tester account `tester@staging.repody.com`.
  Its password is `UI_TESTER_PASSWORD` in staging's `.env`: never print it.
- Ask the owner before any destructive production action (deleting data, restarting databases,
  restoring backups, changing `.env`).

**Shipping**

- Small PRs, one theme each. Merge only when CI is green (lint, typecheck, tests, OpenAPI drift,
  Trivy, SonarCloud). Commit only your own files.
- A merge to `master` deploys staging and runs a real smoke test (deploy.yml). A release is a tag
  `vX.Y.Z` on a master commit staging already ran: `release.yml` promotes the same signed images to
  production. Ask the owner before tagging. After a release, confirm the health check, the deploy's
  smoke test, and no errors in the API, worker and web logs. Details:
  [deploy/vps/README.md](./deploy/vps/README.md#releasing).
- Do not poll CI in loops: one `gh run watch` or `gh pr checks --watch`, in the background.
- The repository must stay public: on GitHub's Free plan, a private repository gets 2,000 Actions
  minutes a month (CI uses more) and ignores the environments' secrets, so deploys stop.

**The model (Modal)**

- Do not deploy the Modal app (`deploy/modal`) without asking the owner. Then deploy through
  Actions → Deploy model: staging first, check it with a smoke run, then `main` (production). The
  workflow pre-warms after deploying; that pre-warm also sets staging's 2-minute idle time.
- GPU time costs credits (`modal billing report`): avoid needless model starts, and say what a step
  will cost before spending more than a few starts.

**On a developer's machine**

- To run the stack from a second checkout or a worktree, set its own `COMPOSE_PROJECT_NAME` (for
  example `repody-test`). The default name `repody` would recreate the main checkout's containers
  with this checkout's env files.
- After editing `messages/en.json`, type-check with `bunx tsc --noEmit --incremental false`: the
  incremental build can miss a removed key.

## UI components (ui-sdk)

Before using ui-sdk, follow the ui-sdk skill ([`.claude/skills/ui-sdk`](./.claude/skills/ui-sdk/SKILL.md))
and read `node_modules/@ui-sdk/react/docs/llms.txt`. To build a new component, also search
`node_modules/@ui-sdk/react/docs/core.md` by heading, and read `rendering.md` next to it.

## Hatchet docs

When implementing against Hatchet, fetch the relevant page below; each URL serves plain markdown. The full index is at https://docs.hatchet.run/llms.txt

**Setup & local dev**

- Quickstart: https://docs.hatchet.run/v1/quickstart.md
- Running Hatchet locally (all options): https://docs.hatchet.run/v1/running-locally.md
- Embedded mode (local engine, no token or Docker): https://docs.hatchet.run/v1/embedded.md
- CLI overview: https://docs.hatchet.run/reference/cli.md
- CLI profiles & tokens: https://docs.hatchet.run/reference/cli/profiles.md
- Run workers locally: https://docs.hatchet.run/reference/cli/running-workers-locally.md
- Full local stack (server + dashboard): https://docs.hatchet.run/reference/cli/running-hatchet-locally.md

**Defining tasks & workflows**

- Tasks: https://docs.hatchet.run/v1/tasks.md
- Workers: https://docs.hatchet.run/v1/workers.md
- DAG workflows: https://docs.hatchet.run/v1/directed-acyclic-graphs.md
- Child spawning: https://docs.hatchet.run/v1/child-spawning.md
- Batch tasks: https://docs.hatchet.run/v1/batch-tasks.md
- Streaming from tasks: https://docs.hatchet.run/v1/streaming.md
- Logging: https://docs.hatchet.run/v1/logging.md

**Triggering & scheduling**

- Run a task from code: https://docs.hatchet.run/v1/running-your-task.md
- Event triggers: https://docs.hatchet.run/v1/events.md
- Cron runs: https://docs.hatchet.run/v1/cron-runs.md
- Scheduled runs: https://docs.hatchet.run/v1/scheduled-runs.md
- Bulk runs: https://docs.hatchet.run/v1/bulk-run.md
- Inbound webhooks: https://docs.hatchet.run/v1/webhooks.md
- Trigger from the CLI: https://docs.hatchet.run/reference/cli/triggering-workflows.md

**Flow control & reliability**

- Concurrency: https://docs.hatchet.run/v1/concurrency.md
- Rate limits: https://docs.hatchet.run/v1/rate-limits.md
- Priority: https://docs.hatchet.run/v1/priority.md
- Retry policies: https://docs.hatchet.run/v1/retry-policies.md
- Timeouts: https://docs.hatchet.run/v1/timeouts.md
- Cancellation: https://docs.hatchet.run/v1/cancellation.md
- Idempotency: https://docs.hatchet.run/v1/idempotency.md
- Bulk retries & cancellations: https://docs.hatchet.run/v1/bulk-retries-and-cancellations.md
- Worker assignment (sticky, affinity, slots): https://docs.hatchet.run/v1/advanced-assignment.md

**Durable execution**

- Overview: https://docs.hatchet.run/v1/durable-execution.md
- Durable tasks: https://docs.hatchet.run/v1/durable-tasks.md
- Durable sleep: https://docs.hatchet.run/v1/durable-sleep.md
- Durable event waits: https://docs.hatchet.run/v1/durable-event-waits.md
- Durable tasks vs DAGs: https://docs.hatchet.run/cookbooks/durable-tasks-vs-dags.md

**Reference**

- Python SDK reference: https://docs.hatchet.run/reference/python.md
- TypeScript SDK reference: https://docs.hatchet.run/reference/typescript.md
- Go SDK reference: https://docs.hatchet.run/reference/go.md
- Ruby SDK reference: https://docs.hatchet.run/reference/ruby.md
- Architecture & guarantees: https://docs.hatchet.run/v1/architecture-and-guarantees.md
- Troubleshooting: https://docs.hatchet.run/v1/troubleshooting.md
