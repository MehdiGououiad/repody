"use client";

import type { RunAuditField } from "@/lib/types";
import { formatExtractedFieldValue } from "@/lib/utils";

export function formatFieldValue(field: RunAuditField, locale: string): string {
  return field.extracted ? formatExtractedFieldValue(field.value, locale) : "—";
}
