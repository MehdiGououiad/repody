"use client";

import { useMemo, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import { normalizeOcrMarkdown, splitOcrMarkdownPages } from "@/lib/ocr-markdown/normalize";

const MARKDOWN_COMPONENTS = {
  h1: ({ children }: { children?: ReactNode }) => (
    <h2 className="text-lg font-bold text-on-surface mt-2 mb-2">{children}</h2>
  ),
  h2: ({ children }: { children?: ReactNode }) => (
    <h3 className="text-base font-semibold text-on-surface mt-4 mb-2 pb-1 border-b border-border/60">
      {children}
    </h3>
  ),
  h3: ({ children }: { children?: ReactNode }) => (
    <h4 className="text-sm font-semibold text-on-surface mt-3 mb-1.5 pl-2 border-l-2 border-primary/40">
      {children}
    </h4>
  ),
  h4: ({ children }: { children?: ReactNode }) => (
    <h5 className="text-sm font-medium text-on-surface mt-2 mb-1">{children}</h5>
  ),
  p: ({ children }: { children?: ReactNode }) => (
    <p className="text-sm text-on-surface leading-6 mb-3 last:mb-0">{children}</p>
  ),
  strong: ({ children }: { children?: ReactNode }) => (
    <strong className="font-semibold text-on-surface">{children}</strong>
  ),
  em: ({ children }: { children?: ReactNode }) => {
    const label = String(children ?? "");
    if (label.startsWith("Image:")) {
      return (
        <div className="my-3 rounded-lg border border-dashed border-border/80 bg-surface-container-lowest px-3 py-2 text-xs text-on-surface-variant">
          {label}
        </div>
      );
    }
    return <em className="italic">{children}</em>;
  },
  ul: ({ children }: { children?: ReactNode }) => (
    <ul className="my-2 space-y-1 list-disc pl-5 marker:text-primary">{children}</ul>
  ),
  ol: ({ children }: { children?: ReactNode }) => (
    <ol className="my-2 space-y-1 list-decimal pl-5 marker:text-primary">{children}</ol>
  ),
  li: ({ children }: { children?: ReactNode }) => (
    <li className="text-sm text-on-surface leading-6">{children}</li>
  ),
  blockquote: ({ children }: { children?: ReactNode }) => (
    <blockquote className="my-3 border-l-4 border-primary/30 pl-3 text-sm text-on-surface-variant italic">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-4 border-border/70" />,
  code: ({ className, children }: { className?: string; children?: ReactNode }) => {
    const isBlock = Boolean(className);
    if (isBlock) {
      return (
        <code className="block overflow-x-auto rounded-lg bg-surface-container-low px-3 py-2 text-[11px] font-mono text-on-surface">
          {children}
        </code>
      );
    }
    return (
      <code className="rounded bg-surface-container-low px-1.5 py-0.5 text-[11px] font-mono text-on-surface">
        {children}
      </code>
    );
  },
  pre: ({ children }: { children?: ReactNode }) => (
    <pre className="my-3 overflow-x-auto rounded-lg border border-border bg-surface-container-low p-3 text-[11px] leading-relaxed">
      {children}
    </pre>
  ),
  table: ({ children }: { children?: ReactNode }) => (
    <div className="overflow-x-auto rounded-xl border border-border my-4 shadow-sm bg-card">
      <table className="w-full text-xs border-collapse min-w-[320px]">{children}</table>
    </div>
  ),
  thead: ({ children }: { children?: ReactNode }) => (
    <thead className="bg-gradient-to-r from-accent-blue/10 to-surface-container-low">{children}</thead>
  ),
  tbody: ({ children }: { children?: ReactNode }) => <tbody>{children}</tbody>,
  tr: ({ children }: { children?: ReactNode }) => (
    <tr className="even:bg-surface-container-lowest/40">{children}</tr>
  ),
  th: ({ children }: { children?: ReactNode }) => (
    <th className="px-3 py-2.5 text-left font-semibold text-on-surface whitespace-nowrap border-b border-border">
      {children}
    </th>
  ),
  td: ({ children }: { children?: ReactNode }) => (
    <td className="px-3 py-2 text-on-surface-variant align-top border-b border-border/60">{children}</td>
  ),
};

export function DocumentMarkdownPreview({
  text,
  className,
  compact = false,
}: {
  text: string;
  className?: string;
  compact?: boolean;
}) {
  const sections = useMemo(() => splitOcrMarkdownPages(text), [text]);

  if (!sections.length) return null;

  return (
    <article className={cn("space-y-5 text-sm text-on-surface-variant leading-relaxed", className)}>
      {sections.map((section, index) => (
        <section
          key={section.header || `section-${index}`}
          className={cn(
            section.header &&
              "rounded-xl border border-border/70 bg-surface-container-lowest/60 overflow-hidden",
          )}
        >
          {section.header ? (
            <header className="px-4 py-2.5 border-b border-border/60 bg-gradient-to-r from-accent-blue/8 to-transparent">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-on-surface-variant">
                {section.header.replace(/^##\s*/, "")}
              </p>
            </header>
          ) : null}
          <div className={cn(section.header ? "px-4 py-3" : undefined, compact && "text-[13px]")}>
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS}>
              {section.body || section.header}
            </ReactMarkdown>
          </div>
        </section>
      ))}
    </article>
  );
}

export function DocumentTextPreviewPanel({
  text,
  label,
  className,
}: {
  text: string;
  label: string;
  className?: string;
}) {
  const normalized = useMemo(() => normalizeOcrMarkdown(text), [text]);

  return (
    <details className={cn("group rounded-xl border border-border/70 bg-card overflow-hidden", className)} open>
      <summary className="cursor-pointer list-none px-4 py-2.5 text-xs font-medium text-on-surface-variant bg-surface-container-low/60 hover:bg-surface-container-low transition-colors [&::-webkit-details-marker]:hidden">
        <span className="inline-flex items-center gap-2">
          <span className="text-on-surface-variant/60 group-open:rotate-90 transition-transform">▸</span>
          {label}
        </span>
      </summary>
      <div className="border-t border-border p-4 max-h-[min(70vh,560px)] overflow-y-auto">
        <DocumentMarkdownPreview text={normalized} compact />
      </div>
    </details>
  );
}
