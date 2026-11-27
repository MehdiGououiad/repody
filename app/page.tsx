import { redirect } from "next/navigation";
import { resolveHomeRoute } from "@/modules/core/entitlements";
import { PLATFORM_MANIFESTS } from "@/modules/core/manifests";
import { fetchEntitlements } from "@/modules/core/server-entitlements";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const entitlements = await fetchEntitlements();
  redirect(resolveHomeRoute(entitlements, PLATFORM_MANIFESTS));
}
