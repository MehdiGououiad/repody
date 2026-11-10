import { spawnSync } from "node:child_process";
import { apiGet } from "./api";
import { API_URL } from "./env";

const SEED_WORKFLOW_ID = "wf-invoice-audit";

const API_NAMESPACE = process.env.E2E_K8S_NAMESPACE ?? "repody";

const SEED_CODE = `
import asyncio
from repody.app.seed import seed
from repody.infra.db import session_factory

async def main() -> None:
    async with session_factory() as session:
        await seed(session)
        await session.commit()

asyncio.run(main())
`;

/** `compose` for the local platform (`pnpm platform`), `kubectl` for a cluster. */
function seedTarget(): "compose" | "kubectl" {
  const explicit = process.env.E2E_SEED_VIA;
  if (explicit === "compose" || explicit === "kubectl") return explicit;
  const host = new URL(API_URL).hostname;
  return host === "localhost" || host === "127.0.0.1" ? "compose" : "kubectl";
}

function seedInApiContainer(): void {
  const via = seedTarget();
  const [cmd, args] =
    via === "compose"
      ? ["docker", ["compose", "-p", "repody", "exec", "-T", "api", "python", "-"]]
      : ["kubectl", ["-n", API_NAMESPACE, "exec", "-i", "deploy/repody-api", "--", "python", "-"]];
  const result = spawnSync(cmd, args, { input: SEED_CODE, encoding: "utf8", shell: false });
  if (result.status !== 0) {
    throw new Error(
      `[e2e] Database seed (${via}) failed\n${result.stdout}\n${result.stderr}`.trim()
    );
  }
}

/** Ensure demo workflow + audit exist (neither the platform nor a cluster seeds on boot by default). */
export async function ensureSeedData(): Promise<void> {
  try {
    const { workflows } = await apiGet<{ workflows: { id: string }[] }>("/workflows");
    if (workflows.some((workflow) => workflow.id === SEED_WORKFLOW_ID)) {
      return;
    }
  } catch {
    /* fall through to seed attempt */
  }

  if (process.env.E2E_SKIP_SEED === "1") {
    console.warn("[e2e] Seed workflow missing; unset E2E_SKIP_SEED to seed via compose or kubectl");
    return;
  }

  console.log(`[e2e] Seeding demo workflow and audit data (${seedTarget()})`);
  seedInApiContainer();
}

export { SEED_WORKFLOW_ID };
