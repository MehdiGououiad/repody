"use client";

import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { Download, LoaderCircle, Play, Upload } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  artifactUrl,
  fetchJobReport,
  fetchLatestBenchmark,
  startBenchmark,
  type BenchmarkReport,
  type BenchmarkResult,
  type OperatorJob,
} from "@/lib/api/operator";
import { benchmarkModelsFromCatalog, useUnifiedModelsCatalog } from "@/lib/hooks/use-catalog-queries";
import { DocumentTextPreviewPanel } from "@/components/documents/document-markdown-preview";
import { ACTIVE_STATUSES, formatDuration, formatPercent } from "../settings-shared";

const SUPPORTED_DOCUMENT_ACCEPT = ".pdf,.png,.jpg,.jpeg,.webp,application/pdf,image/png,image/jpeg,image/webp";

function scoreLabel(row: BenchmarkResult): string {
  if (row.judgeQuality || row.ocrCompare) {
    const chars = row.ocrCompare ? row.rawTextChars : row.ocrTextChars;
    return chars != null ? `${chars} chars` : "—";
  }
  return formatPercent(row.fieldAccuracy);
}

function ReportView({ report, jobId }: { report: BenchmarkReport; jobId?: string }) {
  return (
    <section className="panel-elevated rounded-xl overflow-hidden">
      <div className="px-6 py-5 border-b border-border bg-surface-container-low flex flex-wrap gap-4 items-center justify-between">
        <div>
          <h2 className="font-display text-lg font-semibold">Benchmark report</h2>
          <p className="text-xs text-on-surface-variant mt-1">
            {new Date(report.generatedAt).toLocaleString()} · {report.profile}
          </p>
        </div>
        {jobId ? (
          <div className="flex gap-2">
            {(["json", "csv", "html"] as const).map((artifact) => (
              <Button key={artifact} asChild variant="outline" size="sm">
                <a href={artifactUrl(jobId, artifact)} download>
                  <Download className="h-3.5 w-3.5 mr-1.5" />
                  {artifact.toUpperCase()}
                </a>
              </Button>
            ))}
          </div>
        ) : null}
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-5 border-b border-border">
        {[
          ["Passed", report.summary.passed],
          ["Failed", report.summary.failed],
          ["Skipped", report.summary.skipped],
          ["Field accuracy", formatPercent(report.summary.fieldAccuracy)],
          ["Median wall", formatDuration(report.summary.medianWallMs)],
        ].map(([label, value]) => (
          <div key={label} className="px-5 py-4 border-r border-border last:border-0">
            <p className="text-[11px] uppercase tracking-wider text-on-surface-variant">{label}</p>
            <p className="text-xl font-semibold mt-1 tabular-nums">{value}</p>
          </div>
        ))}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-surface-container-low text-left">
            <tr>
              {["Model", "Phase", "Status", "Wall", "Queue", "Extract", "Validate", "Score"].map((heading) => (
                <th key={heading} className="px-4 py-3 text-[11px] uppercase tracking-wider text-on-surface-variant">
                  {heading}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {report.results.map((row, index) => (
              <Fragment key={`${row.case}-${row.phase}-${index}`}>
                <tr>
                <td className="px-4 py-3">
                  <p className="font-medium">{row.case}</p>
                  <code className="text-[11px] text-on-surface-variant">{row.model}</code>
                </td>
                <td className="px-4 py-3">{row.phase}</td>
                <td className="px-4 py-3">
                  <Badge variant={row.passed ? "success" : row.skipped ? "outline" : "danger"}>
                    {row.status}
                  </Badge>
                </td>
                <td className="px-4 py-3 tabular-nums">{formatDuration(row.wallMs)}</td>
                <td className="px-4 py-3 tabular-nums">{formatDuration(row.queueMs)}</td>
                <td className="px-4 py-3 tabular-nums">{formatDuration(row.extractionMs)}</td>
                <td className="px-4 py-3 tabular-nums">{formatDuration(row.validationMs)}</td>
                <td className="px-4 py-3 tabular-nums">{scoreLabel(row)}</td>
              </tr>
              {row.error ? (
                <tr key={`${row.case}-${row.phase}-${index}-error`} className="bg-destructive/5">
                  <td colSpan={8} className="px-4 py-3 text-xs text-destructive">
                    {row.error}
                  </td>
                </tr>
              ) : null}
              {row.textPreview ? (
                <tr key={`${row.case}-${row.phase}-${index}-preview`} className="bg-surface-container-low/40">
                  <td colSpan={8} className="px-4 py-3">
                    <DocumentTextPreviewPanel
                      text={row.textPreview}
                      label={`Rendered preview (${row.ocrCompare ? "OCR" : "NuExtract markdown"})`}
                    />
                  </td>
                </tr>
              ) : null}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function BenchmarksTab({
  actionsEnabled,
  jobs,
  onJobCreated,
}: {
  actionsEnabled: boolean;
  jobs: OperatorJob[];
  onJobCreated: (job: OperatorJob) => void;
}) {
  const [profile, setProfile] = useState<"quick" | "models" | "full">("models");
  const validationMode = "logic_only";
  const [warmRuns, setWarmRuns] = useState("1");
  const [minimumAccuracy, setMinimumAccuracy] = useState("0");
  const [cacheCheck, setCacheCheck] = useState(true);
  const [judgeQuality, setJudgeQuality] = useState(true);
  const catalogQuery = useUnifiedModelsCatalog();
  const models = useMemo(() => {
    if (!catalogQuery.data) return [];
    return benchmarkModelsFromCatalog(catalogQuery.data).filter(
      (model) => model.available !== false,
    );
  }, [catalogQuery.data]);
  const modelsInitialized = useRef(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [customDataset, setCustomDataset] = useState(false);
  const [document, setDocument] = useState<File | null>(null);
  const [report, setReport] = useState<BenchmarkReport | null>(null);
  const [reportJobId, setReportJobId] = useState<string>();
  const active = jobs.find((job) => job.kind === "benchmark" && ACTIVE_STATUSES.has(job.status));

  useEffect(() => {
    if (!catalogQuery.data || modelsInitialized.current) return;
    modelsInitialized.current = true;
    setSelected(models.map((model) => model.id));
  }, [catalogQuery.data, models]);

  useEffect(() => {
    void fetchLatestBenchmark().then(setReport);
  }, []);

  useEffect(() => {
    const completed = jobs.find(
      (job) => job.kind === "benchmark" && job.hasReport && !ACTIVE_STATUSES.has(job.status)
    );
    if (!completed || completed.id === reportJobId) return;
    void fetchJobReport(completed.id).then((next) => {
      setReport(next);
      setReportJobId(completed.id);
    });
  }, [jobs, reportJobId]);

  const toggleModel = (id: string) => {
    setSelected((current) =>
      current.includes(id) ? current.filter((model) => model !== id) : [...current, id]
    );
  };

  const run = async () => {
    if (customDataset && !document) {
      toast.error("Choose a document to benchmark.");
      return;
    }
    try {
      const job = await startBenchmark({
        profile,
        models: selected,
        validationMode,
        warmRuns: Number(warmRuns),
        minimumAccuracy: Number(minimumAccuracy),
        cacheCheck,
        judgeQuality,
        document: customDataset ? document : null,
      });
      onJobCreated(job);
      setReportJobId(undefined);
      toast.success("Benchmark started");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Benchmark failed to start");
    }
  };

  return (
    <div className="space-y-6">
      <section className="panel-elevated rounded-xl p-6">
        <div className="flex flex-col xl:flex-row gap-8">
          <div className="flex-1 min-w-0 space-y-5">
            <div>
              <h2 className="font-display text-lg font-semibold">Run benchmark suite</h2>
              <p className="text-sm text-on-surface-variant mt-1">
                Compare NuExtract markdown (Repody VLM) and Surya OCR in parallel — you judge text quality from the previews.
              </p>
            </div>
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="benchmark-profile">Profile</Label>
                <Select value={profile} onValueChange={(value) => setProfile(value as typeof profile)}>
                  <SelectTrigger id="benchmark-profile"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="quick">Quick baseline</SelectItem>
                    <SelectItem value="models">Vision models</SelectItem>
                    <SelectItem value="full">Full platform</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="benchmark-validation">Validation</Label>
                <Input id="benchmark-validation" value="Logic only" readOnly disabled />
              </div>
              <div className="space-y-2">
                <Label htmlFor="benchmark-warm-runs">Warm runs per model</Label>
                <Input id="benchmark-warm-runs" type="number" min="0" max="5" value={warmRuns} onChange={(event) => setWarmRuns(event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="benchmark-accuracy">Minimum field accuracy</Label>
                <Input
                  id="benchmark-accuracy"
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  value={minimumAccuracy}
                  disabled={judgeQuality}
                  onChange={(event) => setMinimumAccuracy(event.target.value)}
                />
              </div>
            </div>
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={judgeQuality}
                onChange={(event) => setJudgeQuality(event.target.checked)}
                className="size-4 mt-0.5 accent-primary"
              />
              <span className="text-sm">
                <span className="font-medium block">Judge text quality manually</span>
                <span className="text-on-surface-variant text-xs">
                  Enables NuExtract <code className="text-[10px]">mode: markdown</code> on Repody VLM and passes when markdown/OCR text is non-empty.
                </span>
              </span>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" checked={cacheCheck} onChange={(event) => setCacheCheck(event.target.checked)} className="size-4 accent-primary" />
              <span className="text-sm">Verify extraction cache on the final repeated run</span>
            </label>
          </div>

          <div className="flex-1 min-w-0 space-y-5">
            <div>
              <p className="text-sm font-semibold">Models</p>
              <div className="grid sm:grid-cols-2 gap-2 mt-2">
                {models.map((model) => (
                  <label key={model.id} className="flex min-w-0 items-start gap-3 p-3 rounded-lg border border-border hover:bg-surface-container-low cursor-pointer">
                    <input type="checkbox" checked={selected.includes(model.id)} onChange={() => toggleModel(model.id)} className="size-4 mt-0.5 accent-primary" />
                    <span className="min-w-0">
                      <span className="block text-sm font-medium">{model.label}</span>
                      {model.kind === "ocr_compare" ? (
                        <span className="block text-[11px] text-on-surface-variant mt-0.5">
                          OCR compare — text output only (no structured fields)
                        </span>
                      ) : null}
                    </span>
                  </label>
                ))}
              </div>
            </div>
            <div>
              <p className="text-sm font-semibold">Dataset</p>
              <p className="text-xs text-on-surface-variant mt-1">
                Default: built-in invoice PDF — no upload needed. For your own file, upload the document only;
                fields are optional when judging markdown/OCR text quality.
              </p>
              <label className="mt-3 flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={customDataset}
                  onChange={(event) => {
                    setCustomDataset(event.target.checked);
                    if (!event.target.checked) {
                      setDocument(null);
                    }
                  }}
                  className="size-4 accent-primary"
                />
                <span className="text-sm">Use a custom document</span>
              </label>
              {customDataset ? (
                <Label className="mt-3 block rounded-lg border border-dashed border-outline-variant p-4 cursor-pointer hover:bg-surface-container-low">
                  <Upload className="h-4 w-4 mb-2" />
                  <span className="block text-xs font-medium">{document?.name || "Choose PDF or image"}</span>
                  <input
                    type="file"
                    className="sr-only"
                    accept={SUPPORTED_DOCUMENT_ACCEPT}
                    onChange={(event) => setDocument(event.target.files?.[0] || null)}
                  />
                </Label>
              ) : (
                <p className="mt-2 text-[11px] text-on-surface-variant rounded-lg border border-border/60 bg-surface-container-low/50 px-3 py-2">
                  Using built-in fixture: invoice PDF with reference field checks.
                </p>
              )}
            </div>
          </div>
        </div>
        <div className="mt-6 pt-5 border-t border-border flex flex-wrap items-center justify-between gap-4">
          <p className="text-xs text-on-surface-variant">
            {actionsEnabled ? "Runs asynchronously; you can leave this tab." : "Operator actions are disabled by configuration."}
          </p>
          <Button onClick={() => void run()} disabled={!actionsEnabled || !!active || (profile === "models" && selected.length === 0)}>
            {active ? <LoaderCircle className="h-4 w-4 mr-2 animate-spin" /> : <Play className="h-4 w-4 mr-2" />}
            {active ? "Benchmark running" : "Run benchmark"}
          </Button>
        </div>
      </section>
      {report ? <ReportView report={report} jobId={reportJobId} /> : null}
    </div>
  );
}
