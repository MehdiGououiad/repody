"use client";

import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { DocumentPreview } from "./document-preview";
import { ExtractedDataGrid } from "./extracted-data-grid";
import { ComplianceRulesList } from "./compliance-rules-list";
import type { AuditDetail } from "@/lib/types";

export function AuditLayout({ audit }: { audit: AuditDetail }) {
  return (
    <ResizablePanelGroup orientation="horizontal" className="flex-1 min-h-0">
      <ResizablePanel defaultSize={32} minSize={20}>
        <DocumentPreview audit={audit} />
      </ResizablePanel>
      <ResizableHandle />
      <ResizablePanel defaultSize={34} minSize={22}>
        <ExtractedDataGrid audit={audit} />
      </ResizablePanel>
      <ResizableHandle />
      <ResizablePanel defaultSize={34} minSize={26}>
        <ComplianceRulesList audit={audit} />
      </ResizablePanel>
    </ResizablePanelGroup>
  );
}
