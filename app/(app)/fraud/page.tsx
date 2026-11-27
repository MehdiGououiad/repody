import { notFound } from "next/navigation";
import { hasModule } from "@/modules/core/entitlements";
import { fetchEntitlements } from "@/modules/core/server-entitlements";
import { FraudWorkspace } from "@/modules/fraud/fraud-workspace";

export const dynamic = "force-dynamic";

export default async function FraudPage() {
  const entitlements = await fetchEntitlements();
  if (!hasModule(entitlements, "fraud")) {
    notFound();
  }
  return <FraudWorkspace />;
}
