"use client";

import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { SectionHeading } from "@/components/layout/section-heading";
import { useUnifiedModelsCatalog } from "@/lib/hooks/use-catalog-queries";
import type { DocumentDef } from "@/lib/types";
import { cn, shortId } from "@/lib/utils";
import { DocumentCard } from "./document-card";

export function DocumentsSection({
  documents,
  onChange,
}: {
  documents: DocumentDef[];
  onChange: (docs: DocumentDef[]) => void;
}) {
  const t = useTranslations("workflows.builder");
  const catalogQuery = useUnifiedModelsCatalog();

  const modelStatus = {
    model: catalogQuery.data?.models[0],
    loaded: catalogQuery.isFetched,
    error: catalogQuery.isError,
    onRetry: () => void catalogQuery.refetch(),
  };

  const updateDoc = (id: string, patch: Partial<DocumentDef>) =>
    onChange(documents.map((d) => (d.id === id ? { ...d, ...patch } : d)));
  const removeDoc = (id: string) => onChange(documents.filter((d) => d.id !== id));
  const addDoc = () =>
    onChange([
      ...documents,
      {
        id: `doc${shortId()}`,
        documentType: "",
        schema: [],
      },
    ]);

  return (
    <div className="space-y-4">
      <SectionHeading
        title={t("docSource.title")}
        description={t("docSource.hint")}
        eyebrow="Schema"
      />

      <div className="space-y-3">
        {documents.map((doc, i) => (
          <DocumentCard
            key={doc.id}
            doc={doc}
            index={i}
            canRemove={documents.length > 1}
            onChange={(patch) => updateDoc(doc.id, patch)}
            onRemove={() => removeDoc(doc.id)}
            modelStatus={modelStatus}
          />
        ))}
      </div>

      <button
        type="button"
        onClick={addDoc}
        className={cn(
          "w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl border-2 border-dashed border-accent-blue/30",
          "text-sm text-on-surface-variant hover:border-accent-blue/60 hover:text-on-surface hover:bg-accent-blue/5 transition-[border-color,color,background-color]"
        )}
      >
        <Plus className="h-4 w-4" />
        {t("docSource.addDocument")}
      </button>
    </div>
  );
}
