import type { FraudFinding, FraudSeverity } from "./types";

const SEVERITY_RANK: Record<FraudSeverity, number> = {
  critical: 5,
  high: 4,
  medium: 3,
  low: 2,
  clean: 1,
};

export function sortFindingsBySeverity(findings: readonly FraudFinding[]): FraudFinding[] {
  return [...findings].sort((a, b) => SEVERITY_RANK[b.severity] - SEVERITY_RANK[a.severity]);
}

export function groupFindingsByTier(
  findings: readonly FraudFinding[],
): Record<1 | 2 | 3, FraudFinding[]> {
  const grouped: Record<1 | 2 | 3, FraudFinding[]> = { 1: [], 2: [], 3: [] };
  for (const item of sortFindingsBySeverity(findings)) {
    grouped[item.tier].push(item);
  }
  return grouped;
}

export function normalizeBboxToPercent(bbox: readonly [number, number, number, number]): {
  left: string;
  top: string;
  width: string;
  height: string;
} {
  const [x1, y1, x2, y2] = bbox;
  const clampedX1 = Math.max(0, Math.min(1, x1));
  const clampedY1 = Math.max(0, Math.min(1, y1));
  const clampedX2 = Math.max(clampedX1, Math.min(1, x2));
  const clampedY2 = Math.max(clampedY1, Math.min(1, y2));
  return {
    left: `${(clampedX1 * 100).toFixed(2)}%`,
    top: `${(clampedY1 * 100).toFixed(2)}%`,
    width: `${Math.max(1, (clampedX2 - clampedX1) * 100).toFixed(2)}%`,
    height: `${Math.max(1, (clampedY2 - clampedY1) * 100).toFixed(2)}%`,
  };
}

export function artifactImageUrl(analysisId: string, artifactId: string): string {
  return `/api/fraud/v1/analyses/${encodeURIComponent(analysisId)}/artifacts/${encodeURIComponent(artifactId)}`;
}
