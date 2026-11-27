import { describe, expect, test } from "bun:test";
import {
  artifactImageUrl,
  groupFindingsByTier,
  normalizeBboxToPercent,
  sortFindingsBySeverity,
} from "./helpers";
import type { FraudFinding } from "./types";

describe("fraud helpers", () => {
  test("sortFindingsBySeverity and groupFindingsByTier order findings cleanly", () => {
    const sample: FraudFinding[] = [
      {
        detector: "pdf_structure",
        tier: 1,
        code: "LOW_1",
        severity: "low",
        title: "Low",
        detail: "Detail",
      },
      {
        detector: "pdf_revision_diff",
        tier: 1,
        code: "CRIT_1",
        severity: "critical",
        title: "Crit",
        detail: "Detail",
      },
      {
        detector: "visual_classical",
        tier: 3,
        code: "HIGH_3",
        severity: "high",
        title: "High",
        detail: "Detail",
      },
    ];

    const sorted = sortFindingsBySeverity(sample);
    expect(sorted.map((f) => f.code)).toEqual(["CRIT_1", "HIGH_3", "LOW_1"]);

    const grouped = groupFindingsByTier(sample);
    expect(grouped[1].map((f) => f.code)).toEqual(["CRIT_1", "LOW_1"]);
    expect(grouped[2]).toEqual([]);
    expect(grouped[3].map((f) => f.code)).toEqual(["HIGH_3"]);
  });

  test("normalizeBboxToPercent clamps normalized bounds and builds artifact URL", () => {
    expect(normalizeBboxToPercent([0.1, 0.25, 0.6, 0.75])).toEqual({
      left: "10.00%",
      top: "25.00%",
      width: "50.00%",
      height: "50.00%",
    });
    expect(artifactImageUrl("frd-1", "art-2")).toBe("/api/fraud/v1/analyses/frd-1/artifacts/art-2");
  });
});
