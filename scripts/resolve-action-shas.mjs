#!/usr/bin/env node
/** Resolve GitHub Action tag → commit SHA for pinning. Usage: node scripts/resolve-action-shas.mjs */
import https from "node:https";

const refs = [
  "actions/checkout@v4.2.2",
  "actions/setup-node@v4.4.0",
  "actions/upload-artifact@v4.6.2",
  "actions/download-artifact@v4.3.0",
  "actions/setup-python@v5.6.0",
  "docker/setup-buildx-action@v3.10.0",
  "pnpm/action-setup@v4.1.0",
  "astral-sh/setup-uv@v6.1.0",
  "github/codeql-action@v3.28.18",
  "anchore/sbom-action@v0.20.1",
  "anchore/sbom-action@v0.17.9",
  "sigstore/cosign-installer@v3.7.0",
  "anchore/scan-action@v7",
  "aquasecurity/trivy-action@0.33.1",
  "aquasecurity/setup-trivy@v0.2.3",
];

function get(url) {
  return new Promise((resolve, reject) => {
    https
      .get(
        url,
        {
          headers: {
            "User-Agent": "repody-action-pin",
            Accept: "application/vnd.github+json",
          },
        },
        (res) => {
          let data = "";
          res.on("data", (c) => (data += c));
          res.on("end", () => {
            try {
              resolve(JSON.parse(data));
            } catch (e) {
              reject(e);
            }
          });
        },
      )
      .on("error", reject);
  });
}

for (const spec of refs) {
  const at = spec.lastIndexOf("@");
  const repo = spec.slice(0, at);
  const tag = spec.slice(at + 1);
  const url = `https://api.github.com/repos/${repo}/git/ref/tags/${tag}`;
  try {
    const ref = await get(url);
    if (ref.message) {
      const commitUrl = `https://api.github.com/repos/${repo}/commits/${tag}`;
      const commit = await get(commitUrl);
      console.log(`${spec} ${commit.sha ?? commit.message}`);
      continue;
    }
    let sha = ref.object.sha;
    if (ref.object.type === "tag") {
      const tagObj = await get(ref.object.url);
      sha = tagObj.object.sha;
    }
    console.log(`${spec} ${sha}`);
  } catch (e) {
    console.log(`${spec} ERROR ${e.message}`);
  }
}
