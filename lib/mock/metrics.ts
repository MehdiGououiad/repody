import type {
  KpiMetric,
  PerformancePoint,
  ViolationBreakdown,
} from "@/lib/types";

const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function series(base: number, spread: number): KpiMetric["series"] {
  return days.map((day, i) => ({
    day,
    value: Math.round(base + Math.sin((i + 1) * 0.9) * spread),
  }));
}

export const kpis: KpiMetric[] = [
  {
    id: "auditsWeek",
    label: "Audits this week",
    value: "342",
    rawValue: 342,
    delta: 14,
    deltaUnit: "percent",
    direction: "up",
    positive: true,
    series: series(48, 18),
    icon: "account_tree",
  },
  {
    id: "passRate",
    label: "Pass rate",
    value: "87.3%",
    rawValue: 0.873,
    delta: 1.2,
    deltaUnit: "percent",
    direction: "up",
    positive: true,
    series: series(87, 2),
    icon: "check_circle",
  },
  {
    id: "failures",
    label: "Rule failures",
    value: "45",
    rawValue: 45,
    delta: 5,
    deltaUnit: "absolute",
    direction: "up",
    positive: false,
    series: series(40, 10),
    icon: "gavel",
  },
  {
    id: "pendingReview",
    label: "Pending review",
    value: "8",
    rawValue: 8,
    delta: 3,
    deltaUnit: "absolute",
    direction: "down",
    positive: true,
    series: series(10, 4),
    icon: "timer",
  },
];

export const performanceSeries: PerformancePoint[] = [
  { day: "Mon", runs: 38, prevRuns: 32 },
  { day: "Tue", runs: 54, prevRuns: 41 },
  { day: "Wed", runs: 47, prevRuns: 50 },
  { day: "Thu", runs: 61, prevRuns: 55 },
  { day: "Fri", runs: 72, prevRuns: 63 },
  { day: "Sat", runs: 29, prevRuns: 24 },
  { day: "Sun", runs: 41, prevRuns: 35 },
];

export const violationBreakdown: ViolationBreakdown[] = [
  { type: "format", share: 42, color: "danger" },
  { type: "missing", share: 28, color: "warning" },
  { type: "logic", share: 18, color: "info" },
  { type: "other", share: 12, color: "neutral" },
];
