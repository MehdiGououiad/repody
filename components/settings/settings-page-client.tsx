"use client";

import { Activity, BrainCircuit, ServerCog, ShieldCheck, TestTube2 } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { PageShell } from "@/components/layout/page-shell";
import { SETTINGS_TABS, type SettingsTab } from "@/components/settings/settings-shared";
import { BenchmarksTab } from "@/components/settings/tabs/benchmarks-tab";
import { DiagnosticsTab } from "@/components/settings/tabs/diagnostics-tab";
import { ModelsTab } from "@/components/settings/tabs/models-tab";
import { OverviewTab } from "@/components/settings/tabs/overview-tab";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { PlatformConfig } from "@/lib/api/platform-config";
import { useOperatorState } from "@/lib/hooks/use-operator-state";
import { useQueryParam } from "@/lib/hooks/use-query-param";

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
  const { operator, jobs, addJob, refresh } = useOperatorState();

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
              Set <code>AUDIT_OPERATOR_ACTIONS_ENABLED=true</code> on the API to allow installs,
              warmup, and benchmarks.
            </p>
          </div>
        </div>
      ) : null}
      <Tabs
        value={activeTab}
        onValueChange={(value) => setTabParam(value === "overview" ? null : value)}
      >
        <TabsList className="flex-wrap h-auto gap-1 p-1">
          <TabsTrigger value="overview" className="gap-2">
            <ServerCog className="h-4 w-4" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="models" className="gap-2">
            <BrainCircuit className="h-4 w-4" />
            Models
          </TabsTrigger>
          <TabsTrigger value="benchmarks" className="gap-2">
            <TestTube2 className="h-4 w-4" />
            Benchmarks
          </TabsTrigger>
          <TabsTrigger value="diagnostics" className="gap-2">
            <Activity className="h-4 w-4" />
            Diagnostics
          </TabsTrigger>
        </TabsList>
        <TabsContent value="overview" className="mt-6">
          <OverviewTab platform={platformConfig} operator={operator} />
        </TabsContent>
        <TabsContent value="models" className="mt-6">
          <ModelsTab
            actionsEnabled={!!operator?.actionsEnabled}
            jobs={jobs}
            onJobCreated={addJob}
          />
        </TabsContent>
        <TabsContent value="benchmarks" className="mt-6">
          <BenchmarksTab
            actionsEnabled={!!operator?.actionsEnabled}
            jobs={jobs}
            onJobCreated={addJob}
          />
        </TabsContent>
        <TabsContent value="diagnostics" className="mt-6">
          <DiagnosticsTab
            platform={platformConfig}
            operator={operator}
            jobs={jobs}
            onRefresh={refresh}
          />
        </TabsContent>
      </Tabs>
    </PageShell>
  );
}
