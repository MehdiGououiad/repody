"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

/** A document's Markdown transcription (GitHub-flavoured: tables, lists), styled by
 * `@tailwindcss/typography` with the app's colours. */
export function DocumentMarkdownPreview({ text, className }: { text: string; className?: string }) {
  if (!text.trim()) return null;
  return (
    <article
      className={cn(
        "prose prose-sm max-w-none dark:prose-invert",
        "prose-headings:text-on-surface prose-p:text-on-surface prose-strong:text-on-surface",
        "prose-a:text-primary prose-li:marker:text-primary prose-th:text-on-surface",
        "prose-table:block prose-table:overflow-x-auto prose-pre:bg-surface-container-low",
        className
      )}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </article>
  );
}
