import { describe, expect, it } from "vitest";
import { readDifferences } from "./second-read";

describe("readDifferences", () => {
  it("gives a single value as the second read's", () => {
    expect(readDifferences(1317.24, 3117.24)).toEqual([{ kind: "value", value: 3117.24 }]);
    expect(readDifferences("APPT", null)).toEqual([{ kind: "value", value: null }]);
  });

  it("names the table cells that differ, not the whole table", () => {
    const first = [
      { description: "Revue", quantity: 2, unit_price: 2.5 },
      { description: "Sauce soja", quantity: 2, unit_price: 1.99 },
    ];
    const second = [
      { description: "revue", quantity: 2, unit_price: 2.5 }, // case only: the same
      { description: "Sauce soja", quantity: 2, unit_price: 1.9 },
    ];
    expect(readDifferences(first, second)).toEqual([
      { kind: "cell", row: 2, column: "unit_price", value: 1.9 },
    ]);
  });

  it("names the list items that differ", () => {
    expect(readDifferences([630, 280, 920], [630, 280, 220])).toEqual([
      { kind: "item", item: 3, value: 220 },
    ]);
  });

  it("says when the second read found another number of rows or items", () => {
    expect(readDifferences([{ a: 1 }], [{ a: 1 }, { a: 2 }])).toEqual([
      { kind: "rows", first: 1, second: 2 },
    ]);
    expect(readDifferences([1, 2, 3], [1, 2])).toEqual([{ kind: "items", first: 3, second: 2 }]);
  });

  it("reports a cell the second read left out as empty", () => {
    expect(readDifferences([{ a: 1, b: 2 }], [{ a: 1 }])).toEqual([
      { kind: "cell", row: 1, column: "b", value: null },
    ]);
  });
});
