import { redirect } from "next/navigation";
import { resolveHomeRoute, showModuleSwitcher } from "@/modules/core/entitlements";
import { HubLauncher } from "@/modules/core/hub-launcher";
import { PLATFORM_MANIFESTS } from "@/modules/core/manifests";
import { fetchEntitlements } from "@/modules/core/server-entitlements";

export const dynamic = "force-dynamic";

export default async function HubPage() {
  const entitlements = await fetchEntitlements();
  if (!showModuleSwitcher(entitlements)) {
    redirect(resolveHomeRoute(entitlements, PLATFORM_MANIFESTS));
  }
  return <HubLauncher />;
}
