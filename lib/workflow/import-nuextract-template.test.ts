import { describe, expect, it } from "bun:test";
import type { Catalog } from "@/lib/types";
import { importNuextractTemplate } from "@/lib/workflow/import-nuextract-template";

const CATALOG: Catalog = {
  templateTypes: [
    { value: "number", group: "common", listable: true },
    { value: "string", group: "common", listable: true },
    { value: "email-address", group: "common", listable: true },
    { value: "enum", group: "structure", listable: false },
  ],
  defaultType: "verbatim-string",
  numberTypes: ["number"],
  orderedTypes: ["number"],
  tableType: "object-array",
  operatorsByType: {},
  presenceOperators: ["EXISTS", "IS_EMPTY"],
};

describe("NuExtract template import", () => {
  it("maps every constructor to a schema field", () => {
    const result = importNuextractTemplate(
      JSON.stringify({
        total: "number",
        contact: "email",
        tags: ["string"],
        currency: ["MAD", "EUR"],
        flags: [["A", "B"]],
        vendor: { name: "string" },
        lines: [{ label: "string", amount: "number" }],
        region: "region:FR",
        typo: "numbr",
      }),
      CATALOG
    );
    if (!result.ok) throw new Error(result.error);
    const types = Object.fromEntries(result.fields.map((f) => [f.name, f.templateType]));
    expect(types).toEqual({
      total: "number",
      contact: "email-address",
      tags: "string-list",
      currency: "enum",
      flags: "multi-enum",
      vendor: "object",
      lines: "object-array",
      region: "region:FR",
      typo: "verbatim-string", // an unknown type falls back instead of failing the save
    });
    const lines = result.fields.find((f) => f.name === "lines");
    expect(lines?.children.map((c) => c.name)).toEqual(["label", "amount"]);
  });

  it("explains what it cannot import", () => {
    expect(importNuextractTemplate("", CATALOG)).toEqual({ ok: false, error: "empty" });
    expect(importNuextractTemplate("{", CATALOG)).toEqual({ ok: false, error: "invalid_json" });
    expect(importNuextractTemplate("[]", CATALOG)).toEqual({ ok: false, error: "not_object" });
  });
});
