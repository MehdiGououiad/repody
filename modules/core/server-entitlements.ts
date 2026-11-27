import "server-only";

import { cache } from "react";
import { coreOrigin } from "@/lib/api/backend-origin";
import type { EntitlementState, LicenseStatus, ModuleId } from "./entitlements";
import { parseEnvModules } from "./manifests";

type CoreEntitlementPayload = {
  status?: LicenseStatus;
  modules?: ModuleId[];
  warning?: string | null;
};

/**
 * Resolve runtime module entitlements on the server.
 * Calls `repody-core` when `INTERNAL_CORE_API_URL` is configured, else respects
 * `REPODY_ENABLED_MODULES`, defaulting to single-module IDP parity (`["idp"]`).
 */
export const fetchEntitlements = cache(async (): Promise<EntitlementState> => {
  const origin = coreOrigin();
  if (origin) {
    try {
      const response = await fetch(`${origin}/v1/platform/entitlements`, {
        cache: "no-store",
        signal: AbortSignal.timeout(2500),
      });
      if (response.ok) {
        const body = (await response.json()) as CoreEntitlementPayload;
        if (body.status && Array.isArray(body.modules)) {
          return {
            status: body.status,
            modules: body.modules,
            warning: body.warning ?? null,
          };
        }
      }
    } catch {
      // Fall through to env configuration if Core is unavailable during cold boot.
    }
  }

  const configured = parseEnvModules(process.env.REPODY_ENABLED_MODULES);
  if (configured.length > 0) {
    return { status: "active", modules: configured, warning: null };
  }
  return { status: "active", modules: ["idp"], warning: null };
});
