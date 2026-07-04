import { spawnSync } from "node:child_process";
import { apiGet } from "./api";

const SEED_WORKFLOW_ID = "wf-invoice-audit";

const API_NAMESPACE = process.env.E2E_K8S_NAMESPACE ?? "repody";

function seedViaKubectl(): void {
  const code = `
import asyncio
from audit_workbench.db.base import async_session_factory
from audit_workbench.db.seed import seed_database

async def main() -> None:
    async with async_session_factory() as session:
        await seed_database(session)
        await session.commit()

asyncio.run(main())
`;
  const result = spawnSync(
    "kubectl",
    ["-n", API_NAMESPACE, "exec", "-i", "deploy/repody-api", "--", "python", "-"],
    { input: code, encoding: "utf8", shell: false }
  );
  if (result.status !== 0) {
    throw new Error(
      `[e2e] Database seed failed\n${result.stdout}\n${result.stderr}`.trim()
    );
  }
}

/** Ensure demo workflow + audit exist (k8s local does not seed on boot). */
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
    console.warn("[e2e] Seed workflow missing; set E2E_SKIP_SEED=0 and ensure kubectl access to seed");
    return;
  }

  console.log("[e2e] Seeding demo workflow and audit data");
  seedViaKubectl();
}

export { SEED_WORKFLOW_ID };
