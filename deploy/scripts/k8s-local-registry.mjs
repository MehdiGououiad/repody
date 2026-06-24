import { spawnSync } from "node:child_process";
import path from "node:path";
import { requireDockerEngine } from "./k8s-local-process.mjs";
import { ensureLocalDockerNoProxy } from "./k8s-local-registry-config.mjs";

const PUSH_CONCURRENCY = 2;

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
  connectHarborToKind,
  run,
}) {
  let harborLoggedIn = false;

  function localRegistryRef(image) {
    return `${localRegistry}/${normalizeImageRef(image)}`;
  }

  function registryApiBase() {
    return `http://${harborHost}:${harborHttpPort}`;
  }

  function manifestRepository(image) {
    const normalized = normalizeImageRef(image);
    const colon = normalized.lastIndexOf(":");
    const name = colon > 0 ? normalized.slice(0, colon) : normalized;
    return `${harborProject}/${name}`;
  }

  function manifestTag(image) {
    const normalized = normalizeImageRef(image);
    const colon = normalized.lastIndexOf(":");
    return colon > 0 ? normalized.slice(colon + 1) : "latest";
  }

  function localRegistryHasImage(image) {
    const repository = manifestRepository(image);
    const tag = manifestTag(image);
    const repoName = repository.includes("/")
      ? repository.slice(repository.indexOf("/") + 1)
      : repository;

    if (dockerHasLocalImage(localRegistryRef(image))) {
      return true;
    }

    if (harborAdminPassword) {
      try {
        const encodedRepo = encodeURIComponent(repoName);
        const encodedTag = encodeURIComponent(tag);
        const body = captureNoShell(process.platform === "win32" ? "curl.exe" : "curl", [
          "-fsS",
          "--max-time",
          "5",
          "-u",
          `admin:${harborAdminPassword}`,
          `${registryApiBase()}/api/v2.0/projects/${harborProject}/repositories/${encodedRepo}/artifacts?q=tags%3D${encodedTag}`,
        ]);
        const artifacts = JSON.parse(body);
        if (Array.isArray(artifacts) && artifacts.length > 0) {
          return true;
        }
      } catch {
        // fall through to registry v2 probe
      }
    }

    const curlArgs = [
      "-fsI",
      "--max-time",
      "3",
      "-H",
      "Accept: application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json, application/vnd.docker.distribution.manifest.list.v2+json",
    ];
    if (harborAdminPassword) {
      curlArgs.push("-u", `admin:${harborAdminPassword}`);
    }
    curlArgs.push(`${registryApiBase()}/v2/${repository}/manifests/${tag}`);
    try {
      captureNoShell(process.platform === "win32" ? "curl.exe" : "curl", curlArgs);
      return true;
    } catch {
      return false;
    }
  }

  function dockerLoginHarbor() {
    if (harborLoggedIn) return;
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
    harborLoggedIn = true;
    console.error(`ok: docker logged in to ${registry}`);
  }

  function ensureLocalRegistry() {
    requireDockerEngine();
    ensureLocalDockerNoProxy(harborHost);
    heading(`Harbor registry (${localRegistry})`);
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

  function connectRegistryToKind() {
    connectHarborToKind();
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
    dockerLoginHarbor();
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

  async function pushManyToLocalRegistry(images, { localBuild = false } = {}) {
    const unique = [...new Set(images)];
    let skipped = 0;
    let pushed = 0;
    const queue = [...unique];
    const workers = Array.from(
      { length: Math.min(PUSH_CONCURRENCY, queue.length || 1) },
      async () => {
        while (queue.length > 0) {
          const image = queue.shift();
          if (!image) break;
          if (localRegistryHasImage(image)) {
            skipped += 1;
            console.error(`ok: ${localRegistryRef(image)} already in registry`);
            continue;
          }
          pushToLocalRegistry(image, { localBuild });
          pushed += 1;
        }
      },
    );
    await Promise.all(workers);
    if (skipped > 0) {
      console.error(`ok: ${skipped}/${unique.length} images skipped (already in Harbor)`);
    }
    if (pushed > 0) {
      console.error(`ok: pushed ${pushed} images to Harbor`);
    }
  }

  function repodyImagesInRegistry({ backendTag, webTag }) {
    const backendOk = localRegistryHasImage(`repody-backend:${backendTag}`);
    const webOk = localRegistryHasImage(`repody-web:${webTag}`);
    return { backendOk, webOk, allOk: backendOk && webOk };
  }

  function thirdPartyImagesWarm(images) {
    const unique = [...new Set(images)];
    if (unique.length === 0) return true;
    return unique.every((image) => localRegistryHasImage(image));
  }

  return {
    connectRegistryToKind,
    ensureLocalRegistry,
    localRegistryRef,
    pushManyToLocalRegistry,
    pushToLocalRegistry,
    repodyImagesInRegistry,
    thirdPartyImagesWarm,
  };
}
