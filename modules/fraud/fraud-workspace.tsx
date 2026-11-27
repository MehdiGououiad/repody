"use client";

import { ExternalLink, FileUp, Loader2, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { analyzeDocument } from "./api";
import { FindingsPanel } from "./findings-panel";
import { ForensicViewer } from "./forensic-viewer";
import type { FraudAnalysis, FraudFinding } from "./types";

export function FraudWorkspace({
  initialAnalysis = null,
}: {
  initialAnalysis?: FraudAnalysis | null;
}) {
  const t = useTranslations("fraud");
  const [files, setFiles] = useState<File[]>([]);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [extractedJson, setExtractedJson] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<FraudAnalysis | null>(initialAnalysis);
  const [selectedFinding, setSelectedFinding] = useState<FraudFinding | null>(
    initialAnalysis?.findings[0] ?? null,
  );

  function handleFileChange(nextFiles: File[]) {
    setFiles(nextFiles);
    setPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      const first = nextFiles[0];
      return first && first.type.startsWith("image/") ? URL.createObjectURL(first) : null;
    });
  }

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setRunning(true);
    try {
      const result = await analyzeDocument(files, { extractedDataJson: extractedJson });
      setAnalysis(result);
      setSelectedFinding(result.findings[0] ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("scanFailed"));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-7">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-4">
        <div className="space-y-1">
          <h1 className="flex items-center gap-2 text-xl font-semibold tracking-tight text-ink">
            <ShieldAlert className="size-5 text-fail-ink" aria-hidden />
            {t("title")}
          </h1>
          <p className="text-[13px] text-ink-3">{t("subtitle")}</p>
        </div>
        {analysis ? (
          <Link
            href={`/fraud/${analysis.id}`}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-accent-ink hover:underline"
          >
            <span>{t("permalink")}</span>
            <ExternalLink className="size-3.5" aria-hidden />
          </Link>
        ) : null}
      </header>

      <form
        onSubmit={handleSubmit}
        className="grid gap-4 rounded-xl border border-line bg-raised p-4 shadow-panel md:grid-cols-[1fr_1fr_auto]"
      >
        <div className="flex flex-col gap-1.5">
          <label htmlFor="fraud-upload-files" className="text-xs font-medium text-ink-2">
            {t("uploadLabel")}
          </label>
          <label
            htmlFor="fraud-upload-files"
            className="flex min-h-20 cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-line-strong bg-field px-3 py-2 text-[13px] text-ink-2 transition-colors hover:bg-hover"
          >
            <FileUp className="size-4 shrink-0 text-ink-3" aria-hidden />
            <span className="truncate">
              {files.length > 0 ? files.map((f) => f.name).join(", ") : t("uploadPlaceholder")}
            </span>
          </label>
          <input
            id="fraud-upload-files"
            type="file"
            multiple
            accept="application/pdf,image/png,image/jpeg,image/webp"
            onChange={(e) => handleFileChange(Array.from(e.target.files ?? []))}
            className="sr-only"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="fraud-extracted-json" className="text-xs font-medium text-ink-2">
            {t("jsonLabel")}
          </label>
          <Textarea
            id="fraud-extracted-json"
            value={extractedJson}
            onChange={(e) => setExtractedJson(e.target.value)}
            placeholder={t("jsonPlaceholder")}
            className="min-h-20 font-mono text-xs"
          />
        </div>

        <div className="flex items-end">
          <Button
            type="submit"
            variant="primary"
            size="md"
            disabled={running || (files.length === 0 && !extractedJson.trim())}
            className="w-full md:w-auto"
          >
            {running ? <Loader2 className="size-3.5 animate-spin" aria-hidden /> : null}
            <span>{running ? t("scanning") : t("runScan")}</span>
          </Button>
        </div>
      </form>

      {error ? (
        <div
          role="alert"
          className="rounded-lg border border-fail/30 bg-fail-wash px-4 py-3 text-[13px] text-fail-ink"
        >
          {error}
        </div>
      ) : null}

      {analysis ? (
        <div className="grid gap-5 lg:grid-cols-[1.25fr_1fr]">
          <ForensicViewer
            analysisId={analysis.id}
            previewUrl={previewUrl}
            artifacts={analysis.generated_artifacts}
            findings={analysis.findings}
            selectedFinding={selectedFinding}
            onSelectFinding={setSelectedFinding}
          />
          <FindingsPanel
            analysis={analysis}
            selectedFinding={selectedFinding}
            onSelectFinding={setSelectedFinding}
          />
        </div>
      ) : null}
    </div>
  );
}
