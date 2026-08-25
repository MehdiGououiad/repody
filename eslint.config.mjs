import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

// Division of labour: Biome owns formatting plus general TypeScript, React and
// accessibility linting for the whole repo. ESLint is kept only for the
// Next.js-specific rules Biome cannot express (image/font/script usage, client
// navigation, Core Web Vitals) and for the official React Hooks plugin.
//
// Every rule below belonging to a plugin Biome already covers is switched off,
// so a given problem is reported by exactly one tool.
const BIOME_OWNED_PLUGINS = ["@typescript-eslint", "react", "jsx-a11y", "import"];

function disableBiomeOwnedRules(configs) {
  const disabled = {};
  for (const config of configs) {
    for (const ruleId of Object.keys(config.rules ?? {})) {
      if (BIOME_OWNED_PLUGINS.includes(ruleId.split("/")[0])) {
        disabled[ruleId] = "off";
      }
    }
  }
  return disabled;
}

const nextConfigs = [...nextVitals, ...nextTs];

export default defineConfig([
  ...nextConfigs,
  {
    settings: { react: { version: "19" } },
    rules: disableBiomeOwnedRules(nextConfigs),
  },
  globalIgnores([
    ".next/**",
    "**/.next/**",
    "out/**",
    "build/**",
    "dist/**",
    "next-env.d.ts",
    // Non-frontend trees (Python, infra, generated artifacts) — Biome and ruff
    // cover these instead.
    "backend/**",
    "deploy/**",
    "e2e/**",
    "scripts/**",
    "lib/api/openapi.json",
    "lib/api/generated/**",
  ]),
]);
