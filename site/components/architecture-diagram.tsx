import { ArrowDown } from "lucide-react";
import type { Dict } from "@/content";

type Labels = Dict["architecture"]["diagram"];

function Box({
  title,
  tech,
  tone = "default",
}: {
  title: string;
  tech: string;
  tone?: "default" | "accent" | "muted";
}) {
  const style =
    tone === "accent"
      ? "bg-accent-wash shadow-[0_0_0_1px_var(--accent)]"
      : tone === "muted"
        ? "bg-canvas shadow-[0_0_0_1px_var(--line)]"
        : "bg-panel shadow-[0_0_0_1px_var(--line-strong)]";
  return (
    <div className={`flex flex-col gap-0.5 rounded-lg px-4 py-3 ${style}`}>
      <span className="text-sm font-semibold text-ink">{title}</span>
      <span className="font-mono text-xs text-ink-3">{tech}</span>
    </div>
  );
}

const Arrow = () => (
  <div className="flex justify-center py-2 text-ink-4" aria-hidden>
    <ArrowDown className="size-4" strokeWidth={1.5} />
  </div>
);

/** The components and how a document flows through them, in plain HTML (readable, themable). */
export function ArchitectureDiagram({ t, className = "" }: { t: Labels; className?: string }) {
  return (
    <figure
      className={`rounded-xl bg-canvas p-5 shadow-[0_0_0_1px_var(--line)] md:p-8 ${className}`}
      aria-label={`${t.user}, ${t.client} → ${t.web} → ${t.api} → ${t.workers} → ${t.model}; ${t.db}, ${t.storage}, ${t.idp}`}
    >
      <div className="grid grid-cols-2 gap-3">
        <Box title={t.user} tech={t.userTech} tone="muted" />
        <Box title={t.client} tech={t.clientTech} tone="muted" />
      </div>
      <Arrow />
      <div className="grid gap-3 md:grid-cols-[1fr_1fr_1fr]">
        <Box title={t.web} tech={t.webTech} />
        <Box title={t.api} tech={t.apiTech} />
        <Box title={t.idp} tech={t.idpTech} />
      </div>
      <Arrow />
      <div className="grid gap-3 md:grid-cols-[1fr_1fr_1fr]">
        <Box title={t.workers} tech={t.workersTech} />
        <Box title={t.db} tech={t.dbTech} />
        <Box title={t.storage} tech={t.storageTech} />
      </div>
      <Arrow />
      <Box title={t.model} tech={t.modelTech} tone="accent" />
    </figure>
  );
}
