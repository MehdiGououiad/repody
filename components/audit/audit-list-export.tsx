import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Audit } from "@/lib/types";

export function AuditListExport({
  audits,
  label,
}: {
  audits: Audit[];
  label: string;
}) {
  if (audits.length === 0) {
    return (
      <Button variant="outline" disabled>
        <Download className="h-4 w-4" />
        {label}
      </Button>
    );
  }

  return (
    <Button variant="outline" asChild>
      <a href="/exports/audits" download>
        <Download className="h-4 w-4" />
        {label}
      </a>
    </Button>
  );
}
