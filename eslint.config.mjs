import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    settings: {
      react: { version: "19" },
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "**/.next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Non-frontend trees (Python, infra, generated artifacts):
    "backend/**",
    "deploy/**",
    "e2e/**",
    "scripts/**",
    "lib/api/openapi.json",
    "lib/api/generated/**",
  ]),
]);

export default eslintConfig;
