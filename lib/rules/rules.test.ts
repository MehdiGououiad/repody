import { describe, expect, it } from "vitest";
import { conditionFields, isTouched } from "@/lib/rules/conditions";
import { fieldOptions, tableOptions, typeOf } from "@/lib/rules/document-fields";
import { fieldKey } from "@/lib/rules/field-key";
import { literalInputKind, operatorsFor } from "@/lib/rules/operators";
import type { Catalog, DocumentDef, RuleCondition } from "@/lib/types";
import { newCondition, newDocument, newSchemaField } from "@/lib/workflow/new-items";

const CATALOG: Catalog = {
  templateTypes: [
    { value: "number", group: "common", listable: true },
    { value: "date", group: "common", listable: true },
    { value: "verbatim-string", group: "common", listable: true },
    { value: "object-array", group: "structure", listable: false },
  ],
  defaultType: "verbatim-string",
  numberTypes: ["integer", "number"],
  orderedTypes: ["date", "date-time", "integer", "number", "time"],
  tableType: "object-array",
  operatorsByType: {
    number: ["==", "!=", "IN", "NOT_IN", ">", ">=", "<", "<=", "EXISTS", "IS_EMPTY"],
    date: ["==", "!=", "IN", "NOT_IN", ">", ">=", "<", "<=", "EXISTS", "IS_EMPTY"],
    "verbatim-string": ["==", "!=", "IN", "NOT_IN", "EXISTS", "IS_EMPTY"],
    "verbatim-string-list": ["EXISTS", "IS_EMPTY"],
  },
  presenceOperators: ["EXISTS", "IS_EMPTY"],
};

function invoice(type = "Invoice"): DocumentDef {
  return {
    ...newDocument(),
    documentType: type,
    schema: [
      newSchemaField({ name: "Total Amount", templateType: "number" }),
      newSchemaField({
        name: "Lines",
        templateType: "object-array",
        children: [
          newSchemaField({ name: "Unit Price", templateType: "number" }),
          newSchemaField({ name: "Label" }),
        ],
      }),
    ],
  };
}

describe("field keys", () => {
  it("match the API's field_key", () => {
    expect(fieldKey("Total  Amount")).toBe("total_amount");
    expect(fieldKey(" Invoice.Total ")).toBe("invoice__total");
  });
});

describe("rule field options", () => {
  it("name fields as written, qualified by document type with several documents", () => {
    expect(fieldOptions([invoice()], []).map((f) => f.name)).toEqual(["Total Amount", "Lines"]);
    const two = [invoice(), invoice("Purchase Order")];
    expect(fieldOptions(two, []).map((f) => f.name)).toContain("Purchase Order.Total Amount");
  });

  it("keep table columns as the schema spells them", () => {
    const [table] = tableOptions([invoice()], [], CATALOG);
    expect(table?.columns.map((c) => c.name)).toEqual(["Unit Price", "Label"]);
  });

  it("find a field's type whatever its spelling", () => {
    expect(typeOf("total_amount", fieldOptions([invoice()], []))).toBe("number");
  });
});

describe("conditions", () => {
  it("list the fields they read", () => {
    const condition: RuleCondition = {
      id: "c",
      left: {
        kind: "arithmetic",
        op: "+",
        left: { kind: "field", field: "ht" },
        right: { kind: "field", field: "tva" },
      },
      operator: "==",
      right: { kind: "field", field: "ttc" },
    };
    expect(conditionFields(condition)).toEqual(["ht", "tva", "ttc"]);
    expect(isTouched(newCondition())).toBe(false);
    expect(isTouched(condition)).toBe(true);
  });
});

describe("operators", () => {
  it("offer what the API accepts for each type", () => {
    const ops = (type?: string) => operatorsFor(type, CATALOG).map((o) => o.value);
    expect(ops("number")).toContain(">");
    expect(ops("verbatim-string")).not.toContain(">");
    expect(ops("date")).toContain("IN");
    expect(ops("verbatim-string-list")).toEqual(["EXISTS", "IS_EMPTY"]);
    expect(ops("region:FR")).toEqual(ops("verbatim-string")); // unlisted: the default's
    expect(literalInputKind("integer", CATALOG)).toBe("number");
    expect(literalInputKind("date-time", CATALOG)).toBe("datetime-local");
  });
});
