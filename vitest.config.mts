import { defineConfig } from "vitest/config";

export default defineConfig({
  // Vite resolves the "@/…" paths from tsconfig.json itself.
  resolve: { tsconfigPaths: true },
  test: { include: ["lib/**/*.test.ts", "i18n/**/*.test.ts"], environment: "node" },
});
