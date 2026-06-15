"use client";

import { useTranslations } from "next-intl";
import { GripVertical, Plus, Sparkles, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { SchemaField } from "@/lib/types";
import { shortId } from "@/lib/utils";

export function SchemaTable({
  schema,
  onChange,
  t,
}: {
  schema: SchemaField[];
  onChange: (schema: SchemaField[]) => void;
  t: ReturnType<typeof useTranslations>;
}) {
  const tCommon = useTranslations("common");
  const update = (id: string, patch: Partial<SchemaField>) =>
    onChange(schema.map((f) => (f.id === id ? { ...f, ...patch } : f)));
  const remove = (id: string) => onChange(schema.filter((f) => f.id !== id));
  const add = () =>
    onChange([...schema, { id: `f${shortId()}`, name: "", description: "" }]);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-4">
        <p className="text-[11px] text-on-surface-variant flex items-center gap-1.5">
          <Sparkles className="h-3 w-3 text-accent-blue shrink-0" />
          {t("schema.description")}
        </p>
        <Button variant="ghost" size="sm" className="h-7 text-xs shrink-0" onClick={add}>
          <Plus className="h-3 w-3" />
          {t("schema.addField")}
        </Button>
      </div>

      {schema.length === 0 ? (
        <button
          type="button"
          onClick={add}
          className="w-full border-2 border-dashed border-outline-variant rounded-lg py-8 text-center text-xs text-on-surface-variant hover:border-primary/40 hover:bg-primary/5 transition-colors"
        >
          {t("schema.empty")}
        </button>
      ) : (
        <div className="border border-border rounded-lg overflow-hidden">
          <div className="grid grid-cols-[1fr_2fr_32px] gap-0 bg-surface-container-low border-b border-border">
            <div className="px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant border-r border-border">
              {t("schema.name")}
            </div>
            <div className="px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
              {t("schema.intent")}
            </div>
          </div>
          <div className="divide-y divide-border">
            {schema.map((f) => (
              <div
                key={f.id}
                className="grid grid-cols-[1fr_2fr_32px] group hover:bg-surface-bright transition-colors"
              >
                <div className="flex items-center gap-1 px-2 border-r border-border">
                  <GripVertical className="h-3 w-3 text-outline-variant opacity-0 group-hover:opacity-60 cursor-grab shrink-0" />
                  <Input
                    value={f.name}
                    onChange={(e) => update(f.id, { name: e.target.value })}
                    placeholder={t("schema.namePlaceholder")}
                    className="font-mono text-xs h-9 border-transparent bg-transparent shadow-none focus-visible:bg-card focus-visible:border-input"
                  />
                </div>
                <div className="px-2 flex items-center">
                  <Input
                    value={f.description}
                    onChange={(e) => update(f.id, { description: e.target.value })}
                    placeholder={t("schema.descriptionPlaceholder")}
                    className="text-xs h-9 border-transparent bg-transparent shadow-none focus-visible:bg-card focus-visible:border-input"
                  />
                </div>
                <div className="flex items-center justify-center">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-outline hover:text-danger opacity-0 group-hover:opacity-100"
                    onClick={() => remove(f.id)}
                    aria-label={tCommon("delete")}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
