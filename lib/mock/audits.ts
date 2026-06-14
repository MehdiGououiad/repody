import type { Audit, AuditDetail } from "@/lib/types";
import type { RunAuditDetail } from "@/lib/stores/audit-run-store";

const statuses: Audit["status"][] = ["passed", "failed", "warning", "running"];

function pickStatus(i: number): Audit["status"] {
  if (i % 11 === 0) return "running";
  if (i % 5 === 0) return "failed";
  if (i % 7 === 0) return "warning";
  return "passed";
}

const baseTime = Date.parse("2026-05-15T14:32:00Z");

export const audits: Audit[] = Array.from({ length: 48 }, (_, i) => {
  const status = pickStatus(i);
  const ts = new Date(baseTime - i * 1000 * 60 * 47).toISOString();
  return {
    id: `AUD-2026-${(9812 - i).toString().padStart(4, "0")}`,
    status,
    workflowId: i % 4 === 1 ? "wf-expense" : "wf-invoice-audit",
    workflowName:
      i % 4 === 1 ? "Expense Reconciliation" : "Invoice Audit Pipeline",
    entity: ["Acme Corp", "Globex Inc.", "Initech", "Wayne Industries", "Hooli"][i % 5],
    timestamp: ts,
    rows: status === "running" ? null : Math.floor(40000 + Math.random() * 2_100_000),
    failedRules: status === "failed" ? 1 + (i % 4) : 0,
  };
});

audits.unshift({
  id: "AUD-2023-8902",
  status: "failed",
  workflowId: "wf-invoice-audit",
  workflowName: "Invoice Audit Pipeline",
  entity: "Acme Corp",
  timestamp: "2023-10-24T14:32:00Z",
  rows: 1,
  failedRules: 1,
});

export const auditDetails: Record<string, AuditDetail> = {
  "AUD-2023-8902": {
    id: "AUD-2023-8902",
    status: "failed",
    workflowId: "wf-invoice-audit",
    workflowName: "Invoice Audit Pipeline",
    entity: "Acme Corp",
    timestamp: "2023-10-24T14:32:00Z",
    rows: 1,
    failedRules: 1,
    documentUrl: "/sample-invoice.svg",
    extractedFields: [
      {
        key: "vendor_name",
        value: "Acme Corp Ltd.",
        type: "string",
        bbox: { x: 6, y: 6, w: 38, h: 5 },
      },
      {
        key: "invoice_number",
        value: "INV-002418",
        type: "string",
        bbox: { x: 60, y: 8, w: 30, h: 5 },
      },
      {
        key: "invoice_date",
        value: "2023-10-15",
        type: "date",
        bbox: { x: 60, y: 14, w: 30, h: 5 },
      },
      {
        key: "line_item_1_qty",
        value: "450",
        type: "number",
        bbox: { x: 6, y: 32, w: 12, h: 5 },
      },
      {
        key: "line_item_1_rate",
        value: "$12.50",
        type: "currency",
        bbox: { x: 20, y: 32, w: 16, h: 5 },
      },
      {
        key: "subtotal_calculated",
        value: "$5,625.00",
        type: "calculated",
        bbox: { x: 70, y: 60, w: 22, h: 5 },
        failedRuleIds: ["r-math"],
      },
      {
        key: "tax_rate",
        value: "8.5%",
        type: "percent",
        bbox: { x: 70, y: 66, w: 22, h: 5 },
      },
      {
        key: "total_amount_extracted",
        value: "$6,200.00",
        type: "currency",
        bbox: { x: 70, y: 72, w: 22, h: 5 },
        failedRuleIds: ["r-math"],
      },
      {
        key: "payment_terms",
        value: "Net 30",
        type: "string",
        bbox: { x: 6, y: 84, w: 24, h: 5 },
      },
    ],
    rules: [
      {
        id: "r-vendor",
        name: "Vendor matching",
        kind: "logic",
        status: "passed",
        description:
          "Extracted vendor name perfectly matches canonical database entry.",
        severity: "reject",
      },
      {
        id: "r-math",
        name: "Mathematical integrity check",
        kind: "logic",
        status: "failed",
        description: "Subtotal calculation does not match provided line items.",
        detail:
          "The extracted total amount $6,200.00 deviates from the calculated subtotal + tax. Variance: $36.87.",
        expectedValue: "(450 × $12.50) = $5,625.00",
        actualValue: "$6,200.00",
        affectedFieldKeys: ["subtotal_calculated", "total_amount_extracted"],
        severity: "reject",
      },
      {
        id: "r-date",
        name: "Date validation",
        kind: "logic",
        status: "passed",
        description: "Invoice date is within current fiscal quarter.",
        severity: "flag",
      },
      {
        id: "r-format",
        name: "Mandatory fields present",
        kind: "logic",
        status: "passed",
        description: "All required fields extracted successfully.",
        severity: "reject",
      },
      {
        id: "r-late-fees",
        name: "Hidden late fees",
        kind: "llm",
        status: "passed",
        description: "No suspicious late-fee or penalty wording detected.",
        severity: "flag",
      },
    ],
  },
};

audits.slice(0, 12).forEach((a) => {
  if (auditDetails[a.id]) return;
  auditDetails[a.id] = {
    ...a,
    documentUrl: "/sample-invoice.svg",
    extractedFields: auditDetails["AUD-2023-8902"].extractedFields,
    rules: auditDetails["AUD-2023-8902"].rules.map((r) => ({
      ...r,
      status: a.status === "failed" ? r.status : "passed",
    })),
  };
});

const INVOICE_FIELDS: RunAuditDetail["documents"][number]["fields"] = [
  { key: "vendor_name",    description: "Legal name of the vendor",           value: "Acme Corp Ltd.", type: "string",   confidence: 0.97, extracted: true,  flagged: false },
  { key: "invoice_number", description: "Unique invoice identifier",           value: "INV-002418",    type: "string",   confidence: 0.99, extracted: true,  flagged: false },
  { key: "invoice_date",   description: "Date the invoice was issued",         value: "2026-05-14",    type: "date",     confidence: 0.99, extracted: true,  flagged: false },
  { key: "subtotal",       description: "Sum of line items before tax",        value: "5625.00",       type: "currency", confidence: 0.95, extracted: true,  flagged: false },
  { key: "tax",            description: "Total tax amount applied",             value: "478.13",        type: "currency", confidence: 0.94, extracted: true,  flagged: false },
  { key: "total_amount",   description: "Final amount due including taxes",     value: "6103.13",       type: "currency", confidence: 0.96, extracted: true,  flagged: false },
  { key: "po_number",      description: "Purchase order number referenced",    value: "PO-887412",     type: "string",   confidence: 0.98, extracted: true,  flagged: false },
  { key: "payment_terms",  description: "Payment terms as stated on invoice",  value: "Net 30",        type: "string",   confidence: 0.91, extracted: true,  flagged: false },
];

const EXPENSE_FIELDS: RunAuditDetail["documents"][number]["fields"] = [
  { key: "employee_name",  description: "Employee who submitted the expense",  value: "Sarah Mitchell",  type: "string",   confidence: 0.98, extracted: true,  flagged: false },
  { key: "report_date",    description: "Date of the expense report",          value: "2026-05-10",      type: "date",     confidence: 0.99, extracted: true,  flagged: false },
  { key: "category",       description: "Expense category",                    value: "Travel",          type: "string",   confidence: 0.95, extracted: true,  flagged: false },
  { key: "amount",         description: "Total amount claimed",                value: "842.50",          type: "currency", confidence: 0.97, extracted: true,  flagged: false },
  { key: "currency",       description: "Currency of the claim",               value: "USD",             type: "string",   confidence: 0.99, extracted: true,  flagged: false },
  { key: "approved_by",    description: "Manager who approved the claim",      value: "James Carter",    type: "string",   confidence: 0.88, extracted: true,  flagged: false },
  { key: "cost_center",    description: "Cost center code",                    value: "CC-4421",         type: "string",   confidence: 0.93, extracted: true,  flagged: false },
];

function makeRules(status: Audit["status"], failedRules: number): RunAuditDetail["ruleResults"] {
  const allPass = status === "passed";
  const rules: RunAuditDetail["ruleResults"] = [
    {
      id: "r-total-check",
      name: "Total amount validation",
      kind: "logic",
      scope: "intra",
      status: allPass || failedRules === 0 ? "passed" : "failed",
      severity: "reject",
      expression: "subtotal + tax == total_amount",
      affectedFields: ["subtotal", "tax", "total_amount"],
      detail: allPass || failedRules === 0
        ? "All conditions satisfied on the extracted values."
        : "Computed subtotal + tax does not match the declared total. Variance detected.",
      expectedValue: allPass || failedRules === 0 ? undefined : "$6,103.13",
      actualValue:   allPass || failedRules === 0 ? undefined : "$6,200.00",
    },
    {
      id: "r-fields-present",
      name: "Mandatory fields present",
      kind: "logic",
      scope: "intra",
      status: "passed",
      severity: "reject",
      expression: "vendor_name EXISTS AND invoice_number EXISTS",
      affectedFields: ["vendor_name", "invoice_number"],
      detail: "All required fields extracted successfully.",
    },
    {
      id: "r-llm-fees",
      name: "Hidden charges check",
      kind: "llm",
      scope: "intra",
      status: status === "warning" ? "failed" : "passed",
      severity: "flag",
      expression: "Flag if the document contains hidden fees or penalty charges.",
      affectedFields: [],
      detail: status === "warning"
        ? "LLM detected a potential penalty clause in the payment terms section."
        : "LLM evaluator found no hidden fees or penalty charges.",
    },
    {
      id: "r-date-range",
      name: "Date within fiscal year",
      kind: "logic",
      scope: "intra",
      status: "passed",
      severity: "flag",
      expression: "invoice_date >= fiscal_year_start",
      affectedFields: ["invoice_date"],
      detail: "Date is within the current fiscal year.",
    },
  ];

  // Tag affected fields on failed rules
  const failedKeys = new Set(rules.filter(r => r.status === "failed").flatMap(r => r.affectedFields));
  return rules;
}

export function synthesizeRunAudit(audit: Audit): RunAuditDetail {
  const isExpense = audit.workflowId === "wf-expense";
  const fields = isExpense ? EXPENSE_FIELDS : INVOICE_FIELDS;
  const ruleResults = makeRules(audit.status, audit.failedRules ?? 0);
  const failedKeys = new Set(ruleResults.filter(r => r.status === "failed").flatMap(r => r.affectedFields));
  const taggedFields = fields.map(f => ({ ...f, flagged: failedKeys.has(f.key) }));

  const passed = ruleResults.filter(r => r.status === "passed").length;
  const failed = ruleResults.filter(r => r.status === "failed").length;

  return {
    id: audit.id,
    workflowId: audit.workflowId,
    workflowName: audit.workflowName,
    status: audit.status === "running" ? "passed" : audit.status as "passed" | "failed" | "warning",
    source: "api",
    createdAt: audit.timestamp,
    documents: [
      {
        id: "doc-main",
        documentType: isExpense ? "Expense Report" : "Invoice",
        fields: taggedFields,
      },
    ],
    ruleResults,
    summary: {
      total: ruleResults.length,
      passed,
      failed,
      fieldsExtracted: taggedFields.filter(f => f.extracted).length,
    },
  };
}
