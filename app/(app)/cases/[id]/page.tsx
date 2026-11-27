import { headers } from "next/headers";
import { notFound } from "next/navigation";
import { coreOrigin } from "@/lib/api/backend-origin";
import { currentAccount } from "@/lib/auth/server";
import { verifySession } from "@/lib/auth/dal";
import { showModuleSwitcher } from "@/modules/core/entitlements";
import { fetchEntitlements } from "@/modules/core/server-entitlements";
import { CaseInspector } from "@/modules/pipelines/case-inspector";
import type { ApprovalTask, CaseRecord } from "@/modules/pipelines/types";

export const dynamic = "force-dynamic";

async function loadCoreJson<T>(path: string, token: string | null): Promise<T | null> {
  const origin = coreOrigin();
  if (!origin) return null;
  try {
    const res = await fetch(`${origin}${path}`, {
      cache: "no-store",
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export default async function CaseDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ approvalId?: string }>;
}) {
  const entitlements = await fetchEntitlements();
  if (!showModuleSwitcher(entitlements) && !coreOrigin()) {
    notFound();
  }
  const [{ id }, { approvalId }, hdrs, token] = await Promise.all([
    params,
    searchParams,
    headers(),
    verifySession(),
  ]);
  const [caseRecord, approval, account] = await Promise.all([
    loadCoreJson<CaseRecord>(`/v1/cases/${encodeURIComponent(id)}`, token),
    approvalId
      ? loadCoreJson<ApprovalTask>(`/v1/approvals/${encodeURIComponent(approvalId)}`, token)
      : null,
    currentAccount(hdrs),
  ]);
  if (!caseRecord) {
    notFound();
  }
  return (
    <CaseInspector
      initialCase={caseRecord}
      initialApproval={approval}
      currentActorSub={account?.email ?? account?.name ?? null}
    />
  );
}
