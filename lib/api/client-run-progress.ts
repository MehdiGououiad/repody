import type { RunProgress, RunProgressStep } from "@/lib/api/run-poll";

export type ClientProgressStepId =
  | "save-workflow"
  | "upload-check"
  | "upload-reuse"
  | "upload-presign"
  | "upload-transfer"
  | "upload-confirm"
  | "start-run"
  | "poll-run";

const CLIENT_STEP_ORDER: ClientProgressStepId[] = [
  "save-workflow",
  "upload-check",
  "upload-reuse",
  "upload-presign",
  "upload-transfer",
  "upload-confirm",
  "start-run",
  "poll-run",
];

export type ClientStepLabels = Record<
  ClientProgressStepId,
  { label: string; pendingDetail?: string }
>;

export function buildClientProgressThrough(
  labels: ClientStepLabels,
  throughId: ClientProgressStepId,
  doneDetail?: string,
  activeId?: ClientProgressStepId
): RunProgress {
  const throughIndex = CLIENT_STEP_ORDER.indexOf(throughId);
  const activeIndex = activeId
    ? CLIENT_STEP_ORDER.indexOf(activeId)
    : Math.min(throughIndex + 1, CLIENT_STEP_ORDER.length - 1);
  const steps: RunProgressStep[] = CLIENT_STEP_ORDER.map((id, index) => {
    let status: RunProgressStep["status"] = "pending";
    if (index <= throughIndex) status = "done";
    else if (index === activeIndex) status = "active";
    const row = labels[id];
    return {
      id,
      label: row.label,
      status,
      detail:
        index === throughIndex
          ? doneDetail
          : index === activeIndex
            ? row.pendingDetail
            : undefined,
    };
  });
  return {
    currentIndex: Math.max(0, activeIndex),
    label: labels[CLIENT_STEP_ORDER[activeIndex]].label,
    steps,
  };
}

export function buildClientProgress(
  labels: ClientStepLabels,
  activeId: ClientProgressStepId,
  detail?: string,
  extra?: Partial<RunProgressStep>
): RunProgress {
  const activeIndex = CLIENT_STEP_ORDER.indexOf(activeId);
  const steps: RunProgressStep[] = CLIENT_STEP_ORDER.map((id, index) => {
    let status: RunProgressStep["status"] = "pending";
    if (index < activeIndex) status = "done";
    else if (index === activeIndex) status = "active";
    const row = labels[id];
    return {
      id,
      label: row.label,
      status,
      detail:
        index === activeIndex
          ? detail ?? row.pendingDetail
          : index < activeIndex
            ? undefined
            : row.pendingDetail,
      ...extra,
    };
  });
  return {
    currentIndex: Math.max(0, activeIndex),
    label: labels[activeId].label,
    steps,
  };
}

export function mergeServerProgress(
  client: RunProgress,
  server: RunProgress
): RunProgress {
  const clientDone = client.steps.map((s) => ({
    ...s,
    status: "done" as const,
    detail: s.detail,
  }));
  const serverSteps = server.steps.map((s) => ({
    ...s,
    id: `worker-${s.id}`,
  }));
  const steps = [...clientDone, ...serverSteps];
  const activeIdx = steps.findIndex((s) => s.status === "active");
  const cacheStep = serverSteps.find((s) => s.detail?.toLowerCase().includes("cache hit"));
  return {
    currentIndex: activeIdx >= 0 ? activeIdx : steps.length - 1,
    label: server.label || client.label,
    queuePosition: server.queuePosition,
    queueDepth: server.queueDepth,
    steps: cacheStep
      ? steps.map((s) =>
          s.id === cacheStep.id ? { ...s, cacheHit: true } : s
        )
      : steps,
  };
}
