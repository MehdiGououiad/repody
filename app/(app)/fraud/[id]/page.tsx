import { notFound } from "next/navigation";
import { fraudOrigin } from "@/lib/api/backend-origin";
import { verifySession } from "@/lib/auth/dal";
import { hasModule } from "@/modules/core/entitlements";
import { fetchEntitlements } from "@/modules/core/server-entitlements";
import { FraudWorkspace } from "@/modules/fraud/fraud-workspace";
import type { FraudAnalysis } from "@/modules/fraud/types";

export const dynamic = "force-dynamic";

async function loadServerAnalysis(id: string): Promise<FraudAnalysis | null> {
  const origin = fraudOrigin();
  if (!origin) return null;
  const token = await verifySession();
  const res = await fetch(`${origin}/v1/analyses/${encodeURIComponent(id)}`, {
    cache: "no-store",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    signal: AbortSignal.timeout(5000),
  });
  if (res.status === 404) return null;
  if (!res.ok) return null;
  return (await res.json()) as FraudAnalysis;
}

export default async function FraudAnalysisDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const entitlements = await fetchEntitlements();
  if (!hasModule(entitlements, "fraud")) {
    notFound();
  }
  const { id } = await params;
  const analysis = await loadServerAnalysis(id);
  if (!analysis) {
    notFound();
  }
  return <FraudWorkspace initialAnalysis={analysis} />;
}
