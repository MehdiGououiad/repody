"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

/** A document's Markdown transcription (GitHub-flavoured: tables, lists), styled by
 * `@tailwindcss/typography` with the app's colours. The model writes it from the document, so
 * images are dropped: a crafted document could otherwise make the browser load a remote URL. */
export function DocumentMarkdownPreview({ text, className }: { text: string; className?: string }) {
  if (!text.trim()) return null;
  return (
    <article
      className={cn(
        "prose prose-sm max-w-none dark:prose-invert",
        "prose-headings:text-ink prose-p:text-ink prose-strong:text-ink",
        "prose-a:text-ink prose-li:marker:text-ink prose-th:text-ink",
        "prose-table:block prose-table:overflow-x-auto prose-pre:bg-raised",
        className
      )}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]} disallowedElements={["img"]}>
        {text}
      </ReactMarkdown>
    </article>
  );
}
