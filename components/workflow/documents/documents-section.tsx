"use client";

import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { SectionHeading } from "@/components/layout/section-heading";
import { Button } from "@/components/ui/button";
import type { DocumentDef } from "@/lib/types";
import { newDocument } from "@/lib/workflow/new-items";
import { DocumentCard } from "./document-card";

/** The documents a workflow receives, each with the fields to read from it. */
export function DocumentsSection({
  documents,
  onChange,
}: {
  documents: DocumentDef[];
  onChange: (docs: DocumentDef[]) => void;
}) {
  const t = useTranslations("workflows.builder");
  const updateDoc = (id: string, patch: Partial<DocumentDef>) =>
    onChange(documents.map((d) => (d.id === id ? { ...d, ...patch } : d)));

  return (
    <div className="flex flex-col gap-8">
      <SectionHeading title={t("docSource.title")} description={t("docSource.hint")} />
      <div className="flex flex-col gap-12">
        {documents.map((doc, i) => (
          <DocumentCard
            key={doc.id}
            doc={doc}
            index={i}
            canRemove={documents.length > 1}
            onChange={(patch) => updateDoc(doc.id, patch)}
            onRemove={() => onChange(documents.filter((d) => d.id !== doc.id))}
          />
        ))}
      </div>
      <Button
        variant="secondary"
        className="self-start"
        onClick={() => onChange([...documents, newDocument()])}
      >
        <Plus />
        {t("docSource.addDocument")}
      </Button>
    </div>
  );
}
