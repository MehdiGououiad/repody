#!/usr/bin/env node
import { spawnSync } from "node:child_process";

const [action = "start", ...args] = process.argv.slice(2);
const VALID_MODELS = new Set(["repody-vlm"]);
const detached = args.includes("--detach");

function modelList() {
  const option = args.find((arg) => arg.startsWith("--models="));
  const raw = option?.slice("--models=".length) ?? "repody-vlm";
  const models = [...new Set(raw.split(",").map((value) => value.trim().toLowerCase()).filter(Boolean))];
  const invalid = models.filter((model) => !VALID_MODELS.has(model));
  if (invalid.length) {
    console.error(`Unknown warmup model(s): ${invalid.join(", ")}`);
    console.error(`Available: ${[...VALID_MODELS].join(", ")}`);
    process.exit(1);
  }
  return models;
}

function run(command, commandArgs, env = process.env) {
  const result = spawnSync(command, commandArgs, {
    stdio: "inherit",
    env,
  });
  if (result.status !== 0) process.exit(result.status ?? 1);
}

if (action === "start" || action === "start:warm") {
  const models = modelList();
  const selected = new Set(models);
  const env = {
    ...process.env,
    AUDIT_WARM_MODELS: models.join(","),
    AUDIT_WARM_REPODY_VLM: String(selected.has("repody-vlm")),
  };

  console.error(
    `Starting Repody VLM production platform. Warmup: ${models.join(", ") || "none"}`,
  );
  if (selected.has("repody-vlm")) {
    run("node", ["scripts/prepare-repody-vlm-model.mjs"], env);
  }
  run("node", ["scripts/docker.mjs", "deploy:selective"], env);
  if (models.length) {
    run("node", ["scripts/wait-for-warmup.mjs"], {
      ...env,
      AUDIT_COMPOSE_STACK: "prod-warmup",
    });
  }
  if (!detached) {
    console.error("\nPlatform ready at http://localhost:3000");
    console.error("Streaming all platform logs. Press Ctrl+C to stop the log stream.");
    console.error("Containers remain running; stop them with: pnpm platform:stop\n");
    run("node", ["scripts/docker.mjs", "logs:selective"], env);
  }
} else if (action === "stop") {
  run("node", ["scripts/docker.mjs", "down:selective"]);
} else {
  console.error(`Unknown container stack action: ${action}`);
  console.error("Available: start, start:warm, stop");
  process.exit(1);
}
