import { spawnSync } from "node:child_process";
import path from "node:path";
import { requireDockerEngine } from "./k8s-local-process.mjs";

function normalizeImageRef(image) {
  return image
    .replace(/^docker\.io\//, "")
    .replace(/^registry-1\.docker\.io\//, "");
}

export function createLocalRegistryCommands({
  captureNoShell,
  harborAdminPassword = "",
  harborHost = "",
  harborHttpPort = 8080,
  harborProject = "",
  heading,
  kindPlatform,
  localRegistry,
  registryMode = "simple",
  registryName,
  root,
  run,
}) {
  function localRegistryRef(image) {
    return `${localRegistry}/${normalizeImageRef(image)}`;
  }

  function registryApiBase() {
    if (registryMode === "harbor") {
      return `http://${harborHost}:${harborHttpPort}`;
    }
    return `http://${localRegistry}`;
  }

  function manifestRepository(image) {
    const normalized = normalizeImageRef(image);
    const colon = normalized.lastIndexOf(":");
    const name = colon > 0 ? normalized.slice(0, colon) : normalized;
    if (registryMode === "harbor" && harborProject) {
      return `${harborProject}/${name}`;
    }
    return name;
  }

  function manifestTag(image) {
    const normalized = normalizeImageRef(image);
    const colon = normalized.lastIndexOf(":");
    return colon > 0 ? normalized.slice(colon + 1) : "latest";
  }

  function localRegistryHasImage(image) {
    const repository = manifestRepository(image);
    const tag = manifestTag(image);
    try {
      captureNoShell(process.platform === "win32" ? "curl.exe" : "curl", [
        "-fsI",
        "--max-time",
        "3",
        "-H",
        "Accept: application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json, application/vnd.docker.distribution.manifest.list.v2+json",
        `${registryApiBase()}/v2/${repository}/manifests/${tag}`,
      ]);
      return true;
    } catch {
      return false;
    }
  }

  function dockerLoginHarbor() {
    const registry = `${harborHost}:${harborHttpPort}`;
    const login = spawnSync(
      "docker",
      ["login", registry, "-u", "admin", "--password-stdin"],
      {
        input: harborAdminPassword,
        encoding: "utf8",
        shell: process.platform === "win32",
      },
    );
    if (login.status !== 0) {
      console.error(login.stderr || login.stdout || "docker login failed");
      process.exit(login.status ?? 1);
    }
    console.error(`ok: docker logged in to ${registry}`);
  }

  function ensureHarborRegistry() {
    requireDockerEngine();
    heading(`Using Harbor registry (${localRegistry})`);
    try {
      captureNoShell(process.platform === "win32" ? "curl.exe" : "curl", [
        "-fsS",
        "--max-time",
        "5",
        `${registryApiBase()}/api/v2.0/health`,
      ]);
      console.error("ok: Harbor API is healthy");
    } catch {
      console.error(
        `✗ Harbor not reachable at ${registryApiBase()} — run: pnpm harbor:bootstrap`,
      );
      process.exit(1);
    }
    dockerLoginHarbor();
  }

  function ensureSimpleRegistry() {
    requireDockerEngine();
    heading(`Starting local registry (${localRegistry})`);
    const inspect = spawnSync(
      "docker",
      ["inspect", "-f", "{{.State.Running}}", registryName],
      { encoding: "utf8", shell: process.platform === "win32" },
    );
    if (inspect.status === 0) {
      if (inspect.stdout?.trim() === "true") {
        console.error(`ok: ${registryName} already running`);
        return;
      }
      console.error(`… starting stopped ${registryName} (preserving cached images)`);
      run("docker", ["start", registryName]);
      return;
    }
    run("docker", [
      "run",
      "-d",
      "--restart=always",
      "-p",
      `127.0.0.1:5001:5000`,
      "--name",
      registryName,
      "registry:2",
    ]);
  }

  function ensureLocalRegistry() {
    if (registryMode === "harbor") {
      ensureHarborRegistry();
      return;
    }
    ensureSimpleRegistry();
  }

  function connectRegistryToKind() {
    if (registryMode === "harbor") {
      const script = path.join(root, "deploy/scripts/harbor-local.mjs");
      const result = spawnSync("node", [script, "connect-kind"], {
        cwd: root,
        stdio: "inherit",
        shell: false,
      });
      if (result.status !== 0) {
        process.exit(result.status ?? 1);
      }
      return;
    }
    const result = spawnSync(
      "docker",
      ["network", "connect", "kind", registryName],
      { encoding: "utf8", shell: process.platform === "win32" },
    );
    if (result.status === 0) {
      console.error(`ok: ${registryName} attached to kind network`);
      return;
    }
    const stderr = result.stderr ?? "";
    if (stderr.includes("already exists")) {
      console.error(`ok: ${registryName} already on kind network`);
      return;
    }
    if (stderr) console.error(stderr.trim());
  }

  function dockerHasLocalImage(image) {
    const inspect = spawnSync("docker", ["image", "inspect", image], {
      stdio: "ignore",
      shell: process.platform === "win32",
    });
    return inspect.status === 0;
  }

  function pushToLocalRegistry(image, { localBuild = false } = {}) {
    const upstream = normalizeImageRef(image);
    if (localRegistryHasImage(upstream)) {
      console.error(`ok: ${localRegistryRef(upstream)} already in registry`);
      return localRegistryRef(upstream);
    }
    if (registryMode === "harbor") {
      dockerLoginHarbor();
    }
    let source = upstream;
    if (localBuild) {
      const candidates = [upstream, `${localRegistry}/${upstream}`];
      source =
        candidates.find((candidate) => dockerHasLocalImage(candidate)) ?? "";
      if (!source) {
        throw new Error(
          `Local image missing: ${upstream} (tried ${candidates.join(", ")})`,
        );
      }
    } else if (dockerHasLocalImage(upstream)) {
      console.error(`ok: ${upstream} already in Docker (push to registry)`);
      source = upstream;
    } else {
      console.error(`pull ${upstream} (${kindPlatform})`);
      run("docker", ["pull", "--platform", kindPlatform, upstream]);
    }
    const dest = localRegistryRef(upstream);
    if (source !== dest) {
      run("docker", ["tag", source, dest]);
    }
    console.error(`push ${dest}`);
    run("docker", ["push", dest]);
    return dest;
  }

  function repodyImagesInRegistry({ backendTag, webTag }) {
    const backendOk = localRegistryHasImage(`repody-backend:${backendTag}`);
    const webOk = localRegistryHasImage(`repody-web:${webTag}`);
    return { backendOk, webOk, allOk: backendOk && webOk };
  }

  function stopLocalRegistry() {
    if (registryMode === "harbor") {
      console.error("ok: Harbor registry left running (pnpm harbor:down to stop)");
      return;
    }
    heading(`Stopping local registry (${localRegistry})`);
    const inspect = spawnSync(
      "docker",
      ["inspect", "-f", "{{.State.Running}}", registryName],
      { encoding: "utf8", shell: process.platform === "win32" },
    );
    if (inspect.status !== 0) {
      console.error(`ok: ${registryName} not present`);
      return;
    }
    if (inspect.stdout?.trim() === "true") {
      run("docker", ["stop", registryName]);
      console.error(`✓ ${registryName} stopped`);
      return;
    }
    console.error(`ok: ${registryName} already stopped`);
  }

  return {
    connectRegistryToKind,
    ensureLocalRegistry,
    localRegistryRef,
    pushToLocalRegistry,
    repodyImagesInRegistry,
    stopLocalRegistry,
  };
}
