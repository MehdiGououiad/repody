"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  BrainCircuit,
  ServerCog,
  ShieldCheck,
  TestTube2,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/layout/page-header";
import { PageShell } from "@/components/layout/page-shell";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { PlatformConfig } from "@/lib/api/platform-config";
import {
  fetchOperatorJobs,
  fetchOperatorStatus,
  type OperatorJob,
  type OperatorStatus,
} from "@/lib/api/operator";
import { useQueryParam } from "@/lib/hooks/use-query-param";
import { ACTIVE_STATUSES, SETTINGS_TABS, type SettingsTab } from "./settings-shared";
import { OverviewTab } from "./tabs/overview-tab";
import { ModelsTab } from "./tabs/models-tab";
import { BenchmarksTab } from "./tabs/benchmarks-tab";
import { DiagnosticsTab } from "./tabs/diagnostics-tab";

export function SettingsPageClient({
  platformConfig,
  platformError,
}: {
  platformConfig: PlatformConfig | null;
  platformError: string | null;
}) {
  const [tabParam, setTabParam] = useQueryParam("tab", "overview");
  const activeTab: SettingsTab = SETTINGS_TABS.includes(tabParam as SettingsTab)
    ? (tabParam as SettingsTab)
    : "overview";
  const [operator, setOperator] = useState<OperatorStatus | null>(null);
  const [jobs, setJobs] = useState<OperatorJob[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(async () => {
    try {
      const [status, nextJobs] = await Promise.all([
        fetchOperatorStatus(),
        fetchOperatorJobs(),
      ]);
      setOperator(status);
      setJobs(nextJobs);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Operator API unavailable");
    }
  }, []);

  useEffect(() => {
    void Promise.all([fetchOperatorStatus(), fetchOperatorJobs()])
      .then(([status, nextJobs]) => {
        setOperator(status);
        setJobs(nextJobs);
      })
      .catch((error) => {
        toast.error(error instanceof Error ? error.message : "Operator API unavailable");
      });
  }, [refreshKey]);

  useEffect(() => {
    if (!jobs.some((job) => ACTIVE_STATUSES.has(job.status))) return;
    const timer = window.setInterval(() => void refresh(), 2000);
    return () => window.clearInterval(timer);
  }, [jobs, refresh]);

  const addJob = (job: OperatorJob) => {
    setJobs((current) => [job, ...current.filter((item) => item.id !== job.id)]);
  };

  return (
    <PageShell>
      <PageHeader
        title="Operator Console"
        description="Runtime models, warmup, benchmark evidence, and platform diagnostics."
        eyebrow="Platform"
      />
      {platformError ? (
        <div className="rounded-xl border border-danger/30 bg-danger-soft p-4 text-sm text-danger">
          {platformError}
        </div>
      ) : null}
      {!operator?.actionsEnabled ? (
        <div className="rounded-xl border border-warning/30 bg-warning-soft p-4 flex items-start gap-3">
          <ShieldCheck className="h-5 w-5 text-warning shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold">Operator actions are read only</p>
            <p className="text-xs text-on-surface-variant mt-1">
              Set <code>AUDIT_OPERATOR_ACTIONS_ENABLED=true</code> on the API to allow installs, warmup, and benchmarks.
            </p>
          </div>
        </div>
      ) : null}
      <Tabs
        value={activeTab}
        onValueChange={(value) => setTabParam(value === "overview" ? null : value)}
      >
        <TabsList className="flex-wrap h-auto gap-1 p-1">
          <TabsTrigger value="overview" className="gap-2"><ServerCog className="h-4 w-4" />Overview</TabsTrigger>
          <TabsTrigger value="models" className="gap-2"><BrainCircuit className="h-4 w-4" />Models</TabsTrigger>
          <TabsTrigger value="benchmarks" className="gap-2"><TestTube2 className="h-4 w-4" />Benchmarks</TabsTrigger>
          <TabsTrigger value="diagnostics" className="gap-2"><Activity className="h-4 w-4" />Diagnostics</TabsTrigger>
        </TabsList>
        <TabsContent value="overview" className="mt-6">
          <OverviewTab platform={platformConfig} operator={operator} />
        </TabsContent>
        <TabsContent value="models" className="mt-6">
          <ModelsTab actionsEnabled={!!operator?.actionsEnabled} jobs={jobs} onJobCreated={addJob} />
        </TabsContent>
        <TabsContent value="benchmarks" className="mt-6">
          <BenchmarksTab actionsEnabled={!!operator?.actionsEnabled} jobs={jobs} onJobCreated={addJob} />
        </TabsContent>
        <TabsContent value="diagnostics" className="mt-6">
          <DiagnosticsTab
            platform={platformConfig}
            operator={operator}
            jobs={jobs}
            onRefresh={() => setRefreshKey((value) => value + 1)}
          />
        </TabsContent>
      </Tabs>
    </PageShell>
  );
}
