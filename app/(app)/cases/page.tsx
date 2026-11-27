import { notFound } from "next/navigation";
import { coreOrigin } from "@/lib/api/backend-origin";
import { showModuleSwitcher } from "@/modules/core/entitlements";
import { fetchEntitlements } from "@/modules/core/server-entitlements";
import { CasesWorkspace } from "@/modules/pipelines/cases-workspace";

export const dynamic = "force-dynamic";

export default async function CasesPage() {
  const entitlements = await fetchEntitlements();
  if (!showModuleSwitcher(entitlements) && !coreOrigin()) {
    notFound();
  }
  return <CasesWorkspace />;
}
