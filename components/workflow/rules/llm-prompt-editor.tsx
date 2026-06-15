"use client";

import { useRef } from "react";
import { useTranslations } from "next-intl";

export function LlmPromptEditor({
  value,
  fields,
  onChange,
}: {
  value: string;
  fields: { label: string; token: string }[];
  onChange: (value: string) => void;
}) {
  const t = useTranslations("workflows.builder.rules");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const insertField = (token: string) => {
    const textarea = textareaRef.current;
    const reference = `@${token}`;
    if (!textarea) {
      onChange(`${value}${value ? " " : ""}${reference}`);
      return;
    }
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const needsSpace = start > 0 && !/\s/.test(value[start - 1] ?? "");
    const insertion = `${needsSpace ? " " : ""}${reference}`;
    onChange(`${value.slice(0, start)}${insertion}${value.slice(end)}`);
    requestAnimationFrame(() => {
      const cursor = start + insertion.length;
      textarea.focus();
      textarea.setSelectionRange(cursor, cursor);
    });
  };

  return (
    <div className="space-y-2">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={t("llmPromptPlaceholder")}
        aria-label={t("promptLabel")}
        rows={4}
        className="w-full rounded-lg border border-input bg-surface-container-low px-3 py-2 font-mono text-[12px] text-on-surface focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring resize-y"
      />
      <div className="rounded-lg border border-border/70 bg-surface-container-lowest px-3 py-2">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
          {t("availableFields")}
        </p>
        <div className="flex flex-wrap gap-1.5">
          {fields.length ? (
            fields.map((field) => (
              <button
                key={field.token}
                type="button"
                onClick={() => insertField(field.token)}
                className="rounded-md border border-accent-blue/30 bg-accent-blue/5 px-2 py-1 font-mono text-[11px] text-accent-blue transition-colors hover:bg-accent-blue/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                title={field.label}
              >
                @{field.token}
              </button>
            ))
          ) : (
            <span className="text-[11px] text-on-surface-variant">{t("noFieldsForPrompt")}</span>
          )}
        </div>
        <p className="mt-2 text-[11px] text-on-surface-variant">{t("fieldReferenceHint")}</p>
      </div>
    </div>
  );
}
