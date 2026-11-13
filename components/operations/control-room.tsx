"use client";

import { useQueryClient } from "@tanstack/react-query";
import { toast } from "@ui-sdk/react/toast";
import { Square } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useFormatter, useNow, useTranslations } from "next-intl";
import { When } from "@/components/audit/run-row";
import { CardHeader, card } from "@/components/dashboard/insights";
import { AnimatedNumber } from "@/components/shared/animated-number";
import { Figure } from "@/components/shared/figure";
import { Button } from "@/components/ui/button";
import { confirmAction } from "@/components/ui/overlays";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { Tooltip } from "@/components/ui/tooltip";
import { useStepTitle } from "@/components/workflow/run-progress-steps";
import { $api } from "@/lib/api/browser";
import { EASE_OUT } from "@/lib/motion";
import { errorMessage } from "@/lib/query/get-query-client";
import type { Schema } from "@/lib/types";
import { cn, formatDurationMs } from "@/lib/utils";

type Operations = Schema["Operations"];
type ActiveRun = Operations["active"][number];

const LIVE_MS = 3_000;

function Pulse({ tone = "accent" }: { tone?: "accent" | "pass" | "fail" | "idle" }) {
  const color = { accent: "bg-accent", pass: "bg-pass", fail: "bg-fail", idle: "bg-ink-4" }[tone];
  return (
    <span className="relative flex size-2 shrink-0" aria-hidden>
      {tone !== "idle" ? (
        <span
          className={cn(
            "absolute inset-0 animate-ping rounded-full opacity-60 motion-reduce:hidden",
            color
          )}
        />
      ) : null}
      <span className={cn("relative size-2 rounded-full", color)} />
    </span>
  );
}

/** A run's steps as a track of segments; the active one sweeps, finished ones fill. */
function StepTrack({ run }: { run: ActiveRun }) {
  const title = useStepTitle();
  const steps = run.progress?.steps ?? [];
  const active = steps.filter((s) => s.status === "active");
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex gap-1">
        {steps.map((step) => (
          <span
            key={step.id}
            className="relative h-1 flex-1 overflow-hidden rounded-full bg-selected"
            title={title(step)}
          >
            {step.status === "done" ? (
              <motion.span
                className={cn("absolute inset-0 rounded-full", step.failed ? "bg-fail" : "bg-pass")}
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1 }}
                style={{ originX: 0 }}
                transition={{ duration: 0.3, ease: EASE_OUT }}
              />
            ) : step.status === "active" ? (
              <span className="absolute inset-y-0 w-1/2 animate-[sweep_1.2s_ease-in-out_infinite] rounded-full bg-accent motion-reduce:animate-none" />
            ) : null}
          </span>
        ))}
      </div>
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.span
          key={active.map((s) => s.id).join()}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.18 }}
          className="truncate text-xs text-ink-2"
        >
          {run.status === "queued" && run.progress?.queuePosition
            ? `#${run.progress.queuePosition} / ${run.progress.queueDepth}`
            : active.map(title).join(" · ") || "…"}
        </motion.span>
      </AnimatePresence>
    </div>
  );
}

function Elapsed({ since }: { since: string }) {
  const now = useNow({ updateInterval: 1000 });
  return (
    <span className="tabular-nums">
      {formatDurationMs(Math.max(0, now.getTime() - new Date(since).getTime()))}
    </span>
  );
}

/** Stop one run, after a confirmation; the list refreshes on success. */
function useCancelRun() {
  const t = useTranslations("operations");
  const queryClient = useQueryClient();
  const cancel = $api.useMutation("post", "/v1/runs/{run_id}/cancel", {
    onSuccess: () => {
      toast.success(t("cancelled"));
      void queryClient.invalidateQueries({ queryKey: ["get", "/v1/operations"] });
      void queryClient.invalidateQueries({ queryKey: ["get", "/v1/dashboard"] });
    },
    onError: (error) => toast.error(errorMessage(error, t("cancelFailed"))),
  });
  return async (run: ActiveRun) => {
    const yes = await confirmAction({
      title: t("cancelTitle"),
      description: `${run.workflowName} · ${run.id.slice(-6)}. ${t("cancelHint")}`,
      confirmLabel: t("cancel"),
      cancelLabel: t("keep"),
      danger: true,
    });
    if (yes) cancel.mutate({ params: { path: { run_id: run.id } } });
  };
}

function InFlight({ runs }: { runs: ActiveRun[] }) {
  const t = useTranslations("operations");
  const tAudits = useTranslations("audits");
  const stop = useCancelRun();
  return (
    <section className={card}>
      <CardHeader title={t("inFlight")} hint={t("inFlightHint")} />
      {runs.length ? (
        <ul className="divide-y divide-line">
          <AnimatePresence initial={false}>
            {runs.map((run) => {
              const stale = run.stuck;
              return (
                <motion.li
                  key={run.id}
                  layout
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0, transition: { duration: 0.2 } }}
                  transition={{ duration: 0.25, ease: EASE_OUT }}
                  className="overflow-hidden"
                >
                  <div
                    className={cn(
                      "group grid grid-cols-[14px_minmax(0,1fr)_minmax(0,1.2fr)_72px_auto] items-center gap-4 px-4 py-3",
                      stale && "bg-warn-wash/40"
                    )}
                  >
                    <StatusGlyph
                      status={stale ? "warning" : run.status === "running" ? "running" : "waiting"}
                      label={stale ? t("stuckHint") : undefined}
                    />
                    <span className="min-w-0">
                      <span className="block truncate text-[13px] font-medium text-ink">
                        {run.workflowName}
                      </span>
                      <span className="flex items-center gap-2 truncate text-xs text-ink-4">
                        <span className="font-mono">{run.id.slice(-6)}</span>
                        <span
                          className={cn(
                            "rounded-sm px-1 text-2xs font-medium",
                            run.source === "api"
                              ? "bg-accent-wash text-accent-ink"
                              : "bg-selected text-ink-3"
                          )}
                        >
                          {tAudits(`row.source.${run.source}`)}
                        </span>
                        <span className="truncate">{run.files.join(", ")}</span>
                      </span>
                    </span>
                    <StepTrack run={run} />
                    <span
                      className={cn("text-end text-xs", stale ? "text-warn-ink" : "text-ink-3")}
                    >
                      <Elapsed since={run.startedAt ?? run.createdAt} />
                      {stale ? <span className="block text-2xs">{t("stale")}</span> : null}
                    </span>
                    <Tooltip label={stale ? t("stuckHint") : t("cancel")}>
                      <Button
                        variant={stale ? "secondary" : "ghost"}
                        size="xs"
                        onClick={() => stop(run)}
                        className={cn(
                          "text-fail-ink",
                          !stale &&
                            "pointer-fine:opacity-0 pointer-fine:group-hover:opacity-100 pointer-fine:focus-visible:opacity-100"
                        )}
                      >
                        <Square className="fill-current" />
                        {t("cancel")}
                      </Button>
                    </Tooltip>
                  </div>
                </motion.li>
              );
            })}
          </AnimatePresence>
        </ul>
      ) : (
        <p className="flex items-center gap-2 px-4 py-8 text-[13px] text-ink-3">
          <StatusGlyph status="passed" />
          {t("nothingInFlight")}
        </p>
      )}
    </section>
  );
}

function Throughput({ hours }: { hours: Operations["throughput"] }) {
  const t = useTranslations("operations");
  const format = useFormatter();
  const max = Math.max(1, ...hours.map((h) => h.done + h.failed));
  const done = hours.reduce((sum, h) => sum + h.done, 0);
  const failed = hours.reduce((sum, h) => sum + h.failed, 0);
  return (
    <section className={card}>
      <CardHeader title={t("throughput")} hint={t("throughputHint")} />
      <div className="flex flex-col gap-3 p-4">
        <div className="flex h-24 items-end gap-[3px]">
          {hours.map((h, i) => {
            const label = `${format.dateTime(new Date(h.hour), { hour: "numeric" })} · ${h.done} / ${h.failed}`;
            return (
              <span key={h.hour} title={label} className="flex h-full flex-1 flex-col justify-end">
                <motion.span
                  className="flex w-full flex-col-reverse overflow-hidden rounded-[2px]"
                  initial={{ height: 0 }}
                  animate={{ height: `${((h.done + h.failed) / max) * 100}%` }}
                  transition={{ duration: 0.4, ease: EASE_OUT, delay: i * 0.015 }}
                >
                  {h.done ? <span className="bg-pass" style={{ flexGrow: h.done }} /> : null}
                  {h.failed ? <span className="bg-fail" style={{ flexGrow: h.failed }} /> : null}
                </motion.span>
                {h.done + h.failed === 0 ? (
                  <span className="h-0.5 rounded-full bg-line-strong" />
                ) : null}
              </span>
            );
          })}
        </div>
        <div className="flex gap-4 text-xs text-ink-3">
          <span className="flex items-center gap-1.5">
            <span className="size-2 rounded-[2px] bg-pass" aria-hidden />
            {t("done")} <span className="tabular-nums text-ink-2">{done}</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-2 rounded-[2px] bg-fail" aria-hidden />
            {t("failed")} <span className="tabular-nums text-ink-2">{failed}</span>
          </span>
        </div>
      </div>
    </section>
  );
}

function Errors({ errors }: { errors: Operations["errors"] }) {
  const t = useTranslations("operations");
  return (
    <section className={card}>
      <CardHeader title={t("errors")} hint={t("errorsHint")} />
      {errors.length ? (
        <ul className="divide-y divide-line">
          {errors.map((run) => (
            <li
              key={run.id}
              className="grid grid-cols-[14px_minmax(0,1fr)_auto] gap-x-3 px-4 py-2.5"
            >
              <StatusGlyph status="failed" className="mt-0.5" />
              <span className="min-w-0">
                <span className="block truncate text-[13px] font-medium text-ink">
                  {run.workflowName}
                </span>
                <span className="line-clamp-2 text-xs text-fail-ink">{run.error}</span>
              </span>
              <span className="text-xs tabular-nums text-ink-4">
                <When value={run.createdAt} />
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="flex items-center gap-2 px-4 py-6 text-[13px] text-ink-3">
          <StatusGlyph status="passed" />
          {t("noErrors")}
        </p>
      )}
    </section>
  );
}

/** Live operations: the model, the queue, every run in flight with its step, failures, throughput. */
export function ControlRoom() {
  const t = useTranslations("operations");
  const { data } = $api.useSuspenseQuery("get", "/v1/operations", undefined, {
    refetchInterval: LIVE_MS,
  });
  const platform = $api.useQuery("get", "/v1/platform/config", undefined, {
    refetchInterval: 15_000,
  }).data;
  const model =
    platform?.modelAvailable === true
      ? { text: t("modelAwake"), tone: "pass" as const }
      : platform?.modelAvailable === false
        ? { text: t("modelDown"), tone: "fail" as const }
        : { text: t("modelAsleep"), tone: "idle" as const };
  const integer = (v: number) => String(Math.round(v));
  const queryClient = useQueryClient();
  const recover = $api.useMutation("post", "/v1/operations/recover", {
    onSuccess: ({ failed }) => {
      toast.success(t("recovered", { count: failed.length }));
      void queryClient.invalidateQueries({ queryKey: ["get", "/v1/operations"] });
      void queryClient.invalidateQueries({ queryKey: ["get", "/v1/dashboard"] });
    },
    onError: (error) => toast.error(errorMessage(error, t("recoverFailed"))),
  });

  return (
    <div className="flex flex-col gap-4">
      <div className={cn(card, "grid grid-cols-2 divide-x divide-line md:grid-cols-5")}>
        <Figure
          label={t("model")}
          value={
            <>
              <Pulse tone={model.tone} />
              <span className="truncate text-[15px]">{model.text}</span>
            </>
          }
          foot={platform?.servedModel}
        />
        <Figure
          label={t("running")}
          value={
            <>
              <Pulse tone={data.queue.runningRuns ? "accent" : "idle"} />
              <AnimatedNumber value={data.queue.runningRuns} format={integer} />
            </>
          }
        />
        <Figure
          label={t("queued")}
          value={<AnimatedNumber value={data.queue.queuedRuns} format={integer} />}
        />
        <Figure
          label={t("stale")}
          value={<AnimatedNumber value={data.staleRuns} format={integer} />}
          tone={data.staleRuns ? "text-warn-ink" : undefined}
          foot={
            data.staleRuns ? (
              <Button
                variant="secondary"
                size="xs"
                className="mt-1"
                onClick={() => recover.mutate({})}
              >
                {t("recover")}
              </Button>
            ) : null
          }
        />
        <Figure
          label={t("median")}
          value={formatDurationMs(data.timing.medianMs)}
          foot={`${t("p95")} ${formatDurationMs(data.timing.p95Ms)}`}
        />
      </div>
      <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
        <InFlight runs={data.active} />
        <div className="flex flex-col gap-4">
          <Throughput hours={data.throughput} />
          <Errors errors={data.errors} />
        </div>
      </div>
    </div>
  );
}
